output "public_ip" {
  value = azurerm_public_ip.public_ip.ip_address
}

output "ssh_command" {
  value = "ssh -i ./ssh-keys/terraform-azure azureuser@${azurerm_public_ip.public_ip.ip_address}"
}

output "postgres_host" {
  value = azurerm_postgresql_flexible_server.postgres.fqdn
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}

output "storage_container_name" {
  value = azurerm_storage_container.chatbot.name
}

output "key_vault_name" {
  value = azurerm_key_vault.keyvault.name
}