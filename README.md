# 🤖 AI-Powered Data Analyst

An end-to-end AI-powered data analytics application built with **Python, Pandas, Streamlit, and Generative AI**.

The application helps users transform raw CSV datasets into a structured analytics workflow through an interactive web application.

## Autonomous Data Analyst Agent

The application includes a controlled autonomous-analysis path alongside the existing deterministic query engine and AI insight features. Qwen3 plans and explains analysis, while registered Pandas tools perform every calculation.

```text
User
  → Streamlit
  → Agent Planner
  → Validated Analysis Plan
  → Tool Registry
  → Deterministic Analytics
  → Evidence Validation
  → Insight Generation
  → Visualization Recommendation
  → Business Report
```

The agent never executes LLM-generated Python, SQL, shell commands, URLs, or filesystem operations. It accepts only allow-listed tools and validates tool names, columns, aggregation methods, filters, and step counts before running calculations. The UI presents the answer and visualization guidance, with plan, evidence, and execution trace inside technical expanders.

Simple questions continue through the existing deterministic query engine where possible. Complex questions use the controlled planner and return validated evidence for Qwen3 to interpret.

### Local Ollama / Qwen3

Ollama runs locally and is configured through the ignored `.env` file:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT=120
```

Install and run the local model when required:

```powershell
ollama pull qwen3:8b
ollama serve
```

Ollama models, `.env`, AWS credentials, and PostgreSQL passwords are not committed to GitHub. A public deployment requires a hosted LLM service or separately hosted Ollama endpoint; it cannot rely on the developer machine's `localhost` service.

## SQL Data Layer

SQL provides a durable, queryable analytics layer between the cleaned CSV data and a future Power BI dashboard. The existing Streamlit AI analyst remains independent and continues to analyze uploaded datasets.

```text
CSV
  ↓
Python ETL
  ↓
SQL Database
  ↓
Power BI
```

The retail dataset is loaded into a small star-schema-inspired model:

- `fact_sales`: one record per `Order_ID`, with quantity, unit price, cost, discount, revenue, profit, profit margin, and sales target.
- `dim_customer`: source customer IDs.
- `dim_product`: product name and category.
- `dim_region`: region and state combinations.
- `dim_date`: calendar attributes used for monthly reporting.

The loader deletes and reloads these tables in one transaction, so rerunning it does not create duplicate orders. It supports SQLite for local development and SQLAlchemy URLs for PostgreSQL later.

### Configure and initialize locally

In PowerShell, install dependencies and select a local SQLite database:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///data/analytics.db"
python scripts/init_database.py
```

For PostgreSQL later, set `DATABASE_URL` to a standard SQLAlchemy PostgreSQL URL in `.env`; never commit that file. The initialization script reads `data/raw/sales.csv`, transforms it, creates the schema, loads it, and prints row-count and integrity checks.

`database/queries.sql` contains readable KPI queries for total revenue/profit/orders, monthly and regional performance, target achievement, low-margin products, and margin outliers.

### PostgreSQL production-style target

The same SQLAlchemy loader supports PostgreSQL 18 while retaining SQLite as a local fallback. Configure the ignored `.env` with a PostgreSQL SQLAlchemy URL, then run the S3 pipeline:

```powershell
python scripts/test_postgres_connection.py
python scripts/run_pipeline.py --source s3
```

```text
AWS S3
  ↓
Boto3
  ↓
Python ETL
  ↓
PostgreSQL 18
  ↓
Power BI
  ↓
Power Automate
```

The loader creates the analytics star-schema tables if absent and reloads only those managed tables; it does not drop or recreate the PostgreSQL database.

## S3 Ingestion

The cloud analytics ETL uses the source sales file from the configured AWS S3 bucket without exposing credentials. AWS configuration is loaded from the ignored `.env` file with `python-dotenv`.

```text
AWS S3
  ↓
raw/sales.csv
  ↓
Boto3
  ↓
Pandas DataFrame
  ↓
Python ETL
  ↓
SQL Database
  ↓
Power BI (planned)
```

### Pipeline modes

- **Local development:** reads `data/raw/sales.csv`; useful without an AWS connection.
- **S3/cloud mode:** reads `s3://<configured-bucket>/raw/sales.csv`; this is the default production-style source.

Both modes use the same `transform_sales_data()` and SQL loading logic.

```powershell
python scripts/run_pipeline.py --source local
python scripts/run_pipeline.py --source s3
```

Run a real, read-only connection and dataset-comparison check from the project root:

```powershell
python scripts/test_s3_connection.py
```

The script reports only the region, bucket, object metadata, and dataset shape. It never prints AWS credential values. Unit tests use mocks and require no AWS account access:

```powershell
python -m pytest -q
```

---

## 🚀 Project Overview

Traditional data analysis often requires multiple separate tools and manual steps for data cleaning, quality checking, profiling, analysis, and insight generation.

This project brings these stages together into a single interactive application.

The user can upload a CSV dataset, process and clean the data, evaluate its quality, perform analysis, generate AI-assisted insights, and download the cleaned dataset.

---

## ✨ Key Features

- 📁 Upload CSV datasets
- 🧹 Automated data cleaning
- 🛡️ Data quality assessment
- 📊 Dataset profiling
- 📈 Statistical analysis
- 📅 Date-based analysis
- 🔎 Categorical analysis
- 💡 AI-assisted insight generation
- 📥 Download cleaned datasets
- 🌐 Interactive web interface
- 🔄 End-to-end analytics workflow

---

## 🏗️ Application Workflow

```text
             CSV Dataset
                  │
                  ▼
          📁 Data Upload
                  │
                  ▼
          🧹 Data Cleaning
                  │
                  ▼
        🛡️ Data Quality Checks
                  │
                  ▼
        📊 Dataset Profiling
                  │
                  ▼
          📈 Data Analysis
                  │
                  ▼
         💡 AI-Assisted Insights
                  │
                  ▼
       📥 Download Cleaned Data
