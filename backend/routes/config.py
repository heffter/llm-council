"""Configuration API endpoints for model and provider information."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..providers import (
    get_all_models,
    get_models_by_provider,
    get_all_presets,
    get_preset,
    resolve_preset,
)
from ..config import COUNCIL_MODELS, CHAIRMAN_MODEL, RESEARCH_MODEL
from ..council_validation import (
    validate_council_config,
    get_council_metadata,
    MIN_COUNCIL_SIZE,
    MAX_COUNCIL_SIZE,
)
from ..webhook import get_webhook_config, WebhookEvent


router = APIRouter(prefix="/api/config", tags=["config"])


# =============================================================================
# Response Models
# =============================================================================

class ModelInfoResponse(BaseModel):
    """Model metadata response."""
    id: str
    provider: str
    full_id: str
    display_name: str
    cost_tier: str
    speed_tier: str
    description: str
    context_window: int


class ProviderInfoResponse(BaseModel):
    """Provider information with available models."""
    id: str
    display_name: str
    models: List[ModelInfoResponse]


class PresetResponse(BaseModel):
    """Preset configuration response."""
    name: str
    display_name: str
    description: str
    council_models: List[str]
    chairman_model: str
    research_model: Optional[str]


class CurrentConfigResponse(BaseModel):
    """Current active configuration."""
    council_models: List[str]
    chairman_model: str
    research_model: Optional[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/models", response_model=List[ModelInfoResponse])
async def list_models():
    """
    List all known models with their metadata.

    Returns models from the catalog with cost tier, speed tier, and context window info.
    Models not in the catalog can still be used but won't appear here.
    """
    models = get_all_models()
    return [
        ModelInfoResponse(
            id=m.id,
            provider=m.provider,
            full_id=m.full_id,
            display_name=m.display_name,
            cost_tier=m.cost_tier,
            speed_tier=m.speed_tier,
            description=m.description,
            context_window=m.context_window
        )
        for m in models
    ]


@router.get("/models/{provider}", response_model=List[ModelInfoResponse])
async def list_models_by_provider(provider: str):
    """
    List models for a specific provider.

    Args:
        provider: Provider ID (openai, anthropic, gemini, perplexity, openrouter)
    """
    models = get_models_by_provider(provider)  # type: ignore
    return [
        ModelInfoResponse(
            id=m.id,
            provider=m.provider,
            full_id=m.full_id,
            display_name=m.display_name,
            cost_tier=m.cost_tier,
            speed_tier=m.speed_tier,
            description=m.description,
            context_window=m.context_window
        )
        for m in models
    ]


@router.get("/providers", response_model=List[ProviderInfoResponse])
async def list_providers():
    """
    List all providers with their available models.

    Groups models by provider for easy display in UI.
    """
    providers_map: Dict[str, List[Any]] = {}

    for model in get_all_models():
        if model.provider not in providers_map:
            providers_map[model.provider] = []
        providers_map[model.provider].append(model)

    provider_display_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "gemini": "Google Gemini",
        "perplexity": "Perplexity",
        "openrouter": "OpenRouter"
    }

    return [
        ProviderInfoResponse(
            id=provider_id,
            display_name=provider_display_names.get(provider_id, provider_id),
            models=[
                ModelInfoResponse(
                    id=m.id,
                    provider=m.provider,
                    full_id=m.full_id,
                    display_name=m.display_name,
                    cost_tier=m.cost_tier,
                    speed_tier=m.speed_tier,
                    description=m.description,
                    context_window=m.context_window
                )
                for m in models
            ]
        )
        for provider_id, models in sorted(providers_map.items())
    ]


@router.get("/presets", response_model=List[PresetResponse])
async def list_presets():
    """
    List all available model presets.

    Presets are pre-configured combinations of council, chairman, and research models
    optimized for different use cases (fast, balanced, comprehensive).
    """
    presets = get_all_presets()
    return [
        PresetResponse(
            name=p.name,
            display_name=p.display_name,
            description=p.description,
            council_models=p.council_models,
            chairman_model=p.chairman_model,
            research_model=p.research_model
        )
        for p in presets
    ]


@router.get("/presets/{name}", response_model=PresetResponse)
async def get_preset_by_name(name: str):
    """
    Get a specific preset by name.

    Args:
        name: Preset name (fast, balanced, comprehensive)
    """
    from fastapi import HTTPException

    preset = get_preset(name)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")

    return PresetResponse(
        name=preset.name,
        display_name=preset.display_name,
        description=preset.description,
        council_models=preset.council_models,
        chairman_model=preset.chairman_model,
        research_model=preset.research_model
    )


@router.get("/current", response_model=CurrentConfigResponse)
async def get_current_config():
    """
    Get the current active model configuration.

    Returns the models currently configured via environment variables.
    """
    return CurrentConfigResponse(
        council_models=COUNCIL_MODELS,
        chairman_model=CHAIRMAN_MODEL,
        research_model=RESEARCH_MODEL
    )


# =============================================================================
# Council Configuration Endpoints
# =============================================================================

class CouncilMemberResponse(BaseModel):
    """Council member with metadata."""
    id: str
    provider: str
    display_name: str
    cost_tier: str
    speed_tier: str
    context_window: int


class CouncilConfigResponse(BaseModel):
    """Active council configuration with member metadata."""
    council_models: List[CouncilMemberResponse]
    chairman: Optional[CouncilMemberResponse]
    research: Optional[CouncilMemberResponse]
    constraints: Dict[str, int]


class ValidateCouncilRequest(BaseModel):
    """Request to validate a council configuration."""
    council_models: List[str]
    chairman_model: Optional[str] = None
    research_model: Optional[str] = None


class ValidationResultResponse(BaseModel):
    """Validation result response."""
    valid: bool
    errors: List[str]
    warnings: List[str]


@router.get("/council")
async def get_council_config():
    """
    Get the active council configuration with member metadata.

    Returns the current council composition including provider and
    capability metadata for each member.
    """
    council_metadata = get_council_metadata(COUNCIL_MODELS)

    chairman_metadata = None
    if CHAIRMAN_MODEL:
        chair_meta = get_council_metadata([CHAIRMAN_MODEL])
        if chair_meta:
            chairman_metadata = chair_meta[0]

    research_metadata = None
    if RESEARCH_MODEL:
        research_meta = get_council_metadata([RESEARCH_MODEL])
        if research_meta:
            research_metadata = research_meta[0]

    return {
        "council_models": council_metadata,
        "chairman": chairman_metadata,
        "research": research_metadata,
        "constraints": {
            "min_council_size": MIN_COUNCIL_SIZE,
            "max_council_size": MAX_COUNCIL_SIZE
        }
    }


@router.post("/council/validate", response_model=ValidationResultResponse)
async def validate_council(request: ValidateCouncilRequest):
    """
    Validate a council configuration without applying it.

    Checks:
    - Council size constraints (min 2, max 7)
    - Model ID format and validity
    - Provider diversity (warns if all from same provider)

    Returns validation result with errors and warnings.
    """
    result = validate_council_config(
        council_models=request.council_models,
        chairman_model=request.chairman_model,
        research_model=request.research_model
    )

    return ValidationResultResponse(
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings
    )


# =============================================================================
# Webhook Configuration Endpoints
# =============================================================================

class WebhookConfigResponse(BaseModel):
    """Webhook configuration response."""
    enabled: bool
    url_configured: bool
    secret_configured: bool
    available_events: List[str]


@router.get("/webhook")
async def get_webhook_configuration():
    """
    Get the current webhook configuration status.

    Returns whether webhooks are enabled, whether URL and secret are configured,
    and the list of available event types. Does not expose the actual URL or
    secret values for security.
    """
    config = get_webhook_config()

    return WebhookConfigResponse(
        enabled=config.enabled,
        url_configured=config.url is not None,
        secret_configured=config.secret is not None,
        available_events=[e.value for e in WebhookEvent]
    )
