import io
from typing import Any

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
# CHANGE OPERATION MAPPING
# ============================================================

OPERATION_MAPPING = {
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


# ============================================================
# OPERATION PARAMETER ORDER
# ============================================================

OPERATION_PARAMETERS = {
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


def validate_resolution_strategies(
    resolution_strategies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Validate generated resolution strategies supplied in memory.
    """

    if not isinstance(
        resolution_strategies,
        list,
    ):
        raise TypeError(
            "Resolution strategies must be provided as a list."
        )

    seen_strategy_ids: set[str] = set()

    for index, strategy in enumerate(
        resolution_strategies
    ):
        if not isinstance(strategy, dict):
            raise TypeError(
                f"Strategy at index {index} must be "
                "a dictionary."
            )

        requirement_id = strategy.get(
            "requirement_id"
        )

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                f"Strategy at index {index} has no valid "
                "'requirement_id'."
            )

        strategy_id = strategy.get(
            "resolution_strategy_id"
        )

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            raise ValueError(
                f"Strategy for {requirement_id} has no valid "
                "'resolution_strategy_id'."
            )

        if strategy_id in seen_strategy_ids:
            raise ValueError(
                f"Duplicate resolution strategy ID: "
                f"{strategy_id}"
            )

        seen_strategy_ids.add(
            strategy_id
        )

        change_operations = strategy.get(
            "change_operations"
        )

        if not isinstance(
            change_operations,
            list,
        ):
            raise TypeError(
                f"'change_operations' for {strategy_id} "
                "must be a list."
            )

    return resolution_strategies


# ============================================================
# IN-MEMORY XML HANDLING
# ============================================================

def load_process_from_bytes(
    xml_bytes: bytes,
) -> tuple[
    etree._ElementTree,
    etree._Element,
]:
    """
    Parse an XML process model entirely in memory.

    A new tree is created each time this function is called, ensuring
    that every strategy starts from the unchanged original PST.
    """

    try:
        parser = etree.XMLParser(
            remove_blank_text=True,
            recover=False,
        )

        tree = etree.parse(
            io.BytesIO(xml_bytes),
            parser,
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
# OPERATION ARGUMENTS
# ============================================================

def build_operation_arguments(
    operation_name: str,
    parameters: dict[str, Any],
) -> list[Any]:
    """
    Build positional arguments required by a change operation.
    """

    required_parameters = OPERATION_PARAMETERS.get(
        operation_name
    )

    if required_parameters is None:
        raise ValueError(
            f"Argument mapping is missing for operation: "
            f"{operation_name}"
        )

    missing_parameters = [
        parameter_name
        for parameter_name in required_parameters
        if parameter_name not in parameters
    ]

    if missing_parameters:
        raise ValueError(
            f"Operation '{operation_name}' is missing "
            f"required parameters: "
            f"{', '.join(missing_parameters)}"
        )

    return [
        parameters[parameter_name]
        for parameter_name in required_parameters
    ]


# ============================================================
# VALIDATION
# ============================================================

def validate_updated_pst(
    current_root: Any,
    behavioral_validator: BehavioralValidator,
    pst_validator: PSTValidator,
    structural_validator: StructuralValidator,
) -> dict[str, Any]:
    """
    Validate an updated PST and return each validator outcome.
    """

    validation: dict[str, Any] = {
        "behavioral_validator": "success",
        "pst_validator": "success",
        "structural_validator": "success",
        "warnings": [],
    }

    try:
        behavioral_validator.validate(
            current_root
        )

    except Exception as error:
        validation["behavioral_validator"] = "warning"
        validation["warnings"].append(
            f"BehavioralValidator: {error}"
        )

    try:
        pst_validator.validate(
            current_root
        )

    except Exception as error:
        validation["pst_validator"] = "warning"
        validation["warnings"].append(
            f"PSTValidator: {error}"
        )

    try:
        structural_warnings = (
            structural_validator.validate(
                current_root
            )
        )

        if structural_warnings:
            validation["structural_validator"] = "warning"

            for warning in structural_warnings:
                validation["warnings"].append(
                    f"StructuralValidator: {warning}"
                )

    except Exception as error:
        validation["structural_validator"] = "warning"
        validation["warnings"].append(
            f"StructuralValidator: {error}"
        )

    return validation

# ============================================================
# LOG CONSTRUCTION
# ============================================================

def build_result_log(
    result: dict[str, Any],
) -> str:
    """
    Build a simple in-memory log for one strategy.
    """

    requirement_id = result[
        "requirement_id"
    ]

    strategy_id = result[
        "resolution_strategy_id"
    ]

    validation = result.get(
        "validation",
        {},
    )

    has_error = result.get(
        "error_message"
    ) is not None

    has_warnings = bool(
        validation.get(
            "warnings",
            [],
        )
    )

    lines = [
        f"requirement_id: {requirement_id}",
        f"resolution_strategy_id: {strategy_id}",
    ]

    if has_error:
        lines.append(
            "result: error"
        )

        failed_operation = result.get(
            "failed_operation"
        )

        error_type = result.get(
            "error_type"
        )

        error_message = result.get(
            "error_message"
        )

        if failed_operation:
            lines.append(
                f"failed_operation: {failed_operation}"
            )

        if error_type:
            lines.append(
                f"error_type: {error_type}"
            )

        lines.append(
            f"error: {error_message or 'Unknown error'}"
        )

    elif has_warnings:
        lines.append(
            "result: applied_with_validation_warnings"
        )

        lines.append("warnings:")

        for warning in validation.get(
            "warnings",
            [],
        ):
            lines.append(
                f"- {warning}"
            )

    else:
        lines.append(
            "result: applied_successfully"
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
    Apply one strategy to a fresh in-memory copy of the original PST.

    Application errors are returned in the result and do not stop
    the processing of remaining strategies.
    """

    requirement_id = strategy[
        "requirement_id"
    ]

    strategy_id = strategy[
        "resolution_strategy_id"
    ]

    result: dict[str, Any] = {
        "requirement_id": requirement_id,
        "resolution_strategy_id": strategy_id,
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

    try:
        tree, current_root = (
            load_process_from_bytes(
                original_pst
            )
        )

        for operation_index, operation_data in enumerate(
            strategy["change_operations"],
            start=1,
        ):
            operation_name = None

            try:
                if not isinstance(
                    operation_data,
                    dict,
                ):
                    raise TypeError(
                        f"Operation {operation_index} "
                        "must be a dictionary."
                    )

                operation_name = operation_data.get(
                    "operation"
                )

                parameters = operation_data.get(
                    "parameters"
                )

                if (
                    not isinstance(operation_name, str)
                    or not operation_name.strip()
                ):
                    raise ValueError(
                        f"Operation {operation_index} has "
                        "no valid 'operation' name."
                    )

                if not isinstance(
                    parameters,
                    dict,
                ):
                    raise TypeError(
                        f"Parameters for operation "
                        f"'{operation_name}' must be "
                        "a dictionary."
                    )

                operation_function = (
                    OPERATION_MAPPING.get(
                        operation_name
                    )
                )

                if operation_function is None:
                    raise ValueError(
                        f"Unsupported operation: "
                        f"{operation_name}"
                    )

                operation_validator.validate(
                    operation_function
                )

                arguments = (
                    build_operation_arguments(
                        operation_name=operation_name,
                        parameters=parameters,
                    )
                )

                current_root, _ = applier.apply(
                    current_root,
                    operation_function,
                    *arguments,
                )

            except Exception as error:
                result["failed_operation"] = (
                    operation_name
                )

                result["error_type"] = (
                    type(error).__name__
                )

                result["error_message"] = str(
                    error
                )

                raise

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

        has_warnings = any(
            validator_status == "warning"
            for validator_status in (
                validation["behavioral_validator"],
                validation["pst_validator"],
                validation["structural_validator"],
            )
        )

        result["status"] = (
            "warning"
            if has_warnings
            else "success"
        )

    except Exception as error:
        if result["error_type"] is None:
            result["error_type"] = (
                type(error).__name__
            )

        if result["error_message"] is None:
            result["error_message"] = str(
                error
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
    resolution_strategies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Apply all resolution strategies entirely in memory.

    Each strategy starts from a fresh copy of the original PST.

    Parameters
    ----------
    original_pst : bytes
        Original XML PST content.

    resolution_strategies : list[dict[str, Any]]
        Strategies returned directly by
        generate_resolution_strategies().

    Returns
    -------
    list[dict[str, Any]]
        One result per strategy.

        Successful and warning results contain ``pst_xml`` bytes.
        Every result contains an in-memory ``log`` string.

    Notes
    -----
    This function performs no output file creation.
    """

    validated_pst = validate_original_pst(
        original_pst
    )

    validated_strategies = (
        validate_resolution_strategies(
            resolution_strategies
        )
    )

    applier = ChangeApplier()

    operation_validator = (
        ChangeOperationValidator()
    )

    behavioral_validator = (
        BehavioralValidator()
    )

    pst_validator = PSTValidator()

    structural_validator = (
        StructuralValidator()
    )

    results: list[
        dict[str, Any]
    ] = []

    total = len(
        validated_strategies
    )

    for index, strategy in enumerate(
        validated_strategies,
        start=1,
    ):
        requirement_id = strategy[
            "requirement_id"
        ]

        strategy_id = strategy[
            "resolution_strategy_id"
        ]

        if result.get("error_message") is not None:
            outcome = "error"

        elif result.get(
                "validation",
                {},
        ).get("warnings"):
            outcome = "warning"

        else:
            outcome = "success"

        print(
            f"[{index}/{total}] "
            f"Outcome: {outcome}"
        )

        result = apply_one_strategy(
            original_pst=validated_pst,
            strategy=strategy,
            applier=applier,
            operation_validator=operation_validator,
            behavioral_validator=behavioral_validator,
            pst_validator=pst_validator,
            structural_validator=structural_validator,
        )

        results.append(
            result
        )

        print(
            f"[{index}/{total}] "
            f"Status: {result['status']}"
        )

    return results


# ============================================================
# OPTIONAL XML-ONLY HELPER
# ============================================================

def get_pst_xml_list(
    original_pst: bytes,
    resolution_strategies: list[dict[str, Any]],
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

