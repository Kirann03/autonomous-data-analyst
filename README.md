# Autonomous Data Analyst

## Overview

Autonomous Data Analyst is a Streamlit application for turning structured business data into validated, evidence-grounded analysis. It combines ingestion, ETL, SQL storage, deterministic analytics, and an optional LLM planner without allowing the LLM to execute code, SQL, shell commands, filesystem operations, or arbitrary URLs.

## Problem

Business teams need quick answers from CSV, cloud, database, and API data, but manual analysis is slow and LLM-only answers can be unreliable. This project keeps calculations deterministic while using an LLM only to plan approved analyses and interpret validated evidence.

## Architecture

```text
Data sources (CSV/XLSX, REST API, S3, PostgreSQL)
  -> Pandas DataFrame / ETL
  -> Dataset profiling
  -> Question router
  -> Deterministic query engine OR controlled LLM planner
  -> Validated plan and registered Pandas tools
  -> Evidence validation
  -> Root-cause structure and visualization guidance
  -> Auditable business report
```

## Data Sources

- CSV/XLSX uploads in Streamlit
- AWS S3 CSV ingestion
- PostgreSQL 18, with SQLite local fallback
- User-supplied REST JSON APIs (`GET` only)

API JSON arrays and simple `data`, `results`, `items`, or `records` wrappers are normalized into the same DataFrame path as uploads. This keeps profiling, deterministic analytics, visualizations, and the Autonomous Analyst source-agnostic.

## Autonomous Agent

Simple questions use the deterministic query engine. Complex questions use the controlled planner:

```text
Question -> complexity router -> LLM plan or deterministic fallback
         -> plan validation -> registered deterministic tools
         -> evidence validation -> report / visualization guidance
```

The tool registry validates tool names, columns, filters, aggregations, and step limits before Pandas executes calculations. If a supported planner or narrative request fails, a deterministic fallback preserves validated evidence rather than fabricating an answer.

Regional profitability reports separate Observation, Evidence, Interpretation, and Recommendation. Aggregate data is not treated as proof of causality.

## LLM Providers

### Local mode

Ollama with Qwen3 is the default provider:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

```powershell
ollama pull qwen3:8b
ollama serve
```

### Optional OpenAI mode

OpenAI is optional and must be explicitly selected:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=
```

Optional Ollama-to-OpenAI fallback requires `LLM_FALLBACK_ENABLED=true`. No OpenAI key is required for local/Ollama mode. LLM providers only plan or interpret; they never invoke analytics tools directly.

## Analytics and Evidence

Implemented deterministic operations include aggregation, group-by, top/bottom N, missing-value and duplicate checks, descriptive statistics, correlations, category analysis, and time-series summaries. Results are validated for successful structure and non-finite values before use in reports.

Forecasting and other ML analysis are not implemented. Requests for them return a controlled unsupported response.

## Visualization Recommendations

Each recommendation includes chart type, title, axes, group-by field, validated filters, and rationale. The application outputs concise instructions for Power BI and Tableau; it does not manipulate report files automatically.

## Power BI Dashboard

The completed dashboard contains:

1. Executive Overview
2. Regional Analysis
3. Customer Analysis
4. Product Analysis

Supporting model, DAX, KPI, data-quality, and dashboard documentation is in `docs/`.

## API Security

REST API requests are user-initiated in Streamlit. The LLM cannot select or call API URLs. API ingestion enforces:

- public `http`/`https` URLs only
- blocks localhost, loopback, private, link-local, metadata, reserved, multicast, and unspecified addresses
- hostname resolution before request
- redirects disabled
- JSON content required
- timeouts and streamed response-size limits (`API_MAX_RESPONSE_MB`, default 10 MB)
- optional headers held in memory only and never logged

POST, OAuth, pagination, and API-specific SDKs are intentionally not implemented.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure only the services you intend to use in `.env`. Do not commit `.env`.

## Running

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Local/S3 ETL commands:

```powershell
python scripts/run_pipeline.py --source local
python scripts/run_pipeline.py --source s3
```

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .test-tmp -p no:cacheprovider
```

Tests mock API, Ollama, OpenAI, S3, and database-facing dependencies as appropriate; they do not require a live OpenAI key.

## Project Structure

```text
app.py                 Streamlit application
src/                   analytics, agent, configuration, LLM, and data-source modules
src/llm/               provider interface, Ollama, OpenAI, and factory
src/data_sources/      secured REST API ingestion
etl/                   extract, transform, load, and pipeline orchestration
database/              schema and KPI queries
aws/                   S3 client
docs/                  Power BI implementation documentation
scripts/               database, pipeline, and connection commands
tests/                 offline unit and integration tests
```

## Security and GitHub Safety

`.env`, virtual environments, cache artifacts, and local databases are ignored by Git. Credentials are loaded from environment variables and should never be committed, printed, or placed in source code.

## Limitations

- Complex local Ollama planning can depend on local hardware/runtime health; supported questions retain a deterministic fallback.
- OpenAI live mode requires a user-supplied API key and has not been exercised without one.
- REST API ingestion currently supports public GET/JSON endpoints only.
- Forecasting, classification, anomaly detection, and other ML capabilities are not implemented.
