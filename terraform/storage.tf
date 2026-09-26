# Azure Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  min_tls_version = "TLS1_2"
}

# Blob container
resource "azurerm_storage_container" "chatbot" {
  name                  = "chatbot-files"
  storage_account_id    = azurerm_storage_account.storage.id
  container_access_type = "private"
}