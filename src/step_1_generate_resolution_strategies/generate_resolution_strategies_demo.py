import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


# ==========================================================
# Configuration
# ==========================================================

SCENARIO_NAME = "06_BPMQ"
MODEL = "openai/gpt-5.5"
REQUEST_TIMEOUT_SECONDS = 300


# ==========================================================
# Project paths and imports
# ==========================================================

# This file is expected to be located at:
#
# PTRepair/
# └── src/
#     └── step_1_generate_resolution_strategies/
#         └── generate_resolution_strategies_demo.py
#
# parents[2] therefore resolves to the PTRepair project root.
BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# IMPORTANT:
# Change this import only if simplify_ast.py is located in another package.
#
# Example location:
# src/step_0_preprocessing/simplify_ast.py
#
# In that case, this import is correct:
from step_0_preprocessing.simplify_pst_demo import simplify_pst


# ==========================================================
# File loading utilities
# ==========================================================

def load_json(path: Path) -> Any:
    """
    Load a JSON file with clear validation errors.

    Parameters
    ----------
    path : Path
        Path to the JSON file.

    Returns
    -------
    Any
        Parsed JSON content.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Expected a JSON file, received: {path}"
        )

    raw_content = path.read_text(encoding="utf-8")

    if not raw_content.strip():
        raise ValueError(
            f"JSON file is empty: {path}"
        )

    try:
        return json.loads(raw_content)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {path}\n"
            f"Line: {error.lineno}\n"
            f"Column: {error.colno}\n"
            f"Reason: {error.msg}"
        ) from error


def load_text(path: Path) -> str:
    """
    Load a non-empty text file.

    Parameters
    ----------
    path : Path
        Path to the text file.

    Returns
    -------
    str
        File content.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Text file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Expected a text file, received: {path}"
        )

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(
            f"Text file is empty: {path}"
        )

    return content


# ==========================================================
# Compliance result loading
# ==========================================================

def load_compliance_result(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load violations and compliant requirements.

    Expected input structure:

    {
        "violations": [
            {
                "requirement_id": "R2",
                "requirement": "...",
                "assurance": 90,
                "evidence": [...]
            }
        ],
        "context": [
            {
                "requirement_id": "R1",
                "requirement": "...",
                "assurance": 100
            }
        ]
    }

    Parameters
    ----------
    path : Path
        Path to the compliance result JSON file.

    Returns
    -------
    tuple
        A tuple containing:
        - violations
        - compliant requirement context
    """

    compliance_result = load_json(path)

    if not isinstance(compliance_result, dict):
        raise TypeError(
            "The compliance result file must contain a JSON object "
            "with 'violations' and 'context' fields."
        )

    violations = compliance_result.get("violations", [])
    resolution_context = compliance_result.get("context", [])

    if not isinstance(violations, list):
        raise TypeError(
            "The 'violations' field must contain a JSON array."
        )

    if not isinstance(resolution_context, list):
        raise TypeError(
            "The 'context' field must contain a JSON array."
        )

    for index, violation in enumerate(violations):
        if not isinstance(violation, dict):
            raise TypeError(
                f"Violation at index {index} must be a JSON object."
            )

        requirement_id = violation.get("requirement_id")

        if not requirement_id:
            raise ValueError(
                f"Violation at index {index} has no 'requirement_id'."
            )

    for index, context_requirement in enumerate(resolution_context):
        if not isinstance(context_requirement, dict):
            raise TypeError(
                f"Context requirement at index {index} "
                "must be a JSON object."
            )

        requirement_id = context_requirement.get("requirement_id")

        if not requirement_id:
            raise ValueError(
                f"Context requirement at index {index} "
                "has no 'requirement_id'."
            )

    return violations, resolution_context


# ==========================================================
# Prompt construction
# ==========================================================

def build_prompt(
    base_prompt: str,
    pst: str,
    violation: dict[str, Any],
    resolution_context: list[dict[str, Any]],
) -> str:
    """
    Build a complete model prompt for one violation.

    Parameters
    ----------
    base_prompt : str
        General resolution strategy instructions.

    pst : str
        Simplified PST generated in memory.

    violation : dict
        The violation being repaired.

    resolution_context : list
        Requirements that are currently compliant and should remain
        compliant.

    Returns
    -------
    str
        Complete model prompt.
    """

    return f"""{base_prompt}

============================================================
PROCESS STRUCTURED TREE
============================================================

{pst}

============================================================
DETECTED VIOLATION
============================================================

{json.dumps(violation, indent=2, ensure_ascii=False)}

============================================================
RESOLUTION CONTEXT REQUIREMENTS
============================================================

The following requirements are currently satisfied.

The generated repair should preserve these requirements whenever
possible and should avoid introducing new violations.

{json.dumps(resolution_context, indent=2, ensure_ascii=False)}

============================================================
OUTPUT REQUIREMENTS
============================================================

IMPORTANT:

- Generate exactly ONE resolution strategy for the detected violation
- Return ONLY valid JSON
- Do not use markdown
- Do not use code fences
- Do not add explanatory text outside the JSON
- Ensure the response is parseable using json.loads()
"""


# ==========================================================
# OpenRouter request
# ==========================================================

def generate_resolution_strategy(
    api_key: str,
    prompt: str,
) -> Any:
    """
    Generate one resolution strategy using OpenRouter.

    Parameters
    ----------
    api_key : str
        OpenRouter API key.

    prompt : str
        Complete prompt for the model.

    Returns
    -------
    Any
        Parsed JSON returned by the model.
    """

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0,
            "reasoning": {
                "enabled": True,
            },
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise RuntimeError(
            "The OpenRouter request failed.\n"
            f"Status code: {response.status_code}\n"
            f"Response: {response.text}"
        ) from error

    try:
        response_json = response.json()

    except requests.JSONDecodeError as error:
        raise ValueError(
            "OpenRouter returned a response that was not valid JSON.\n"
            f"Response content:\n{response.text}"
        ) from error

    try:
        generated_text = response_json["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(
            "The OpenRouter response does not contain model output.\n"
            f"Response:\n"
            f"{json.dumps(response_json, indent=2, ensure_ascii=False)}"
        ) from error

    if not isinstance(generated_text, str):
        raise ValueError(
            "The model output is not a string."
        )

    generated_text = generated_text.strip()

    if not generated_text:
        raise ValueError(
            "The model returned an empty response."
        )

    try:
        return json.loads(generated_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The model output is not valid JSON.\n"
            f"Line: {error.lineno}\n"
            f"Column: {error.colno}\n"
            f"Reason: {error.msg}\n\n"
            f"Model output:\n{generated_text}"
        ) from error


# ==========================================================
# Output normalization
# ==========================================================

def normalize_resolution_strategies(
    requirement_id: str,
    generated_result: Any,
) -> list[dict[str, Any]]:
    """
    Normalize a generated result into a flat list.

    Supported model output formats include:

    A single strategy:

    {
        "requirement_id": "R2",
        "resolution_strategy_id": "R2_RS1",
        "change_description": "...",
        "change_risk": {...},
        "change_operations": [...]
    }

    A nested strategy list:

    {
        "resolution_strategies": [
            {
                "requirement_id": "R2",
                "resolution_strategy_id": "R2_RS1",
                ...
            }
        ]
    }

    A direct list:

    [
        {
            "resolution_strategy_id": "R2_RS1",
            ...
        }
    ]

    The returned result is always flat and contains exactly one trusted
    requirement_id per strategy.

    Parameters
    ----------
    requirement_id : str
        Requirement associated with the model request.

    generated_result : Any
        Parsed model response.

    Returns
    -------
    list
        Flat list of normalized strategy objects.
    """

    if isinstance(generated_result, dict):
        nested_strategies = generated_result.get(
            "resolution_strategies"
        )

        if isinstance(nested_strategies, list):
            raw_strategies = nested_strategies
        else:
            raw_strategies = [generated_result]

    elif isinstance(generated_result, list):
        raw_strategies = generated_result

    else:
        raw_strategies = [
            {
                "resolution_strategy": generated_result,
            }
        ]

    normalized_strategies: list[dict[str, Any]] = []

    for strategy_index, strategy in enumerate(
        raw_strategies,
        start=1,
    ):
        if not isinstance(strategy, dict):
            normalized_strategies.append(
                {
                    "requirement_id": requirement_id,
                    "resolution_strategy": strategy,
                }
            )
            continue

        # Remove values that would duplicate or override the trusted
        # requirement identifier.
        cleaned_strategy = {
            key: value
            for key, value in strategy.items()
            if key not in {
                "requirement_id",
                "resolution_strategies",
                "scenario_name",
            }
        }

        # Add a strategy ID when the model did not provide one.
        if not cleaned_strategy.get("resolution_strategy_id"):
            cleaned_strategy["resolution_strategy_id"] = (
                f"{requirement_id}_RS{strategy_index}"
            )

        normalized_strategies.append(
            {
                "requirement_id": requirement_id,
                **cleaned_strategy,
            }
        )

    return normalized_strategies


# ==========================================================
# Main execution
# ==========================================================

def main() -> None:
    """
    Load inputs, simplify the original PST in memory, generate repair
    strategies, and save a flat JSON result.
    """

    start_time = time.time()

    print(f"Project root: {BASE_DIR}")
    print(f"Scenario: {SCENARIO_NAME}")

    # ------------------------------------------------------
    # Input paths
    # ------------------------------------------------------

    api_key_file = (
        BASE_DIR
        / "config"
        / "api_keys.json"
    )

    prompt_file = (
        BASE_DIR
        / "data"
        / "input"
        / "prompts"
        / "generate_resolution_strategies_demo.txt"
    )

    original_pst_file = (
        BASE_DIR
        / "data"
        / "input"
        / "process_models"
        / "cpee_trees"
        / f"{SCENARIO_NAME}.xml"
    )

    compliance_result_file = (
        BASE_DIR
        / "data"
        / "output"
        / "compliance_result_file"
        / f"{SCENARIO_NAME}_resolution_context.json"
    )

    # ------------------------------------------------------
    # Output path
    # ------------------------------------------------------

    output_dir = (
        BASE_DIR
        / "data"
        / "output"
        / "generated_resolution_strategies"
        / SCENARIO_NAME
        / "resolution_strategies_clean"
    )

    output_file = (
        output_dir
        / f"{SCENARIO_NAME}_resolution_strategies.json"
    )

    # ------------------------------------------------------
    # Load API key
    # ------------------------------------------------------

    api_key_config = load_json(api_key_file)

    if not isinstance(api_key_config, dict):
        raise TypeError(
            f"The API key file must contain a JSON object: "
            f"{api_key_file}"
        )

    api_key = api_key_config.get("OPENROUTER_API_KEY")

    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError(
            f"'OPENROUTER_API_KEY' is missing or empty in "
            f"{api_key_file}."
        )

    api_key = api_key.strip()

    # ------------------------------------------------------
    # Load prompt and compliance data
    # ------------------------------------------------------

    base_prompt = load_text(prompt_file)

    violations, resolution_context = load_compliance_result(
        compliance_result_file
    )

    print(f"Violations found: {len(violations)}")
    print(
        f"Compliant context requirements: "
        f"{len(resolution_context)}"
    )

    # ------------------------------------------------------
    # Simplify the original PST in memory
    # ------------------------------------------------------

    if not original_pst_file.exists():
        raise FileNotFoundError(
            f"Original process model not found: "
            f"{original_pst_file}"
        )

    print(f"Original process model: {original_pst_file}")
    print("Simplifying original PST in memory...")

    simplified_pst = simplify_pst(original_pst_file)

    if not isinstance(simplified_pst, str):
        raise TypeError(
            "simplify_pst() must return the simplified PST as a string."
        )

    if not simplified_pst.strip():
        raise ValueError(
            "simplify_pst() returned an empty PST."
        )

    print(
        "PST simplified successfully: "
        f"{len(simplified_pst.splitlines())} lines"
    )

    # The simplified PST is not saved to disk. It remains only in the
    # simplified_pst variable.

    # ------------------------------------------------------
    # Generate strategies
    # ------------------------------------------------------

    accumulated_strategies: list[dict[str, Any]] = []

    if not violations:
        print(
            "No violations were found. "
            "An empty strategy list will be written."
        )

    for index, violation in enumerate(
        violations,
        start=1,
    ):
        requirement_id = violation["requirement_id"]

        print(
            f"[{index}/{len(violations)}] "
            f"Generating strategy for {requirement_id}..."
        )

        prompt = build_prompt(
            base_prompt=base_prompt,
            pst=simplified_pst,
            violation=violation,
            resolution_context=resolution_context,
        )

        generated_result = generate_resolution_strategy(
            api_key=api_key,
            prompt=prompt,
        )

        normalized_strategies = normalize_resolution_strategies(
            requirement_id=requirement_id,
            generated_result=generated_result,
        )

        accumulated_strategies.extend(
            normalized_strategies
        )

        print(
            f"[{index}/{len(violations)}] "
            f"Generated {len(normalized_strategies)} normalized "
            f"strategy entry."
        )

    # ------------------------------------------------------
    # Save flat output without scenario_name
    # ------------------------------------------------------

    consolidated_output = {
        "resolution_strategies": accumulated_strategies,
    }

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            consolidated_output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    elapsed_seconds = round(
        time.time() - start_time,
        2,
    )

    print(
        f"Saved {len(accumulated_strategies)} strategies to:"
    )
    print(output_file)
    print(f"Execution time: {elapsed_seconds} seconds")


if __name__ == "__main__":
    main()