# HC AI Project History

## Overview
5-week development history of the HC AI medical platform, reconstructed from git commits.

---

## Week 1: Foundation (Jan 9-15, 2026)

### Jan 9 - Project Kickoff
- **Initial commit** - Project created
- **FHIR structure analysis** - Explored FHIR resource formats
- **Chunking strategy research** - Tested different chunking methods
- **Final chunking decision**: Recursive JSON splitter, min 100 / max 1000 chars
- **Embedding details** - Initial embedding configuration

### Jan 12 - Database Setup
- **PostgreSQL + pgvector implementation**
- Initial LangChain integration for vector operations

### Jan 13 - Embeddings Pipeline
- **Embeddings to DB finished** - Full pipeline working
- FHIR data successfully embedded and stored

### Jan 14 - Retrieval POC
- **POC_retrieval** - First retrieval proof of concept
- Cross-encoder reranking exploration
- README documentation
- Continued DB embedding while developing

### Jan 15 - Reranker Integration
- **Adjusted reranker** configuration
- **Ingested full JSON to DB** - Complete FHIR bundles stored

---

## Week 2: Agent Development (Jan 16-22, 2026)

### Jan 16 - First Agent
- **First run through on an agent** - Basic agent working
- **Frontend first try** - Initial React/Next.js setup
- Optimizations to agent logic

### Jan 17 - Continued Development
- Various agent improvements

### Jan 19 - Multi-Agent Architecture
- **Multi-agent implementation** - Researcher + Validator + Responder pattern
- **Tools implementation** - Medical domain tools (FDA, LOINC, etc.)
- Test fixes and refinements

### Jan 20 - Prompt Engineering
- **Clarified prompts** - First major prompt revision
- Improved agent instructions

### Jan 21-22 - RAGAS Evaluation
- **RAGAS implementation** - Evaluation framework setup
- Iterative improvements to RAGAS testing
- "Needs a lot more work" - ongoing evaluation challenges

---

## Week 3: Integration & Polish (Jan 25-31, 2026)

### Jan 25 - Testing
- **Fixed tests** - Test suite stabilization

### Jan 26 - API Consolidation
- **Consolidated API** - Unified FastAPI application
- **DB movement** - Database restructuring
- **Frontend and chatbot changes** - UI improvements

### Jan 27 - RAG Feature Complete
- **Finished RAG feature** - Core retrieval working
- **Layout and frontend integration** - UI polish
- **Prompting changes** - Continued prompt refinement

### Jan 28 - Working Prototype
- **Working prototype** achieved
- Prepared for RAGAS evaluation

### Jan 29 - RAGAS Testing
- Added RAGAS documentation
- Pre-evaluation preparation

### Jan 31 - Global Implementation Prep
- Prepared for broader deployment

---

## Week 4: Production Readiness (Feb 2-3, 2026)

### Feb 2 - Final RAG & AWS Prep
- **RAGAS testing** - Comprehensive evaluation
- **RAGAS improvements** - Based on test results
- **Final RAG before AWS** - Production-ready state

### Feb 3 - Cleanup
- Deleted api.log and other cleanup

---

## Week 5: Major Fixes & Optimization (Feb 4, 2026)

### Feb 4 - Extensive Improvements (Single Day - Many Commits)

#### Morning: Core Fixes
1. **CLAUDE.md added** - Project documentation for AI assistance
2. **Patient name prefixing** - Embedded content prefixed with patient names for better semantic search

#### Patient ID Auto-Injection
3. **Patient selection UI** - Frontend patient picker
4. **Auto-inject patient_id** - Tools receive patient_id from context automatically
5. **Context module** (`context.py`) - Thread-safe patient_id storage via contextvars

#### Search Fixes
6. **SQL-level patient filtering** - Fixed critical bug where semantic search wasn't filtering by patient
   - Problem: Danial Larsen's 2 conditions buried among 5000+ global results
   - Solution: SQL WHERE clause with patient_id before semantic ranking
   - Result: Accuracy improved from 0.513 to 0.83

#### Agent Robustness
7. **LangGraph recursion limits** - Unified AGENT_MAX_ITERATIONS=15
8. **Echo bug prevention** - Detect when researcher echoes system messages
9. **Empty query handling** - Graceful errors instead of 422s

#### Prompt Engineering (Research-Backed)
10. **Query decomposition** - Broad questions trigger multiple tool calls
11. **Date extraction** - Explicit instructions for FHIR date fields
12. **Response Synthesizer** - New agent for user-friendly output formatting
13. **Validator focus shift** - Accuracy over formatting

#### Frontend Polish
14. **Removed prompt dialog** - Streamlined patient selection
15. **Reorganized ReferencePanel** - Patient first, then prompts
16. **Visual indicators** - Selected patient shown in chat header

#### Evening: Hallucination Debugging (This Session)
17. **Identified example contamination** - LLM copying prompt examples as real data
18. **Removed all medical examples** - Replaced with placeholders
19. **Session history disabled** - Prevent cross-session pollution
20. **Model upgrade** - Changed from llama3.1:8b to qwen2.5:32b
21. **Debug logging** - Added DEBUG_HALLUCINATION flag

---

## Key Milestones

| Date | Milestone |
|------|-----------|
| Jan 9 | Project started |
| Jan 13 | Embeddings pipeline complete |
| Jan 16 | First working agent |
| Jan 19 | Multi-agent architecture |
| Jan 27 | RAG feature complete |
| Jan 28 | Working prototype |
| Feb 2 | Production-ready for AWS |
| Feb 4 | Major bug fixes, model upgrade |

---

## Architecture Evolution

### Phase 1: POC (Week 1)
```
FHIR JSON → Chunker → Embeddings → PostgreSQL
```

### Phase 2: Basic Agent (Week 2)
```
User Query → Single Agent → Response
```

### Phase 3: Multi-Agent (Week 2-3)
```
User Query → Researcher → Validator → Responder → Response
```

### Phase 4: Production (Week 4-5)
```
Frontend → Patient Selection → Auto-Injection → Multi-Agent Graph → Streaming Response
```

---

## Lessons Learned

1. **Small models hallucinate from examples** - llama3.1:8b copied prompt examples as real data
2. **SQL-level filtering required** - Post-hoc Python filtering misses sparse patient data
3. **Session history can pollute** - Old hallucinated responses leak into new sessions
4. **Dates matter for FHIR** - Explicit date extraction instructions needed
5. **Validator can harm** - With small models, validation loops cause more problems than it solves

---

## Files by Development Phase

### Core Infrastructure
- `api/database/postgres.py` - Vector store, hybrid search
- `api/embeddings/` - FHIR embedding pipeline
- `api/retrieval/` - Cross-encoder reranking

### Agent System
- `api/agent/multi_agent_graph.py` - LangGraph workflow
- `api/agent/prompts.yaml` - All agent prompts
- `api/agent/tools/` - Medical domain tools

### Frontend
- `frontend/src/app/page.tsx` - Main chat interface
- `frontend/src/hooks/useChat.ts` - Chat state management
- `frontend/src/components/` - UI components

### Evaluation
- `POC_RAGAS/` - RAGAS evaluation framework
