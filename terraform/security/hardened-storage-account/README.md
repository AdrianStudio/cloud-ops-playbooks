# Hardened Azure Storage Account

OpenTofu module that creates an Azure Storage Account with secure defaults and one private blob container.

## Problem
Teams create storage accounts by hand or with inconsistent settings. Old TLS versions, anonymous blob access and open network rules stay enabled, and an accidental delete cannot be undone. Security and platform teams have no single reviewed baseline to reuse.

## Prerequisites
- `name`: globally unique storage account name, 3 to 24 lowercase letters and digits.
- `resource_group_name`: existing resource group that holds the account.
- `location`: Azure region.
- `ip_allowlist`: optional list of public IPv4 addresses or CIDR ranges (default `[]`). Azure rejects /31 and /32 ranges and private ranges.
- `container_name`: optional private container name (default `private`).
- `soft_delete_retention_days`: optional, 1 to 365 (default `14`), applied to blobs and containers.
- `account_replication_type`: optional (default `GRS`).
- `tags`: optional map of tags.
- Azure permissions: Contributor on the resource group, or Storage Account Contributor, for the identity running OpenTofu.
- The caller configures the `azurerm` provider (`features {}` and credentials, for example `ARM_SUBSCRIPTION_ID`) and owns the resource group.
- Runtime: OpenTofu 1.6 or later, `hashicorp/azurerm` 4.20 or later and below 5.0.
- Network: the host running `tofu apply` must be in `ip_allowlist`, otherwise the container call is blocked by the Deny rule.

## Usage
```hcl
module "storage" {
  source = "./terraform/security/hardened-storage-account"

  name                = "<storageaccountname>"
  resource_group_name = "<resource-group-name>"
  location            = "<azure-region>"
  ip_allowlist        = ["<203.0.113.0/24>"]
}
```

```sh
tofu init
tofu plan -out storage.tfplan
tofu apply storage.tfplan
```

## Outputs
- `storage_account_id`: resource ID of the account.
- `storage_account_name`: account name.
- `primary_blob_endpoint`: primary blob endpoint URL.
