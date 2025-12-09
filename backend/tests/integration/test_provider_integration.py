"""
Integration tests for LLM provider API communication.

These tests make REAL API calls to verify actual connectivity and configuration.
They are not mocked and will consume API credits.

Run with: pytest backend/tests/integration/test_provider_integration.py -v -s

Environment Variables Required:
- OPENAI_API_KEY (for OpenAI tests)
- ANTHROPIC_API_KEY (for Anthropic tests)
- GOOGLE_API_KEY (for Gemini tests)
- PERPLEXITY_API_KEY (for Perplexity tests)
- OPENROUTER_API_KEY (for OpenRouter tests)
"""

import os
import pytest
import asyncio
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load environment variables from .env
load_dotenv()

from backend.providers.base import Message, CompletionRequest, CompletionResponse
from backend.providers.registry import ProviderRegistry, get_registry
from backend.providers.parser import ProviderId


# Test configuration
TEST_PROMPT = "Say 'Hello' and nothing else."
TEST_TIMEOUT = 30.0  # seconds
MAX_TOKENS = 50  # Keep responses short to save credits


class IntegrationTestResults:
    """Track integration test results for comprehensive reporting."""

    def __init__(self):
        self.results: Dict[str, Dict] = {}

    def add_result(self, provider: str, model: str, success: bool,
                   response: Optional[str] = None, error: Optional[str] = None,
                   duration: Optional[float] = None):
        """Add a test result."""
        self.results[provider] = {
            'model': model,
            'success': success,
            'response': response,
            'error': error,
            'duration': duration
        }

    def print_summary(self):
        """Print a comprehensive summary of all test results."""
        print("\n" + "="*80)
        print("PROVIDER INTEGRATION TEST SUMMARY")
        print("="*80)

        success_count = sum(1 for r in self.results.values() if r['success'])
        total_count = len(self.results)

        for provider, result in self.results.items():
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"\n{status} {provider.upper()}")
            print(f"  Model: {result['model']}")
            if result['duration']:
                print(f"  Duration: {result['duration']:.2f}s")
            if result['success']:
                print(f"  Response: {result['response'][:100]}...")
            else:
                print(f"  Error: {result['error']}")

        print("\n" + "="*80)
        print(f"OVERALL: {success_count}/{total_count} providers passed")
        print("="*80 + "\n")


@pytest.fixture(scope="module")
def test_results():
    """Fixture to track test results across all tests."""
    results = IntegrationTestResults()
    yield results
    results.print_summary()


@pytest.fixture(scope="module")
def registry():
    """Get a fresh provider registry with env vars loaded."""
    # Force reload of environment
    load_dotenv(override=True)

    # Create fresh registry
    reg = ProviderRegistry()
    reg.register_from_env()
    return reg


@pytest.fixture
def test_request():
    """Create a standard test request."""
    return CompletionRequest(
        model="",  # Will be set per provider
        messages=[Message(role="user", content=TEST_PROMPT)],
        temperature=0.1,
        max_tokens=MAX_TOKENS,
        timeout=TEST_TIMEOUT
    )


def is_provider_configured(provider: ProviderId) -> bool:
    """Check if a provider has its API key configured."""
    env_vars = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'gemini': 'GOOGLE_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY'
    }

    api_key = os.getenv(env_vars[provider], '')
    # Check if key is set and not a placeholder
    return bool(api_key and not api_key.startswith('$'))


@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('openai'),
                    reason="OPENAI_API_KEY not configured")
async def test_openai_integration(registry, test_request, test_results):
    """Test actual OpenAI API communication."""
    import time

    print("\n" + "="*80)
    print("Testing OpenAI Provider")
    print("="*80)

    provider_id: ProviderId = 'openai'
    model = "gpt-4o-mini"  # Use mini for cost efficiency

    try:
        start_time = time.time()

        # Get client
        print(f"Getting client for provider: {provider_id}")
        client = registry.get_client(provider_id)
        print(f"✓ Client created successfully")

        # Make API call
        print(f"Making API call to model: {model}")
        test_request.model = model
        response = await client.complete(test_request)

        duration = time.time() - start_time

        # Validate response
        assert isinstance(response, CompletionResponse)
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✓ API call successful")
        print(f"Response: {response.content}")
        print(f"Duration: {duration:.2f}s")

        test_results.add_result(
            provider_id, model, True,
            response.content, None, duration
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        test_results.add_result(provider_id, model, False, None, str(e))
        raise


@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('anthropic'),
                    reason="ANTHROPIC_API_KEY not configured")
async def test_anthropic_integration(registry, test_request, test_results):
    """Test actual Anthropic API communication."""
    import time

    print("\n" + "="*80)
    print("Testing Anthropic Provider")
    print("="*80)

    provider_id: ProviderId = 'anthropic'
    model = "claude-3-5-haiku-20241022"  # Use haiku for cost efficiency

    try:
        start_time = time.time()

        # Get client
        print(f"Getting client for provider: {provider_id}")
        client = registry.get_client(provider_id)
        print(f"✓ Client created successfully")

        # Make API call
        print(f"Making API call to model: {model}")
        test_request.model = model
        response = await client.complete(test_request)

        duration = time.time() - start_time

        # Validate response
        assert isinstance(response, CompletionResponse)
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✓ API call successful")
        print(f"Response: {response.content}")
        print(f"Duration: {duration:.2f}s")

        test_results.add_result(
            provider_id, model, True,
            response.content, None, duration
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        test_results.add_result(provider_id, model, False, None, str(e))
        raise


@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('gemini'),
                    reason="GOOGLE_API_KEY not configured")
async def test_gemini_integration(registry, test_request, test_results):
    """Test actual Google Gemini API communication."""
    import time

    print("\n" + "="*80)
    print("Testing Gemini Provider")
    print("="*80)

    provider_id: ProviderId = 'gemini'
    model = "gemini-2.0-flash-exp"  # Use flash for speed

    try:
        start_time = time.time()

        # Get client
        print(f"Getting client for provider: {provider_id}")
        client = registry.get_client(provider_id)
        print(f"✓ Client created successfully")

        # Make API call
        print(f"Making API call to model: {model}")
        test_request.model = model
        response = await client.complete(test_request)

        duration = time.time() - start_time

        # Validate response
        assert isinstance(response, CompletionResponse)
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✓ API call successful")
        print(f"Response: {response.content}")
        print(f"Duration: {duration:.2f}s")

        test_results.add_result(
            provider_id, model, True,
            response.content, None, duration
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        test_results.add_result(provider_id, model, False, None, str(e))
        raise


@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('perplexity'),
                    reason="PERPLEXITY_API_KEY not configured")
async def test_perplexity_integration(registry, test_request, test_results):
    """Test actual Perplexity API communication."""
    import time

    print("\n" + "="*80)
    print("Testing Perplexity Provider")
    print("="*80)

    provider_id: ProviderId = 'perplexity'
    model = "sonar-pro"

    try:
        start_time = time.time()

        # Get client
        print(f"Getting client for provider: {provider_id}")
        client = registry.get_client(provider_id)
        print(f"✓ Client created successfully")

        # Make API call
        print(f"Making API call to model: {model}")
        test_request.model = model
        response = await client.complete(test_request)

        duration = time.time() - start_time

        # Validate response
        assert isinstance(response, CompletionResponse)
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✓ API call successful")
        print(f"Response: {response.content}")
        print(f"Duration: {duration:.2f}s")

        test_results.add_result(
            provider_id, model, True,
            response.content, None, duration
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        test_results.add_result(provider_id, model, False, None, str(e))
        raise


@pytest.mark.asyncio
@pytest.mark.skipif(not is_provider_configured('openrouter'),
                    reason="OPENROUTER_API_KEY not configured")
async def test_openrouter_integration(registry, test_request, test_results):
    """Test actual OpenRouter API communication."""
    import time

    print("\n" + "="*80)
    print("Testing OpenRouter Provider")
    print("="*80)

    provider_id: ProviderId = 'openrouter'
    model = "openai/gpt-4o-mini"  # Use paid model (more reliable than free tier)

    try:
        start_time = time.time()

        # Get client
        print(f"Getting client for provider: {provider_id}")
        client = registry.get_client(provider_id)
        print(f"✓ Client created successfully")

        # Make API call
        print(f"Making API call to model: {model}")
        test_request.model = model
        response = await client.complete(test_request)

        duration = time.time() - start_time

        # Validate response
        assert isinstance(response, CompletionResponse)
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✓ API call successful")
        print(f"Response: {response.content}")
        print(f"Duration: {duration:.2f}s")

        test_results.add_result(
            provider_id, model, True,
            response.content, None, duration
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        test_results.add_result(provider_id, model, False, None, str(e))
        raise


@pytest.mark.asyncio
async def test_configured_models_from_env(registry, test_results):
    """
    Test the exact models configured in .env file.
    This verifies the production configuration.
    """
    print("\n" + "="*80)
    print("Testing Production Configuration from .env")
    print("="*80)

    from backend.config import COUNCIL_MODELS, CHAIRMAN_MODEL, RESEARCH_MODEL

    # Collect all configured models
    all_models = []
    if COUNCIL_MODELS:
        all_models.extend(COUNCIL_MODELS)
    if CHAIRMAN_MODEL and CHAIRMAN_MODEL not in all_models:
        all_models.append(CHAIRMAN_MODEL)
    if RESEARCH_MODEL and RESEARCH_MODEL not in all_models:
        all_models.append(RESEARCH_MODEL)

    print(f"\nFound {len(all_models)} configured models:")
    for model_id in all_models:
        print(f"  - {model_id}")

    if not all_models:
        pytest.skip("No models configured in .env")

    # Test each configured model
    from backend.providers.parser import parse_provider_model

    results_summary = []

    for model_id in all_models:
        try:
            print(f"\n{'='*60}")
            print(f"Testing: {model_id}")
            print(f"{'='*60}")

            # Parse model ID
            parsed = parse_provider_model(model_id)
            provider_id = parsed.provider
            model_name = parsed.model

            # Check if provider is configured
            if not registry.is_provider_configured(provider_id):
                print(f"⊘ Skipping: Provider {provider_id} not configured")
                results_summary.append((model_id, 'SKIPPED', 'Provider not configured'))
                continue

            # Get client and test
            import time
            start_time = time.time()

            client = registry.get_client(provider_id)

            request = CompletionRequest(
                model=model_name,
                messages=[Message(role="user", content=TEST_PROMPT)],
                temperature=0.1,
                max_tokens=MAX_TOKENS,
                timeout=TEST_TIMEOUT
            )

            response = await client.complete(request)
            duration = time.time() - start_time

            # Validate
            assert response.content is not None
            assert len(response.content) > 0

            print(f"✓ Success!")
            print(f"Response: {response.content[:100]}...")
            print(f"Duration: {duration:.2f}s")

            results_summary.append((model_id, 'PASS', f"{duration:.2f}s"))

        except Exception as e:
            print(f"✗ Failed: {e}")
            results_summary.append((model_id, 'FAIL', str(e)))

    # Print summary
    print("\n" + "="*80)
    print("PRODUCTION CONFIGURATION TEST SUMMARY")
    print("="*80)

    for model_id, status, detail in results_summary:
        status_symbol = {
            'PASS': '✓',
            'FAIL': '✗',
            'SKIPPED': '⊘'
        }.get(status, '?')

        print(f"{status_symbol} {model_id:50s} {status:10s} {detail}")

    print("="*80 + "\n")

    # Count results
    passed = sum(1 for _, status, _ in results_summary if status == 'PASS')
    failed = sum(1 for _, status, _ in results_summary if status == 'FAIL')
    skipped = sum(1 for _, status, _ in results_summary if status == 'SKIPPED')

    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    # Test passes if at least one model worked
    assert passed > 0, "At least one configured model must pass"


@pytest.mark.asyncio
async def test_parallel_requests(registry):
    """Test parallel requests to multiple providers."""
    print("\n" + "="*80)
    print("Testing Parallel Provider Requests")
    print("="*80)

    # Find all configured providers
    providers_to_test = []
    provider_models = {
        'openai': 'gpt-4o-mini',
        'anthropic': 'claude-3-5-haiku-20241022',
        'gemini': 'gemini-2.0-flash-exp',
        'perplexity': 'sonar-pro',
        'openrouter': 'openai/gpt-4o-mini'
    }

    for provider_id, model in provider_models.items():
        if is_provider_configured(provider_id):
            providers_to_test.append((provider_id, model))

    if len(providers_to_test) < 2:
        pytest.skip("Need at least 2 providers configured for parallel test")

    print(f"Testing {len(providers_to_test)} providers in parallel...")

    # Create tasks for all providers
    async def test_provider(provider_id: ProviderId, model: str):
        client = registry.get_client(provider_id)
        request = CompletionRequest(
            model=model,
            messages=[Message(role="user", content="Say 'test'")],
            temperature=0.1,
            max_tokens=10,
            timeout=TEST_TIMEOUT
        )
        return await client.complete(request)

    import time
    start_time = time.time()

    tasks = [test_provider(p, m) for p, m in providers_to_test]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    duration = time.time() - start_time

    # Check results
    success_count = 0
    for (provider_id, model), response in zip(providers_to_test, responses):
        if isinstance(response, Exception):
            print(f"✗ {provider_id}: {response}")
        else:
            print(f"✓ {provider_id}: {response.content[:50]}")
            success_count += 1

    print(f"\nParallel execution completed in {duration:.2f}s")
    print(f"Success rate: {success_count}/{len(providers_to_test)}")

    # Test passes if at least half succeeded
    assert success_count >= len(providers_to_test) / 2


if __name__ == "__main__":
    """
    Run integration tests directly.

    Usage:
        python -m backend.tests.integration.test_provider_integration
    """
    import sys

    # Run pytest programmatically
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))
