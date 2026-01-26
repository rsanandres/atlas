# POC Agent Service

This service hosts a LangGraph ReAct agent for healthcare RAG.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure the reranker service is running:
   ```bash
   uvicorn POC_retrieval.reranker.service:app --reload --port 8001
   ```

3. Configure environment variables (repo root `.env`):
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=chevalblanc/claude-3-haiku:latest
   OLLAMA_BASE_URL=http://localhost:11434
   PII_MASKER_PROVIDER=local
   ```

## Run the Agent Service

```bash
uvicorn POC_agent.service:app --reload --port 8002
```

## Terminal CLI Interface

A terminal-based chat interface is available for interactive conversations with the agent:

```bash
python POC_agent/scripts/chat_cli.py
```

Or to continue an existing session:

```bash
python POC_agent/scripts/chat_cli.py <session_id>
```

The CLI automatically:
- Creates a new session ID if none is provided
- Loads and injects conversation history into the agent context
- Displays formatted responses with sources and tool usage
- Supports session management commands

**Commands:**
- Type your question and press Enter to send
- Type `exit`, `quit`, or `q` to exit
- Type `clear` to clear the current session history

**Note:** The agent service must be running (see above) and the session store (DynamoDB) must be configured for conversation history to work.

## Query Endpoint

`POST /agent/query`

Body:
```json
{
  "query": "What medications is the patient taking for diabetes?",
  "session_id": "demo-session",
  "patient_id": "patient-123"
}
```

## Tests

Integration test (requires reranker running):
```bash
python POC_agent/test_agent_integration.py "diabetes medications"
```

Unit tests:
```bash
python POC_agent/test_agent.py
```
