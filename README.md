# SentinelAI


SentinelAI investigates customer-support cases using a local LLM, retrieval over policy documents, and tightly scoped MCP tools. It is designed as a reliability-focused AI engineering project: deterministic checks validate the agent's tool use and final answer instead of treating fluent model output as ground truth.



| **Problem** | Support agents can invent policy, inspect the wrong order, or miss evidence. |
|---|---|
| **Approach** | Local Qwen agent + RAG + narrowly scoped MCP tools + deterministic evidence gate. |
| **Proof** | MiniLM + FAISS reached **1.000 Recall@3/5** and **0.932 MRR** on the included retrieval benchmark. |
| **Honest baseline** | The latest 20-case end-to-end run achieved **45% overall success**; failures are retained and measured rather than hidden. 

## What it does

A customer says they were charged twice. SentinelAI:

1. identifies the customer's in-scope orders;
2. calls deterministic payment and operations tools to inspect the evidence;
3. retrieves the relevant NovaShop policy through semantic search;
4. rejects answers that lack required evidence or verified facts; and
5. returns a verified response or escalates the case for human review.

```text
Customer request
       |
       v
Local Qwen agent --> execution scope --> MCP tools
       |                                  |- Support DB (SQLite)
       |                                  |- Operations rules
       |                                  `- Policy search (MiniLM + FAISS)
       v
EvidenceGate --> verified answer or human review
```

## Why this is different

The LLM proposes an investigation; it does not get unrestricted database or code access, and it does not have final authority. SentinelAI adds several guardrails:

- **Scoped capabilities:** the model can call named MCP tools, not arbitrary SQL or Python.
- **Execution scope:** customer and order identifiers are constrained as evidence accumulates.
- **Deterministic decisions:** duplicate-payment and operations checks are implemented as business rules, not model guesses.
- **Evidence-gated answers:** required tool calls, policy retrieval, and answer facts are checked before accepting a response.
- **Observable failures:** benchmark output records coverage, accuracy, model/tool calls, rejections, tokens, and latency.

## Results

### Retrieval benchmark

The included benchmark compares lexical retrieval with the semantic retriever over the policy corpus.

| Retriever | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| TF-IDF | 0.636 | 0.818 | 0.955 | 0.759 |
| MiniLM + FAISS | **0.864** | **1.000** | **1.000** | **0.932** |

### Latest end-to-end agent benchmark

This is a 20-case local-model baseline, saved in [`artifacts/evaluations/agent_benchmark_latest.json`](artifacts/evaluations/agent_benchmark_latest.json). It is intentionally reported as-is: the project measures where a small local model fails and routes unsupported conclusions to human review.

| Metric | Result |
|---|---:|
| Completion rate | 75% |
| Required duplicate-payment tool coverage | 70% |
| Duplicate-payment accuracy | 70% |
| Policy-retrieval coverage | 95% |
| Final-answer fact coverage | 70% |
| Overall success | **45%** |
| Average latency | 94.25 s |
| Average model / tool calls | 6.20 / 5.95 |

The key engineering outcome is not that a 1.7B local model is perfect; it is that unsupported or incomplete answers are measurable and can be rejected rather than silently presented as correct.

## Stack

Python · FastAPI · SQLAlchemy · SQLite · Ollama · Qwen3 1.7B · MCP · sentence-transformers · FAISS · scikit-learn · pytest

## Run it locally

Prerequisites: Python 3.11+ and [Ollama](https://ollama.com/) running locally.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ollama pull qwen3:1.7b
python -m database.seed
pytest -v
```

Run a sample duplicate-payment investigation:

```bash
python scripts/run_agent.py
```

Run the full benchmark or a single case:

```bash
python scripts/run_agent_benchmark.py
python scripts/run_agent_benchmark.py --case agent-dup-001
```

Compare the two retrieval strategies:

```bash
python -m sentinel.evaluation.compare_retrievers
```

Start the API and check its health endpoint:

```bash
uvicorn apps.api.main:app --reload
curl http://127.0.0.1:8000/v1/health
```

## Project map

```text
sentinel/
  agent/           controlled agent, tool registry, execution scope
  business/        deterministic support and payment rules
  evaluation/      retrieval and end-to-end benchmarks
  models/          local Ollama client
  repositories/    database access layer
  retrieval/       document chunking, TF-IDF, embeddings, FAISS
  verification/    EvidenceGate and answer-fact checks
mcp_servers/       support database, operations, and knowledge MCP servers
data/              synthetic NovaShop policies and benchmark cases
database/          schema, session, and deterministic seed data
tests/             unit and integration coverage
```
