#!/usr/bin/env python3
"""
Diagnostic script for failed providers.

This script follows community best practices:
1. Reads full error response body (not just status code)
2. Implements retry with exponential backoff
3. Tests multiple models per provider
4. Checks API key format validity
5. Tests with minimal payloads first
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import httpx

load_dotenv()


def print_header(text: str):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_success(text: str):
    print(f"\033[92m[OK] {text}\033[0m")


def print_error(text: str):
    print(f"\033[91m[ERROR] {text}\033[0m")


def print_warning(text: str):
    print(f"\033[93m[WARN] {text}\033[0m")


def print_info(text: str):
    print(f"[INFO] {text}")


async def test_gemini_detailed():
    """Detailed Gemini API diagnostics."""
    print_header("GEMINI PROVIDER DIAGNOSTICS")

    api_key = os.getenv("GOOGLE_API_KEY", "")

    # Step 1: Check API key format
    print("\n1. API Key Validation:")
    if not api_key:
        print_error("GOOGLE_API_KEY is not set")
        return False
    if api_key.startswith("$"):
        print_error(f"GOOGLE_API_KEY contains unexpanded variable: {api_key}")
        return False
    if not api_key.startswith("AIza"):
        print_warning(f"API key doesn't start with 'AIza' (typical Google API key prefix)")
        print_info(f"Key prefix: {api_key[:10]}...")
    else:
        print_success(f"API key format looks valid (starts with AIza, length={len(api_key)})")

    # Step 2: Test different models
    print("\n2. Testing Different Models:")

    models_to_test = [
        "gemini-1.5-flash",      # Stable, generally available
        "gemini-1.5-pro",        # Pro model
        "gemini-2.0-flash",      # Newer flash (from .env)
        "gemini-2.0-flash-exp",  # Experimental (from test)
    ]

    base_url = "https://generativelanguage.googleapis.com/v1beta"

    for model in models_to_test:
        print(f"\n   Testing model: {model}")

        # Minimal payload
        payload = {
            "contents": [{"role": "user", "parts": [{"text": "Hi"}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }

        url = f"{base_url}/models/{model}:generateContent?key={api_key}"

        # Retry with backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json=payload
                    )

                    print_info(f"   Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            print_success(f"   Response: {text[:50]}")
                        else:
                            print_warning(f"   No candidates in response: {json.dumps(data, indent=2)[:200]}")
                        break
                    elif response.status_code == 429:
                        # Parse error details
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown")
                            print_warning(f"   Rate limited: {error_msg}")
                        except:
                            print_warning(f"   Rate limited (no details)")

                        if attempt < max_retries - 1:
                            wait_time = 2 ** (attempt + 1)
                            print_info(f"   Retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                            await asyncio.sleep(wait_time)
                        else:
                            print_error(f"   Failed after {max_retries} attempts")
                    elif response.status_code == 400:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown")
                        print_error(f"   Bad request: {error_msg}")
                        break
                    elif response.status_code == 403:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown")
                        print_error(f"   Forbidden (API key issue?): {error_msg}")
                        break
                    elif response.status_code == 404:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown")
                        print_error(f"   Model not found: {error_msg}")
                        break
                    else:
                        print_error(f"   Unexpected status: {response.status_code}")
                        print_info(f"   Response: {response.text[:500]}")
                        break

            except httpx.TimeoutException:
                print_error(f"   Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                print_error(f"   Exception: {e}")
                break

    # Step 3: Check quota/billing status via list models endpoint
    print("\n3. Checking API Access (List Models):")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            list_url = f"{base_url}/models?key={api_key}"
            response = await client.get(list_url)

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print_success(f"API key is valid - can access {len(models)} models")
                gemini_models = [m["name"] for m in models if "gemini" in m.get("name", "").lower()]
                print_info(f"Available Gemini models: {gemini_models[:5]}...")
            else:
                print_error(f"Cannot list models: {response.status_code}")
                print_info(f"Response: {response.text[:300]}")
    except Exception as e:
        print_error(f"Failed to list models: {e}")

    return True


async def test_openrouter_detailed():
    """Detailed OpenRouter API diagnostics."""
    print_header("OPENROUTER PROVIDER DIAGNOSTICS")

    api_key = os.getenv("OPENROUTER_API_KEY", "")

    # Step 1: Check API key format
    print("\n1. API Key Validation:")
    if not api_key:
        print_error("OPENROUTER_API_KEY is not set")
        return False
    if api_key.startswith("$"):
        print_error(f"OPENROUTER_API_KEY contains unexpanded variable: {api_key}")
        return False
    if not api_key.startswith("sk-or-"):
        print_warning(f"API key doesn't start with 'sk-or-' (typical OpenRouter prefix)")
        print_info(f"Key prefix: {api_key[:10]}...")
    else:
        print_success(f"API key format looks valid (starts with sk-or-, length={len(api_key)})")

    # Step 2: Check account/credits status
    print("\n2. Checking Account Status:")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check auth key endpoint
            response = await client.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if response.status_code == 200:
                data = response.json()
                print_success(f"API key is valid")
                print_info(f"Account data: {json.dumps(data.get('data', {}), indent=2)}")
            else:
                print_error(f"Auth check failed: {response.status_code}")
                print_info(f"Response: {response.text[:300]}")
    except Exception as e:
        print_error(f"Failed to check auth: {e}")

    # Step 3: Test different models
    print("\n3. Testing Different Models:")

    models_to_test = [
        "openai/gpt-4o-mini",                        # Popular, should work
        "anthropic/claude-3-haiku",                  # Claude via OpenRouter
        "meta-llama/llama-3.2-3b-instruct:free",    # Free model (from test)
        "google/gemini-flash-1.5",                   # Gemini via OpenRouter
        "mistralai/mistral-7b-instruct:free",       # Another free model
    ]

    base_url = "https://openrouter.ai/api/v1"

    for model in models_to_test:
        print(f"\n   Testing model: {model}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/llm-council",  # Required by OpenRouter
            "X-Title": "LLM Council Test"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10
        }

        # Retry with backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )

                    print_info(f"   Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        print_success(f"   Response: {content[:50]}")
                        break
                    elif response.status_code == 429:
                        # Parse error details
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown")
                            print_warning(f"   Rate limited: {error_msg}")
                        except:
                            print_warning(f"   Rate limited (no details)")

                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            print_info(f"   Retry-After header: {retry_after}s")

                        if attempt < max_retries - 1:
                            wait_time = int(retry_after) if retry_after else 2 ** (attempt + 1)
                            print_info(f"   Retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                            await asyncio.sleep(wait_time)
                        else:
                            print_error(f"   Failed after {max_retries} attempts")
                    elif response.status_code == 400:
                        error_data = response.json()
                        print_error(f"   Bad request: {json.dumps(error_data, indent=2)[:200]}")
                        break
                    elif response.status_code == 401:
                        print_error(f"   Unauthorized - invalid API key")
                        break
                    elif response.status_code == 402:
                        print_error(f"   Payment required - insufficient credits")
                        try:
                            error_data = response.json()
                            print_info(f"   Details: {json.dumps(error_data, indent=2)[:200]}")
                        except:
                            pass
                        break
                    elif response.status_code == 404:
                        print_error(f"   Model not found")
                        break
                    else:
                        print_error(f"   Unexpected status: {response.status_code}")
                        print_info(f"   Response: {response.text[:500]}")
                        break

            except httpx.TimeoutException:
                print_error(f"   Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                print_error(f"   Exception: {e}")
                break

    # Step 4: Check available models
    print("\n4. Checking Rate Limits Info:")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                free_models = [m["id"] for m in models if ":free" in m.get("id", "")]
                print_success(f"Can access models endpoint - {len(models)} models available")
                print_info(f"Free models available: {free_models[:5]}...")
            else:
                print_warning(f"Cannot fetch models: {response.status_code}")
    except Exception as e:
        print_warning(f"Failed to fetch models: {e}")

    return True


async def main():
    """Run all diagnostics."""
    print_header("LLM PROVIDER DIAGNOSTICS")
    print_info("This script performs detailed diagnostics on failed providers")
    print_info("Following community best practices for API debugging")

    await test_gemini_detailed()

    print("\n" + "-" * 80)
    print("Waiting 5 seconds before testing OpenRouter...")
    print("-" * 80)
    await asyncio.sleep(5)

    await test_openrouter_detailed()

    print_header("DIAGNOSTICS COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
