# AI Nexus — Requirements & Architecture Traceability Matrix

## Overview
**AI Nexus — Intelligent Multi-Model API Hub**
"One API. Any AI. Intelligent routing."
A production-style configurable AI API gateway platform allowing administrators to create reusable AI-powered API connectors without writing backend code for each use case.

---

## 1. Traceability Matrix

| Section | Requirement | Implementation Component | Status |
|---|---|---|---|
| **2.A** | Admin connector creation (name, description, provider, model, prompt, inputs, schema, auth, active/disabled) | `backend/models.py`, `backend/routers/connectors.py`, `frontend/src/components/ConnectorForm.tsx` | Pending |
| **2.B** | Multiple AI providers (Gemini, OpenAI, modular adapter pattern for Anthropic/Groq) | `backend/services/providers/base.py`, `backend/services/providers/gemini.py`, `backend/services/providers/openai.py`, `backend/services/providers/registry.py` | Pending |
| **3** | Dynamic input system (Text, Number, Boolean, Image, File, JSON with validation, required/optional, defaults) | `backend/services/input_validator.py`, `frontend/src/components/DynamicFieldEditor.tsx`, `frontend/src/components/DynamicForm.tsx` | Pending |
| **4** | Dynamic structured output schema (JSON-schema like, provider instructions, parse, validate, normalize) | `backend/services/schema_engine.py`, `frontend/src/components/SchemaEditor.tsx` | Pending |
| **5** | Real generated API endpoints (`POST /api/v1/run/{slug}`, authentication, validation, provider dispatch, persistence, standard response envelope) | `backend/routers/gateway.py` | Pending |
| **6** | Automatic API documentation (endpoint URL, headers, parameter table, cURL sample, request/response examples) | `backend/routers/connectors.py` (docs generation), `frontend/src/components/ApiDocs.tsx` | Pending |
| **7** | API testing playground (dynamically generated form, run test, show latency, cost, tokens, raw request/response trace) | `frontend/src/components/Playground.tsx` | Pending |
| **8** | Persistent usage logging (connector_id, timestamp, provider, model, latency, tokens, cost, status, error, request_id, trace) | `backend/models.py` (RequestLog), `backend/services/logger_service.py`, `backend/routers/analytics.py` | Pending |
| **9** | Admin dashboard (metrics, connectors table/cards, request count, success rate, cost, latency, actions) | `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/AnalyticsCharts.tsx` | Pending |
| **10** | Security (Backend API keys in env, application API keys with SHA-256 hash validation, payload & file size guards, sanitized errors) | `backend/services/auth.py`, `backend/core/config.py`, `backend/middleware/error_handler.py` | Pending |
| **11** | Live deployment readiness (Dockerfile, Procfile / render.yaml, health endpoint, env documentation, standalone static build serving) | `Dockerfile`, `docker-compose.yml`, `render.yaml`, `backend/main.py` | Pending |
| **12** | Responsive UI (Modern developer-tool aesthetic, dark/light theme, clean cards, mobile/tablet/desktop) | `frontend/src/index.css`, Responsive Tailwind/CSS layouts | Pending |
| **13** | Required Demo Connectors (1. Business Card Scanner [Vision], 2. Article Intelligence [Text]) | `backend/seed.py` (automated seeds on initial startup) | Pending |
| **14** | Intelligent Model Routing (Specific, Cheapest, Fastest, Balanced, Highest Quality, Auto with deterministic score engine) | `backend/services/routing_engine.py` | Pending |
| **15** | Cost-aware routing & tracking (Token pricing catalog, cost calculation, daily/weekly cost aggregation) | `backend/services/cost_catalog.py`, `backend/routers/analytics.py` | Pending |
| **16** | Automatic Fallback (Primary failure -> fallback model retry with audit log) | `backend/services/fallback_service.py` | Pending |
| **17** | Model Comparison / Evaluation (Dual-model execution with latency/cost/token diff) | `backend/routers/evaluations.py`, `frontend/src/components/ModelCompare.tsx` | Pending |
| **18** | Automatic Response Repair (JSON syntax repair, schema coercion, retry pipeline) | `backend/services/repair_service.py` | Pending |
| **19** | Endpoint Blueprint Generator (Prompt-to-connector generator with review step) | `backend/routers/blueprint.py`, `frontend/src/components/BlueprintModal.tsx` | Pending |
| **20** | Request Trace (End-to-end execution pipeline steps visualized with unique Request IDs) | `backend/routers/gateway.py` (trace metadata), `frontend/src/components/RequestTraceView.tsx` | Pending |
| **21** | Provider Abstraction Design (`AIProvider` interface with `generate()`, `supports_vision()`, etc.) | `backend/services/providers/base.py` | Pending |
| **22** | Model Catalog (Metadata for Gemini, OpenAI, Groq, Anthropic with cost, speed, quality) | `backend/services/cost_catalog.py` & DB model table | Pending |
| **23** | Database Design (SQLAlchemy async SQLite + Postgres compatible) | `backend/database.py`, `backend/models.py` | Pending |
| **24** | Robust Error Handling (Standard envelope, safe error codes, no stack leaks) | `backend/middleware/error_handler.py` | Pending |
| **25** | Automated Testing (Unit tests for validation, routing, provider mocks, API gateway, fallback) | `backend/tests/test_*.py`, pytest | Pending |
| **26** | Health Check (`GET /health` with DB status) | `backend/routers/health.py` | Pending |
| **27** | Documentation (`README.md`, setup guide, architecture diagrams, cURL examples) | `README.md`, `ARCHITECTURE.md` | Pending |
| **33** | Final Acceptance Scenarios (A through G verification) | `backend/tests/test_acceptance.py` & manual verification script | Pending |

---

## 2. Phased Execution Plan

- **Phase 1 (Foundation & Core DB)**:
  - Database schema (`SQLAlchemy` async with SQLite/Postgres compatibility).
  - Models: `Connector`, `ConnectorInput`, `ApiKey`, `RequestLog`, `ModelCatalogEntry`.
  - Migrations / Auto-init engine with Seed Data (Business Card Scanner + Article Intelligence).

- **Phase 2 (Provider Adapters & Validation Engine)**:
  - Common `AIProvider` base class.
  - `GeminiProvider` (using official `google-genai` / REST).
  - `OpenAIProvider` (using `openai` / httpx REST compatible with OpenAI-compatible providers like Groq).
  - Dynamic input validation engine (`Text`, `Number`, `Boolean`, `Image`, `File`, `JSON`).
  - Dynamic output schema enforcement & structured prompt injection.

- **Phase 3 (Gateway & Auth Execution Engine)**:
  - Public endpoint `POST /api/v1/run/{slug}`.
  - API Key hash authentication (`X-API-Key`).
  - Request logging & trace generation (`REQ-YYYYMMDD-XXXX`).
  - Standard response envelope.
  - Error handling middleware.

- **Phase 4 (Intelligence Layer)**:
  - Intelligent router (Cheapest, Fastest, Balanced, Highest Quality, Auto).
  - Model catalog with cost calculation.
  - Automatic fallback handler.
  - Automatic response repair (JSON repairs, markdown fence stripping, regex extraction, schema healing).
  - Blueprint generator (AI/heuristic assisted connector spec generator).
  - Model comparison runner.

- **Phase 5 (Frontend Single-Page Application)**:
  - React + TypeScript + Vite + Tailwind CSS / Lucide icons.
  - Admin Dashboard with metrics & charts.
  - Connector Manager (List, Create, Edit, Toggle, Delete, Blueprint Modal).
  - Interactive Playground with dynamic form generator & Request Trace visualizer.
  - Automatic Interactive API Documentation with cURL & code snippets.
  - Logs & Analytics explorer.
  - Model Comparison tab.

- **Phase 6 (Testing, Deployment & Acceptance)**:
  - Pytest suite covering all mandatory and intelligence components with mocked providers.
  - Integration smoke tests.
  - Production build & single-container / unified server packaging.
  - Final Acceptance verification (Scenarios A through G).
  - Complete `README.md` and `REQUIREMENTS_STATUS.md`.
