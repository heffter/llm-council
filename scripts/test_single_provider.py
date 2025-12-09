#!/usr/bin/env python3
"""
Quick test script for a single provider.

Usage:
    python scripts/test_single_provider.py openai gpt-4o-mini
    python scripts/test_single_provider.py anthropic claude-3-5-haiku-20241022
    python scripts/test_single_provider.py gemini gemini-2.0-flash-exp

Environment variables required:
    - OPENAI_API_KEY (for openai)
    - ANTHROPIC_API_KEY (for anthropic)
    - GOOGLE_API_KEY (for gemini)
    - PERPLEXITY_API_KEY (for perplexity)
    - OPENROUTER_API_KEY (for openrouter)
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from backend.providers.registry import ProviderRegistry
from backend.providers.base import Message, CompletionRequest, CompletionResponse
from backend.providers.parser import ProviderId

# Load environment
load_dotenv()


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_success(text: str):
    """Print success message in green."""
    print(f"\033[92m✓ {text}\033[0m")


def print_error(text: str):
    """Print error message in red."""
    print(f"\033[91m✗ {text}\033[0m")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


async def test_provider(provider: ProviderId, model: str, prompt: str = "Say 'Hello' and nothing else."):
    """
    Test a single provider with a specific model.

    Args:
        provider: Provider ID (openai, anthropic, gemini, perplexity, openrouter)
        model: Model identifier
        prompt: Test prompt to send
    """
    print_header(f"Testing {provider.upper()} Provider")

    # Check if API key is configured
    env_var_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'gemini': 'GOOGLE_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY'
    }

    api_key_env = env_var_map.get(provider)
    api_key = os.getenv(api_key_env, '')

    print_info(f"Provider: {provider}")
    print_info(f"Model: {model}")
    print_info(f"API Key: {'configured' if api_key and not api_key.startswith('$') else 'NOT configured'}")

    if not api_key or api_key.startswith('$'):
        print_error(f"API key not configured. Please set {api_key_env}")
        return False

    try:
        # Create registry and get client
        print_info("Creating provider client...")
        registry = ProviderRegistry()
        registry.register_from_env()

        if not registry.is_provider_configured(provider):
            print_error(f"Provider '{provider}' is not registered")
            return False

        client = registry.get_client(provider)
        print_success("Client created successfully")

        # Create request
        print_info(f"Sending request: '{prompt}'")
        request = CompletionRequest(
            model=model,
            messages=[Message(role="user", content=prompt)],
            temperature=0.1,
            max_tokens=100,
            timeout=30.0
        )

        # Make API call
        start_time = time.time()
        response = await client.complete(request)
        duration = time.time() - start_time

        # Validate response
        if not response or not response.content:
            print_error("Received empty response")
            return False

        print_success(f"API call completed in {duration:.2f}s")
        print("\n" + "-" * 80)
        print("RESPONSE:")
        print("-" * 80)
        print(response.content)
        print("-" * 80)

        if response.reasoning_details:
            print("\nReasoning details:", response.reasoning_details)

        return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        print("\nFull error:")
        traceback.print_exc()
        return False


async def test_all_configured():
    """Test all configured providers."""
    print_header("Testing All Configured Providers")

    providers_to_test = []

    # Scan for configured providers
    test_configs = {
        'openai': ('OPENAI_API_KEY', 'gpt-4o-mini'),
        'anthropic': ('ANTHROPIC_API_KEY', 'claude-3-5-haiku-20241022'),
        'gemini': ('GOOGLE_API_KEY', 'gemini-2.0-flash-exp'),
        'perplexity': ('PERPLEXITY_API_KEY', 'sonar-pro'),
        'openrouter': ('OPENROUTER_API_KEY', 'openai/gpt-4o-mini')
    }

    for provider, (env_var, model) in test_configs.items():
        api_key = os.getenv(env_var, '')
        if api_key and not api_key.startswith('$'):
            providers_to_test.append((provider, model))

    if not providers_to_test:
        print_error("No providers configured!")
        print("\nPlease set at least one API key:")
        for provider, (env_var, _) in test_configs.items():
            print(f"  export {env_var}='your-key-here'")
        return

    print_info(f"Found {len(providers_to_test)} configured provider(s):\n")
    for provider, model in providers_to_test:
        print(f"  - {provider} ({model})")

    print("\n")

    # Test each provider
    results = []
    for provider, model in providers_to_test:
        success = await test_provider(provider, model)
        results.append((provider, model, success))
        print("\n")

    # Print summary
    print_header("SUMMARY")
    success_count = sum(1 for _, _, success in results if success)

    for provider, model, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        status_color = "\033[92m" if success else "\033[91m"
        print(f"{status_color}{status}\033[0m {provider:15s} ({model})")

    print("\n" + "=" * 80)
    print(f"Results: {success_count}/{len(results)} providers passed")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # No arguments - test all configured
        asyncio.run(test_all_configured())
    elif len(sys.argv) == 3:
        # Provider and model specified
        provider = sys.argv[1]
        model = sys.argv[2]

        valid_providers = ['openai', 'anthropic', 'gemini', 'perplexity', 'openrouter']
        if provider not in valid_providers:
            print_error(f"Invalid provider: {provider}")
            print(f"Valid providers: {', '.join(valid_providers)}")
            sys.exit(1)

        success = asyncio.run(test_provider(provider, model))
        sys.exit(0 if success else 1)
    else:
        print("Usage:")
        print("  python scripts/test_single_provider.py                    # Test all configured")
        print("  python scripts/test_single_provider.py <provider> <model> # Test specific")
        print("\nExamples:")
        print("  python scripts/test_single_provider.py openai gpt-4o-mini")
        print("  python scripts/test_single_provider.py anthropic claude-3-5-haiku-20241022")
        print("  python scripts/test_single_provider.py gemini gemini-2.0-flash-exp")
        sys.exit(1)


if __name__ == "__main__":
    main()
