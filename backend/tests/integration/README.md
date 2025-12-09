# Provider Integration Tests

This directory contains integration tests that verify actual API communication with all configured LLM providers.

## Important Notes

- These tests make **REAL API CALLS** to provider APIs
- They will **CONSUME API CREDITS**
- They are **NOT mocked** - this is intentional for live verification
- Tests are automatically skipped if API keys are not configured

## Running Tests

### Run All Integration Tests

```bash
# From project root
uv run pytest backend/tests/integration/test_provider_integration.py -v -s

# Or using Python module syntax
uv run python -m backend.tests.integration.test_provider_integration
```

### Run Specific Provider Tests

```bash
# Test only OpenAI
uv run pytest backend/tests/integration/test_provider_integration.py::test_openai_integration -v -s

# Test only Anthropic
uv run pytest backend/tests/integration/test_provider_integration.py::test_anthropic_integration -v -s

# Test only production config
uv run pytest backend/tests/integration/test_provider_integration.py::test_configured_models_from_env -v -s
```

### Run Without Output Capture (Recommended)

The `-s` flag disables pytest's output capture, showing verbose logging during tests:

```bash
uv run pytest backend/tests/integration/test_provider_integration.py -v -s
```

## Environment Setup

Tests automatically load API keys from the `.env` file in the project root.

### Required Environment Variables

Configure at least one provider in `.env`:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=...

# Perplexity
PERPLEXITY_API_KEY=pplx-...

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
```

### Production Configuration Test

The `test_configured_models_from_env` test verifies the exact models configured in your `.env`:

```bash
COUNCIL_MODELS=openai:gpt-4.1,anthropic:claude-3-5-sonnet-latest,gemini:gemini-2.0-pro
CHAIRMAN_MODEL=anthropic:claude-3-5-sonnet-latest
RESEARCH_MODEL=perplexity:sonar-pro
```

This test ensures your production configuration is valid before deployment.

## Test Coverage

### Individual Provider Tests

Each provider has its own test function:

- `test_openai_integration` - Tests OpenAI GPT models
- `test_anthropic_integration` - Tests Anthropic Claude models
- `test_gemini_integration` - Tests Google Gemini models
- `test_perplexity_integration` - Tests Perplexity Sonar models
- `test_openrouter_integration` - Tests OpenRouter proxy

### Configuration Tests

- `test_configured_models_from_env` - Tests all models from `.env` configuration
- `test_parallel_requests` - Tests concurrent requests to multiple providers

## Test Behavior

### Automatic Skipping

Tests are automatically skipped if:
- API key is not configured in `.env`
- API key is a placeholder (starts with `$`)
- Fewer than required providers are configured (for parallel tests)

### Cost Efficiency

Tests are designed to minimize API costs:
- Uses smallest/cheapest models per provider (e.g., `gpt-4o-mini`, `claude-3-5-haiku`)
- Limits response to 50 tokens
- Uses simple prompts ("Say 'Hello' and nothing else")
- Short timeout (30 seconds)

### Comprehensive Reporting

Tests provide detailed output:
- Success/failure status for each provider
- Response content preview
- Request duration
- Error messages with full context
- Summary table at the end

Example output:

```
================================================================================
PROVIDER INTEGRATION TEST SUMMARY
================================================================================

✓ PASS OPENAI
  Model: gpt-4o-mini
  Duration: 1.23s
  Response: Hello...

✗ FAIL PERPLEXITY
  Model: sonar-pro
  Error: API key invalid

================================================================================
OVERALL: 4/5 providers passed
================================================================================
```

## Troubleshooting

### Test Fails with "Provider not configured"

Ensure the API key is set in `.env` and not a placeholder:

```bash
# Wrong (placeholder)
OPENAI_API_KEY=$OPENAI_API_KEY

# Right (actual key)
OPENAI_API_KEY=sk-proj-abc123...
```

### Test Fails with "Rate limit exceeded"

Provider APIs have rate limits. Wait a few minutes and retry, or use different models.

### Test Hangs

If a test hangs, it will timeout after 30 seconds. This may indicate:
- Network connectivity issues
- Provider API downtime
- Invalid API endpoint configuration

Check provider status pages:
- OpenAI: https://status.openai.com
- Anthropic: https://status.anthropic.com
- Google: https://status.cloud.google.com

### Import Errors

Run tests from project root and ensure dependencies are installed:

```bash
cd /home/heffter/devel/llm-council
uv sync
uv run pytest backend/tests/integration/test_provider_integration.py -v -s
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines with secrets:

```yaml
# GitHub Actions example
- name: Run Provider Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
  run: |
    uv run pytest backend/tests/integration/ -v -s
```

**Warning**: Be cautious about API costs in CI/CD. Consider:
- Only running on main branch merges
- Using free-tier models
- Setting up spending limits
- Caching results for pull requests

## Extending Tests

To add tests for new providers:

1. Add provider configuration in `backend/providers/`
2. Register in `backend/providers/registry.py`
3. Add integration test following the existing pattern:

```python
@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('newprovider'),
                    reason="NEWPROVIDER_API_KEY not configured")
async def test_newprovider_integration(registry, test_request, test_results):
    """Test actual NewProvider API communication."""
    # Implementation here
```

## Baseline Storage

For future baseline-driven testing, consider storing successful responses:

```bash
backend/tests/integration/baselines/
  openai_gpt-4o-mini.json
  anthropic_claude-3-5-haiku.json
  gemini_gemini-2.0-flash.json
```

This would enable regression detection when provider behavior changes.
