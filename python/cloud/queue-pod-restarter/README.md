# Queue Pod Restarter

Detects stuck Azure Storage Queues, purges them and evicts the K3s pods that consume them.

## Problem
Azure Storage Queues have no dead-letter queue. A poison message that keeps failing is redelivered forever and blocks the consumer pod running on K3s. Operators currently clear the queue and restart the pod by hand.

## Prerequisites
- Python 3.12 and `requests`.
- `AZURE_STORAGE_ACCOUNT`: storage account name.
- `AZURE_STORAGE_SAS_TOKEN`: SAS token for the queues listed in the mapping file, with read (`r`) permission for peeking and delete (`d`) permission for clearing messages.
- `K8S_API_SERVER`: Kubernetes API URL, for example `https://<k3s-host>:6443`.
- `K8S_TOKEN`: bearer token of a service account.
- `K8S_CA_CERT` (optional): path to the cluster CA bundle. K3s uses a self-signed CA, so set it unless the CA is in the system store.
- RBAC for the service account: `list` on `pods` and `create` on `pods/eviction` in each target namespace.
- Mapping file: JSON object of queue name to `namespace` and `label_selector` of the consumer pods.
- A queue is stuck when one of its first 32 messages has a dequeue count of at least `--max-dequeue-count` (default 5) or is older than `--max-age-minutes` (default 60).
- Purging deletes every message in the queue. Flagged message IDs are printed first.
- Eviction respects PodDisruptionBudgets and fails loudly when one blocks it.

## Usage
```
cat > queues.json <<'EOF'
{"orders": {"namespace": "<namespace>", "label_selector": "app=<consumer-label>"}}
EOF

python queue_pod_restarter.py --mapping queues.json
python queue_pod_restarter.py --mapping queues.json --apply
```
