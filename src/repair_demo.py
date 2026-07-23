from typing import Any


# ============================================================
# PROJECT IMPORTS
# ============================================================

from src.step_1_generate_resolution_strategies.generate_resolution_strategies_demo import (
    generate_resolution_strategies,
)

from src.step_2_apply_validate_resolution_strategies.apply_validate_resolution_strategies_demo import (
    apply_resolution_strategies,
)


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_original_pst(
    original_pst: bytes,
) -> bytes:
    """Validate the original PST content."""

    if not isinstance(original_pst, bytes):
        raise TypeError(
            "The original PST must be provided as bytes."
        )

    if not original_pst.strip():
        raise ValueError(
            "The original PST is empty."
        )

    return original_pst


def validate_compliance_result(
    compliance_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate the compliance result structure.

    Expected structure::

        {
            "violations": [...],
            "context": [...]
        }
    """

    if not isinstance(compliance_result, dict):
        raise TypeError(
            "The compliance result must be a dictionary."
        )

    required_fields = {
        "violations",
        "context",
    }

    missing_fields = required_fields - set(
        compliance_result
    )

    if missing_fields:
        raise ValueError(
            "The compliance result is missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    violations = compliance_result.get(
        "violations"
    )

    context = compliance_result.get(
        "context"
    )

    if not isinstance(violations, list):
        raise TypeError(
            "The 'violations' field must contain a list."
        )

    if not isinstance(context, list):
        raise TypeError(
            "The 'context' field must contain a list."
        )

    return compliance_result


# ============================================================
# RESOLUTION STRATEGY NORMALIZATION
# ============================================================

def extract_resolution_strategies(
    generated_value: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> list[dict[str, Any]]:
    """
    Extract the strategy list from the generation result.

    Both supported generator return forms are accepted:

    1. A plain list of strategy dictionaries.
    2. The complete schema envelope::

           {"resolution_strategies": [...]}
    """

    if isinstance(generated_value, dict):
        if "resolution_strategies" not in generated_value:
            raise ValueError(
                "The generated strategy object is missing the "
                "'resolution_strategies' field."
            )

        strategies = generated_value.get(
            "resolution_strategies"
        )

    else:
        strategies = generated_value

    if not isinstance(strategies, list):
        raise TypeError(
            "Generated resolution strategies must be a list or "
            "an object containing a 'resolution_strategies' list."
        )

    return strategies


# ============================================================
# STRATEGY AND RESULT COMBINATION
# ============================================================

def create_resolution_strategy_results(
    strategies: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Combine generated strategies with their application results.

    Strategies and results are matched through
    ``resolution_strategy_id``. Result values take precedence for
    application-specific fields such as ``status``, ``pst_xml``,
    validation output, errors, and logs.
    """

    if not isinstance(strategies, list):
        raise TypeError(
            "Strategies must be provided as a list."
        )

    if not isinstance(results, list):
        raise TypeError(
            "Results must be provided as a list."
        )

    strategies_by_id: dict[
        str,
        dict[str, Any],
    ] = {}

    strategy_order: list[str] = []

    for index, strategy in enumerate(strategies):
        if not isinstance(strategy, dict):
            raise TypeError(
                f"Strategy at index {index} must be a dictionary."
            )

        strategy_id = strategy.get(
            "resolution_strategy_id"
        )

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            raise ValueError(
                f"Strategy at index {index} has no valid "
                "'resolution_strategy_id'."
            )

        normalized_strategy_id = strategy_id.strip()

        if normalized_strategy_id in strategies_by_id:
            raise ValueError(
                "Duplicate resolution strategy ID: "
                f"{normalized_strategy_id}"
            )

        strategies_by_id[
            normalized_strategy_id
        ] = strategy

        strategy_order.append(
            normalized_strategy_id
        )

    results_by_id: dict[
        str,
        dict[str, Any],
    ] = {}

    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise TypeError(
                f"Result at index {index} must be a dictionary."
            )

        strategy_id = result.get(
            "resolution_strategy_id"
        )

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            raise ValueError(
                f"Result at index {index} has no valid "
                "'resolution_strategy_id'."
            )

        normalized_strategy_id = strategy_id.strip()

        if normalized_strategy_id not in strategies_by_id:
            raise ValueError(
                "No generated strategy matches result ID: "
                f"{normalized_strategy_id}"
            )

        if normalized_strategy_id in results_by_id:
            raise ValueError(
                "Duplicate application result for strategy ID: "
                f"{normalized_strategy_id}"
            )

        results_by_id[
            normalized_strategy_id
        ] = result

    missing_result_ids = [
        strategy_id
        for strategy_id in strategy_order
        if strategy_id not in results_by_id
    ]

    if missing_result_ids:
        raise ValueError(
            "No application result was returned for strategy IDs: "
            + ", ".join(missing_result_ids)
        )

    combined_strategies: list[
        dict[str, Any]
    ] = []

    for strategy_id in strategy_order:
        strategy = strategies_by_id[
            strategy_id
        ]

        result = results_by_id[
            strategy_id
        ]

        combined_strategies.append(
            {
                **strategy,
                **result,
            }
        )

    return combined_strategies


# ============================================================
# API RESULT SERIALIZATION
# ============================================================

def create_api_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert combined resolution-strategy results into
    JSON-serializable values.

    ``pst_xml`` bytes are decoded to UTF-8 strings. The input result
    dictionaries are not modified.
    """

    if not isinstance(results, list):
        raise TypeError(
            "Results must be provided as a list."
        )

    api_results: list[dict[str, Any]] = []

    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise TypeError(
                f"Result at index {index} must be a dictionary."
            )

        api_result = dict(result)

        pst_xml = api_result.get(
            "pst_xml"
        )

        if isinstance(pst_xml, bytes):
            try:
                api_result["pst_xml"] = pst_xml.decode(
                    "utf-8"
                )

            except UnicodeDecodeError as error:
                raise ValueError(
                    "The generated PST XML for result at index "
                    f"{index} is not valid UTF-8."
                ) from error

        elif pst_xml is not None and not isinstance(
            pst_xml,
            str,
        ):
            raise TypeError(
                "The 'pst_xml' value for result at index "
                f"{index} must be bytes, a string, or None."
            )

        api_results.append(
            api_result
        )

    return api_results


# ============================================================
# RESULT CLASSIFICATION
# ============================================================

def has_result_error(
    result: dict[str, Any],
) -> bool:
    """Return whether a repair result contains an application error."""

    return (
        result.get("status") == "error"
        or result.get("error_message") is not None
    )


def has_validation_warnings(
    result: dict[str, Any],
) -> bool:
    """Return whether a non-error result has validation warnings."""

    if has_result_error(result):
        return False

    if result.get("status") == "warning":
        return True

    validation = result.get(
        "validation",
        {},
    )

    if not isinstance(validation, dict):
        return False

    warnings = validation.get(
        "warnings",
        [],
    )

    return isinstance(warnings, list) and bool(
        warnings
    )


def count_result_outcomes(
    results: list[dict[str, Any]],
) -> dict[str, int]:
    """Count successful, warning, and error strategy results."""

    errors = sum(
        has_result_error(result)
        for result in results
    )

    warnings = sum(
        has_validation_warnings(result)
        for result in results
    )

    successful = len(results) - warnings - errors

    return {
        "successful": successful,
        "warnings": warnings,
        "errors": errors,
    }


# ============================================================
# REPAIR PIPELINE
# ============================================================

def repair(
    original_pst: bytes,
    compliance_result: dict[str, Any],
    api_key: str | None = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """
    Generate, apply, and validate resolution strategies in memory.

    Parameters
    ----------
    original_pst : bytes
        Original XML PST content.

    compliance_result : dict[str, Any]
        Compliance result containing ``violations`` and ``context``.

    api_key : str | None
        Optional OpenRouter API key. When omitted, the generation
        module may use the ``OPENROUTER_API_KEY`` environment variable.

    prompt : str | None
        Optional resolution-generation prompt supplied directly.

    Returns
    -------
    dict[str, Any]
        A JSON-serializable object with the full strategy schema:

        {
            "resolution_strategies": [
                {
                    "requirement_id": "...",
                    "resolution_strategy_id": "...",
                    "change_description": "...",
                    "change_risk": {
                        "value": "...",
                        "reason": "..."
                    },
                    "change_operations": [...],
                    "status": "success | warning | error",
                    "pst_xml": "... | null",
                    "validation": {...},
                    "failed_operation": "... | null",
                    "error_type": "... | null",
                    "error_message": "... | null",
                    "log": "..."
                }
            ]
        }

    Notes
    -----
    This function performs no output-file creation.
    """

    validated_pst = validate_original_pst(
        original_pst
    )

    validated_compliance_result = (
        validate_compliance_result(
            compliance_result
        )
    )

    print("================================================")
    print("STEP 1: GENERATE RESOLUTION STRATEGIES")
    print("================================================")

    generated_value = generate_resolution_strategies(
        original_pst=validated_pst,
        compliance_result=(
            validated_compliance_result
        ),
        api_key=api_key,
        prompt=prompt,
    )

    strategies = extract_resolution_strategies(
        generated_value
    )

    print(
        f"Generated strategies: {len(strategies)}"
    )

    print("\n================================================")
    print("STEP 2: APPLY AND VALIDATE STRATEGIES")
    print("================================================")

    internal_results = apply_resolution_strategies(
        original_pst=validated_pst,
        resolution_strategies=strategies,
    )

    combined_strategies = (
        create_resolution_strategy_results(
            strategies=strategies,
            results=internal_results,
        )
    )

    api_resolution_strategies = create_api_results(
        combined_strategies
    )

    outcome_counts = count_result_outcomes(
        internal_results
    )

    print("\n================================================")
    print("REPAIR COMPLETED")
    print("================================================")
    print(
        f"Generated strategies: {len(strategies)}"
    )
    print(
        f"Successful: {outcome_counts['successful']}"
    )
    print(
        f"Warnings: {outcome_counts['warnings']}"
    )
    print(
        f"Errors: {outcome_counts['errors']}"
    )

    return {
        "resolution_strategies": (
            api_resolution_strategies
        ),
    }
