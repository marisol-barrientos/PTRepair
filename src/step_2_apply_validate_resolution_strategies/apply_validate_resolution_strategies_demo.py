import io
from typing import Any, Callable

from lxml import etree


# ============================================================
# PROJECT IMPORTS
# ============================================================

from src.step_2_apply_validate_resolution_strategies.change_management.change_applier import (
    ChangeApplier,
)

from src.step_2_apply_validate_resolution_strategies.validators.change_operation_validator import (
    ChangeOperationValidator,
)

from src.step_2_apply_validate_resolution_strategies.validators.behavioral_validator import (
    BehavioralValidator,
)

from src.step_2_apply_validate_resolution_strategies.validators.pst_validator import (
    PSTValidator,
)

from src.step_2_apply_validate_resolution_strategies.validators.structural_validator import (
    StructuralValidator,
)

from src.step_2_apply_validate_resolution_strategies.change_operations.operations import (
    add_write,
    add_xor_branch,
    copy_after,
    copy_before,
    delete,
    embed_activity_in_xor,
    embed_post_loop,
    embed_pre_loop,
    insert_after,
    insert_before,
    merge_by_label,
    modify_condition,
    modify_loop_condition,
    modify_read,
    modify_resource,
    modify_timeout,
    modify_write,
    move_after,
    move_before,
    parallelize,
    remove_branch,
    remove_branch_by_condition,
    remove_loop,
    remove_write,
    rename,
    sequentialize_parallel,
    split,
    swap,
)


# ============================================================
# CHANGE OPERATION CONFIGURATION
# ============================================================

OPERATION_MAPPING: dict[str, Callable[..., Any]] = {
    "insert_after": insert_after,
    "insert_before": insert_before,
    "delete": delete,
    "rename": rename,
    "move_after": move_after,
    "move_before": move_before,
    "swap": swap,
    "merge": merge_by_label,
    "split": split,
    "copy_after": copy_after,
    "copy_before": copy_before,
    "modify_condition": modify_condition,
    "modify_resource": modify_resource,
    "modify_write": modify_write,
    "add_write": add_write,
    "remove_write": remove_write,
    "modify_read": modify_read,
    "parallelize": parallelize,
    "sequentialize_parallel": sequentialize_parallel,
    "add_xor_branch": add_xor_branch,
    "remove_branch": remove_branch,
    "remove_branch_by_condition": remove_branch_by_condition,
    "embed_activity_in_xor": embed_activity_in_xor,
    "embed_pre_loop": embed_pre_loop,
    "embed_post_loop": embed_post_loop,
    "remove_loop": remove_loop,
    "modify_loop_condition": modify_loop_condition,
    "modify_timeout": modify_timeout,
}


OPERATION_PARAMETERS: dict[str, tuple[str, ...]] = {
    "insert_after": (
        "target_activity_label",
        "new_activity_label",
    ),
    "insert_before": (
        "target_activity_label",
        "new_activity_label",
    ),
    "delete": (
        "target_activity_label",
    ),
    "rename": (
        "target_activity_label",
        "new_activity_label",
    ),
    "move_after": (
        "source_activity_label",
        "target_activity_label",
    ),
    "move_before": (
        "source_activity_label",
        "target_activity_label",
    ),
    "swap": (
        "first_activity_label",
        "second_activity_label",
    ),
    "merge": (
        "first_activity_label",
        "second_activity_label",
    ),
    "split": (
        "target_activity_label",
    ),
    "copy_after": (
        "source_activity_label",
        "target_activity_label",
    ),
    "copy_before": (
        "source_activity_label",
        "target_activity_label",
    ),
    "parallelize": (
        "first_activity_label",
        "second_activity_label",
    ),
    "sequentialize_parallel": (
        "first_activity_label",
        "second_activity_label",
    ),
    "remove_branch": (
        "target_activity_label",
    ),
    "remove_branch_by_condition": (
        "target_condition",
    ),
    "modify_condition": (
        "target_activity_label",
        "new_condition",
    ),
    "modify_resource": (
        "target_activity_label",
        "new_resource",
    ),
    "modify_write": (
        "target_activity_label",
        "new_statement",
    ),
    "add_write": (
        "target_activity_label",
        "added_statement",
    ),
    "remove_write": (
        "target_activity_label",
        "removed_variable_name",
    ),
    "modify_read": (
        "target_activity_label",
        "old_variable_name",
        "new_variable_name",
    ),
    "remove_loop": (
        "target_activity_label",
    ),
    "modify_loop_condition": (
        "target_activity_label",
        "new_condition",
    ),
    "modify_timeout": (
        "target_activity_label",
        "new_timeout",
    ),
    "add_xor_branch": (
        "existing_branch_condition",
        "new_branch_condition",
        "new_activity_label",
    ),
    "embed_activity_in_xor": (
        "target_activity_label",
        "condition",
        "mode",
    ),
    "embed_pre_loop": (
        "start_activity_label",
        "end_activity_label",
        "condition",
    ),
    "embed_post_loop": (
        "start_activity_label",
        "end_activity_label",
        "condition",
    ),
}


ALLOWED_RISK_VALUES = {
    "very_low",
    "low",
    "medium",
    "high",
    "very_high",
}


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_original_pst(
    original_pst: bytes,
) -> bytes:
    """
    Validate the original PST byte content.
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


def require_non_empty_string(
    value: Any,
    field_path: str,
) -> str:
    """
    Validate and normalize a required non-empty string.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"'{field_path}' must be a non-empty string."
        )

    return value.strip()


def normalize_resolution_strategies(
    resolution_strategies: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> list[dict[str, Any]]:
    """
    Normalize the supported strategy input forms to a plain list.
    """

    if isinstance(resolution_strategies, dict):
        try:
            resolution_strategies = resolution_strategies[
                "resolution_strategies"
            ]

        except KeyError as error:
            raise ValueError(
                "The strategy object is missing "
                "'resolution_strategies'."
            ) from error

    if not isinstance(resolution_strategies, list):
        raise TypeError(
            "Resolution strategies must be a list."
        )

    return resolution_strategies


def validate_change_risk(
    change_risk: Any,
    field_path: str,
) -> None:
    """
    Validate one change-risk object.
    """

    if not isinstance(change_risk, dict):
        raise TypeError(
            f"'{field_path}' must be a dictionary."
        )

    risk_value = require_non_empty_string(
        change_risk.get("value"),
        f"{field_path}.value",
    )

    if risk_value not in ALLOWED_RISK_VALUES:
        raise ValueError(
            f"'{field_path}.value' has unsupported value "
            f"'{risk_value}'."
        )

    require_non_empty_string(
        change_risk.get("reason"),
        f"{field_path}.reason",
    )


def build_operation_arguments(
    operation_name: str,
    parameters: Any,
    field_path: str,
) -> list[Any]:
    """
    Validate operation parameters and return positional arguments.
    """

    if not isinstance(parameters, dict):
        raise TypeError(
            f"'{field_path}' must be a dictionary."
        )

    required_parameters = OPERATION_PARAMETERS[
        operation_name
    ]

    arguments: list[Any] = []

    for parameter_name in required_parameters:
        if parameter_name not in parameters:
            raise ValueError(
                f"'{field_path}' is missing required parameter "
                f"'{parameter_name}'."
            )

        value = parameters[parameter_name]

        if value is None:
            raise ValueError(
                f"'{field_path}.{parameter_name}' must not be null."
            )

        if isinstance(value, str) and not value.strip():
            raise ValueError(
                f"'{field_path}.{parameter_name}' must not be empty."
            )

        arguments.append(value)

    return arguments


def validate_resolution_strategies(
    resolution_strategies: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> list[dict[str, Any]]:
    """
    Validate the complete resolution-strategy schema.

    Operation parameter validation is delegated to
    ``build_operation_arguments`` so parameter rules have one owner.
    """

    strategies = normalize_resolution_strategies(
        resolution_strategies
    )

    seen_strategy_ids: set[str] = set()

    for strategy_index, strategy in enumerate(
        strategies
    ):
        strategy_path = (
            f"resolution_strategies[{strategy_index}]"
        )

        if not isinstance(strategy, dict):
            raise TypeError(
                f"'{strategy_path}' must be a dictionary."
            )

        requirement_id = require_non_empty_string(
            strategy.get("requirement_id"),
            f"{strategy_path}.requirement_id",
        )

        strategy_id = require_non_empty_string(
            strategy.get("resolution_strategy_id"),
            f"{strategy_path}.resolution_strategy_id",
        )

        if strategy_id in seen_strategy_ids:
            raise ValueError(
                "Duplicate resolution strategy ID: "
                f"'{strategy_id}'."
            )

        seen_strategy_ids.add(strategy_id)

        require_non_empty_string(
            strategy.get("change_description"),
            f"{strategy_path}.change_description",
        )

        validate_change_risk(
            strategy.get("change_risk"),
            f"{strategy_path}.change_risk",
        )

        operations = strategy.get(
            "change_operations"
        )

        if not isinstance(operations, list):
            raise TypeError(
                f"'{strategy_path}.change_operations' "
                "must be a list."
            )

        if not operations:
            raise ValueError(
                f"'{strategy_path}.change_operations' "
                "must contain at least one operation."
            )

        for operation_index, operation_data in enumerate(
            operations
        ):
            operation_path = (
                f"{strategy_path}.change_operations"
                f"[{operation_index}]"
            )

            if not isinstance(operation_data, dict):
                raise TypeError(
                    f"'{operation_path}' must be a dictionary."
                )

            operation_name = require_non_empty_string(
                operation_data.get("operation"),
                f"{operation_path}.operation",
            )

            if operation_name not in OPERATION_MAPPING:
                raise ValueError(
                    f"Unsupported operation '{operation_name}' "
                    f"at '{operation_path}'."
                )

            build_operation_arguments(
                operation_name=operation_name,
                parameters=operation_data.get("parameters"),
                field_path=f"{operation_path}.parameters",
            )

    return strategies


# ============================================================
# XML HANDLING
# ============================================================

def load_process_from_bytes(
    xml_bytes: bytes,
) -> tuple[
    etree._ElementTree,
    etree._Element,
]:
    """
    Parse one fresh in-memory PST tree.
    """

    try:
        tree = etree.parse(
            io.BytesIO(xml_bytes),
            etree.XMLParser(
                remove_blank_text=True,
                recover=False,
            ),
        )

    except etree.XMLSyntaxError as error:
        raise ValueError(
            f"The original PST is not valid XML: {error}"
        ) from error

    root = tree.getroot()

    if root is None:
        raise ValueError(
            "The original PST has no XML root element."
        )

    return tree, root


def serialize_pst(
    tree: etree._ElementTree,
) -> bytes:
    """
    Serialize an updated PST to XML bytes.
    """

    return etree.tostring(
        tree,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


# ============================================================
# UPDATED PST VALIDATION
# ============================================================

def run_validator(
    validator_name: str,
    validator: Any,
    current_root: Any,
) -> tuple[str, list[str]]:
    """
    Run one validator and normalize its output.

    Validators may either:
    - return no warnings,
    - return an iterable of warnings,
    - raise an exception.
    """

    try:
        returned_warnings = (
            validator.validate(current_root)
            or []
        )

    except Exception as error:
        return (
            "warning",
            [f"{validator_name}: {error}"],
        )

    if isinstance(returned_warnings, str):
        returned_warnings = [
            returned_warnings
        ]

    warnings = [
        f"{validator_name}: {warning}"
        for warning in returned_warnings
    ]

    return (
        "warning" if warnings else "success",
        warnings,
    )


def validate_updated_pst(
    current_root: Any,
    behavioral_validator: BehavioralValidator,
    pst_validator: PSTValidator,
    structural_validator: StructuralValidator,
) -> dict[str, Any]:
    """
    Run all PST validators and return normalized outcomes.
    """

    validation: dict[str, Any] = {
        "warnings": [],
    }

    validators = (
        (
            "behavioral_validator",
            "BehavioralValidator",
            behavioral_validator,
        ),
        (
            "pst_validator",
            "PSTValidator",
            pst_validator,
        ),
        (
            "structural_validator",
            "StructuralValidator",
            structural_validator,
        ),
    )

    for result_key, display_name, validator in validators:
        status, warnings = run_validator(
            validator_name=display_name,
            validator=validator,
            current_root=current_root,
        )

        validation[result_key] = status
        validation["warnings"].extend(
            warnings
        )

    return validation


# ============================================================
# RESULT CONSTRUCTION
# ============================================================

def create_result(
    strategy: dict[str, Any],
) -> dict[str, Any]:
    """
    Create the initial result object for one strategy.
    """

    return {
        "requirement_id": strategy["requirement_id"],
        "resolution_strategy_id": (
            strategy["resolution_strategy_id"]
        ),
        "change_description": (
            strategy["change_description"]
        ),
        "change_risk": strategy["change_risk"],
        "change_operations": (
            strategy["change_operations"]
        ),
        "status": "error",
        "pst_xml": None,
        "validation": {
            "behavioral_validator": "not_executed",
            "pst_validator": "not_executed",
            "structural_validator": "not_executed",
            "warnings": [],
        },
        "failed_operation": None,
        "error_type": None,
        "error_message": None,
        "log": "",
    }


def set_result_error(
    result: dict[str, Any],
    error: Exception,
    failed_operation: str | None = None,
) -> None:
    """
    Store one application error in a strategy result.
    """

    result["status"] = "error"
    result["failed_operation"] = failed_operation
    result["error_type"] = type(error).__name__
    result["error_message"] = str(error)


def build_result_log(
    result: dict[str, Any],
) -> str:
    """
    Build an in-memory text log for one strategy.
    """

    change_risk = result.get(
        "change_risk",
        {},
    )

    lines = [
        f"requirement_id: {result['requirement_id']}",
        (
            "resolution_strategy_id: "
            f"{result['resolution_strategy_id']}"
        ),
        (
            "change_description: "
            f"{result.get('change_description', '')}"
        ),
        (
            "change_risk: "
            f"{change_risk.get('value', '')}"
        ),
        (
            "change_risk_reason: "
            f"{change_risk.get('reason', '')}"
        ),
        f"result: {result['status']}",
    ]

    if result["status"] == "error":
        if result.get("failed_operation"):
            lines.append(
                "failed_operation: "
                f"{result['failed_operation']}"
            )

        if result.get("error_type"):
            lines.append(
                f"error_type: {result['error_type']}"
            )

        lines.append(
            "error: "
            f"{result.get('error_message') or 'Unknown error'}"
        )

    elif result["status"] == "warning":
        lines.append("warnings:")

        for warning in result["validation"]["warnings"]:
            lines.append(
                f"- {warning}"
            )

    return "\n".join(lines) + "\n"


# ============================================================
# APPLY ONE STRATEGY
# ============================================================

def apply_one_strategy(
    original_pst: bytes,
    strategy: dict[str, Any],
    applier: ChangeApplier,
    operation_validator: ChangeOperationValidator,
    behavioral_validator: BehavioralValidator,
    pst_validator: PSTValidator,
    structural_validator: StructuralValidator,
) -> dict[str, Any]:
    """
    Apply one strategy to a fresh copy of the original PST.

    Application failures are returned in the result so remaining
    strategies continue to run.
    """

    result = create_result(
        strategy
    )

    try:
        tree, current_root = load_process_from_bytes(
            original_pst
        )

        for operation_data in strategy[
            "change_operations"
        ]:
            operation_name = operation_data[
                "operation"
            ]

            try:
                operation_function = OPERATION_MAPPING[
                    operation_name
                ]

                operation_validator.validate(
                    operation_function
                )

                arguments = build_operation_arguments(
                    operation_name=operation_name,
                    parameters=operation_data[
                        "parameters"
                    ],
                    field_path=(
                        f"operation '{operation_name}' parameters"
                    ),
                )

                current_root, _ = applier.apply(
                    current_root,
                    operation_function,
                    *arguments,
                )

            except Exception as error:
                set_result_error(
                    result=result,
                    error=error,
                    failed_operation=operation_name,
                )

                break

        if result["status"] != "error" or (
            result["error_message"] is None
        ):
            tree._setroot(
                current_root
            )

            validation = validate_updated_pst(
                current_root=current_root,
                behavioral_validator=behavioral_validator,
                pst_validator=pst_validator,
                structural_validator=structural_validator,
            )

            result["pst_xml"] = serialize_pst(
                tree
            )

            result["validation"] = validation
            result["status"] = (
                "warning"
                if validation["warnings"]
                else "success"
            )

    except Exception as error:
        if result["error_message"] is None:
            set_result_error(
                result=result,
                error=error,
            )

    result["log"] = build_result_log(
        result
    )

    return result


# ============================================================
# PUBLIC IN-MEMORY FUNCTION
# ============================================================

def apply_resolution_strategies(
    original_pst: bytes,
    resolution_strategies: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> list[dict[str, Any]]:
    """
    Apply and validate all resolution strategies in memory.

    Every strategy starts from a fresh copy of the original PST.
    """

    validated_pst = validate_original_pst(
        original_pst
    )

    strategies = validate_resolution_strategies(
        resolution_strategies
    )

    applier = ChangeApplier()
    operation_validator = ChangeOperationValidator()
    behavioral_validator = BehavioralValidator()
    pst_validator = PSTValidator()
    structural_validator = StructuralValidator()

    results: list[dict[str, Any]] = []
    total = len(strategies)

    for index, strategy in enumerate(
        strategies,
        start=1,
    ):
        result = apply_one_strategy(
            original_pst=validated_pst,
            strategy=strategy,
            applier=applier,
            operation_validator=operation_validator,
            behavioral_validator=behavioral_validator,
            pst_validator=pst_validator,
            structural_validator=structural_validator,
        )

        results.append(result)

        print(
            f"[{index}/{total}] "
            f"Outcome: {result['status']}"
        )

    return results


# ============================================================
# OPTIONAL XML-ONLY HELPER
# ============================================================

def get_pst_xml_list(
        original_pst: bytes,
        resolution_strategies: (
                list[dict[str, Any]]
                | dict[str, Any]
        ),
) -> list[bytes]:
    """
    Return only successfully generated PST XML values.

    Results with validation warnings are included.
    Failed strategy results are excluded.
    """

    results = apply_resolution_strategies(
        original_pst=original_pst,
        resolution_strategies=(
            resolution_strategies
        ),
    )

    return [
        result["pst_xml"]
        for result in results
        if result.get("pst_xml") is not None
    ]
