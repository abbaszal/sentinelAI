# SentinelAI

> **Local-first agentic AI system for customer-support investigations using RAG, MCP tools, local LLMs, deterministic verification, and evaluation.**

SentinelAI is a portfolio project focused on building a **reliable AI agent**, not just a chatbot.  
It combines **RAG**, **tool-using agents**, **MCP**, **Ollama/Qwen**, structured business logic, and benchmark-driven evaluation.

---

## What this project demonstrates

- **RAG** with Markdown policies, MiniLM embeddings, and FAISS
- **Agentic workflows** with multi-step tool use
- **MCP** servers for database, knowledge, and business operations
- **Local LLMs** with Ollama + Qwen3 1.7B on CPU
- **Deterministic business rules** for trusted decisions
- **Execution scope** to stop the agent accessing unrelated orders
- **Evidence verification** before accepting final answers
- **Agent benchmarks** for correctness, tool usage, latency, and token cost

---

## Architecture

```text
User
  ↓
Qwen Agent
  ↓
Execution Scope
  ↓
MCP Tools
  ├── Support DB → SQLAlchemy → SQLite
  ├── Operations → Deterministic Business Rules
  └── Knowledge → MiniLM + FAISS → Policy Docs
  ↓
EvidenceGate
  ↓
Verified Answer / Human Review
```

---

## Core stack

`Python` · `FastAPI` · `SQLAlchemy` · `SQLite` · `Ollama` · `Qwen3` · `MCP` · `sentence-transformers` · `FAISS` · `scikit-learn` · `pytest`

---

## RAG

NovaShop policies are stored as Markdown documents and chunked by section with size limits and overlap.

Two retrievers were implemented and benchmarked:

| Retriever | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| TF-IDF | 0.636 | 0.818 | 0.955 | 0.759 |
| MiniLM + FAISS | **0.864** | **1.000** | **1.000** | **0.932** |

The embedding retriever became the main knowledge-search system.

---

## MCP tools

The agent does not receive unrestricted SQL or arbitrary Python access.

It works through narrow MCP capabilities such as:

```text
get_customer_summary
get_orders
get_payment_status
get_shipment_status
get_refunds
search_policy
detect_duplicate_payment
check_cancellation_eligibility
```

This keeps tool usage structured, testable, and auditable.

---

## Controlled agent

The local Qwen model can investigate cases by calling tools, but it does not have final authority.

Example duplicate-payment flow:

```text
Customer complaint
      ↓
get_orders(customer_id)
      ↓
detect_duplicate_payment(order_id)
      ↓
search_policy(...)
      ↓
EvidenceGate
      ↓
final answer
```

The controller also enforces:

- maximum reasoning steps,
- maximum tool calls,
- repeated-call protection,
- tool allowlists,
- dynamic order/customer scope.

---

## Why verification was added

During testing, the LLM sometimes:

- skipped required tools,
- used the wrong order,
- ignored correct evidence,
- invented policy,
- or omitted confirmed facts.

Instead of relying only on prompt engineering, SentinelAI adds a deterministic `EvidenceGate`.

It can require missing evidence:

```text
get_orders(customer_id=2)
detect_duplicate_payment(order_id=2)
detect_duplicate_payment(order_id=3)
search_policy(...)
```

It can also reject final answers that omit verified facts such as:

```text
Order 2 → duplicate payment → overpayment 49.99
Order 3 → duplicate payment → overpayment 39.90
```

After each tool batch, the verifier can also suggest only the **next missing required tools**, reducing unnecessary agent exploration.

---

## Synthetic NovaShop environment

The project includes deterministic test data for:

- normal orders,
- duplicate payments,
- failed payments,
- cancelled-but-charged orders,
- shipments,
- refunds,
- damaged-item scenarios.

This provides known ground truth for evaluating the agent.

---

## Evaluation

SentinelAI evaluates both individual components and the full agent.

### Retrieval evaluation

Metrics:

```text
Recall@1
Recall@3
Recall@5
MRR
```

### Agent evaluation

The end-to-end benchmark measures:

```text
completion rate
required tool coverage
duplicate-payment accuracy
policy retrieval coverage
final-answer fact coverage
model calls
tool calls
verification rejections
prompt/output tokens
latency
```

The benchmark oracle is calculated from the database and deterministic business rules, not from the LLM itself.

---

## Latest full agent benchmark

> Fill this section after running the full benchmark.

```text
Cases:                     20
Completed:                 0.750
Duplicate coverage:        0.700
Duplicate accuracy:        0.700
Policy coverage:           0.950
Answer fact coverage:      0.700
Overall success:           0.450

Average model calls:       6.20
Average tool calls:        5.95
Average prompt tokens:     8,634.15
Average latency:           94.25s
```

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

ollama pull qwen3:1.7b

python -m database.seed

pytest -v
```

Run one real agent investigation:

```bash
python scripts/run_agent.py
```

Run the agent benchmark:

```bash
python scripts/run_agent_benchmark.py
```

---

## Project structure

```text
sentinel/
├── agent/          # controlled agent, MCP registry, execution scope
├── business/       # deterministic business rules
├── evaluation/     # retrieval + agent benchmarks
├── models/         # Ollama / LLM client
├── repositories/   # database access
├── retrieval/      # TF-IDF, embeddings, FAISS
└── verification/   # EvidenceGate

mcp_servers/
├── support_db/
├── operations/
└── knowledge/

data/
├── policies/
└── benchmarks/
```

