# NextLevel RAG System

Production-ready RAG system for Databricks with LangGraph agents.

## 🚀 Features

- **LangGraph Agents**: Summarization and question generation
- **Terraform Infrastructure**: Complete IaC for Databricks
- **Widget-Based Config**: Centralized configuration via Terraform
- **CI/CD**: Automatic deployment via GitHub Actions

## 📁 Structure

```
NextLevel/
├── agents/                  # LangGraph agents
│   ├── summarization/      # Extract technical/operator info
│   └── question_generation/ # Generate training questions
├── jobs/                    # Databricks job notebooks
│   └── ingest_pipeline.py  # PDF ingestion pipeline
├── terraform/               # Infrastructure as Code
│   ├── bootstrap/          # Azure resources setup
│   └── modules/            # Databricks resources
└── docs/                    # Documentation
```

## 🔧 Setup

1. Run bootstrap to create Azure resources
2. Configure Terraform variables
3. Deploy infrastructure with Terraform
4. Push code - CI/CD handles the rest!

## 📚 Documentation

See `docs/` folder for detailed guides.

---

**Status:** ✅ Production Ready
