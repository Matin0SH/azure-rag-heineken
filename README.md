# Databricks RAG Infrastructure Setup

Complete Terraform infrastructure for deploying a Databricks-based RAG (Retrieval-Augmented Generation) system on Azure.

## Prerequisites

1. **Azure Account** with active subscription
2. **Azure CLI** installed and logged in (`az login`)
3. **Terraform** installed (>= 1.6.0)
4. **Databricks Workspace** already created on Azure (Premium tier for Unity Catalog)
5. **Databricks Personal Access Token** generated
6. **SQL Warehouse** created in Databricks

## Architecture

This infrastructure is split into two stages:

### 1. Bootstrap (Foundation)
Creates the base Azure infrastructure:
- Resource Group
- Storage Account (for Terraform state)
- Storage Container (for state files)
- Key Vault (for secrets management)
- Stores Databricks credentials in Key Vault

### 2. Terraform (Databricks Resources)
Creates Databricks resources:
- Unity Catalog and Schema
- Tables: documents, chunks, chunks_embedded, summaries, questions
- Vector Search Index on chunks_embedded table
- Databricks Jobs (ingestion, summarization, question generation)

## Setup Instructions

### Step 1: Bootstrap Infrastructure

```bash
cd bootstrap
terraform init
terraform plan
terraform apply
```

**What this creates:**
- `rg-databricks-rag-dev` - Resource Group
- `stdatabricksragstate` - Storage Account
- `tfstate` - Container for Terraform state
- `kv-databricks-rag-dev` - Key Vault with your Databricks credentials

### Step 2: Deploy Databricks Resources

```bash
cd ../terraform
terraform init
terraform plan
terraform apply
```

**What this creates:**
- Unity Catalog: `heineken_test_workspace`
- Schema: `nextlevel-rag`
- Tables for RAG pipeline
- Vector search endpoint and index
- 3 Databricks jobs (ingestion, summarization, question generation)

## Important Notes

### Sensitive Files (DO NOT COMMIT)
Both `terraform.tfvars` files contain sensitive credentials and are excluded from git via `.gitignore`:
- `bootstrap/terraform.tfvars`
- `terraform/terraform.tfvars`

### Unity Catalog Requirement
The Unity Catalog `heineken_test_workspace` must exist in your Databricks workspace. If it doesn't:
1. Go to Databricks UI → Data → Catalogs
2. Create a new catalog named `heineken_test_workspace`
3. Or update the `catalog_name` in `terraform/terraform.tfvars`

### Vector Search Endpoint
The vector search endpoint `heineken-vdb` must be created manually in Databricks:
1. Go to Databricks UI → Compute → Vector Search
2. Create endpoint named `heineken-vdb`
3. Wait for it to be online before running terraform

### Databricks Jobs
The job notebook paths reference `/Repos/Production/azure-rag-heineken/jobs/`. You need to:
1. Connect your GitHub repo to Databricks
2. Create a Repo under `/Repos/Production/`
3. Or update the paths in `terraform.tfvars`

## Cleanup

To destroy all resources:

```bash
# First destroy Databricks resources
cd terraform
terraform destroy

# Then destroy bootstrap infrastructure
cd ../bootstrap
terraform destroy
```

**Warning:** This will delete all data in your tables!

## Troubleshooting

### Error: Catalog doesn't exist
Create the catalog in Databricks UI or via SQL:
```sql
CREATE CATALOG IF NOT EXISTS heineken_test_workspace;
```

### Error: Vector endpoint not found
Create the endpoint in Databricks UI or wait for it to be online.

### Error: Notebook path not found
Update the notebook paths in `terraform.tfvars` to match your Databricks Repo structure.

## Next Steps

After successful deployment:
1. Upload documents to trigger ingestion job
2. Monitor job runs in Databricks Jobs UI
3. Query the vector index for RAG queries
4. Set up CI/CD pipeline for automated deployments
