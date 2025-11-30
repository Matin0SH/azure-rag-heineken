# Step-by-Step Implementation Plan

## Overview

This document outlines the complete implementation plan from initial setup to production deployment.

## Phase 1: Bootstrap Infrastructure

### Step 1: Prerequisites & Information Gathering

**Required Information:**
- [ ] Azure Subscription ID
- [ ] Azure Region (matching Databricks workspace region)
- [ ] Databricks Workspace URL
- [ ] Databricks Workspace ID
- [ ] Databricks Personal Access Token
- [ ] SQL Warehouse ID
- [ ] Vector Search Endpoint name
- [ ] Existing Catalog name
- [ ] Existing Schema name
- [ ] Naming preferences (resource group, storage account, etc.)

**Required Tools:**
- [ ] Azure CLI installed and authenticated
- [ ] Terraform 1.6+ installed
- [ ] Git installed
- [ ] Code editor (VS Code recommended)

### Step 2: Create Azure Service Principal

**Manual Steps:**
```bash
# Create Service Principal
az ad sp create-for-rbac --name "sp-databricks-terraform" \
  --role="Contributor" \
  --scopes="/subscriptions/{subscription-id}"

# Output (SAVE THIS):
# - appId (Client ID)
# - password (Client Secret)
# - tenant (Tenant ID)
```

**Grant Databricks Permissions:**
- Add Service Principal to Databricks workspace
- Grant appropriate Unity Catalog permissions

### Step 3: Bootstrap Terraform State Backend

**Location:** `terraform/bootstrap/`

**Resources to Create:**
1. Resource Group
2. Storage Account (for Terraform state)
3. Storage Container (for state files)
4. Key Vault
5. Upload secrets to Key Vault

**Process:**
1. Write Terraform with local state
2. Apply to create resources
3. Migrate state to Azure backend
4. Destroy local state files

**Validation:**
- State stored in Azure Blob Storage
- Secrets accessible in Key Vault
- Service Principal has access to resources

## Phase 2: Databricks Foundation

### Step 4: Create Schema and Volumes

**Module:** `databricks_foundation`

**Resources:**
1. Unity Catalog Schema (if doesn't exist)
2. Volume: `raw_pdfs`
3. Volume: `screenshots`

**Validation:**
- Schema visible in Databricks SQL Editor
- Volumes accessible via workspace

### Step 5: Create Delta Tables

**Module:** `databricks_tables`

**Resources:** 8 Delta tables with schemas

**Approach:**
- Use `databricks_sql_query` to execute CREATE TABLE DDL
- One resource per table
- Proper data types (ARRAY<FLOAT> for embeddings)

**Validation:**
- All 8 tables visible in catalog explorer
- Correct schemas via DESCRIBE TABLE

## Phase 3: Vector Search

### Step 6: Create Vector Search Index

**Module:** `databricks_vector`

**Resources:**
1. Vector Search Index on `chunks_embedded`

**Configuration:**
- Endpoint: `heineken-vdb` (reference existing)
- Source table: `chunks_embedded`
- Primary key: `chunk_id`
- Embedding column: `embedding`
- Sync mode: TRIGGERED (initial), switch to CONTINUOUS after first data load

**Validation:**
- Index visible in vector search UI
- Index status: READY

## Phase 4: Databricks Jobs

### Step 7: Upload Notebooks and Create Jobs

**Module:** `databricks_jobs`

**Process:**
1. Fix hardcoded credentials in `graph_community_pipeline.py`
2. Upload 3 notebooks to workspace
3. Create 3 job definitions

**Jobs:**
1. **Ingest Pipeline**
   - Task: Notebook task
   - Parameters: pdf_name, pdf_id
   - Cluster: Job cluster (small)

2. **Graph Community Detection**
   - Task: Notebook task
   - Parameters: pdf_name, pdf_id
   - Cluster: Job cluster (medium)
   - Auto-trigger: Summarization job (via API in notebook)

3. **Graph Summarization**
   - Task: Notebook task
   - Parameters: pdf_name, pdf_id
   - Cluster: Job cluster (medium)

**Validation:**
- Jobs visible in Databricks Jobs UI
- Can trigger manually with test parameters
- Test run completes successfully

## Phase 5: Application Infrastructure

### Step 8: Create Azure Container Registry

**Module:** `azure_infrastructure`

**Resources:**
1. Container Registry (ACR)
2. Admin credentials enabled

**Validation:**
- ACR accessible via Azure Portal
- Can login via Docker CLI

### Step 9: Create App Service

**Module:** `azure_infrastructure`

**Resources:**
1. App Service Plan (Linux, B1 tier for dev)
2. App Service (Linux container)

**Configuration:**
- Container: ACR (initially empty)
- Environment variables:
  - DATABRICKS_HOST (from Key Vault)
  - DATABRICKS_TOKEN (from Key Vault)
  - DATABRICKS_WAREHOUSE_ID (from Key Vault)
  - Other config values
- Health check: `/` (Streamlit health)
- Always On: Enabled

**Validation:**
- App Service created
- Default page accessible (no container yet)

## Phase 6: Dockerization

### Step 10: Create Dockerfile

**Location:** `docker/Dockerfile`

**Multi-stage Build:**
1. Base stage: Python dependencies
2. Production stage: App code + non-root user

**Optimizations:**
- Layer caching for dependencies
- Minimal base image (python:3.11-slim)
- Health check endpoint
- Non-root user

**Validation:**
- Build locally succeeds
- Container runs locally
- Health check returns 200

### Step 11: Test Local Docker Build

```bash
# Build image
docker build -t databricks-rag:local -f docker/Dockerfile .

# Run container
docker run -p 8501:8501 --env-file .env databricks-rag:local

# Test in browser
curl http://localhost:8501
```

## Phase 7: CI/CD Pipeline

### Step 12: GitHub Actions - Terraform Plan

**Workflow:** `.github/workflows/terraform-plan.yml`

**Trigger:** Pull Request

**Steps:**
1. Checkout code
2. Setup Terraform
3. Configure Azure credentials
4. Terraform init
5. Terraform plan
6. Comment plan on PR

**Validation:**
- Create test PR
- Plan runs successfully
- Plan output commented on PR

### Step 13: GitHub Actions - Terraform Apply

**Workflow:** `.github/workflows/terraform-apply.yml`

**Trigger:** Push to main

**Steps:**
1. Checkout code
2. Setup Terraform
3. Configure Azure credentials
4. Terraform init
5. Terraform apply (auto-approve)

**Validation:**
- Merge PR to main
- Apply runs successfully
- Resources created/updated

### Step 14: GitHub Actions - Docker Build & Deploy

**Workflow:** `.github/workflows/deploy.yml`

**Trigger:** Push to main (after terraform)

**Steps:**
1. Checkout code
2. Login to ACR
3. Build Docker image
4. Tag with git SHA and 'latest'
5. Push to ACR
6. Update App Service with new image
7. Wait for health check

**Validation:**
- Push to main triggers build
- Image appears in ACR
- App Service updates
- Application accessible

## Phase 8: Integration & Testing

### Step 15: End-to-End Test

**Test Flow:**
1. Upload test PDF via Streamlit
2. Verify ingestion job triggered
3. Verify job completes successfully
4. Verify chunks in table
5. Verify vector index synced
6. Test RAG chat query
7. Trigger summarization
8. Verify summary generated

**Validation:**
- All pipelines work
- Data flows correctly
- Application functional

### Step 16: Documentation

**Create:**
- [ ] README.md (project overview)
- [ ] DEPLOYMENT.md (deployment instructions)
- [ ] ARCHITECTURE.md (architecture diagram)
- [ ] TROUBLESHOOTING.md (common issues)

## Success Criteria

### Infrastructure
- ✅ All Terraform modules apply successfully
- ✅ State stored in Azure backend
- ✅ Secrets in Key Vault
- ✅ All 8 tables created
- ✅ Vector search index operational
- ✅ All 3 jobs created

### Application
- ✅ Docker image builds successfully
- ✅ ACR contains images
- ✅ App Service running
- ✅ Application accessible via URL
- ✅ Health checks passing

### CI/CD
- ✅ Terraform plan on PR works
- ✅ Terraform apply on merge works
- ✅ Docker build/push automated
- ✅ App Service updates automatically

### Functionality
- ✅ PDF upload works
- ✅ Ingestion pipeline works
- ✅ Vector search returns results
- ✅ RAG chat works
- ✅ Summarization pipeline works

## Timeline Estimate

| Phase | Estimated Time |
|-------|---------------|
| Phase 1: Bootstrap | 1-2 hours |
| Phase 2: Databricks Foundation | 1 hour |
| Phase 3: Vector Search | 30 min |
| Phase 4: Databricks Jobs | 1-2 hours |
| Phase 5: App Infrastructure | 1 hour |
| Phase 6: Dockerization | 1-2 hours |
| Phase 7: CI/CD | 2-3 hours |
| Phase 8: Testing | 1-2 hours |
| **Total** | **9-14 hours** |

## Next Steps

After reading this plan:
1. Review and approve approach
2. Gather information (Step 1B)
3. Begin Step 2: Create Service Principal
4. Proceed with bootstrap Terraform

## Notes

- Each step builds on previous steps
- Can pause between phases
- Terraform state allows resuming at any point
- All steps are reversible (terraform destroy)
