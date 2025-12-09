#!/bin/bash
# Run provider integration tests
#
# This script runs integration tests that make REAL API calls to LLM providers.
# These tests verify actual connectivity and proper configuration.
#
# Usage:
#   ./scripts/run_integration_tests.sh
#
# Prerequisites:
#   1. Set API keys in environment or .env file
#   2. Ensure uv is installed
#   3. Run from project root

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "LLM Council Provider Integration Tests"
echo "================================================================================"
echo ""
echo "WARNING: These tests make REAL API calls and will consume API credits!"
echo ""

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    echo "Usage: ./scripts/run_integration_tests.sh"
    exit 1
fi

# Load .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
fi

# Check which providers are configured
echo ""
echo "Checking configured providers..."
echo "----------------------------------------"

PROVIDERS_CONFIGURED=0

if [ ! -z "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != '$OPENAI_API_KEY' ]; then
    echo -e "${GREEN}✓ OpenAI configured${NC}"
    PROVIDERS_CONFIGURED=$((PROVIDERS_CONFIGURED + 1))
else
    echo -e "${YELLOW}⊘ OpenAI not configured (set OPENAI_API_KEY)${NC}"
fi

if [ ! -z "$ANTHROPIC_API_KEY" ] && [ "$ANTHROPIC_API_KEY" != '$ANTHROPIC_API_KEY' ]; then
    echo -e "${GREEN}✓ Anthropic configured${NC}"
    PROVIDERS_CONFIGURED=$((PROVIDERS_CONFIGURED + 1))
else
    echo -e "${YELLOW}⊘ Anthropic not configured (set ANTHROPIC_API_KEY)${NC}"
fi

if [ ! -z "$GOOGLE_API_KEY" ] && [ "$GOOGLE_API_KEY" != '$GOOGLE_API_KEY' ]; then
    echo -e "${GREEN}✓ Google Gemini configured${NC}"
    PROVIDERS_CONFIGURED=$((PROVIDERS_CONFIGURED + 1))
else
    echo -e "${YELLOW}⊘ Google Gemini not configured (set GOOGLE_API_KEY)${NC}"
fi

if [ ! -z "$PERPLEXITY_API_KEY" ] && [ "$PERPLEXITY_API_KEY" != '$PERPLEXITY_API_KEY' ]; then
    echo -e "${GREEN}✓ Perplexity configured${NC}"
    PROVIDERS_CONFIGURED=$((PROVIDERS_CONFIGURED + 1))
else
    echo -e "${YELLOW}⊘ Perplexity not configured (set PERPLEXITY_API_KEY)${NC}"
fi

if [ ! -z "$OPENROUTER_API_KEY" ] && [ "$OPENROUTER_API_KEY" != '$OPENROUTER_API_KEY' ]; then
    echo -e "${GREEN}✓ OpenRouter configured${NC}"
    PROVIDERS_CONFIGURED=$((PROVIDERS_CONFIGURED + 1))
else
    echo -e "${YELLOW}⊘ OpenRouter not configured (set OPENROUTER_API_KEY)${NC}"
fi

echo "----------------------------------------"

if [ $PROVIDERS_CONFIGURED -eq 0 ]; then
    echo -e "${RED}Error: No providers configured!${NC}"
    echo ""
    echo "Please set at least one API key:"
    echo "  export OPENAI_API_KEY='sk-...'"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "  export GOOGLE_API_KEY='...'"
    echo "  export PERPLEXITY_API_KEY='pplx-...'"
    echo "  export OPENROUTER_API_KEY='sk-or-v1-...'"
    echo ""
    echo "Or add them to .env file (without the $ prefix)"
    exit 1
fi

echo ""
echo "Found $PROVIDERS_CONFIGURED configured provider(s)"
echo ""

# Ensure dependencies are installed
echo "Installing dependencies..."
uv sync --all-extras

echo ""
echo "================================================================================"
echo "Running Integration Tests"
echo "================================================================================"
echo ""

# Run tests with verbose output
uv run pytest backend/tests/integration/test_provider_integration.py -v -s --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "================================================================================"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests completed successfully!${NC}"
else
    echo -e "${RED}✗ Some integration tests failed${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Invalid or expired API keys"
    echo "  - Network connectivity problems"
    echo "  - Provider API rate limits"
    echo "  - Provider service outages"
fi

echo "================================================================================"

exit $TEST_EXIT_CODE
