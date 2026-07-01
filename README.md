# Travel Reimbursement Approval Agent

A professional prototype for an MNC‑level demo.  
Uses **Mistral API** (open‑source model), **Qdrant** vector DB, and **LangChain** to decide Approve / Partially Approve / Reject / Manual Review with streaming UI.

## Features
- Claim intake via JSON (API + UI)
- Semantic policy retrieval using Qdrant
- 5 tools: policy lookup, receipt check, per‑diem, duplicate detection, approval threshold
- Agentic workflow with live streaming of thoughts & tool calls
- Structured JSON output with confidence, deductions, policy references
- Manual review handling

## Tech Stack
- Python 3.10+, FastAPI, Uvicorn
- Mistral API (mistral‑large‑latest)
- Qdrant (Docker)
- LangChain & langchain‑mistralai
- HTML + CSS + JavaScript (EventSource)

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Mistral API key ([console.mistral.ai](https://console.mistral.ai))

### 1. Clone & Environment
```bash
git clone <your-repo> travel_reimbursement_agent/
cd travel_reimbursement_agent
conda create -n travel_agent python=3.11
conda activate travel_agent
pip install -r requirements.txt