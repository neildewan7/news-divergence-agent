# Working Conventions

## Stack
- Model: Gemini (latest available), accessed via Vertex AI (ChatVertexAI)
- Orchestration: LangChain MCP adapter + LangGraph ReAct agent
- Tool integration: Elastic MCP server
- Hosting target: Google Cloud Run
- Embeddings: Vertex AI multilingual text-embedding model
- Frontend: minimal single-page UI (plain HTML or React, TBD)

## Hackathon constraints
- No OpenAI, no Anthropic, no third-party LLMs in the deployed agent
- No tools that compete with Elastic (search/database) or Google Cloud
- All code newly written May 5 – June 11 2026
- Deadline: June 11 2026, 2:00 PM PT — hard cutoff

## Code conventions
- Language: Python
- Secrets: never committed; use .env + .gitignore
- Dependencies: track in requirements.txt
- Debug flag: keep DEBUG = False at top of agent.py; set True locally only

## What the agent does and does not do
- DOES: surface what each source claimed; flag where sources diverge; cite every claim
- DOES NOT: verify truth, score source reliability, produce ground-truth estimates
- Every claim in output must link to its source article — no floating numbers

## Repo layout (current)
- agent.py — main agent loop
- CHANGELOG.md — append an entry after every meaningful session
- CONVENTIONS.md — this file; update if conventions change
- PROJECT_KNOWLEDGE.md — product context and decisions; update if direction changes
