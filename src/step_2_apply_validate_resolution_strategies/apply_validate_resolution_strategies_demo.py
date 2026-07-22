import json
import sys
import time
from pathlib import Path
from typing import Any, Union


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_PATH = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_PATH / "src"

STEP2_DIR = (
    SRC_DIR
    / "step_2_apply_validate_resolution_strategies"
)

for path in (SRC_DIR, STEP2_DIR):
    path_string = str(path)

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ============================================================
# PROJECT IMPORTS
# ============================================================

from utils.process_io import load_process

from change_management.change_applier import ChangeApplier

from validators.change_operation_validator import (
    ChangeOperationValidator,
)

from validators.behavioral_validator import BehavioralValidator
from validators.pst_validator import PSTValidator
from validators.structural_validator import StructuralValidator

from change_operations.operations import (
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


PathLike = Union[str, Path]


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

# Each tuple defines the order in which parameters are passed
# to ChangeApplier.apply(...).

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
# FILE LOADING
# ============================================================

def load_json(path: PathLike) -> Any:
    """
    Load and parse a non-empty JSON file.
    """

    json_path = Path(path).expanduser().resolve()

    if not json_path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {json_path}"
        )

    if not json_path.is_file():
        raise ValueError(
            f"Expected a JSON file, received: {json_path}"
        )

    raw_content = json_path.read_text(encoding="utf-8")

    if not raw_content.strip():
        raise ValueError(
            f"JSON file is empty: {json_path}"
        )

    try:
        return json.loads(raw_content)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {json_path}. "
            f"Line {error.lineno}, column {error.colno}: "
            f"{error.msg}"
        ) from error


def load_resolution_strategies(
    path: PathLike,
) -> list[dict[str, Any]]:
    """
    Load resolution strategies using the new flat schema.

    Expected structure:

    {
        "resolution_strategies": [
            {
                "requirement_id": "R2",
                "resolution_strategy_id": "R2_RS1",
                "change_description": "...",
                "change_risk": {...},
                "change_operations": [...]
            }
        ]
    }
    """

    resolution_data = load_json(path)

    if not isinstance(resolution_data, dict):
        raise TypeError(
            "The generated strategies file must contain "
            "a JSON object."
        )

    resolution_strategies = resolution_data.get(
        "resolution_strategies"
    )

    if not isinstance(resolution_strategies, list):
        raise TypeError(
            "The 'resolution_strategies' field must "
            "contain a JSON array."
        )

    seen_requirements: set[str] = set()

    for index, strategy in enumerate(resolution_strategies):
        if not isinstance(strategy, dict):
            raise TypeError(
                f"Strategy at index {index} must be "
                "a JSON object."
            )

        requirement_id = strategy.get("requirement_id")

        if not isinstance(requirement_id, str) or not requirement_id:
            raise ValueError(
                f"Strategy at index {index} has no valid "
                "'requirement_id'."
            )

        strategy_id = strategy.get("resolution_strategy_id")

        if not isinstance(strategy_id, str) or not strategy_id:
            raise ValueError(
                f"Strategy for {requirement_id} has no valid "
                "'resolution_strategy_id'."
            )

        change_operations = strategy.get("change_operations")

        if not isinstance(change_operations, list):
            raise TypeError(
                f"'change_operations' for {requirement_id} "
                "must be a JSON array."
            )

        # The requested output is one PST per requirement.
        # Multiple strategies for the same requirement would otherwise
        # create more than one PST for that requirement.
        if requirement_id in seen_requirements:
            raise ValueError(
                f"More than one strategy was provided for "
                f"requirement {requirement_id}. "
                "Exactly one strategy per requirement is expected."
            )

        seen_requirements.add(requirement_id)

    return resolution_strategies


# ============================================================
# ARGUMENT CONSTRUCTION
# ============================================================

def build_operation_arguments(
    operation_name: str,
    parameters: dict[str, Any],
) -> list[Any]:
    """
    Convert an operation's parameter dictionary into the positional
    argument list expected by its implementation.
    """

    if operation_name not in OPERATION_PARAMETERS:
        raise ValueError(
            f"Argument mapping is missing for operation: "
            f"{operation_name}"
        )

    required_parameters = OPERATION_PARAMETERS[operation_name]
    missing_parameters = [
        parameter_name
        for parameter_name in required_parameters
        if parameter_name not in parameters
    ]

    if missing_parameters:
        missing_text = ", ".join(missing_parameters)

        raise ValueError(
            f"Operation '{operation_name}' is missing required "
            f"parameters: {missing_text}"
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
    Validate an updated PST.

    Validator failures are recorded as warnings and do not discard
    the resulting PST.
    """

    validation = {
        "status": "success",
        "behavioral_validator": "success",
        "pst_validator": "success",
        "structural_validator": "success",
        "warnings": [],
    }

    try:
        behavioral_validator.validate(current_root)

    except Exception as error:
        validation["status"] = "warning"
        validation["behavioral_validator"] = "warning"
        validation["warnings"].append(
            f"BehavioralValidator: {error}"
        )

    try:
        pst_validator.validate(current_root)

    except Exception as error:
        validation["status"] = "warning"
        validation["pst_validator"] = "warning"
        validation["warnings"].append(
            f"PSTValidator: {error}"
        )

    try:
        structural_warnings = structural_validator.validate(
            current_root
        )

        if structural_warnings:
            validation["status"] = "warning"
            validation["structural_validator"] = "warning"

            for warning in structural_warnings:
                validation["warnings"].append(
                    f"StructuralValidator: {warning}"
                )

    except Exception as error:
        validation["status"] = "warning"
        validation["structural_validator"] = "warning"
        validation["warnings"].append(
            f"StructuralValidator: {error}"
        )

    return validation


# ============================================================
# APPLY ONE STRATEGY
# ============================================================

def apply_one_strategy(
    original_pst: PathLike,
    strategy: dict[str, Any],
    applier: ChangeApplier,
    pattern_validator: ChangeOperationValidator,
    behavioral_validator: BehavioralValidator,
    pst_validator: PSTValidator,
    structural_validator: StructuralValidator,
) -> dict[str, Any]:
    """
    Apply one requirement's resolution strategy to a fresh copy of
    the original PST.

    The original PST is reloaded for every requirement. Therefore,
    changes for one requirement do not affect another requirement's
    output PST.
    """

    requirement_id = strategy["requirement_id"]
    strategy_id = strategy["resolution_strategy_id"]

    # Reload the original PST for this requirement.
    tree, root = load_process(str(original_pst))
    current_root = root

    operation_logs: list[str] = []
    applied_operations: list[str] = []

    started_at = time.time()

    for operation_index, operation_data in enumerate(
        strategy["change_operations"],
        start=1,
    ):
        if not isinstance(operation_data, dict):
            raise TypeError(
                f"Operation {operation_index} for {requirement_id} "
                "must be a JSON object."
            )

        operation_name = operation_data.get("operation")
        parameters = operation_data.get("parameters")

        if not isinstance(operation_name, str):
            raise ValueError(
                f"Operation {operation_index} for {requirement_id} "
                "has no valid 'operation' name."
            )

        if not isinstance(parameters, dict):
            raise TypeError(
                f"Parameters for operation '{operation_name}' "
                f"in {requirement_id} must be a JSON object."
            )

        if operation_name not in OPERATION_MAPPING:
            raise ValueError(
                f"Unsupported operation '{operation_name}' "
                f"for requirement {requirement_id}."
            )

        operation_function = OPERATION_MAPPING[operation_name]

        # Validate the operation implementation.
        pattern_validator.validate(operation_function)

        arguments = build_operation_arguments(
            operation_name=operation_name,
            parameters=parameters,
        )

        try:
            current_root, operation_log = applier.apply(
                current_root,
                operation_function,
                *arguments,
            )

        except Exception as error:
            raise RuntimeError(
                f"Failed to apply operation '{operation_name}' "
                f"for requirement {requirement_id}: {error}"
            ) from error

        applied_operations.append(operation_name)
        operation_logs.append(str(operation_log))

    # Attach the new root to the original ElementTree.
    tree._setroot(current_root)

    validation = validate_updated_pst(
        current_root=current_root,
        behavioral_validator=behavioral_validator,
        pst_validator=pst_validator,
        structural_validator=structural_validator,
    )

    execution_time_ms = round(
        (time.time() - started_at) * 1000,
        2,
    )

    return {
        "requirement_id": requirement_id,
        "resolution_strategy_id": strategy_id,
        "pst": tree,
        "root": current_root,
        "applied_operations": applied_operations,
        "operation_logs": operation_logs,
        "validation": validation,
        "execution_time_ms": execution_time_ms,
    }


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def apply_resolution_strategies(
    original_pst: PathLike,
    generated_strategies_file: PathLike,
) -> list[dict[str, Any]]:
    """
    Apply generated resolution strategies to an original PST.

    Parameters
    ----------
    original_pst : str | Path
        Path to the original XML PST.

    generated_strategies_file : str | Path
        Path to the generated resolution strategies JSON file.

    Returns
    -------
    list[dict]
        One result per violated requirement.

        Each result contains:
        - requirement_id
        - resolution_strategy_id
        - pst: updated ElementTree
        - root: updated PST root
        - applied_operations
        - operation_logs
        - validation
        - execution_time_ms

    Notes
    -----
    Each requirement starts from the original PST.

    For example, the PST produced for R4 does not include the changes
    made for R2.
    """

    original_pst_path = Path(original_pst).expanduser().resolve()
    strategies_path = (
        Path(generated_strategies_file)
        .expanduser()
        .resolve()
    )

    if not original_pst_path.exists():
        raise FileNotFoundError(
            f"Original PST not found: {original_pst_path}"
        )

    if not original_pst_path.is_file():
        raise ValueError(
            f"Original PST is not a file: {original_pst_path}"
        )

    resolution_strategies = load_resolution_strategies(
        strategies_path
    )

    applier = ChangeApplier()
    pattern_validator = ChangeOperationValidator()
    behavioral_validator = BehavioralValidator()
    pst_validator = PSTValidator()
    structural_validator = StructuralValidator()

    generated_psts: list[dict[str, Any]] = []

    for index, strategy in enumerate(
        resolution_strategies,
        start=1,
    ):
        requirement_id = strategy["requirement_id"]
        strategy_id = strategy["resolution_strategy_id"]

        print(
            f"[{index}/{len(resolution_strategies)}] "
            f"Applying {strategy_id} for {requirement_id}..."
        )

        result = apply_one_strategy(
            original_pst=original_pst_path,
            strategy=strategy,
            applier=applier,
            pattern_validator=pattern_validator,
            behavioral_validator=behavioral_validator,
            pst_validator=pst_validator,
            structural_validator=structural_validator,
        )

        generated_psts.append(result)

        print(
            f"[{index}/{len(resolution_strategies)}] "
            f"Created PST for {requirement_id} "
            f"with validation status "
            f"'{result['validation']['status']}'."
        )

    return generated_psts


# ============================================================
# OPTIONAL HELPER: RETURN ONLY PST OBJECTS
# ============================================================

def get_pst_list(
    original_pst: PathLike,
    generated_strategies_file: PathLike,
) -> list[Any]:
    """
    Apply all strategies and return only the updated ElementTree
    objects.

    The position of each PST follows the order of strategies in the
    generated strategies file.
    """

    results = apply_resolution_strategies(
        original_pst=original_pst,
        generated_strategies_file=generated_strategies_file,
    )

    return [
        result["pst"]
        for result in results
    ]

def save_generated_psts(
    results: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for result in results:
        requirement_id = result["requirement_id"]
        strategy_id = result["resolution_strategy_id"]
        tree = result["pst"]

        output_file = (
            output_dir
            / f"{requirement_id}_{strategy_id}.xml"
        )

        tree.write(
            str(output_file),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

        print(f"Saved PST: {output_file}")


# ============================================================
# OPTIONAL COMMAND-LINE EXECUTION
# ============================================================

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Apply generated resolution strategies to an original PST."
        )
    )

    parser.add_argument(
        "original_pst",
        type=Path,
        help="Path to the original XML PST.",
    )

    parser.add_argument(
        "generated_strategies",
        type=Path,
        help="Path to the generated strategies JSON file.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("generated_psts"),
        help="Directory where generated PST XML files are saved.",
    )

    args = parser.parse_args()

    results = apply_resolution_strategies(
        original_pst=args.original_pst,
        generated_strategies_file=args.generated_strategies,
    )

    save_generated_psts(
        results=results,
        output_dir=args.output_dir,
    )

    print("\nGenerated PSTs:")

    for result in results:
        print(
            f"- Requirement: {result['requirement_id']}, "
            f"strategy: {result['resolution_strategy_id']}, "
            f"validation: {result['validation']['status']}"
        )

    print(f"\nTotal PSTs generated: {len(results)}")

if __name__ == "__main__":
    main()
