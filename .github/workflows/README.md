# GitHub Actions CI/CD Setup

This workflow automatically deploys your code to Databricks when you push to the `main` branch.

## 🔧 Required GitHub Secrets

You need to add these secrets to your GitHub repository:

### Go to: `https://github.com/Matin0SH/azure-rag-heineken/settings/secrets/actions`

Add these secrets:

### 1. `DATABRICKS_HOST`
- **Value:** `https://adb-2145154803054656.16.azuredatabricks.net`

### 2. `DATABRICKS_TOKEN`
- **Value:** Your Databricks personal access token
- Get it from: Databricks → User Settings → Access Tokens

### 3. `AZURE_CREDENTIALS`
- **Value:** JSON with Azure service principal credentials
- Format:
```json
{
  "clientId": "<your-client-id>",
  "clientSecret": "<your-client-secret>",
  "subscriptionId": "21754b33-13f1-4d10-9656-71dc66b1e263",
  "tenantId": "<your-tenant-id>"
}
```

**To create Azure Service Principal:**
```bash
az ad sp create-for-rbac \
  --name "github-actions-databricks" \
  --role contributor \
  --scopes /subscriptions/21754b33-13f1-4d10-9656-71dc66b1e263 \
  --sdk-auth
```

---

## 🚀 What Happens When You Push

### Workflow: `deploy.yml`

**Trigger:** Push to `main` branch

**Jobs:**

1. **sync-to-databricks** (3-5 minutes)
   - Syncs code to `/Repos/Production/azure-rag-heineken`
   - Updates notebooks automatically

2. **deploy-terraform** (5-10 minutes)
   - Creates/updates Databricks infrastructure
   - Tables, jobs, vector indexes
   - Only runs if Terraform files changed

3. **validate-deployment** (1-2 minutes)
   - Verifies repo exists
   - Checks jobs are created
   - Final validation

---

## 📊 Monitoring

**View workflow runs:**
`https://github.com/Matin0SH/azure-rag-heineken/actions`

**Logs show:**
- ✅ Success: Green checkmark
- ❌ Failed: Red X with error logs
- 🟡 Running: Yellow dot

---

## 🔄 Development Workflow

### Making Changes:

```bash
# 1. Edit code locally
code jobs/ingest_pipeline.py

# 2. Commit
git add .
git commit -m "Update ingest pipeline"

# 3. Push - CI/CD does the rest!
git push origin main

# 4. Watch deployment
# Go to: https://github.com/Matin0SH/azure-rag-heineken/actions
```

### Manual Trigger:

Go to Actions → Deploy to Databricks → Run workflow

---

## 🛠️ Troubleshooting

### "Repo not found" error
- Go to Databricks workspace
- Create folder: `/Repos/Production/`
- Re-run workflow

### "Terraform backend" error
- Make sure bootstrap ran successfully
- Check Azure storage account exists

### "Permission denied" error
- Check GitHub secrets are set correctly
- Verify Databricks token is valid

---

## 📝 Configuration

Edit variables in `deploy.yml`:
- Line 97-106: Terraform variables
- Line 53: Databricks Repo path
- Line 76: Terraform conditions

---

*Last updated: 2025-11-30*
