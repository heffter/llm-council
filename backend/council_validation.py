"""Council configuration validation utilities."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .providers import parse_provider_model, get_or_create_model_info


# Council size constraints
MIN_COUNCIL_SIZE = 2
MAX_COUNCIL_SIZE = 7


@dataclass
class ValidationResult:
    """Result of council configuration validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


def validate_council_size(models: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate council size constraints.

    Args:
        models: List of model IDs

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    count = len(models)

    if count < MIN_COUNCIL_SIZE:
        errors.append(
            f"Council requires at least {MIN_COUNCIL_SIZE} models, got {count}"
        )
    elif count > MAX_COUNCIL_SIZE:
        errors.append(
            f"Council allows at most {MAX_COUNCIL_SIZE} models, got {count}"
        )

    return errors, warnings


def check_provider_diversity(models: List[str]) -> List[str]:
    """
    Check for provider diversity and return warnings if lacking.

    Args:
        models: List of model IDs in provider:model format

    Returns:
        List of warning messages
    """
    warnings = []

    if not models:
        return warnings

    # Extract providers
    providers = set()
    for model_id in models:
        try:
            parsed = parse_provider_model(model_id)
            providers.add(parsed.provider)
        except ValueError:
            # Invalid model will be caught by other validation
            pass

    # Warn if all models are from the same provider
    if len(providers) == 1 and len(models) > 1:
        provider = list(providers)[0]
        warnings.append(
            f"All {len(models)} council models are from '{provider}'. "
            f"Consider using models from different providers for diverse perspectives."
        )

    return warnings


def validate_model_ids(
    models: List[str],
    registry=None
) -> Tuple[List[str], List[str]]:
    """
    Validate model IDs format and existence.

    Args:
        models: List of model IDs
        registry: Optional provider registry for API key validation

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    for model_id in models:
        try:
            parsed = parse_provider_model(model_id)

            # Check if model is in catalog (warn if not)
            info = get_or_create_model_info(model_id)
            if info.description == "Custom model":
                warnings.append(
                    f"Model '{model_id}' is not in the catalog. "
                    f"It will be used as a custom model."
                )

            # Check API key if registry is provided
            if registry:
                try:
                    registry.validate_model_id(model_id)
                except ValueError as e:
                    errors.append(f"Model '{model_id}': {str(e)}")

        except ValueError as e:
            errors.append(f"Invalid model ID '{model_id}': {str(e)}")

    return errors, warnings


def validate_council_config(
    council_models: List[str],
    chairman_model: Optional[str] = None,
    research_model: Optional[str] = None,
    registry=None
) -> ValidationResult:
    """
    Validate a complete council configuration.

    Args:
        council_models: List of council member model IDs
        chairman_model: Optional chairman model ID
        research_model: Optional research model ID
        registry: Optional provider registry for API key validation

    Returns:
        ValidationResult with errors and warnings
    """
    all_errors = []
    all_warnings = []

    # Validate council size
    size_errors, size_warnings = validate_council_size(council_models)
    all_errors.extend(size_errors)
    all_warnings.extend(size_warnings)

    # Validate council model IDs
    model_errors, model_warnings = validate_model_ids(council_models, registry)
    all_errors.extend(model_errors)
    all_warnings.extend(model_warnings)

    # Check provider diversity
    diversity_warnings = check_provider_diversity(council_models)
    all_warnings.extend(diversity_warnings)

    # Validate chairman model if provided
    if chairman_model:
        chair_errors, chair_warnings = validate_model_ids([chairman_model], registry)
        all_errors.extend([f"Chairman: {e}" for e in chair_errors])
        all_warnings.extend([f"Chairman: {w}" for w in chair_warnings])

    # Validate research model if provided
    if research_model:
        research_errors, research_warnings = validate_model_ids([research_model], registry)
        all_errors.extend([f"Research: {e}" for e in research_errors])
        all_warnings.extend([f"Research: {w}" for w in research_warnings])

    return ValidationResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )


def get_council_metadata(models: List[str]) -> List[Dict[str, Any]]:
    """
    Get metadata for council models.

    Args:
        models: List of model IDs in provider:model format

    Returns:
        List of model metadata dictionaries
    """
    metadata = []

    for model_id in models:
        try:
            info = get_or_create_model_info(model_id)
            metadata.append({
                "id": model_id,
                "provider": info.provider,
                "display_name": info.display_name,
                "cost_tier": info.cost_tier,
                "speed_tier": info.speed_tier,
                "context_window": info.context_window
            })
        except ValueError:
            # For invalid models, include minimal info
            metadata.append({
                "id": model_id,
                "provider": "unknown",
                "display_name": model_id,
                "cost_tier": "unknown",
                "speed_tier": "unknown",
                "context_window": 0
            })

    return metadata
