"""Configuration for the LLM Council."""

import os
from typing import List, Optional
from dotenv import load_dotenv
from .providers.registry import get_registry

load_dotenv()


def parse_model_list(env_value: Optional[str]) -> List[str]:
    """
    Parse comma-separated model list from environment variable.

    Args:
        env_value: String like "openai:gpt-4.1,anthropic:claude-3-5-sonnet"

    Returns:
        List of model IDs
    """
    if not env_value:
        return []
    return [m.strip() for m in env_value.split(',') if m.strip()]


# Parse council models from env (comma-separated provider:model notation)
# Example: COUNCIL_MODELS=openai:gpt-4.1,anthropic:claude-3-5-sonnet,gemini:gemini-2.0-pro
_council_models_env = os.getenv("COUNCIL_MODELS", "")
COUNCIL_MODELS = parse_model_list(_council_models_env)

# Chairman model (single provider:model)
# Example: CHAIRMAN_MODEL=anthropic:claude-3-5-sonnet
CHAIRMAN_MODEL = os.getenv("CHAIRMAN_MODEL", "")

# Optional research model for ranking/title/auxiliary prompts
# Example: RESEARCH_MODEL=perplexity:sonar-pro
RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "")

# Data directory for conversation storage
DATA_DIR = "data/conversations"


def validate_config() -> None:
    """
    Validate configuration on startup.

    Ensures all configured models have their provider API keys set.

    Raises:
        ValueError: If required config is missing or invalid
    """
    registry = get_registry()
    errors = []

    # Validate council models
    if not COUNCIL_MODELS:
        errors.append("COUNCIL_MODELS environment variable is required")
    else:
        for model_id in COUNCIL_MODELS:
            try:
                registry.validate_model_id(model_id)
            except ValueError as e:
                errors.append(f"Council model '{model_id}': {e}")

    # Validate chairman model
    if not CHAIRMAN_MODEL:
        errors.append("CHAIRMAN_MODEL environment variable is required")
    else:
        try:
            registry.validate_model_id(CHAIRMAN_MODEL)
        except ValueError as e:
            errors.append(f"Chairman model '{CHAIRMAN_MODEL}': {e}")

    # Validate optional research model (warn only)
    if RESEARCH_MODEL:
        try:
            registry.validate_model_id(RESEARCH_MODEL)
        except ValueError as e:
            print(f"WARNING: Research model '{RESEARCH_MODEL}': {e}")
            print("Research features will be disabled.")

    # Fail fast if any errors
    if errors:
        error_msg = "Configuration validation failed:\n  " + "\n  ".join(errors)
        raise ValueError(error_msg)
