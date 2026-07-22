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
# RESULT SUMMARY
# ============================================================

def create_repair_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create a JSON-serializable repair summary.

    XML bytes and log content remain in the detailed results and are
    not duplicated in the summary.
    """

    entries = []

    for result in results:
        entry = {
            "requirement_id": result.get(
                "requirement_id"
            ),
            "resolution_strategy_id": result.get(
                "resolution_strategy_id"
            ),
            "status": result.get(
                "status"
            ),
            "validation": result.get(
                "validation"
            ),
        }

        if result.get("status") == "error":
            entry["failed_operation"] = result.get(
                "failed_operation"
            )

            entry["error_type"] = result.get(
                "error_type"
            )

            entry["error_message"] = result.get(
                "error_message"
            )

        entries.append(entry)

    return {
        "total": len(results),
        "successful": sum(
            result.get("status") == "success"
            for result in results
        ),
        "warnings": sum(
            result.get("status") == "warning"
            for result in results
        ),
        "errors": sum(
            result.get("status") == "error"
            for result in results
        ),
        "results": entries,
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
    Generate and apply resolution strategies entirely in memory.

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
        In-memory repair result containing:

        - resolution_strategies
        - results
        - summary

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

    results = apply_resolution_strategies(
        original_pst=validated_pst,
        resolution_strategies=strategies,
    )

    summary = create_repair_summary(
        results
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
        f"{summary['successful']}"
    )
    print(
        f"Warnings: "
        f"{summary['warnings']}"
    )
    print(
        f"Errors: "
        f"{summary['errors']}"
    )

    return {
        "resolution_strategies": strategies,
        "results": results,
        "summary": summary,
    }