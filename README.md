# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, etc.), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses multiple LLM providers to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Features

- **Multi-Provider Support**: Use models from OpenAI, Anthropic, Google Gemini, Perplexity, or OpenRouter
- **Provider Abstraction**: Unified `provider:model` notation for easy model configuration
- **Storage Safety**: UUID-validated conversation IDs with path traversal prevention
- **Authentication**: Optional shared-secret auth for write endpoints
- **Rate Limiting**: Configurable per-token/IP rate limiting
- **Resilience**: Automatic retries with exponential backoff for transient failures
- **Structured Logging**: JSON-formatted logs with automatic secret redaction
- **SSE Error Handling**: Detailed error propagation in Server-Sent Events
- **Health Endpoint**: Monitor provider status and configuration
- **Data Safety Warnings**: Clear UI warnings about unencrypted local storage

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Keys

Create a `.env` file in the project root. See `.env.example` for all options.

**Minimum required configuration:**
```bash
# At least one provider API key is required
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-proj-...
# OR
GOOGLE_API_KEY=...
# OR
PERPLEXITY_API_KEY=pplx-...
# OR
OPENROUTER_API_KEY=sk-or-v1-...

# Model configuration using provider:model notation
COUNCIL_MODELS=anthropic:claude-3-5-sonnet-latest,openai:gpt-4o
CHAIRMAN_MODEL=anthropic:claude-3-5-sonnet-latest
```

**Get API keys:**
- OpenAI: [platform.openai.com](https://platform.openai.com/)
- Anthropic: [console.anthropic.com](https://console.anthropic.com/)
- Google Gemini: [aistudio.google.com](https://aistudio.google.com/)
- Perplexity: [perplexity.ai](https://www.perplexity.ai/)
- OpenRouter: [openrouter.ai](https://openrouter.ai/)

### 3. Configure Models

Models use `provider:model` notation. Edit your `.env` file:

```bash
# Council models (comma-separated)
COUNCIL_MODELS=openai:gpt-4o,anthropic:claude-3-5-sonnet-latest,gemini:gemini-2.0-pro

# Chairman model (single model)
CHAIRMAN_MODEL=anthropic:claude-3-5-sonnet-latest

# Optional research model for title generation
RESEARCH_MODEL=perplexity:sonar-pro
```

**Supported providers and example models:**
- `openai:gpt-4o`, `openai:gpt-4o-mini`, `openai:o3-mini`
- `anthropic:claude-3-5-sonnet-latest`, `anthropic:claude-3-opus-latest`
- `gemini:gemini-2.0-pro`, `gemini:gemini-1.5-flash`
- `perplexity:sonar-pro`, `perplexity:sonar-reasoning`
- `openrouter:anthropic/claude-3-5-sonnet`, `openrouter:openai/gpt-4o`

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

**Option 3: Docker Compose (Recommended for deployment)**

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Then open http://localhost in your browser (port 80).

See [Docker Deployment](#docker-deployment) for detailed configuration.

## Configuration Reference

### Provider Configuration

Each provider requires its corresponding API key:

```bash
OPENAI_API_KEY=           # For OpenAI models
ANTHROPIC_API_KEY=        # For Anthropic Claude models
GOOGLE_API_KEY=           # For Google Gemini models
PERPLEXITY_API_KEY=       # For Perplexity models
OPENROUTER_API_KEY=       # For OpenRouter proxy
```

**Base URLs (optional overrides):**
```bash
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
PERPLEXITY_BASE_URL=https://api.perplexity.ai
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Authentication & Security

**Optional shared secret for write endpoints:**
```bash
SHARED_WRITE_TOKEN=your-secret-token-here
```

When set, all write operations (POST, PUT, PATCH, DELETE) require an `X-Shared-Token` header.

**Rate limiting (disabled by default):**
```bash
RATE_LIMIT_ENABLED=false              # Set to 'true' to enable
RATE_LIMIT_WINDOW_MS=60000           # Window size in ms (1 minute)
RATE_LIMIT_MAX_REQUESTS=60           # Max requests per window
```

### Storage Configuration

```bash
MAX_STORED_RESPONSE_BYTES=262144     # Max response size (256KB default)
```

Responses larger than this are truncated with a `[TRUNCATED]` marker.

### Observability

```bash
EXPOSE_HEALTH_ENDPOINT=true          # Enable /health endpoint
```

Access health status: `GET http://localhost:8001/health`

Returns provider status, role configuration, and storage info (no secrets).

## Data Storage & Safety

**Important:** Conversations are stored as **unencrypted JSON files** in `data/conversations/`.

- **Location:** `data/conversations/` directory
- **Format:** One JSON file per conversation (UUID filename)
- **Encryption:** None - all data is plain text
- **Security:** Suitable for local development only
- **Deletion:** Remove `data/` folder to delete all conversations

The frontend displays a dismissible warning banner on first use.

For production or sensitive data:
- Implement encrypted storage
- Use a proper database backend
- Configure secure backup solutions

## API Endpoints

**Conversation Management:**
- `GET /api/conversations` - List all conversations
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}` - Get conversation details
- `POST /api/conversations/{id}/message` - Send message (batch response)
- `POST /api/conversations/{id}/message/stream` - Send message (SSE streaming)

**Health & Monitoring:**
- `GET /` - Basic health check
- `GET /health` - Detailed health and config (if enabled)

## Error Handling

The application uses Server-Sent Events (SSE) for streaming responses with structured error events:

**Error event format:**
```json
{
  "type": "error",
  "stage": "stage1",
  "message": "Error description",
  "retryable": true
}
```

**Error types:**
- `stage1`, `stage2`, `stage3` - Stage-specific errors
- `provider_error` - Provider/model failures
- `config_error` - Configuration issues

## Resilience Features

- **Automatic Retries:** 2 retries with exponential backoff for transient errors
- **Smart Error Classification:** Skips retries for 4xx client errors
- **Timeout Optimization:** 5s for title generation, 120s for main responses
- **Structured Logging:** JSON logs with automatic secret redaction
- **Graceful Degradation:** Title generation failures don't block responses

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, pydantic
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
- **Logging:** Structured JSON logging with ISO-8601 timestamps
- **Error Handling:** SSE with per-stage error propagation

## Development

**Linting:**
```bash
cd frontend
npm run lint
```

**Project Structure:**
```
├── backend/
│   ├── config.py              # Configuration and validation
│   ├── main.py                # FastAPI application
│   ├── council.py             # 3-stage council orchestration
│   ├── llm_client.py          # High-level LLM interface
│   ├── storage.py             # Conversation storage
│   ├── storage_utils.py       # Storage safety utilities
│   ├── middleware.py          # Auth and rate limiting
│   ├── retry.py               # Retry logic with backoff
│   ├── logger.py              # Structured logging
│   └── providers/             # Provider abstraction
│       ├── base.py            # Abstract base class
│       ├── parser.py          # Provider:model notation
│       ├── registry.py        # Provider registry
│       ├── openai_provider.py
│       ├── anthropic_provider.py
│       ├── gemini_provider.py
│       ├── perplexity_provider.py
│       └── openrouter_provider.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── StorageWarningBanner.jsx  # Data safety warning
│       │   └── ...
│       └── ...
└── data/                      # Conversation storage (git-ignored)
```

## Security Considerations

1. **API Keys:** Store in `.env`, never commit to version control
2. **Data Storage:** Unencrypted - not suitable for sensitive data
3. **Authentication:** Enable `SHARED_WRITE_TOKEN` for production
4. **Rate Limiting:** Enable for production deployments
5. **HTTPS:** Use HTTPS termination (nginx, Cloudflare) in production
6. **Secrets in Logs:** Automatically redacted by structured logger

## Troubleshooting

**"Configuration validation failed":**
- Check that required API keys are set in `.env`
- Verify `provider:model` notation is correct
- Ensure configured providers have API keys

**"Provider not configured":**
- The model's provider needs its API key in `.env`
- Example: `openai:gpt-4o` requires `OPENAI_API_KEY`

**Rate limit errors (429):**
- Check `RATE_LIMIT_ENABLED` setting
- Adjust `RATE_LIMIT_MAX_REQUESTS` if needed
- Wait for window reset (see `Retry-After` header)

**Storage errors:**
- Conversation IDs must be valid UUID v4
- Check disk space in `data/conversations/`
- Verify `data/` is writable

## Docker Deployment

The project includes Docker support for easy deployment.

### Quick Start

```bash
# 1. Create/update .env with your API keys
cp .env.example .env
# Edit .env with your API keys

# 2. Build and run
docker-compose up --build -d

# 3. Check services are healthy
docker-compose ps

# 4. View logs
docker-compose logs -f backend
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8001 | FastAPI Python backend |
| `frontend` | 80 | React app served by nginx |
| `redis` | 6379 | Optional: distributed rate limiting |

### Environment Variables

All configuration is passed via environment variables. Create a `.env` file:

```bash
# Required: At least one provider API key
OPENROUTER_API_KEY=sk-or-v1-...

# Model configuration
COUNCIL_MODELS=openrouter:anthropic/claude-3-5-sonnet,openrouter:openai/gpt-4o
CHAIRMAN_MODEL=openrouter:anthropic/claude-3-5-sonnet

# Optional: Production settings
SHARED_WRITE_TOKEN=your-secret-token
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=100
```

### Data Persistence

Conversations are stored in `./data/conversations/` which is mounted as a Docker volume:

```yaml
volumes:
  - ./data:/app/data
```

To backup conversations, copy the `data/` directory. To reset, delete it.

### Building Individual Images

```bash
# Backend only
docker build -f backend/Dockerfile -t llm-council-backend .

# Frontend only (with custom API URL)
docker build -f frontend/Dockerfile \
  --build-arg VITE_API_BASE=https://api.example.com \
  -t llm-council-frontend ./frontend
```

### Production Considerations

1. **HTTPS:** Use a reverse proxy (nginx, Traefik, Cloudflare) for TLS termination
2. **Authentication:** Set `SHARED_WRITE_TOKEN` for write endpoint protection
3. **Rate Limiting:** Enable with `RATE_LIMIT_ENABLED=true`
4. **Redis:** Uncomment Redis service in `docker-compose.yml` for distributed rate limiting
5. **Secrets:** Use Docker secrets or a secrets manager instead of `.env` in production

### Health Checks

Both services include health checks:

- Backend: `curl http://localhost:8001/health`
- Frontend: `wget http://localhost:80/`

Check health status:
```bash
docker-compose ps
# Or
docker inspect llm-council-backend --format='{{.State.Health.Status}}'
```

### Troubleshooting Docker

**Container won't start:**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing API keys in .env
# - Invalid COUNCIL_MODELS format
```

**Frontend can't reach backend:**
```bash
# Ensure backend is healthy first
docker-compose ps

# Check network connectivity
docker-compose exec frontend wget -O- http://backend:8001/health
```

**Permission errors on data volume:**
```bash
# Fix ownership
sudo chown -R 1000:1000 ./data
```

## License

See LICENSE file.
