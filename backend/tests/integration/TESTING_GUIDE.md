# Provider Integration Testing Guide

This guide explains how to verify that your LLM Council installation can successfully communicate with all configured LLM providers.

## Overview

Integration tests verify:
- API keys are correctly configured
- Network connectivity to provider APIs
- Request/response formatting is correct
- All configured models are accessible
- Concurrent requests work properly

## Quick Start

### Method 1: Using the Test Runner Script (Recommended)

```bash
# From project root
./scripts/run_integration_tests.sh
```

This script will:
- Check which providers are configured
- Install dependencies if needed
- Run all integration tests
- Provide a detailed summary

### Method 2: Direct pytest Execution

```bash
# Run all integration tests
uv run pytest backend/tests/integration/test_provider_integration.py -v -s

# Run specific test
uv run pytest backend/tests/integration/test_provider_integration.py::test_openai_integration -v -s

# Run as Python module
uv run python -m backend.tests.integration.test_provider_integration
```

### Method 3: Quick Validation

Just test your production configuration:

```bash
uv run pytest backend/tests/integration/test_provider_integration.py::test_configured_models_from_env -v -s
```

## Setting Up API Keys

Integration tests load API keys from environment variables. You have two options:

### Option 1: Export Environment Variables

```bash
export OPENAI_API_KEY='sk-proj-...'
export ANTHROPIC_API_KEY='sk-ant-...'
export GOOGLE_API_KEY='...'
export PERPLEXITY_API_KEY='pplx-...'
export OPENROUTER_API_KEY='sk-or-v1-...'
```

### Option 2: Configure .env File

Edit `.env` in project root and replace placeholders with actual keys:

```bash
# Before (placeholder - won't work)
OPENAI_API_KEY=$OPENAI_API_KEY

# After (actual key - will work)
OPENAI_API_KEY=sk-proj-abc123xyz789...
```

**Important**: Tests will be skipped if API keys are:
- Not set
- Still set to placeholder values (starting with `$`)
- Invalid or expired

## Understanding Test Results

### Successful Test Output

```
================================================================================
Testing OpenAI Provider
================================================================================
Getting client for provider: openai
✓ Client created successfully
Making API call to model: gpt-4o-mini
✓ API call successful
Response: Hello
Duration: 1.23s

test_openai_integration PASSED
```

### Skipped Test Output

```
test_anthropic_integration SKIPPED (ANTHROPIC_API_KEY not configured)
```

This is normal if you haven't configured that provider.

### Failed Test Output

```
✗ Test failed: API error 401: Invalid authentication
test_openai_integration FAILED
```

This indicates a problem with configuration or API access.

### Summary Report

At the end of all tests, you'll see a comprehensive summary:

```
================================================================================
PROVIDER INTEGRATION TEST SUMMARY
================================================================================

✓ PASS OPENAI
  Model: gpt-4o-mini
  Duration: 1.23s
  Response: Hello...

✓ PASS ANTHROPIC
  Model: claude-3-5-haiku-20241022
  Duration: 2.45s
  Response: Hello!...

⊘ SKIP PERPLEXITY
  Error: Provider not configured

================================================================================
OVERALL: 2/3 providers passed
================================================================================
```

## Test Coverage Details

### Individual Provider Tests

Each provider has a dedicated test:

| Test Function | Provider | Model Used | Purpose |
|--------------|----------|------------|---------|
| `test_openai_integration` | OpenAI | gpt-4o-mini | Verify OpenAI API access |
| `test_anthropic_integration` | Anthropic | claude-3-5-haiku | Verify Anthropic API access |
| `test_gemini_integration` | Google | gemini-2.0-flash-exp | Verify Google AI access |
| `test_perplexity_integration` | Perplexity | sonar-pro | Verify Perplexity API access |
| `test_openrouter_integration` | OpenRouter | llama-3.2-3b (free) | Verify OpenRouter proxy |

### Configuration Tests

| Test Function | Purpose |
|--------------|---------|
| `test_configured_models_from_env` | Tests the exact models from your `.env` config |
| `test_parallel_requests` | Verifies concurrent requests to multiple providers |

### What Each Test Does

1. **Load API credentials** from environment
2. **Create provider client** using the registry
3. **Send simple test prompt** ("Say 'Hello' and nothing else")
4. **Validate response**:
   - Response is not None
   - Response contains content
   - Response completed within timeout
5. **Measure performance** (duration)
6. **Report results** with detailed logging

## Cost Considerations

Integration tests are designed to minimize API costs:

### Cost-Saving Measures

1. **Uses cheapest models**:
   - OpenAI: `gpt-4o-mini` instead of `gpt-4o`
   - Anthropic: `claude-3-5-haiku` instead of `claude-3-5-sonnet`
   - OpenRouter: Free tier models when available

2. **Minimal token usage**:
   - Prompt: ~10 tokens ("Say 'Hello' and nothing else")
   - Response: Limited to 50 tokens max
   - Total: ~60 tokens per test

3. **Single request per provider**:
   - Each test makes exactly 1 API call
   - No retries on success
   - Short timeout (30 seconds)

### Estimated Costs

Based on typical pricing (December 2024):

| Provider | Model | Cost per Test | Notes |
|----------|-------|---------------|-------|
| OpenAI | gpt-4o-mini | ~$0.0001 | Extremely cheap |
| Anthropic | claude-3-5-haiku | ~$0.0002 | Very affordable |
| Google | gemini-2.0-flash | Free tier | No cost for testing |
| Perplexity | sonar-pro | ~$0.0005 | Research model |
| OpenRouter | llama-3.2 (free) | $0 | Free tier model |

**Total estimated cost**: Less than $0.001 (one tenth of one cent) per test run.

### Running in CI/CD

If running in CI/CD pipelines:
- Consider running only on main branch merges
- Cache test results for pull requests
- Set up billing alerts
- Use free models where available

## Troubleshooting

### Problem: All tests skipped

**Symptoms**:
```
5 skipped in 0.02s
```

**Cause**: No API keys configured

**Solution**:
```bash
# Check current configuration
grep "API_KEY" .env

# Update with real keys (remove $ placeholders)
nano .env
```

### Problem: 401 Authentication Error

**Symptoms**:
```
✗ Test failed: API error 401: Invalid authentication
```

**Cause**: API key is invalid, expired, or incorrectly formatted

**Solution**:
1. Verify API key in provider dashboard:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/settings/keys
   - Google: https://aistudio.google.com/app/apikey
   - Perplexity: https://www.perplexity.ai/settings/api
   - OpenRouter: https://openrouter.ai/keys

2. Regenerate key if needed
3. Update `.env` with new key
4. Ensure no extra spaces or quotes

### Problem: Timeout Error

**Symptoms**:
```
✗ Test failed: Request timeout after 30.0s
```

**Cause**: Network issue or provider API downtime

**Solution**:
1. Check internet connectivity
2. Check provider status pages:
   - OpenAI: https://status.openai.com
   - Anthropic: https://status.anthropic.com
   - Google: https://status.cloud.google.com
3. Try again later
4. Check firewall/proxy settings

### Problem: Rate Limit Error

**Symptoms**:
```
✗ Test failed: Rate limit exceeded
```

**Cause**: Too many requests to provider API

**Solution**:
- Wait 1-5 minutes before retrying
- Check your API plan's rate limits
- Upgrade to higher tier if needed
- Use different models with higher limits

### Problem: Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'backend'
```

**Cause**: Running from wrong directory or dependencies not installed

**Solution**:
```bash
# Ensure you're in project root
cd /home/heffter/devel/llm-council

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest backend/tests/integration/test_provider_integration.py -v -s
```

### Problem: Model Not Found Error

**Symptoms**:
```
✗ Test failed: Model 'gpt-4.1' not found
```

**Cause**: Model ID doesn't exist or has been deprecated

**Solution**:
1. Check provider documentation for current model names
2. Update `.env` with valid model names
3. Common current models (Dec 2024):
   - OpenAI: `gpt-4o`, `gpt-4o-mini`, `o1-preview`
   - Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`
   - Google: `gemini-2.0-flash-exp`, `gemini-1.5-pro`

### Problem: Tests Pass but App Fails

**Symptoms**: Integration tests pass, but council responses fail in the app

**Possible causes**:
1. Model in `.env` differs from test model
2. Different timeout settings
3. Different message formatting
4. Rate limits hit during actual use

**Solution**:
1. Run `test_configured_models_from_env` specifically:
   ```bash
   uv run pytest backend/tests/integration/test_provider_integration.py::test_configured_models_from_env -v -s
   ```
2. This tests the EXACT models from your `.env`
3. If this fails, update your `.env` configuration

## Advanced Usage

### Testing Specific Models

Modify the test file to use specific models:

```python
# In test_openai_integration
model = "gpt-4o"  # Change from gpt-4o-mini

# In test_anthropic_integration
model = "claude-3-5-sonnet-20241022"  # Change from haiku
```

### Custom Test Prompts

Modify `TEST_PROMPT` at the top of the test file:

```python
TEST_PROMPT = "Explain quantum computing in one sentence."
```

### Longer Responses

Modify `MAX_TOKENS`:

```python
MAX_TOKENS = 500  # Increase from 50
```

**Warning**: Higher token limits = higher costs

### Increased Timeout

For slower models:

```python
TEST_TIMEOUT = 60.0  # Increase from 30.0 seconds
```

### Verbose Logging

Add logging to see HTTP requests:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Save Responses

Capture responses for baseline testing:

```python
# In test function
with open(f'baselines/{provider_id}_{model}.txt', 'w') as f:
    f.write(response.content)
```

## Integration with Development Workflow

### Pre-deployment Check

Run before deploying:

```bash
./scripts/run_integration_tests.sh && echo "Ready to deploy!"
```

### Git Hook

Add to `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running provider integration tests..."
./scripts/run_integration_tests.sh
```

### VS Code Task

Add to `.vscode/tasks.json`:

```json
{
  "label": "Test Provider Integration",
  "type": "shell",
  "command": "./scripts/run_integration_tests.sh",
  "group": "test",
  "presentation": {
    "reveal": "always"
  }
}
```

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Provider Integration Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Run integration tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          uv sync --all-extras
          uv run pytest backend/tests/integration/ -v
```

## Next Steps

After integration tests pass:

1. **Run the application**:
   ```bash
   ./start.sh
   ```

2. **Test with UI**: Visit http://localhost:5173 and send a test query

3. **Monitor logs**: Watch for any errors in API communication

4. **Check baselines**: Consider implementing baseline testing for regression detection

5. **Set up monitoring**: Track API latency and error rates in production

## Need Help?

- Check backend logs: `backend/logs/` (if configured)
- Review provider documentation
- Check this project's GitHub issues
- Verify API account status and billing

## Summary

Integration tests provide confidence that:
- ✓ All configured providers are accessible
- ✓ API keys are valid and working
- ✓ Network connectivity is functional
- ✓ Request/response format is correct
- ✓ Your production configuration is valid

Run them regularly to catch configuration issues early!
