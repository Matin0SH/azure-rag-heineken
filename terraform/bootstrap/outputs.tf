# ===========================
# BOOTSTRAP OUTPUTS
# ===========================
# Output values from bootstrap (used in main Terraform config)

output "resource_group_name" {
  description = "Name of the created Resource Group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the Resource Group"
  value       = azurerm_resource_group.main.location
}

output "storage_account_name" {
  description = "Name of the Storage Account for Terraform state"
  value       = azurerm_storage_account.tfstate.name
}

output "storage_container_name" {
  description = "Name of the Storage Container for state files"
  value       = azurerm_storage_container.tfstate.name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# ===========================
# NEXT STEPS OUTPUT
# ===========================
output "next_steps" {
  description = "Instructions for next steps"
  value       = <<-EOT

   Bootstrap Complete!

  Next Steps:
  1. Configure backend in main Terraform:
     - Storage Account: ${azurerm_storage_account.tfstate.name}
     - Container: ${azurerm_storage_container.tfstate.name}
     - Resource Group: ${azurerm_resource_group.main.name}

  2. Run: terraform init -migrate-state

  3. Secrets stored in Key Vault:
     - Vault Name: ${azurerm_key_vault.main.name}
     - URI: ${azurerm_key_vault.main.vault_uri}

  4. Ready to build Databricks infrastructure!

  EOT
}
