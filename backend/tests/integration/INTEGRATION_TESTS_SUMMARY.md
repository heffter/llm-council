# Provider Integration Tests - Implementation Summary

## Overview

Complete integration test suite for verifying actual API communication with all LLM providers configured in the LLM Council project.

**Created**: December 9, 2024
**Purpose**: Live API testing (not mocked) to verify provider connectivity and configuration
**Cost**: < $0.001 per full test run

## Files Created

### Test Files

1. **`backend/tests/integration/test_provider_integration.py`** (main test file)
   - Individual provider tests (OpenAI, Anthropic, Gemini, Perplexity, OpenRouter)
   - Production configuration test (`test_configured_models_from_env`)
   - Parallel request test
   - Comprehensive result tracking and reporting
   - ~500 lines of well-documented code

2. **`backend/tests/integration/__init__.py`**
   - Package initialization

### Documentation

3. **`backend/tests/integration/README.md`**
   - Quick start guide
   - Test coverage details
   - Troubleshooting common issues
   - CI/CD integration examples

4. **`backend/tests/integration/TESTING_GUIDE.md`**
   - Comprehensive testing guide (~400 lines)
   - Detailed troubleshooting section
   - Cost analysis and optimization tips
   - Advanced usage examples
   - Development workflow integration

### Scripts

5. **`scripts/run_integration_tests.sh`**
   - Automated test runner with environment checks
   - Color-coded output
   - Provider configuration detection
   - Error handling and helpful messages
   - Executable bash script

6. **`scripts/test_single_provider.py`**
   - Quick manual testing tool
   - Test individual providers without pytest
   - Test all configured providers
   - Real-time feedback with color output
   - Executable Python script

## Test Coverage

### Provider Tests

Each provider has a dedicated integration test:

| Provider | Test Function | Model Used | API Key Required |
|----------|--------------|------------|------------------|
| OpenAI | `test_openai_integration` | gpt-4o-mini | OPENAI_API_KEY |
| Anthropic | `test_anthropic_integration` | claude-3-5-haiku-20241022 | ANTHROPIC_API_KEY |
| Google Gemini | `test_gemini_integration` | gemini-2.0-flash-exp | GOOGLE_API_KEY |
| Perplexity | `test_perplexity_integration` | sonar-pro | PERPLEXITY_API_KEY |
| OpenRouter | `test_openrouter_integration` | llama-3.2-3b (free) | OPENROUTER_API_KEY |

### Configuration Tests

- **`test_configured_models_from_env`**: Tests the exact models configured in `.env` (COUNCIL_MODELS, CHAIRMAN_MODEL, RESEARCH_MODEL)
- **`test_parallel_requests`**: Verifies concurrent requests to multiple providers work correctly

## Key Features

### 1. Real API Testing
- Makes actual HTTP calls to provider APIs
- No mocking or stubbing
- Validates end-to-end connectivity
- Verifies request/response formats

### 2. Automatic Skipping
Tests are automatically skipped when:
- API key not configured
- API key is a placeholder (starts with `$`)
- Provider not needed for the test

### 3. Cost Optimization
- Uses cheapest/free models per provider
- Minimal token usage (~60 tokens per test)
- Short timeouts (30 seconds)
- Single request per provider
- Estimated cost: < $0.001 per run

### 4. Comprehensive Reporting
- Real-time progress logging
- Response content preview
- Performance metrics (duration)
- Error details with context
- Summary table at completion

### 5. Detailed Logging
Every test includes:
- Provider and model being tested
- API key status (configured/not configured)
- Client creation confirmation
- Request details
- Response content
- Duration measurement
- Error messages and stack traces

### 6. Flexible Execution
Multiple ways to run tests:
- Full test suite with pytest
- Individual provider tests
- Production config verification
- Quick manual testing script
- Automated bash runner

## Usage Examples

### Run All Tests

```bash
# Using test runner script (recommended)
./scripts/run_integration_tests.sh

# Using pytest directly
uv run pytest backend/tests/integration/test_provider_integration.py -v -s

# Run as Python module
uv run python -m backend.tests.integration.test_provider_integration
```

### Test Specific Provider

```bash
# Using pytest
uv run pytest backend/tests/integration/test_provider_integration.py::test_openai_integration -v -s

# Using manual script
python scripts/test_single_provider.py openai gpt-4o-mini
```

### Test Production Configuration

```bash
uv run pytest backend/tests/integration/test_provider_integration.py::test_configured_models_from_env -v -s
```

### Quick Test All Configured

```bash
python scripts/test_single_provider.py
```

## Configuration

### Environment Variables

Tests load from `.env` file or environment:

```bash
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
OPENROUTER_API_KEY=sk-or-v1-...
```

### Important Notes

1. **Do not use placeholders**: Keys like `$OPENAI_API_KEY` won't work
2. **Load from environment**: Can also export keys before running
3. **No commit secrets**: Never commit `.env` with real keys to git

## Test Architecture

### Class: IntegrationTestResults
Tracks results across all tests for comprehensive reporting:
- Stores success/failure status
- Captures response content
- Measures duration
- Records error messages
- Generates summary report

### Fixtures

- **`test_results`**: Module-scoped fixture for result tracking
- **`registry`**: Fresh ProviderRegistry with env vars loaded
- **`test_request`**: Standard CompletionRequest template

### Helper Functions

- **`is_provider_configured()`**: Check if provider has valid API key
- **`print_header()`**, **`print_success()`**, etc.: Formatted output

## Expected Output

### Successful Run

```
================================================================================
Testing OpenAI Provider
================================================================================
  Provider: openai
  API Key: configured
  Creating provider client...
✓ Client created successfully
  Sending request: 'Say 'Hello' and nothing else.'
✓ API call completed in 1.23s

--------------------------------------------------------------------------------
RESPONSE:
--------------------------------------------------------------------------------
Hello
--------------------------------------------------------------------------------

test_openai_integration PASSED

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

================================================================================
OVERALL: 2/2 providers passed
================================================================================
```

### Partial Run (Some Skipped)

```
test_openai_integration PASSED
test_anthropic_integration SKIPPED (ANTHROPIC_API_KEY not configured)
test_gemini_integration PASSED

================================================================================
OVERALL: 2/3 providers passed
================================================================================
```

### Failed Test

```
✗ Test failed: API error 401: Invalid authentication

test_openai_integration FAILED

Full error:
Traceback (most recent call last):
  ...
Exception: OpenAI API error: 401 Unauthorized
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| All tests skipped | No API keys configured | Set at least one key in `.env` |
| 401 Authentication | Invalid/expired key | Regenerate key from provider dashboard |
| Timeout | Network issue or API down | Check connectivity and provider status |
| Rate limit | Too many requests | Wait 1-5 minutes before retry |
| Import error | Wrong directory | Run from project root |
| Model not found | Invalid model ID | Check provider docs for current models |

### Provider Status Pages

- OpenAI: https://status.openai.com
- Anthropic: https://status.anthropic.com
- Google: https://status.cloud.google.com

## Integration with Development Workflow

### Pre-Deployment Check

```bash
./scripts/run_integration_tests.sh && echo "Ready to deploy!"
```

### Git Hook

Add to `.git/hooks/pre-push` to verify before pushing:

```bash
#!/bin/bash
./scripts/run_integration_tests.sh
```

### CI/CD (GitHub Actions)

```yaml
- name: Run Provider Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    uv sync --all-extras
    uv run pytest backend/tests/integration/ -v
```

### VS Code Task

```json
{
  "label": "Test Provider Integration",
  "type": "shell",
  "command": "./scripts/run_integration_tests.sh"
}
```

## Dependencies

Required packages (already in `pyproject.toml`):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]
```

Install with:

```bash
uv sync --all-extras
```

## Future Enhancements

### Baseline Storage
Store successful responses for regression detection:

```
backend/tests/integration/baselines/
  openai_gpt-4o-mini_response.json
  anthropic_claude-3-5-haiku_response.json
```

### Performance Benchmarking
Track response times over time to detect degradation:

```python
def test_performance_baseline(registry):
    results = []
    for _ in range(10):
        start = time.time()
        response = await client.complete(request)
        results.append(time.time() - start)

    avg_duration = sum(results) / len(results)
    assert avg_duration < BASELINE_THRESHOLD
```

### Error Recovery Testing
Test retry logic and error handling:

```python
def test_retry_on_failure(registry):
    # Simulate transient failures
    # Verify retry behavior
```

### Streaming Tests
Test streaming responses:

```python
def test_streaming_response(registry):
    async for chunk in client.stream(request):
        assert chunk is not None
```

## Maintenance Notes

### Updating Models
When providers release new models, update test model names in:
- `test_provider_integration.py` (individual test functions)
- `scripts/test_single_provider.py` (test_configs dictionary)
- Documentation examples

### Adding New Providers
To add a new provider:

1. Create provider implementation in `backend/providers/`
2. Register in `backend/providers/registry.py`
3. Add test function in `test_provider_integration.py`:

```python
@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('newprovider'),
                    reason="NEWPROVIDER_API_KEY not configured")
async def test_newprovider_integration(registry, test_request, test_results):
    # Implementation
```

4. Update documentation and scripts

### Monitoring Costs
Track actual costs in your provider dashboards:
- Review usage after test runs
- Set up billing alerts
- Monitor for unexpected charges

## Testing Philosophy

These integration tests follow several key principles:

1. **Real API Testing**: No mocks - verify actual connectivity
2. **Cost Conscious**: Minimize API usage while maintaining coverage
3. **Fail Fast**: Quick feedback on configuration issues
4. **Comprehensive**: Test all configured providers
5. **Self-Documenting**: Verbose output explains what's happening
6. **Production-Ready**: Test the exact configuration used in production

## Summary

The integration test suite provides:

✓ Verification of provider API connectivity
✓ Validation of API key configuration
✓ Testing of production model configuration
✓ Comprehensive error reporting
✓ Cost-optimized test execution
✓ Multiple execution methods
✓ Detailed documentation
✓ CI/CD integration support

**Total cost per run**: < $0.001
**Execution time**: ~5-15 seconds (depending on providers)
**Confidence**: High - tests actual API communication

Run regularly to ensure your LLM Council configuration remains valid and functional!
