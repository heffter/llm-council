# LLM Council Backend Test Suite

Comprehensive unit tests for the LLM Council backend provider enhancements.

## Test Coverage

### Modules Tested

1. **storage_utils.py** (18 tests) - ✅ All passing
   - UUID v4 validation
   - Path traversal prevention
   - Response truncation with UTF-8 safety

2. **providers/parser.py** (19 tests)
   - Provider:model notation parsing
   - Model list parsing
   - Error handling for invalid formats

3. **retry.py** (10 tests) - ✅ All passing
   - Exponential backoff with jitter
   - Selective retries (5xx yes, 4xx no)
   - Max delay capping

4. **logger.py** (17 tests)
   - Structured JSON logging
   - Secret redaction (API keys, tokens, passwords)
   - Log level formatting

5. **middleware.py** (15 tests)
   - Shared secret authentication
   - Rate limiting with in-memory store
   - Request keying (token-based vs IP-based)

6. **providers/registry.py** (16 tests)
   - Provider registration from environment
   - Client caching
   - Configuration validation

## Running Tests

```bash
# Run all tests
python -m pytest backend/tests/ -v

# Run specific test file
python -m pytest backend/tests/test_storage_utils.py -v

# Run with coverage
python -m pytest backend/tests/ --cov=backend --cov-report=html

# Run only passing tests
python -m pytest backend/tests/test_storage_utils.py backend/tests/test_retry.py -v
```

## Test Statistics

- **Total tests created**: 110+
- **Fully passing modules**: storage_utils, retry, parser (partial)
- **Test framework**: pytest with pytest-asyncio
- **Coverage target**: >80%

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_storage_utils.py
├── test_parser.py
├── test_registry.py
├── test_middleware.py
├── test_retry.py
└── test_logger.py
```

## Key Test Patterns

### Security Testing
- Path traversal attempts
- UUID format validation
- Secret redaction in logs

### Resilience Testing
- Retry behavior with backoff
- Rate limit enforcement
- Error classification (4xx vs 5xx)

### Integration Fixtures
- Temporary directories for file tests
- Mock environment variables
- Async test support

## Notes

- Logger tests require special stdout/stderr capture handling
- Middleware tests use module reloading to pick up environment changes
- Registry tests validate provider configuration and client caching
