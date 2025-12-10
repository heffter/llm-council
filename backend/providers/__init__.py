"""LLM provider abstraction layer."""

from .base import LLMProviderClient, Message, CompletionRequest, CompletionResponse
from .parser import parse_provider_model, ParsedModelId, ProviderId
from .registry import ProviderRegistry, get_registry
from .models import (
    ModelInfo,
    PresetConfig,
    MODEL_CATALOG,
    PRESETS,
    get_model_info,
    get_models_by_provider,
    get_all_models,
    get_preset,
    get_all_presets,
    resolve_preset,
    get_or_create_model_info,
)

__all__ = [
    'LLMProviderClient',
    'Message',
    'CompletionRequest',
    'CompletionResponse',
    'parse_provider_model',
    'ParsedModelId',
    'ProviderId',
    'ProviderRegistry',
    'get_registry',
    # Model catalog
    'ModelInfo',
    'PresetConfig',
    'MODEL_CATALOG',
    'PRESETS',
    'get_model_info',
    'get_models_by_provider',
    'get_all_models',
    'get_preset',
    'get_all_presets',
    'resolve_preset',
    'get_or_create_model_info',
]
