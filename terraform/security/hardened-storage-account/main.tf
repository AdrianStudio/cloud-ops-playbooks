# Purpose: hardened Azure Storage Account with a private blob container.
# Inputs: name, resource_group_name, location (required); ip_allowlist,
# container_name, soft_delete_retention_days, account_replication_type, tags (optional).
# Usage: call as a module from a root configuration that configures the azurerm
# provider and owns the resource group, then run tofu init, plan and apply.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.20.0, < 5.0.0"
    }
  }
}

variable "name" {
  description = "Storage account name: 3 to 24 lowercase letters and digits, globally unique."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.name))
    error_message = "name must be 3 to 24 lowercase letters and digits."
  }
}

variable "resource_group_name" {
  description = "Existing resource group that holds the storage account."
  type        = string
}

variable "location" {
  description = "Azure region of the storage account."
  type        = string
}

variable "ip_allowlist" {
  description = "Public IPv4 addresses or CIDR ranges allowed through the firewall. Azure rejects /31 and /32 ranges and private ranges. Empty keeps the account reachable only through the AzureServices bypass."
  type        = list(string)
  default     = []
}

variable "container_name" {
  description = "Name of the private blob container."
  type        = string
  default     = "private"
}

variable "soft_delete_retention_days" {
  description = "Days that deleted blobs and containers stay recoverable."
  type        = number
  default     = 14

  validation {
    condition     = var.soft_delete_retention_days >= 1 && var.soft_delete_retention_days <= 365
    error_message = "soft_delete_retention_days must be between 1 and 365."
  }
}

variable "account_replication_type" {
  description = "Replication type: LRS, GRS, RAGRS, ZRS, GZRS or RAGZRS."
  type        = string
  default     = "GRS"
}

variable "tags" {
  description = "Tags applied to the storage account."
  type        = map(string)
  default     = {}
}

resource "azurerm_storage_account" "hardened" {
  name                     = var.name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = var.account_replication_type

  min_tls_version                   = "TLS1_2"
  https_traffic_only_enabled        = true
  allow_nested_items_to_be_public   = false
  cross_tenant_replication_enabled  = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = var.soft_delete_retention_days
    }

    container_delete_retention_policy {
      days = var.soft_delete_retention_days
    }
  }

  # Bypass keeps trusted Azure services (for example logging and backup) working under Deny.
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = var.ip_allowlist
  }

  tags = var.tags
}

resource "azurerm_storage_container" "private" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.hardened.id
  container_access_type = "private"
}

output "storage_account_id" {
  description = "Resource ID of the storage account."
  value       = azurerm_storage_account.hardened.id
}

output "storage_account_name" {
  description = "Name of the storage account."
  value       = azurerm_storage_account.hardened.name
}

output "primary_blob_endpoint" {
  description = "Primary blob service endpoint URL."
  value       = azurerm_storage_account.hardened.primary_blob_endpoint
}
