# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

**Quick start (both services):**
```bash
./start.sh
```

**Manual start:**
```bash
# Terminal 1 - Backend (port 8001)
uv run python -m backend.main

# Terminal 2 - Frontend (port 5173)
cd frontend && npm run dev
```

**Install dependencies:**
```bash
uv sync                      # Backend (Python)
cd frontend && npm install   # Frontend (React)
```

**Frontend linting:**
```bash
cd frontend && npm run lint
```

## Architecture

LLM Council is a 3-stage deliberation system where multiple LLMs answer user questions collaboratively:

1. **Stage 1**: Parallel queries to all council models for individual responses
2. **Stage 2**: Each model reviews and ranks all responses (anonymized as "Response A, B, C..." to prevent bias)
3. **Stage 3**: Chairman model synthesizes a final answer from all responses and rankings

### Key Files

- `backend/config.py` - Model configuration (`COUNCIL_MODELS`, `CHAIRMAN_MODEL`) and API key loading
- `backend/council.py` - Core 3-stage logic, ranking parsing, aggregate calculations
- `backend/openrouter.py` - Async OpenRouter API client with parallel query support
- `backend/storage.py` - JSON file storage in `data/conversations/`
- `backend/main.py` - FastAPI app (port 8001)
- `frontend/src/api.js` - API client (points to localhost:8001)
- `frontend/src/App.jsx` - Main React orchestration
- `frontend/src/components/Stage[1-3].jsx` - Display components for each stage

### API Endpoints

- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation
- `POST /api/conversations/{id}/message` - Send message (batch response)
- `POST /api/conversations/{id}/message/stream` - Send message (SSE streaming)

### Data Flow

```
User Query -> Stage 1 (parallel) -> Stage 2 (anonymize + parallel rank) -> Stage 3 (chairman) -> Response
```

Metadata (label_to_model mapping, aggregate_rankings) is returned via API but NOT persisted to storage.

## Important Details

### Backend Module System
Backend uses relative imports (`from .config import ...`). Always run from project root with `python -m backend.main`, not from the backend directory.

### Port Configuration
If changing ports, update both `backend/main.py` (uvicorn) and `frontend/src/api.js` (API_BASE).

### Stage 2 Ranking Format
Models must output rankings in this exact format for reliable parsing:
```
FINAL RANKING:
1. Response C
2. Response A
...
```
The `parse_ranking_from_text()` function in `council.py` extracts this section.

### Markdown Rendering
Frontend uses ReactMarkdown. All markdown content must be wrapped in `<div className="markdown-content">` for consistent styling (defined in `index.css`).

### Environment
Requires `.env` file with `OPENROUTER_API_KEY=sk-or-v1-...`

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
