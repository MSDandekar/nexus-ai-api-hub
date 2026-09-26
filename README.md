# AI Nexus — Intelligent Multi-Model API Hub

> **"One API. Any AI. Intelligent routing."**

[![CI Tests](https://img.shields.io/badge/pytest-18%20passed-emerald)](file:///backend/tests)
[![Status](https://img.shields.io/badge/status-production--ready-cyan)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688)]()
[![React](https://img.shields.io/badge/React-19+-61DAFB)]()

**AI Nexus** is a production-grade, configurable AI API gateway and orchestration platform. It enables administrators and developers to create reusable, AI-powered API connectors with arbitrary dynamic input parameters and strict structured output schemas **without writing any backend code for each use case**.

---

## 1. Architecture Overview

```mermaid
flowchart TD
    Client[External Client / App] -->|POST /api/v1/run/:slug\nX-API-Key: nx_live_...| Gateway[API Gateway Layer]

    subgraph AI Nexus Engine
        Gateway --> Auth[SHA-256 Auth & Rate Validator]
        Auth --> InputVal[Dynamic Input Validator\nText, Number, Boolean, Image, File, JSON]
        InputVal --> Router[Intelligent Routing Engine\nCheapest | Fastest | Balanced | Quality | Auto]
        
        Router --> Catalog[(Model Pricing Catalog & DB)]
        Router --> Fallback[Fallback & Resilience Orchestrator]
        
        Fallback --> ProviderAdapter{AIProvider Adapter}
        ProviderAdapter -->|Gemini REST| Gemini[Google Gemini Adapter]
        ProviderAdapter -->|OpenAI REST| OpenAI[OpenAI Adapter]
        ProviderAdapter -->|Groq REST| Groq[Groq Adapter]
        
        Gemini & OpenAI & Groq --> OutputEngine[Dynamic Output Schema Engine]
        OutputEngine -->|Invalid JSON / Drift?| RepairEngine[Automatic Response Repair\nHeuristic + Single-Pass Repair]
        RepairEngine --> OutputEngine
        
        OutputEngine --> Logger[Persistent Usage & Cost Logger]
    end

    Logger --> DB[(SQLite / PostgreSQL DB)]
    OutputEngine -->|Standard JSON Envelope| Client
```

---

## 2. Key Features

- **Administrator Connector Creation**: Define custom APIs with names, descriptions, provider selection, prompts, dynamic parameters, and JSON schemas in seconds.
- **Provider-Adapter Architecture**: Clean interface abstraction (`AIProvider`) decoupling upstream endpoints from specific AI providers (Google Gemini, OpenAI, Groq, Anthropic).
- **Dynamic Input System**: Native support and runtime validation for `text`, `number`, `boolean`, `image`, `file`, and `json` inputs.
- **Dynamic Structured Output Schema**: Enforces output schemas with type normalization, coercion, and standard response envelopes.
- **Real Generated Endpoints**: Publicly callable `POST /api/v1/run/{slug}` endpoints protected by API key authentication.
- **Automatic Interactive API Docs**: Dynamically generates cURL commands, header requirements, parameter tables, and response schemas.
- **Interactive API Playground**: Auto-generates testing forms based on connector inputs with live response previews and execution tracing.
- **Intelligent & Cost-Aware Routing**: Deterministic engine supporting `Specific`, `Cheapest`, `Fastest`, `Highest Quality`, `Balanced`, and `Auto` strategies based on real-time modality and cost factors.
- **Automatic Fallback**: Automatic failover to secondary configured models upon transient rate limits or provider downtime.
- **Automatic Response Repair**: Multi-stage JSON recovery (fenced block extraction, trailing comma repairs, single-pass AI schema repair).
- **Request Trace Visualization**: End-to-end execution pipeline steps logged with unique `REQ-YYYYMMDD-XXXX` identifiers.
- **Model Evaluation & Comparison**: Side-by-side benchmark runner comparing latency, token consumption, cost differentials, and schema adherence.
- **Endpoint Blueprint Generator**: Prompt-to-connector generator proposing complete connector specs from natural language descriptions.
- **Persistent Analytics & Cost Metering**: Tracks input/output token counts, estimated USD costs, success rates, and historical logs across restarts.

---

## 3. Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Asyncio)
- **Database**: SQLite (via `aiosqlite`) for development; PostgreSQL compatible via standard `DATABASE_URL`
- **Frontend**: React 19, TypeScript, Vite, Vanilla CSS design system with Lucide icons
- **Testing**: `pytest`, `pytest-asyncio`, `httpx` (18/18 passing tests)
- **Deployment**: Multi-stage Docker container, `docker-compose.yml`, `render.yaml`

---

## 4. Pre-Configured Demonstration Connectors

AI Nexus initializes automatically with two demonstration connectors:

1. **Business Card Scanner** (`card-scanner`):
   - **Input**: `image` (Type: `image`, required: true)
   - **Provider**: Google Gemini (`gemini-2.5-flash`) with OpenAI (`gpt-4o-mini`) fallback
   - **Routing**: `balanced`
   - **Output Schema**: Contact JSON (`name`, `company`, `designation`, `phone`, `email`, `website`)

2. **Article Intelligence** (`article-intelligence`):
   - **Inputs**: `article_text` (Type: `text`, min length 20), `focus_area` (Type: `text`, optional)
   - **Provider**: OpenAI (`gpt-4o-mini`) with Gemini fallback
   - **Routing**: `balanced`
   - **Output Schema**: Editorial JSON (`title`, `summary`, `key_points`, `sentiment`, `topics`)

---

## 5. Local Setup & Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Step 1: Clone & Configure Environment
```bash
cp .env.example .env
```
Add your API keys to `.env`:
```env
GEMINI_API_KEY="your-gemini-key"
OPENAI_API_KEY="your-openai-key"
DEFAULT_ADMIN_API_KEY="nexus-dev-master-key-2026"
```

### Step 2: Install Python Dependencies & Seed Database
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\pip install -r <(echo "fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy[asyncio] greenlet aiosqlite httpx python-multipart pytest pytest-asyncio")
.\venv\Scripts\python -m backend.seed
```

### Step 3: Build Frontend Assets
```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Run Unified Server
```bash
.\venv\Scripts\python -m uvicorn backend.main:app --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the complete developer dashboard!

---

## 6. Running Automated Tests

All core requirements, routing strategies, fallback mechanisms, schema repair pipelines, and acceptance scenarios A through G are verified by automated tests:

```bash
.\venv\Scripts\pytest backend\tests -v
```

Output:
```text
backend/tests/test_acceptance.py::test_acceptance_scenarios_a_through_g PASSED
backend/tests/test_api_gateway.py::test_health_endpoint PASSED
backend/tests/test_api_gateway.py::test_gateway_unauthorized PASSED
backend/tests/test_api_gateway.py::test_gateway_validation_failure PASSED
backend/tests/test_api_gateway.py::test_gateway_successful_execution_and_trace PASSED
backend/tests/test_api_gateway.py::test_gateway_automatic_fallback PASSED
backend/tests/test_api_gateway.py::test_disabled_connector PASSED
backend/tests/test_api_gateway.py::test_analytics_and_logs PASSED
backend/tests/test_routing.py::test_routing_vision_modality_filter PASSED
backend/tests/test_routing.py::test_routing_strategies PASSED
backend/tests/test_routing.py::test_repair_markdown_extraction PASSED
backend/tests/test_routing.py::test_repair_trailing_commas PASSED
backend/tests/test_schema.py::test_schema_valid_and_normalization PASSED
backend/tests/test_schema.py::test_schema_missing_required PASSED
backend/tests/test_validation.py::test_dynamic_text_and_number_validation PASSED
backend/tests/test_validation.py::test_missing_required_field PASSED
backend/tests/test_validation.py::test_text_length_and_number_range PASSED
backend/tests/test_validation.py::test_image_base64_input PASSED
============================== 18 passed in 0.66s ==============================
```

---

## 7. Calling Generated APIs (cURL Examples)

### Example 1: Article Intelligence API
```bash
curl -X POST 'http://localhost:8000/api/v1/run/article-intelligence' \
  -H 'X-API-Key: nexus-dev-master-key-2026' \
  -H 'Content-Type: application/json' \
  -d '{
    "article_text": "Neural scaling laws have demonstrated predictable loss reductions across compute and dataset magnitudes, guiding multi-billion dollar frontier cluster architectures.",
    "focus_area": "Compute Infrastructure"
  }'
```

#### Standard Response:
```json
{
  "success": true,
  "data": {
    "title": "Predictability in Neural Scaling and Cluster Architecture",
    "summary": "The excerpt discusses empirical neural scaling laws that forecast computational loss reductions as compute and dataset sizes expand.",
    "key_points": [
      "Loss reductions correlate predictably with compute expansion",
      "Guides capital expenditure on AI infrastructure clusters"
    ],
    "sentiment": "positive",
    "topics": ["Artificial Intelligence", "Infrastructure", "Scaling Laws"]
  },
  "error": null,
  "meta": {
    "request_id": "REQ-20260927-4E2A1",
    "connector": "article-intelligence",
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "routing": {
      "strategy": "balanced",
      "task_type": "structured_extraction",
      "reason": "Balanced selection: Task matched with Gemini 2.5 Flash",
      "candidates_evaluated": 7
    },
    "fallback_used": false,
    "repair_attempted": false,
    "response_time_ms": 385.2,
    "tokens": {
      "input": 142,
      "output": 84,
      "total": 226
    },
    "estimated_cost_usd": 0.000071,
    "trace": [
      {"step": "Request Received", "status": "ok", "detail": "Method POST on slug 'article-intelligence'"},
      {"step": "Authentication", "status": "ok", "detail": "Valid API key authorized"},
      {"step": "Connector Loaded", "status": "ok", "detail": "Loaded 'Article Intelligence' (active)"},
      {"step": "Input Validation", "status": "ok", "detail": "2 input fields verified"},
      {"step": "Model Routing", "status": "ok", "detail": "Strategy: BALANCED -> gemini/gemini-2.5-flash"},
      {"step": "AI Inference", "status": "ok", "detail": "Completed via gemini/gemini-2.5-flash in 340.5ms"},
      {"step": "Schema Validation", "status": "ok", "detail": "Output matches configured schema"},
      {"step": "Persistent Logging", "status": "ok", "detail": "Logged request REQ-20260927-4E2A1"}
    ]
  }
}
```

### Example 2: Business Card Scanner API (Multipart Form)
```bash
curl -X POST 'http://localhost:8000/api/v1/run/card-scanner' \
  -H 'X-API-Key: nexus-dev-master-key-2026' \
  -F 'image=@business_card.jpg'
```

---

## 8. Security Architecture

1. **Zero Secret Leakage**: Provider API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) reside exclusively in backend environment variables. They are never sent to the browser, stored in client-side bundles, or written to request logs.
2. **SHA-256 Application Keys**: Generated client API keys are hashed with SHA-256 before storage in the database. Full raw keys are displayed only once upon generation.
3. **Payload & Size Guards**: Multi-part and base64 uploads are limited to 10MB by default.
4. **Sanitized Error Envelopes**: Production API responses never leak internal Python stack traces; predictable error codes (`UNAUTHORIZED`, `VALIDATION_ERROR`, `PROVIDER_ERROR`) are provided with safe explanations.

---

## 9. Cloud Deployment

### Option A: Docker Deployment (Any Cloud / VPS)
```bash
docker build -t ai-nexus .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your-gemini-key" \
  -e OPENAI_API_KEY="your-openai-key" \
  -e DEFAULT_ADMIN_API_KEY="nexus-live-master-key" \
  ai-nexus
```

### Option B: 1-Click Render.com Blueprint
The repository includes a verified `render.yaml`. Connect your repository to Render, configure `GEMINI_API_KEY` and `OPENAI_API_KEY` under environment secrets, and deploy. The database persists automatically on the attached persistent disk.

### Option C: Health Check Verification
```bash
curl https://your-deployed-domain.com/health
# Returns: {"status": "ok", "database": "ok", "version": "1.0.0"}
```

---

## 10. Known Limitations & Extensibility

- **New Providers**: Adding Anthropic or a custom on-premise vLLM instance requires implementing the `AIProvider` base class and registering it in `backend/services/providers/registry.py`.
- **Database Scaling**: For high-concurrency deployments exceeding 1,000 req/sec, switch `DATABASE_URL` from SQLite to PostgreSQL (`postgresql+asyncpg://...`). No code changes are required.
