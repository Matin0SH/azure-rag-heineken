# ===========================
# BACKEND CONFIGURATION
# ===========================
# This tells Terraform to store state in Azure Blob Storage
# Uncomment AFTER bootstrap is complete and you run: terraform init -migrate-state

# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-databricks-rag-dev"
#     storage_account_name = "stdatabricksragstate"
#     container_name       = "tfstate"
#     key                  = "bootstrap.tfstate"  # State file name
#   }
# }
