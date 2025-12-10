"""Model metadata and presets for the LLM Council."""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict


# Type definitions
CostTier = Literal["low", "medium", "high"]
SpeedTier = Literal["fast", "medium", "slow"]
ProviderId = Literal["openai", "anthropic", "gemini", "perplexity", "openrouter"]


@dataclass
class ModelInfo:
    """Metadata for a specific model."""
    id: str                    # Full model ID (e.g., "gpt-4o", "claude-3-5-sonnet-latest")
    provider: ProviderId       # Provider name
    display_name: str          # Human-readable name
    cost_tier: CostTier        # Estimated cost tier
    speed_tier: SpeedTier      # Response speed tier
    description: str = ""      # Optional description
    context_window: int = 0    # Context window size (0 = unknown)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @property
    def full_id(self) -> str:
        """Return provider:model format."""
        return f"{self.provider}:{self.id}"


@dataclass
class PresetConfig:
    """Configuration for a model preset."""
    name: str
    display_name: str
    description: str
    council_models: List[str]    # List of provider:model strings
    chairman_model: str          # provider:model string
    research_model: Optional[str] = None  # provider:model string (optional)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# =============================================================================
# Model Catalog
# =============================================================================
# This catalog contains known models with their metadata.
# Models not in this catalog can still be used - they just won't have metadata.

MODEL_CATALOG: Dict[str, ModelInfo] = {}

def _register_model(model: ModelInfo) -> None:
    """Register a model in the catalog."""
    MODEL_CATALOG[model.full_id] = model


# OpenAI Models
_register_model(ModelInfo(
    id="gpt-4o",
    provider="openai",
    display_name="GPT-4o",
    cost_tier="high",
    speed_tier="medium",
    description="Most capable GPT-4 model with vision",
    context_window=128000
))
_register_model(ModelInfo(
    id="gpt-4o-mini",
    provider="openai",
    display_name="GPT-4o Mini",
    cost_tier="low",
    speed_tier="fast",
    description="Smaller, faster GPT-4o variant",
    context_window=128000
))
_register_model(ModelInfo(
    id="gpt-4.1",
    provider="openai",
    display_name="GPT-4.1",
    cost_tier="high",
    speed_tier="medium",
    description="Latest GPT-4 model",
    context_window=128000
))
_register_model(ModelInfo(
    id="gpt-4.1-mini",
    provider="openai",
    display_name="GPT-4.1 Mini",
    cost_tier="low",
    speed_tier="fast",
    description="Smaller GPT-4.1 variant",
    context_window=128000
))
_register_model(ModelInfo(
    id="o3-mini",
    provider="openai",
    display_name="O3 Mini",
    cost_tier="medium",
    speed_tier="fast",
    description="Reasoning-optimized model",
    context_window=128000
))

# Anthropic Models
_register_model(ModelInfo(
    id="claude-3-5-sonnet-latest",
    provider="anthropic",
    display_name="Claude 3.5 Sonnet",
    cost_tier="medium",
    speed_tier="medium",
    description="Balanced performance and cost",
    context_window=200000
))
_register_model(ModelInfo(
    id="claude-3-opus-latest",
    provider="anthropic",
    display_name="Claude 3 Opus",
    cost_tier="high",
    speed_tier="slow",
    description="Most capable Claude model",
    context_window=200000
))
_register_model(ModelInfo(
    id="claude-3-haiku-20240307",
    provider="anthropic",
    display_name="Claude 3 Haiku",
    cost_tier="low",
    speed_tier="fast",
    description="Fast and efficient",
    context_window=200000
))
_register_model(ModelInfo(
    id="claude-sonnet-4-5",
    provider="anthropic",
    display_name="Claude Sonnet 4.5",
    cost_tier="medium",
    speed_tier="medium",
    description="Latest Claude Sonnet",
    context_window=200000
))

# Gemini Models
_register_model(ModelInfo(
    id="gemini-2.0-pro",
    provider="gemini",
    display_name="Gemini 2.0 Pro",
    cost_tier="high",
    speed_tier="medium",
    description="Google's most capable model",
    context_window=1000000
))
_register_model(ModelInfo(
    id="gemini-2.0-flash",
    provider="gemini",
    display_name="Gemini 2.0 Flash",
    cost_tier="low",
    speed_tier="fast",
    description="Fast Gemini variant",
    context_window=1000000
))
_register_model(ModelInfo(
    id="gemini-1.5-pro",
    provider="gemini",
    display_name="Gemini 1.5 Pro",
    cost_tier="medium",
    speed_tier="medium",
    description="Previous generation Pro",
    context_window=1000000
))
_register_model(ModelInfo(
    id="gemini-1.5-flash",
    provider="gemini",
    display_name="Gemini 1.5 Flash",
    cost_tier="low",
    speed_tier="fast",
    description="Previous generation Flash",
    context_window=1000000
))

# Perplexity Models
_register_model(ModelInfo(
    id="sonar-pro",
    provider="perplexity",
    display_name="Sonar Pro",
    cost_tier="medium",
    speed_tier="medium",
    description="Research-optimized with web access",
    context_window=127000
))
_register_model(ModelInfo(
    id="sonar-reasoning",
    provider="perplexity",
    display_name="Sonar Reasoning",
    cost_tier="high",
    speed_tier="slow",
    description="Advanced reasoning with citations",
    context_window=127000
))

# OpenRouter Models (proxied)
_register_model(ModelInfo(
    id="anthropic/claude-3-5-sonnet",
    provider="openrouter",
    display_name="Claude 3.5 Sonnet (OR)",
    cost_tier="medium",
    speed_tier="medium",
    description="Claude via OpenRouter",
    context_window=200000
))
_register_model(ModelInfo(
    id="openai/gpt-4o",
    provider="openrouter",
    display_name="GPT-4o (OR)",
    cost_tier="high",
    speed_tier="medium",
    description="GPT-4o via OpenRouter",
    context_window=128000
))
_register_model(ModelInfo(
    id="google/gemini-2.0-flash-exp:free",
    provider="openrouter",
    display_name="Gemini 2.0 Flash (Free)",
    cost_tier="low",
    speed_tier="fast",
    description="Free Gemini via OpenRouter",
    context_window=1000000
))


# =============================================================================
# Presets
# =============================================================================

PRESETS: Dict[str, PresetConfig] = {
    "fast": PresetConfig(
        name="fast",
        display_name="Fast",
        description="Optimized for speed with cost-efficient models",
        council_models=[
            "openai:gpt-4o-mini",
            "anthropic:claude-3-haiku-20240307",
            "gemini:gemini-2.0-flash"
        ],
        chairman_model="anthropic:claude-3-5-sonnet-latest",
        research_model=None
    ),
    "balanced": PresetConfig(
        name="balanced",
        display_name="Balanced",
        description="Good balance of quality, speed, and cost",
        council_models=[
            "openai:gpt-4o",
            "anthropic:claude-3-5-sonnet-latest",
            "gemini:gemini-2.0-flash"
        ],
        chairman_model="anthropic:claude-3-5-sonnet-latest",
        research_model="perplexity:sonar-pro"
    ),
    "comprehensive": PresetConfig(
        name="comprehensive",
        display_name="Comprehensive",
        description="Maximum quality with top-tier models",
        council_models=[
            "openai:gpt-4.1",
            "anthropic:claude-3-opus-latest",
            "gemini:gemini-2.0-pro"
        ],
        chairman_model="anthropic:claude-3-opus-latest",
        research_model="perplexity:sonar-reasoning"
    )
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """
    Get metadata for a model by its full ID (provider:model).

    Args:
        model_id: Full model identifier (e.g., "openai:gpt-4o")

    Returns:
        ModelInfo if found in catalog, None otherwise
    """
    return MODEL_CATALOG.get(model_id)


def get_models_by_provider(provider: ProviderId) -> List[ModelInfo]:
    """
    Get all known models for a specific provider.

    Args:
        provider: Provider identifier

    Returns:
        List of ModelInfo for that provider
    """
    return [m for m in MODEL_CATALOG.values() if m.provider == provider]


def get_all_models() -> List[ModelInfo]:
    """Get all known models."""
    return list(MODEL_CATALOG.values())


def get_preset(name: str) -> Optional[PresetConfig]:
    """
    Get a preset configuration by name.

    Args:
        name: Preset name (fast, balanced, comprehensive)

    Returns:
        PresetConfig if found, None otherwise
    """
    return PRESETS.get(name.lower())


def get_all_presets() -> List[PresetConfig]:
    """Get all available presets."""
    return list(PRESETS.values())


def resolve_preset(preset_name: str) -> Optional[Dict[str, any]]:
    """
    Resolve a preset name to its model configuration.

    Args:
        preset_name: Name of the preset

    Returns:
        Dict with council_models, chairman_model, research_model keys,
        or None if preset not found
    """
    preset = get_preset(preset_name)
    if preset is None:
        return None

    return {
        "council_models": preset.council_models,
        "chairman_model": preset.chairman_model,
        "research_model": preset.research_model
    }


def create_unknown_model_info(model_id: str) -> ModelInfo:
    """
    Create a ModelInfo for a model not in the catalog.

    Args:
        model_id: Full model identifier (provider:model)

    Returns:
        ModelInfo with default/unknown values
    """
    parts = model_id.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid model ID format: {model_id}")

    provider, model = parts
    return ModelInfo(
        id=model,
        provider=provider,  # type: ignore
        display_name=model,
        cost_tier="medium",
        speed_tier="medium",
        description="Custom model"
    )


def get_or_create_model_info(model_id: str) -> ModelInfo:
    """
    Get model info from catalog or create a default one.

    Args:
        model_id: Full model identifier (provider:model)

    Returns:
        ModelInfo from catalog or newly created default
    """
    info = get_model_info(model_id)
    if info is not None:
        return info
    return create_unknown_model_info(model_id)
