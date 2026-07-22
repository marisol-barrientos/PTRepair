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
    Validate the compliance result structure.

    Expected structure:

    {
        "violations": [...],
        "context": [...]
    }
    """

    if not isinstance(compliance_result, dict):
        raise TypeError(
            "The compliance result must be a dictionary."
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
# STRATEGY AND RESULT COMBINATION
# ============================================================

def create_resolution_strategy_results(
    strategies: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Combine each generated resolution strategy with its application
    and validation result.

    Strategies and results are matched through
    ``resolution_strategy_id``.
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

        strategy_id = strategy_id.strip()

        if strategy_id in strategies_by_id:
            raise ValueError(
                "Duplicate resolution strategy ID: "
                f"{strategy_id}"
            )

        strategies_by_id[
            strategy_id
        ] = strategy

    combined_strategies: list[
        dict[str, Any]
    ] = []

    seen_result_ids: set[str] = set()

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

        strategy_id = strategy_id.strip()

        strategy = strategies_by_id.get(
            strategy_id
        )

        if strategy is None:
            raise ValueError(
                "No generated strategy matches result ID: "
                f"{strategy_id}"
            )

        if strategy_id in seen_result_ids:
            raise ValueError(
                "Duplicate application result for strategy ID: "
                f"{strategy_id}"
            )

        seen_result_ids.add(
            strategy_id
        )

        combined_strategies.append(
            {
                **strategy,
                **result,
            }
        )

    missing_result_ids = [
        strategy_id
        for strategy_id in strategies_by_id
        if strategy_id not in seen_result_ids
    ]

    if missing_result_ids:
        raise ValueError(
            "No application result was returned for strategy IDs: "
            + ", ".join(missing_result_ids)
        )

    return combined_strategies


# ============================================================
# API RESULT SERIALIZATION
# ============================================================

def create_api_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert combined resolution strategy results into
    JSON-serializable values.

    Results may contain ``pst_xml`` as bytes. Those bytes are decoded
    to UTF-8 strings so the result can be returned directly by a JSON
    endpoint and displayed in JavaScript.

    The input result dictionaries are not modified.
    """

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
    """
    Return whether a repair result contains an application error.
    """

    return result.get(
        "error_message"
    ) is not None


def has_validation_warnings(
    result: dict[str, Any],
) -> bool:
    """
    Return whether a non-error result contains validation warnings.
    """

    if has_result_error(result):
        return False

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
        Compliance result containing:

        {
            "violations": [...],
            "context": [...]
        }

    api_key : str | None
        Optional OpenRouter API key.

        When omitted, the generation module uses the
        OPENROUTER_API_KEY environment variable.

    prompt : str | None
        Optional resolution-generation prompt supplied directly.

        When omitted, the generation module may load its configured
        server-side prompt file.

    Returns
    -------
    dict[str, Any]
        JSON-serializable result containing one top-level field:

        - resolution_strategies

        Each item combines:

        - the generated strategy
        - its change operations
        - the repaired PST
        - explicit validator outcomes
        - warnings
        - error details
        - the processing log

        ``pst_xml`` is returned as a UTF-8 string instead of bytes.

        No general result ``status`` field is required.

    Notes
    -----
    This function does not save generated strategies, repaired PSTs,
    or logs to disk.
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

    strategies = generate_resolution_strategies(
        original_pst=validated_pst,
        compliance_result=(
            validated_compliance_result
        ),
        api_key=api_key,
        prompt=prompt,
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

    errors = sum(
        has_result_error(result)
        for result in internal_results
    )

    warnings = sum(
        has_validation_warnings(result)
        for result in internal_results
    )

    successful = (
        len(internal_results)
        - warnings
        - errors
    )

    print("\n================================================")
    print("REPAIR COMPLETED")
    print("================================================")
    print(
        f"Generated strategies: "
        f"{len(strategies)}"
    )
    print(
        f"Successful: "
        f"{successful}"
    )
    print(
        f"Warnings: "
        f"{warnings}"
    )
    print(
        f"Errors: "
        f"{errors}"
    )

    return {
        "resolution_strategies":
            api_resolution_strategies,
    }