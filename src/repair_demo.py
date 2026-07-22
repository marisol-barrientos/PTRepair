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
# API RESULT SERIALIZATION
# ============================================================

def create_api_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert internal repair results into JSON-serializable values.

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
        JSON-serializable repair result containing:

        - resolution_strategies
        - results

        In each detailed result, ``pst_xml`` is returned as a UTF-8
        string instead of bytes so it can be serialized as JSON and
        displayed directly in JavaScript.

        Results do not require a general ``status`` field. Outcomes
        are represented through:

        - explicit validator values in ``validation``
        - ``validation.warnings``
        - ``failed_operation``
        - ``error_type``
        - ``error_message``

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

    api_results = create_api_results(
        internal_results
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
        "resolution_strategies": strategies,
        "results": api_results,
    }