# Serves components: backend-api, web
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  # Backend config supplied at init time via -backend-config flags (storage account/container/key
  # are resolved per app+environment by DEPLOY, not hardcoded here) — see lib/terraform-apply.ts.
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}


resource "azurerm_postgresql_flexible_server" "postgresql" {
  tags = var.common_tags
  name                   = "psql-transcript-cred"
  resource_group_name    = "transcript-cred-"
  location               = "uksouth"
  version                = "16"
  # B_Standard_B1ms is a valid SKU name and is listed as offered in uksouth (Azure's capabilities API
  # confirms it, no restriction flag), but regional hardware stock for it has been intermittently
  # exhausted — a capacity error (SkuNotAvailable), not a quota or config problem, and not something a
  # retry on the same SKU reliably clears. B_Standard_B2s is Azure's own default Burstable SKU for this
  # region and has not shown the same stockout. Regression: legal-contartct-test-15, apply failed twice
  # with "Specified SKU is not supported in this region. Please choose a different SKU."
  sku_name               = "B_Standard_B2s"
  storage_mb             = 32768
  administrator_login    = "psqladmin"
  administrator_password = random_password.postgresql_admin.result
  public_network_access_enabled = false
  backup_retention_days         = 35
  geo_redundant_backup_enabled  = true

  # Azure assigns an availability zone on creation since none is declared here — a later apply
  # then sees that as drift and tries to reset it, which the provider rejects outright:
  # "zone can only be changed when exchanged with the zone specified in
  # high_availability.0.standby_availability_zone". Observed on prompt-lib-test-10, blocking every
  # apply after the first. Ignoring drift on the attribute this config never set an opinion on is
  # correct, not a workaround — the alternative is declaring an explicit zone, which would make a
  # dev-tier single-app server fail to provision at all if that zone has no capacity.
  lifecycle {
    ignore_changes = [zone]
  }
}

resource "random_password" "postgresql_admin" {
  length  = 24
  special = true
}

data "azurerm_private_dns_zone" "postgresql_dns_zone" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = var.hub_resource_group
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql_dns_zone_link" {
  tags = var.common_tags
  name                  = "link-transcript-cred"
  resource_group_name   = var.hub_resource_group
  private_dns_zone_name = data.azurerm_private_dns_zone.postgresql_dns_zone.name
  virtual_network_id    = var.vnet_id
}

resource "azurerm_private_endpoint" "postgresql_pe" {
  tags = var.common_tags
  name                = "pe-psql-transcript-cred"
  resource_group_name = "transcript-cred-"
  location            = "uksouth"
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "psql-privateserviceconnection"
    private_connection_resource_id = azurerm_postgresql_flexible_server.postgresql.id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "psql-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.postgresql_dns_zone.id]
  }
}

resource "azurerm_search_service" "search" {
  tags = var.common_tags
  name                = "search-transcript-cred"
  resource_group_name = "transcript-cred-"
  location            = "uksouth"
  sku                 = "basic"
  public_network_access_enabled = false
}

data "azurerm_private_dns_zone" "search_dns_zone" {
  name                = "privatelink.search.windows.net"
  resource_group_name = var.hub_resource_group
}

resource "azurerm_private_dns_zone_virtual_network_link" "search_dns_zone_link" {
  tags = var.common_tags
  name                  = "link-transcript-cred"
  resource_group_name   = var.hub_resource_group
  private_dns_zone_name = data.azurerm_private_dns_zone.search_dns_zone.name
  virtual_network_id    = var.vnet_id
}

resource "azurerm_private_endpoint" "search_pe" {
  tags = var.common_tags
  name                = "pe-search-transcript-cred"
  resource_group_name = "transcript-cred-"
  location            = "uksouth"
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "search-privateserviceconnection"
    private_connection_resource_id = azurerm_search_service.search.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "search-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.search_dns_zone.id]
  }
}

resource "azurerm_storage_account" "blob" {
  tags = var.common_tags
  name                     = "sttranscriptcred"
  resource_group_name      = "transcript-cred-"
  location                 = "uksouth"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  public_network_access_enabled = false
  # Azure Policy "Storage account public access should be disallowed" denies the create outright without this,
  # and the two settings are not the same thing: public_network_access_enabled above closes the network path,
  # while this controls whether individual blobs may be marked public. The azurerm provider defaults it to true,
  # so omitting it is an active choice to allow public blobs, which the policy refuses.
  #
  # Regression: harbour-legal-test-10. The apply created Postgres, AI Search and both private endpoints, then
  # died on this with RequestDisallowedByPolicy / Forbidden: "Please ensure that Blob Public Access is blocked
  # before creating your storage account." Every app needing Blob Storage failed the same way.
  allow_nested_items_to_be_public = false
}

data "azurerm_private_dns_zone" "blob_dns_zone" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.hub_resource_group
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob_dns_zone_link" {
  tags = var.common_tags
  name                  = "link-transcript-cred"
  resource_group_name   = var.hub_resource_group
  private_dns_zone_name = data.azurerm_private_dns_zone.blob_dns_zone.name
  virtual_network_id    = var.vnet_id
}

resource "azurerm_private_endpoint" "blob_pe" {
  tags = var.common_tags
  name                = "pe-blob-transcript-cred"
  resource_group_name = "transcript-cred-"
  location            = "uksouth"
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "blob-privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.blob.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "blob-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blob_dns_zone.id]
  }
}