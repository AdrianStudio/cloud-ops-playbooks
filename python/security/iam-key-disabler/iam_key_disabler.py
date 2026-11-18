"""Report and optionally deactivate IAM access keys created inside a lookback window.

Required environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
Optional: AWS_SESSION_TOKEN.

Usage:
    python iam_key_disabler.py --lookback-hours 72
    python iam_key_disabler.py --lookback-hours 72 --exclude-user ci-deployer --apply
"""

import argparse
import hashlib
import hmac
import os
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

IAM_ENDPOINT = "https://iam.amazonaws.com/"
IAM_HOST = "iam.amazonaws.com"
IAM_REGION = "us-east-1"
IAM_API_VERSION = "2010-05-08"
IAM_XML_NAMESPACE = "{https://iam.amazonaws.com/doc/2010-05-08/}"
REQUEST_TIMEOUT_SECONDS = 30


def call_iam(action: str, action_params: dict[str, str]) -> ElementTree.Element:
    access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]

    params = {"Action": action, "Version": IAM_API_VERSION, **action_params}
    body = urlencode(sorted(params.items()))

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    signed_header_values = {
        "content-type": "application/x-www-form-urlencoded; charset=utf-8",
        "host": IAM_HOST,
        "x-amz-date": amz_date,
    }
    if "AWS_SESSION_TOKEN" in os.environ:
        signed_header_values["x-amz-security-token"] = os.environ["AWS_SESSION_TOKEN"]

    signed_headers = ";".join(sorted(signed_header_values))
    canonical_headers = "".join(
        f"{name}:{signed_header_values[name]}\n" for name in sorted(signed_header_values)
    )
    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    credential_scope = f"{date_stamp}/{IAM_REGION}/iam/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    signing_key = hmac.new(
        f"AWS4{secret_access_key}".encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256
    ).digest()
    signing_key = hmac.new(signing_key, IAM_REGION.encode("utf-8"), hashlib.sha256).digest()
    signing_key = hmac.new(signing_key, b"iam", hashlib.sha256).digest()
    signing_key = hmac.new(signing_key, b"aws4_request", hashlib.sha256).digest()
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    request_headers = {
        "Content-Type": signed_header_values["content-type"],
        "X-Amz-Date": amz_date,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }
    if "x-amz-security-token" in signed_header_values:
        request_headers["X-Amz-Security-Token"] = signed_header_values["x-amz-security-token"]

    response = requests.post(
        IAM_ENDPOINT, data=body, headers=request_headers, timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return ElementTree.fromstring(response.content)


def list_iam_members(
    action: str, action_params: dict[str, str], container_tag: str
) -> list[ElementTree.Element]:
    members = []
    page_params = dict(action_params)
    while True:
        root = call_iam(action, page_params)
        result = root.find(f"{IAM_XML_NAMESPACE}{action}Result")
        container = result.find(f"{IAM_XML_NAMESPACE}{container_tag}")
        members.extend(container.findall(f"{IAM_XML_NAMESPACE}member"))
        if result.find(f"{IAM_XML_NAMESPACE}IsTruncated").text != "true":
            return members
        page_params["Marker"] = result.find(f"{IAM_XML_NAMESPACE}Marker").text


def member_text(member: ElementTree.Element, tag: str) -> str:
    return member.find(f"{IAM_XML_NAMESPACE}{tag}").text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--lookback-hours",
        type=int,
        required=True,
        help="flag users and access keys created within this many hours",
    )
    parser.add_argument(
        "--exclude-user",
        action="append",
        default=[],
        help="IAM user name to skip, can be repeated",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="set flagged Active access keys to Inactive (default is report only)",
    )
    arguments = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=arguments.lookback_hours)
    iam_users = list_iam_members("ListUsers", {}, "Users")

    recent_user_names = []
    recent_access_keys = []
    for iam_user in iam_users:
        user_name = member_text(iam_user, "UserName")
        if user_name in arguments.exclude_user:
            continue

        if datetime.fromisoformat(member_text(iam_user, "CreateDate")) >= cutoff:
            recent_user_names.append(user_name)

        access_keys = list_iam_members(
            "ListAccessKeys", {"UserName": user_name}, "AccessKeyMetadata"
        )
        for access_key in access_keys:
            created_at = datetime.fromisoformat(member_text(access_key, "CreateDate"))
            if created_at >= cutoff:
                recent_access_keys.append(
                    (user_name, member_text(access_key, "AccessKeyId"),
                     member_text(access_key, "Status"), created_at)
                )

    for user_name in recent_user_names:
        print(f"RECENT USER  {user_name}")

    for user_name, access_key_id, status, created_at in recent_access_keys:
        print(f"RECENT KEY   {user_name} {access_key_id} status={status} created={created_at.isoformat()}")
        if status != "Active":
            continue
        if arguments.apply:
            call_iam(
                "UpdateAccessKey",
                {"UserName": user_name, "AccessKeyId": access_key_id, "Status": "Inactive"},
            )
            print(f"DEACTIVATED  {access_key_id}")
        else:
            print(f"WOULD DEACTIVATE  {access_key_id}")

    print(
        f"{len(recent_user_names)} recent users, {len(recent_access_keys)} recent access keys "
        f"in the last {arguments.lookback_hours} hours"
    )


if __name__ == "__main__":
    main()
