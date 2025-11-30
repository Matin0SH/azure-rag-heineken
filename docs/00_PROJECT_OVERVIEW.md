# Project Overview: Databricks RAG System with Terraform CI/CD

## Vision

Build a fully automated, production-ready CI/CD pipeline for the Databricks RAG (Retrieval Augmented Generation) application using:
- **Terraform** for Infrastructure as Code
- **GitHub Actions** for CI/CD automation
- **Docker** for containerization
- **Azure App Service** for hosting

## Current Application Architecture

### Databricks Resources

**Unity Catalog:**
- Catalog: `heineken_test_workspace`
- Schema: `heineken-streamlit`

**Tables (8 total):**
1. `pdf_registery` - PDF upload/processing status tracker
2. `chunks_embedded` - Text chunks with embeddings (ARRAY<FLOAT>)
3. `page_screenshots` - Screenshot paths from PDF parsing
4. `chunks_embedded_index` - Vector search index
5. `page_embeddings_graph` - Page-level embeddings for graph analysis
6. `page_sections` - Page-to-section mappings from Louvain community detection
7. `section_summaries_graph` - Section summaries using reflection method
8. `graph_metadata` - Graph statistics and metrics

**Volumes:**
- `raw_pdfs` - Uploaded PDF files storage
- `screenshots` - Page screenshot image storage

**Vector Search:**
- Endpoint: `heineken-vdb`
- Index: `chunks_embedded_index`

**SQL Warehouse:**
- ID: `28150cf4611d3a27`

### Application Pipelines

**1. Ingestion Pipeline** (`jobs/ingest_pipeline.py`)
- Parses PDFs using Databricks `ai_parse_document()`
- Extracts text and screenshots
- Chunks text with LangChain (smart merging)
- Generates embeddings with `databricks-gte-large-en`
- Stores in Delta tables and syncs vector index

**2. Graph Community Detection** (`jobs/graph_community_pipeline.py`)
- Groups chunks by page
- Generates page-level embeddings
- Builds KNN graph (mutual neighbors + distance decay)
- Adds adjacency edges (P+1, P+2)
- Runs Louvain community detection
- **Auto-triggers** summarization pipeline

**3. Graph Summarization** (`jobs/graph_summarization_pipeline.py`)
- Reflection-based MAP-REDUCE approach
- Batch processing: Draft → Critique → Revise
- Hierarchical reduction for large sections
- Generates SOPs (Standard Operating Procedures)

### Streamlit Application

**Pages:**
1. **Upload** (`app.py`) - Fire-and-forget PDF upload
2. **Chat** (`pages/1_💬_Chat.py`) - RAG chat interface
3. **Jobs** (`pages/2_📊_Jobs.py`) - Job monitoring
4. **Summarize** (`pages/3_📝_Summarize.py`) - Graph-based summarization trigger

**RAG Flow:**
1. Vector search (retrieve top K chunks)
2. Fetch full page contexts
3. Deduplicate pages
4. LLM-based reranking
5. Answer generation with citations
6. Display with page screenshots

## Target Architecture

### Infrastructure Components

**Azure Resources:**
- Resource Group (new, Terraform-managed)
- Storage Account (Terraform state backend)
- Key Vault (secrets management)
- Container Registry (Docker images)
- App Service (Linux containers)

**Databricks Resources (Terraform-managed):**
- Unity Catalog Schema
- Volumes (2)
- Delta Tables (8)
- Vector Search Index
- Jobs (3)

**CI/CD Pipeline:**
- GitHub Actions workflows
- Automated Terraform plan/apply
- Docker build and push
- App Service deployment
- Integration testing

## Project Goals

1. **Full Infrastructure as Code** - Everything defined in Terraform
2. **Automated CI/CD** - Push to main = automatic deployment
3. **Containerized Application** - Docker for consistency
4. **Secure Secrets Management** - Azure Key Vault integration
5. **Repeatable Deployments** - Can recreate entire stack from scratch
6. **Best Practices** - Modular Terraform, multi-stage Docker, proper state management

## Technology Stack

**Infrastructure:**
- Terraform 1.6+
- Databricks Provider ~1.30+
- Azure Provider ~3.80+

**Application:**
- Python 3.11
- Streamlit
- Databricks SDK
- LangChain

**DevOps:**
- GitHub Actions
- Docker
- Azure CLI

**Cloud:**
- Azure Databricks
- Azure App Service
- Azure Container Registry
- Azure Key Vault
- Azure Blob Storage (state)
