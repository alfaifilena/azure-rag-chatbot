variable "resource_group_name" {
  type = string
}

variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "postgres_server_name" {
  type = string
}

variable "postgres_admin_user" {
  type    = string
  default = "pgadmin"
}

variable "postgres_admin_password" {
  type      = string
  sensitive = true
}

variable "storage_account_name" {
  type = string
}

variable "postgres_location" {
  type    = string
  default = "centralus"
}

variable "key_vault_name" {
  type = string
}