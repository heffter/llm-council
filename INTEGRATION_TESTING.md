# Provider Integration Testing

This project includes comprehensive integration tests that verify actual API communication with all configured LLM providers.

## Quick Start

### Run All Tests

```bash
./scripts/run_integration_tests.sh
```

This automated script will:
- Check which providers are configured
- Install dependencies if needed
- Run all integration tests
- Provide a detailed summary

### Manual Testing

Test a specific provider manually:

```bash
python scripts/test_single_provider.py openai gpt-4o-mini
python scripts/test_single_provider.py anthropic claude-3-5-haiku-20241022
```

Or test all configured providers:

```bash
python scripts/test_single_provider.py
```

### Using pytest Directly

```bash
# All tests
uv run pytest backend/tests/integration/test_provider_integration.py -v -s

# Specific provider
uv run pytest backend/tests/integration/test_provider_integration.py::test_openai_integration -v -s

# Production configuration only
uv run pytest backend/tests/integration/test_provider_integration.py::test_configured_models_from_env -v -s
```

## What Gets Tested

### Individual Provider Tests
- **OpenAI** - Verifies GPT model access
- **Anthropic** - Verifies Claude model access
- **Google Gemini** - Verifies Gemini model access
- **Perplexity** - Verifies Sonar model access
- **OpenRouter** - Verifies OpenRouter proxy access

### Configuration Tests
- **Production Config** - Tests exact models from `.env` (COUNCIL_MODELS, CHAIRMAN_MODEL, RESEARCH_MODEL)
- **Parallel Requests** - Tests concurrent provider requests

## Important Notes

**These tests make REAL API calls:**
- They are NOT mocked
- They WILL consume API credits (minimal < $0.001 per run)
- Tests are automatically skipped if API keys are not configured

## Configuration

### Setting API Keys

Edit `.env` and replace placeholders with actual keys:

```bash
# Before (won't work)
OPENAI_API_KEY=$OPENAI_API_KEY

# After (will work)
OPENAI_API_KEY=sk-proj-abc123xyz789...
```

Or export environment variables:

```bash
export OPENAI_API_KEY='sk-proj-...'
export ANTHROPIC_API_KEY='sk-ant-...'
export GOOGLE_API_KEY='...'
```

### Required Environment Variables

At least one provider must be configured:
- `OPENAI_API_KEY` - For OpenAI/GPT models
- `ANTHROPIC_API_KEY` - For Anthropic/Claude models
- `GOOGLE_API_KEY` - For Google/Gemini models
- `PERPLEXITY_API_KEY` - For Perplexity/Sonar models
- `OPENROUTER_API_KEY` - For OpenRouter proxy

## Cost Optimization

Tests are designed to minimize API costs:
- Uses cheapest models per provider (e.g., gpt-4o-mini, claude-3-5-haiku)
- Limits responses to 50 tokens
- Uses simple prompts
- Makes only 1 request per provider
- **Total estimated cost: < $0.001 per full test run**

## Documentation

Detailed documentation is available in:

- **`backend/tests/integration/README.md`** - Quick reference and troubleshooting
- **`backend/tests/integration/TESTING_GUIDE.md`** - Comprehensive testing guide
- **`backend/tests/integration/INTEGRATION_TESTS_SUMMARY.md`** - Implementation details

## Example Output

### Successful Test

```
================================================================================
Testing OpenAI Provider
================================================================================
  Provider: openai
  API Key: configured
✓ Client created successfully
✓ API call completed in 1.23s

RESPONSE:
Hello

test_openai_integration PASSED
```

### Summary Report

```
================================================================================
PROVIDER INTEGRATION TEST SUMMARY
================================================================================

✓ PASS OPENAI
  Model: gpt-4o-mini
  Duration: 1.23s

✓ PASS ANTHROPIC
  Model: claude-3-5-haiku-20241022
  Duration: 2.45s

⊘ SKIP PERPLEXITY
  Error: Provider not configured

================================================================================
OVERALL: 2/3 providers passed
================================================================================
```

## Troubleshooting

### All Tests Skipped
**Problem**: No API keys configured
**Solution**: Set at least one API key in `.env` (remove `$` placeholders)

### 401 Authentication Error
**Problem**: Invalid or expired API key
**Solution**: Regenerate key from provider dashboard and update `.env`

### Timeout Error
**Problem**: Network issue or provider API down
**Solution**: Check internet connection and provider status pages

### Import Error
**Problem**: Running from wrong directory
**Solution**: Run from project root: `cd /home/heffter/devel/llm-council`

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Provider Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    uv sync --all-extras
    uv run pytest backend/tests/integration/ -v
```

## Pre-Deployment Check

Run before deploying to verify configuration:

```bash
./scripts/run_integration_tests.sh && echo "Ready to deploy!"
```

## Files Overview

```
backend/tests/integration/
├── __init__.py                          # Package initialization
├── test_provider_integration.py         # Main test suite (7 tests)
├── README.md                            # Quick reference
├── TESTING_GUIDE.md                     # Comprehensive guide
└── INTEGRATION_TESTS_SUMMARY.md         # Implementation summary

scripts/
├── run_integration_tests.sh             # Automated test runner
└── test_single_provider.py              # Manual testing tool
```

## Testing Philosophy

These tests verify that:
- ✓ All configured providers are accessible
- ✓ API keys are valid and working
- ✓ Network connectivity is functional
- ✓ Request/response format is correct
- ✓ Production configuration is valid

Run them regularly to catch configuration issues early!

## Need Help?

See detailed documentation:
- `backend/tests/integration/TESTING_GUIDE.md` - Full troubleshooting guide
- `backend/tests/integration/README.md` - Quick reference
- Provider status pages (OpenAI, Anthropic, Google, etc.)

## Summary

- **7 integration tests** covering all providers
- **Real API calls** (not mocked)
- **Automatic skipping** for unconfigured providers
- **Cost optimized** (< $0.001 per run)
- **Comprehensive reporting** with detailed logs
- **Multiple execution methods** (pytest, scripts, manual)
- **Production verification** (tests exact `.env` config)

Run before deployment to ensure all providers are accessible!
