# Terraform Strategy & Architecture

## Design Principles

1. **Modular Architecture** - Separate concerns into reusable modules
2. **Environment Isolation** - Support dev/staging/prod with same code
3. **State Management** - Remote state in Azure with locking
4. **Secrets Security** - Never commit secrets, use Key Vault
5. **Idempotency** - Safe to run multiple times
6. **Clear Dependencies** - Explicit resource dependencies

## Module Structure

```
terraform/
├── modules/
│   ├── databricks_foundation/      # Unity Catalog schema + volumes
│   ├── databricks_tables/          # 8 Delta tables with schemas
│   ├── databricks_vector/          # Vector search endpoint + index
│   ├── databricks_jobs/            # 3 job definitions
│   └── azure_infrastructure/       # ACR + App Service
├── bootstrap/                       # One-time setup (state backend)
├── main.tf                          # Root module
├── variables.tf                     # Input variables
├── outputs.tf                       # Outputs
├── providers.tf                     # Provider configuration
├── backend.tf                       # Remote state config
└── terraform.tfvars.example         # Example variables
```

## What Terraform Manages

### ✅ Terraform-Managed Resources

**Databricks:**
- Unity Catalog Schema (catalog may be pre-existing)
- Volumes: `raw_pdfs`, `screenshots`
- Delta Tables (8 tables with proper schemas)
- Vector Search Index
- Databricks Jobs (3 jobs)
- Service Principal permissions
- Workspace notebooks (uploaded from code)

**Azure:**
- Resource Group
- Storage Account (state backend)
- Container (state storage)
- Key Vault
- Container Registry
- App Service Plan
- App Service (Linux container)
- Service Principal (for automation)

### ❌ NOT Terraform-Managed

**Databricks:**
- SQL Warehouse (pre-existing, shared resource)
- Vector Search Endpoint (pre-existing: `heineken-vdb`)
- Model Serving Endpoints (ML ops concern)
- Databricks Workspace (enterprise-managed)
- Unity Catalog (catalog level, pre-existing)

**Application Data:**
- Data inside Delta tables (managed by pipelines)
- Uploaded PDFs (managed by application)
- Generated embeddings (managed by jobs)

## State Management

### Backend Configuration

**Azure Blob Storage:**
- Storage Account: `stdatabricksragstate`
- Container: `tfstate`
- State file: `terraform.tfstate`
- Features:
  - State locking (prevents concurrent runs)
  - Encryption at rest
  - Versioning enabled
  - Access via Service Principal

### State File Organization

**Single Environment:**
```
tfstate/
└── terraform.tfstate
```

**Multiple Environments (future):**
```
tfstate/
├── dev.tfstate
├── staging.tfstate
└── prod.tfstate
```

## Module Details

### 1. databricks_foundation

**Purpose:** Create schema and volumes in Unity Catalog

**Resources:**
- `databricks_schema` - Schema in catalog
- `databricks_volume` (x2) - raw_pdfs, screenshots

**Variables:**
- `catalog_name` - Unity Catalog name
- `schema_name` - Schema name
- `volumes` - List of volume configurations

**Outputs:**
- `schema_id` - Full schema identifier
- `volume_paths` - Map of volume names to paths

### 2. databricks_tables

**Purpose:** Create all 8 Delta tables with proper schemas

**Resources:**
- `databricks_sql_query` - Execute CREATE TABLE DDL for each table

**Tables:**
1. `pdf_registery` - (pdf_id STRING, pdf_name STRING, file_path STRING, upload_date TIMESTAMP, processing_status STRING, processed_date TIMESTAMP, error_message STRING)
2. `chunks_embedded` - (chunk_id STRING, pdf_id STRING, page_number INT, chunk_index INT, text STRING, embedding ARRAY<FLOAT>, created_at TIMESTAMP)
3. `page_screenshots` - (page_id STRING, pdf_id STRING, page_number INT, screenshot_path STRING, created_at TIMESTAMP)
4. `page_embeddings_graph` - (pdf_id STRING, page_number INT, page_text STRING, embedding ARRAY<FLOAT>, created_at TIMESTAMP)
5. `page_sections` - (pdf_id STRING, page_number INT, section_id INT, created_at TIMESTAMP)
6. `section_summaries_graph` - (summary_id STRING, pdf_id STRING, section_id INT, title STRING, summary_text STRING, key_topics ARRAY<STRING>, page_range_start INT, page_range_end INT, num_pages INT, batch_count INT, processing_model STRING, processing_time_seconds FLOAT, created_at TIMESTAMP)
7. `graph_metadata` - (pdf_id STRING, total_pages INT, total_nodes INT, total_edges INT, knn_edges INT, adjacency_edges INT, num_sections INT, modularity FLOAT, k_neighbors INT, similarity_threshold FLOAT, resolution FLOAT, created_at TIMESTAMP)

**Dependencies:**
- Requires schema from `databricks_foundation`

### 3. databricks_vector

**Purpose:** Create vector search index

**Resources:**
- `databricks_vector_search_index` - Index on chunks_embedded table

**Configuration:**
- Endpoint: `heineken-vdb` (pre-existing)
- Source table: `chunks_embedded`
- Primary key: `chunk_id`
- Embedding dimension: 1024 (databricks-gte-large-en)
- Embedding column: `embedding`
- Sync mode: Continuous

**Dependencies:**
- Requires `chunks_embedded` table
- Requires vector search endpoint (pre-existing)

### 4. databricks_jobs

**Purpose:** Create 3 Databricks jobs with notebook tasks

**Resources:**
- `databricks_notebook` (x3) - Upload notebooks to workspace
- `databricks_job` (x3) - Job definitions

**Jobs:**
1. **Ingest Pipeline**
   - Notebook: `ingest_pipeline.py`
   - Parameters: `pdf_name`, `pdf_id`
   - Cluster: Job cluster (compute-optimized)

2. **Graph Community Detection**
   - Notebook: `graph_community_pipeline.py`
   - Parameters: `pdf_name`, `pdf_id`
   - Auto-triggers: Summarization job
   - Cluster: Job cluster (memory-optimized)

3. **Graph Summarization**
   - Notebook: `graph_summarization_pipeline.py`
   - Parameters: `pdf_name`, `pdf_id`
   - Cluster: Job cluster (memory-optimized)

**Dependencies:**
- Requires tables to exist
- Requires vector search index

### 5. azure_infrastructure

**Purpose:** Create Azure resources for application hosting

**Resources:**
- `azurerm_container_registry` - ACR for Docker images
- `azurerm_service_plan` - Linux App Service Plan
- `azurerm_linux_web_app` - App Service
- App Service configuration:
  - Container settings (ACR)
  - Environment variables (from Key Vault)
  - Health check endpoint
  - Auto-scaling rules (optional)

**Variables:**
- `location` - Azure region
- `resource_group_name` - RG name
- `app_name` - Application name
- `docker_image` - Image name in ACR

**Outputs:**
- `acr_login_server` - ACR URL
- `app_service_url` - Application URL
- `app_service_identity` - Managed identity ID

## Secrets Management

### Azure Key Vault Strategy

**Secrets Stored:**
- `databricks-token` - Personal Access Token
- `databricks-host` - Workspace URL
- `databricks-warehouse-id` - SQL Warehouse ID
- `sp-client-id` - Service Principal ID
- `sp-client-secret` - Service Principal secret
- `acr-username` - ACR username
- `acr-password` - ACR password

**Access Pattern:**
- Terraform reads from Key Vault during apply
- App Service references Key Vault secrets
- GitHub Actions uses repository secrets (not Key Vault)

### GitHub Secrets

**Repository Secrets:**
- `AZURE_CREDENTIALS` - Service Principal JSON
- `AZURE_SUBSCRIPTION_ID` - Subscription ID
- `DATABRICKS_TOKEN` - For Databricks provider
- `DATABRICKS_HOST` - Workspace URL

## Critical Dependencies

### Resource Creation Order

```
1. Resource Group
   └─> Storage Account (state backend)
   └─> Key Vault
   └─> Container Registry

2. Databricks Schema
   └─> Volumes
   └─> Delta Tables
       └─> Vector Search Index
           └─> Jobs
```

### Chicken-and-Egg Problems

**Problem 1: State Backend**
- Need Storage Account for state
- Need Terraform to create Storage Account
- **Solution:** Bootstrap phase with local state, then migrate

**Problem 2: Vector Index Needs Data**
- Index requires table with embeddings
- Table gets data from jobs
- Jobs need index to exist
- **Solution:** Create index in TRIGGERED mode, first job run populates, then switch to CONTINUOUS

**Problem 3: Job Chaining**
- Community detection job triggers summarization
- Hardcoded credentials in notebook
- **Solution:** Use Databricks secrets scope, update notebook to reference secrets

## Best Practices

1. **Use Variables** - Never hardcode values
2. **Use Outputs** - Pass data between modules
3. **Use depends_on** - Explicit dependencies when implicit doesn't work
4. **Use Data Sources** - Reference existing resources (SQL Warehouse)
5. **Use Lifecycle Rules** - Prevent accidental destruction
6. **Use Workspaces** - For multiple environments (future)
7. **Tag Everything** - Resource tracking and cost allocation
8. **Version Providers** - Lock provider versions
9. **Validate Before Apply** - Always run `terraform plan`
10. **Backup State** - Enable versioning on state storage

## Known Limitations

1. **Vector Search Endpoint** - Cannot create via Terraform (pre-existing)
2. **Model Endpoints** - Not managed by Terraform
3. **Table Data** - Terraform creates schema, not data
4. **SQL Warehouse** - Expensive, using pre-existing
5. **Notebook Code Updates** - Requires re-upload, triggers job recreation
