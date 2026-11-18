"""Purge stuck Azure Storage Queues and evict the K3s pods that consume them.

Storage Queues have no dead-letter queue, so a queue counts as stuck when one of
the first 32 messages has a high dequeue count or has waited too long.

Required environment variables:
    AZURE_STORAGE_ACCOUNT    storage account name
    AZURE_STORAGE_SAS_TOKEN  SAS token with read and delete permissions on the queues
    K8S_API_SERVER           Kubernetes API URL, for example https://<k3s-host>:6443
    K8S_TOKEN                service account bearer token
Optional environment variables:
    K8S_CA_CERT              path to the cluster CA bundle (default: system CA store)

Usage:
    python queue_pod_restarter.py --mapping queues.json
    python queue_pod_restarter.py --mapping queues.json --apply
"""
import argparse
import json
import os
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl

import requests

REQUEST_TIMEOUT_SECONDS = 30
QUEUE_API_VERSION = "2020-10-02"
PEEK_MESSAGE_COUNT = 32


def find_stuck_messages(queue_url: str, sas_params: dict, max_dequeue_count: int, max_age: timedelta) -> list[dict]:
    response = requests.get(
        f"{queue_url}/messages",
        params={**sas_params, "peekonly": "true", "numofmessages": str(PEEK_MESSAGE_COUNT)},
        headers={"x-ms-version": QUEUE_API_VERSION},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    now = datetime.now(timezone.utc)
    stuck_messages = []
    for message in ElementTree.fromstring(response.content).findall("QueueMessage"):
        dequeue_count = int(message.find("DequeueCount").text)
        inserted_at = parsedate_to_datetime(message.find("InsertionTime").text)
        if dequeue_count >= max_dequeue_count or now - inserted_at > max_age:
            stuck_messages.append({
                "message_id": message.find("MessageId").text,
                "dequeue_count": dequeue_count,
                "age": now - inserted_at,
            })
    return stuck_messages


def purge_queue(queue_url: str, sas_params: dict) -> None:
    response = requests.delete(
        f"{queue_url}/messages",
        params=sas_params,
        headers={"x-ms-version": QUEUE_API_VERSION},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def list_consumer_pod_names(session: requests.Session, api_server: str, namespace: str, label_selector: str) -> list[str]:
    response = session.get(
        f"{api_server}/api/v1/namespaces/{namespace}/pods",
        params={"labelSelector": label_selector},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return [pod["metadata"]["name"] for pod in response.json()["items"]]


def evict_pod(session: requests.Session, api_server: str, namespace: str, pod_name: str) -> None:
    eviction = {
        "apiVersion": "policy/v1",
        "kind": "Eviction",
        "metadata": {"name": pod_name, "namespace": namespace},
    }
    response = session.post(
        f"{api_server}/api/v1/namespaces/{namespace}/pods/{pod_name}/eviction",
        json=eviction,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mapping", required=True,
                        help="JSON file: queue name -> {namespace, label_selector} of its consumer pods")
    parser.add_argument("--max-dequeue-count", type=int, default=5,
                        help="dequeue count at which a message is considered poisoned")
    parser.add_argument("--max-age-minutes", type=int, default=60,
                        help="message age in minutes at which a queue is considered stuck")
    parser.add_argument("--apply", action="store_true",
                        help="purge the stuck queues and evict their consumer pods")
    args = parser.parse_args()

    with open(args.mapping, encoding="utf-8") as mapping_file:
        queue_targets = json.load(mapping_file)

    queue_endpoint = f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.queue.core.windows.net"
    sas_params = dict(parse_qsl(os.environ["AZURE_STORAGE_SAS_TOKEN"].lstrip("?")))
    api_server = os.environ["K8S_API_SERVER"].rstrip("/")

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {os.environ['K8S_TOKEN']}"
    if "K8S_CA_CERT" in os.environ:
        session.verify = os.environ["K8S_CA_CERT"]

    max_age = timedelta(minutes=args.max_age_minutes)
    for queue_name, target in queue_targets.items():
        queue_url = f"{queue_endpoint}/{queue_name}"
        stuck_messages = find_stuck_messages(queue_url, sas_params, args.max_dequeue_count, max_age)
        if not stuck_messages:
            print(f"{queue_name}: healthy")
            continue

        print(f"{queue_name}: {len(stuck_messages)} stuck message(s) in the first {PEEK_MESSAGE_COUNT}")
        for message in stuck_messages:
            print(f"  id={message['message_id']} dequeue_count={message['dequeue_count']} age={message['age']}")

        namespace = target["namespace"]
        pod_names = list_consumer_pod_names(session, api_server, namespace, target["label_selector"])
        if not args.apply:
            print(f"  would purge queue {queue_name} and evict pods {pod_names} in namespace {namespace}")
            continue

        purge_queue(queue_url, sas_params)
        print(f"  purged queue {queue_name}")
        for pod_name in pod_names:
            evict_pod(session, api_server, namespace, pod_name)
            print(f"  evicted pod {namespace}/{pod_name}")


if __name__ == "__main__":
    main()
