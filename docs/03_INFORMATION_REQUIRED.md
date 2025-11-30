# Information Required to Start

This document lists all information needed from you to begin the Terraform implementation.

## Step 1B: Information Gathering Checklist

### 1. Azure Subscription Information

**Required:**
- [ ] **Azure Subscription ID**
  - Where to find: Azure Portal → Subscriptions
  - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
  - Example: `12345678-1234-1234-1234-123456789012`

- [ ] **Azure Region**
  - Recommendation: Should match your Databricks workspace region
  - Common options: `eastus`, `eastus2`, `westus2`, `westeurope`, `northeurope`
  - Your Databricks workspace appears to be in Azure (based on URL pattern)
  - **Question:** Which region is your Databricks workspace in?

### 2. Databricks Workspace Information

**You already mentioned you have these - please confirm:**

- [ ] **Databricks Workspace URL**
  - Current: `https://adb-2145154803054656.16.azuredatabricks.net`
  - Confirm: Is this correct? ✓ or ✗

- [ ] **Databricks Workspace ID**
  - Current: `2145154803054656` (extracted from URL)
  - Confirm: Is this correct? ✓ or ✗

- [ ] **Databricks Personal Access Token**
  - How to create: Databricks UI → User Settings → Access Tokens → Generate New Token
  - Permissions needed: Workspace access, SQL access, Repos access
  - Expiration: 90 days or longer recommended
  - Format: `dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
  - **Action:** Create a new token specifically for Terraform (or provide existing)

- [ ] **SQL Warehouse ID**
  - Current: `28150cf4611d3a27`
  - Confirm: Is this correct? ✓ or ✗

- [ ] **Vector Search Endpoint Name**
  - Current: `heineken-vdb`
  - Confirm: Is this still active and accessible? ✓ or ✗

### 3. Unity Catalog Information

**Existing Resources to Reference:**

- [ ] **Catalog Name**
  - Current: `heineken_test_workspace`
  - Confirm: Is this correct? ✓ or ✗
  - Question: Should Terraform manage this catalog or just reference it?
    - [ ] Manage with Terraform (Terraform will create/destroy)
    - [ ] Reference only (already exists, Terraform just uses it)

- [ ] **Schema Name**
  - Current: `heineken-streamlit`
  - Confirm: Is this correct? ✓ or ✗
  - Question: Should Terraform manage this schema?
    - [ ] Manage with Terraform (recreate as part of infrastructure)
    - [ ] Reference only (keep existing)

### 4. Compute Resources

- [ ] **Existing Compute Cluster ID** (if you want to reuse for jobs)
  - Where to find: Databricks → Compute → Click cluster → URL or "Tags" section
  - Format: `XXXX-XXXXXX-XXXXXXXX`
  - **Question:** Do you have a preferred cluster, or should Terraform create new job clusters?
    - [ ] Use existing cluster ID: `________________`
    - [ ] Create new job clusters (Terraform-managed)

### 5. Naming Conventions

**Please choose names for new resources:**

- [ ] **Resource Group Name**
  - Suggested: `rg-databricks-rag-dev`
  - Your preference: `________________________`

- [ ] **Storage Account Name** (for Terraform state)
  - Requirements: 3-24 chars, lowercase, numbers only, globally unique
  - Suggested: `stdatabricksragstate`
  - Your preference: `________________________`

- [ ] **Key Vault Name**
  - Requirements: 3-24 chars, alphanumeric and hyphens, globally unique
  - Suggested: `kv-databricks-rag-dev`
  - Your preference: `________________________`

- [ ] **Container Registry Name**
  - Requirements: 5-50 chars, alphanumeric only, globally unique
  - Suggested: `acrdatabricksrag`
  - Your preference: `________________________`

- [ ] **App Service Name**
  - Requirements: Alphanumeric and hyphens, globally unique
  - Suggested: `app-databricks-rag-dev`
  - Your preference: `________________________`
  - Note: Final URL will be `https://{name}.azurewebsites.net`

### 6. Environment Strategy

- [ ] **Number of Environments**
  - [ ] Single environment (dev/prod combined) - **RECOMMENDED FOR NOW**
  - [ ] Multiple environments (dev, staging, prod)

- [ ] **Environment Name** (if single)
  - Suggested: `dev` or `prod`
  - Your preference: `________________________`

### 7. Cost Considerations

- [ ] **App Service Tier**
  - [ ] Free (F1) - Free tier, limited to 60 CPU min/day, 1GB RAM
  - [ ] Basic (B1) - ~$13/month, 1.75GB RAM, recommended for dev
  - [ ] Standard (S1) - ~$70/month, 1.75GB RAM, auto-scaling, recommended for prod
  - Your choice: `________________________`

- [ ] **Vector Search Endpoint**
  - Current endpoint: `heineken-vdb`
  - Question: Is this shared or dedicated to this project?
  - [ ] Shared (don't recreate)
  - [ ] Dedicated (can manage with Terraform if needed in future)

### 8. GitHub Repository

- [ ] **GitHub Repository URL**
  - Format: `https://github.com/{username}/{repo-name}`
  - Your repository: `________________________`
  - Note: Needed for GitHub Actions setup

- [ ] **Branch Strategy**
  - [ ] Single branch (`main`) - **RECOMMENDED FOR NOW**
  - [ ] Multiple branches (`dev`, `main`)
  - Your choice: `________________________`

### 9. Additional Questions

- [ ] **Hardcoded Token Issue**
  - File: `graph_community_pipeline.py:462`
  - Contains: Hardcoded Databricks token
  - Question: Should we fix this as part of Terraform work?
    - [ ] Yes, fix before proceeding (update notebook to use Databricks secrets)
    - [ ] No, fix later
    - [ ] Already fixed

- [ ] **Databricks Workspace Admin Access**
  - Question: Do you have admin access to create Service Principals in Databricks?
    - [ ] Yes, I'm admin
    - [ ] No, I'll need to request access
    - [ ] Not sure

- [ ] **Azure Subscription Permissions**
  - Question: Can you create Service Principals and assign Contributor role?
    - [ ] Yes, I have Owner or User Access Administrator role
    - [ ] No, I'll need to request access
    - [ ] Not sure

## Summary of Critical Information

Please provide at minimum:

1. **Azure Subscription ID**: `________________________________`
2. **Azure Region**: `________________________________`
3. **Databricks PAT Token**: `________________________________`
4. **Confirm existing Databricks resources** (URLs, IDs listed above)
5. **Resource naming preferences** (or approve suggestions)
6. **GitHub repository URL**: `________________________________`

## Next Steps After Providing Information

Once you provide this information, I will:

1. Create Terraform variables file with your values
2. Write bootstrap Terraform code
3. Provide step-by-step commands to run
4. Help you create Service Principal
5. Guide you through first Terraform apply

## How to Provide This Information

Please respond with:

```
AZURE SUBSCRIPTION ID: xxx-xxx-xxx
AZURE REGION: eastus2
DATABRICKS PAT: dapiXXXXXXX
RESOURCE GROUP NAME: rg-my-project
... (rest of information)
```

Or answer each checkbox/question in order.

---

**Ready?** Once you provide this information, we'll proceed to Step 2: Service Principal creation and bootstrap Terraform!
