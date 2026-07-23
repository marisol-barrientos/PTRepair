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
    """
    Validate the original PST content.
    """

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
    Validate the compliance-result structure.
    """

    if not isinstance(compliance_result, dict):
        raise TypeError(
            "The compliance result must be a dictionary."
        )

    try:
        violations = compliance_result["violations"]
        context = compliance_result["context"]

    except KeyError as error:
        raise ValueError(
            "The compliance result is missing required field: "
            f"'{error.args[0]}'."
        ) from error

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
    Return the generated resolution-strategy list.

    Accepted generator return forms:

    1. A plain list of strategy dictionaries.
    2. An object containing ``resolution_strategies``.
    """

    if isinstance(generated_value, dict):
        try:
            generated_value = generated_value[
                "resolution_strategies"
            ]

        except KeyError as error:
            raise ValueError(
                "The generated strategy object is missing "
                "'resolution_strategies'."
            ) from error

    if not isinstance(generated_value, list):
        raise TypeError(
            "Generated resolution strategies must be a list."
        )

    return generated_value


# ============================================================
# STRATEGY AND RESULT COMBINATION
# ============================================================

def combine_strategy_results(
    strategies: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Combine generated strategies with application results.

    The application layer is responsible for validating strategy
    structure and returning exactly one result per strategy.
    """

    results_by_id = {
        result["resolution_strategy_id"]: result
        for result in results
    }

    try:
        return [
            {
                **strategy,
                **results_by_id[
                    strategy["resolution_strategy_id"]
                ],
            }
            for strategy in strategies
        ]

    except KeyError as error:
        raise RuntimeError(
            "Could not match a generated strategy with its "
            f"application result: '{error.args[0]}'."
        ) from error


# ============================================================
# API RESULT SERIALIZATION
# ============================================================

def serialize_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert repaired PST byte values to UTF-8 strings.

    Input dictionaries are not modified.
    """

    serialized_results: list[
        dict[str, Any]
    ] = []

    for result in results:
        serialized_result = dict(
            result
        )

        pst_xml = serialized_result.get(
            "pst_xml"
        )

        if isinstance(pst_xml, bytes):
            serialized_result["pst_xml"] = (
                pst_xml.decode("utf-8")
            )

        serialized_results.append(
            serialized_result
        )

    return serialized_results


# ============================================================
# RESULT CLASSIFICATION
# ============================================================

def count_result_outcomes(
    results: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Count strategy results by their explicit status.
    """

    counts = {
        "success": 0,
        "warning": 0,
        "error": 0,
    }

    for result in results:
        status = result.get(
            "status"
        )

        if status not in counts:
            raise RuntimeError(
                "Application result contains an unsupported "
                f"status: {status!r}."
            )

        counts[status] += 1

    return counts


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
        JSON-serializable repair output:

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
    The application layer owns complete resolution-strategy schema
    validation and operation validation.

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

    combined_results = combine_strategy_results(
        strategies=strategies,
        results=internal_results,
    )

    api_results = serialize_results(
        combined_results
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
        f"Successful: {outcome_counts['success']}"
    )
    print(
        f"Warnings: {outcome_counts['warning']}"
    )
    print(
        f"Errors: {outcome_counts['error']}"
    )

    return {
        "resolution_strategies": api_results,
    }