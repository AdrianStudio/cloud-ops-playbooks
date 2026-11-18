# IAM Key Disabler

Lists IAM users and access keys created inside a lookback window and, on request, sets the active keys to Inactive.

## Problem
After an AWS account compromise, attackers create new IAM users and access keys to keep access. Responders have to find these by hand in the console while the incident is running. Missed keys let the attacker back in after credentials are rotated.

## Prerequisites
- Python 3.12 and `requests` (no AWS SDK needed, requests are signed with SigV4 in the script).
- `AWS_ACCESS_KEY_ID`: access key ID of the responder identity.
- `AWS_SECRET_ACCESS_KEY`: secret key of the responder identity.
- `AWS_SESSION_TOKEN`: optional, only needed for temporary credentials.
- IAM permissions for report mode: `iam:ListUsers`, `iam:ListAccessKeys`.
- Additional IAM permission for `--apply`: `iam:UpdateAccessKey`.
- Keys are only deactivated, never deleted. Reactivate a key with `aws iam update-access-key --status Active` if it was flagged by mistake.

## Usage
```
# Report only: lists recent users and keys, prints what would be deactivated
python iam_key_disabler.py --lookback-hours 72 --exclude-user <trusted-user>

# Deactivate the flagged Active keys
python iam_key_disabler.py --lookback-hours 72 --exclude-user <trusted-user> --apply
```
