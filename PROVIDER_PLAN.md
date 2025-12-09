# Provider & Security Enhancements (LLM Council)

## Provider Abstraction & Routing
- Support `provider:model` notation (e.g., `openai:gpt-4.1`, `anthropic:claude-3-5-sonnet`, `gemini:gemini-2.0-pro`, `perplexity:sonar-pro`, `openrouter:gpt-4.1`). Keep OpenRouter as an option, add OpenAI, Anthropic, Gemini, Perplexity.
- Env-driven per-role config (council list + chairman). Fail fast with clear errors when a provider/model is unavailable or keys are missing.
- Optional research role (Perplexity) for ranking/title/aux prompts; remain optional with explicit SSE errors if missing/limited.

## Storage Safety
- Enforce UUID conversation IDs at the API boundary; reject non-UUIDs.
- Sanitize paths to ensure files stay under `data/conversations/`; block traversal.
- Cap/truncate oversized responses before persistence.

## Auth & Rate Limiting
- Optional shared secret header on write endpoints; deny when missing/invalid.
- Simple per-token/IP rate limit, toggle via env; default off for local use.

## Resilience & Observability
- Retries with backoff for upstream calls; shorter timeouts for title generation.
- Structured logging; propagate provider failures to frontend via SSE `error` events.
- Optional health/config endpoint exposing enabled providers (without secrets).

## Data Safety Messaging
- Warn users that `data/conversations/` is unencrypted local JSON; keep `data/` git-ignored.
- Frontend banner or notice linking to storage warning/config notes.

## Docs & Config
- Update `.env.example`/README with provider keys (OPENAI/ANTHROPIC/GEMINI/PERPLEXITY/OPENROUTER), shared token, rate-limit toggle, and provider notation.
- Note error handling expectations (SSE errors) and storage warning in README/UI.
