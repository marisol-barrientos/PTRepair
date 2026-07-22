import io
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


# ==========================================================
# Configuration
# ==========================================================

MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-5.5",
)

REQUEST_TIMEOUT_SECONDS = int(
    os.getenv(
        "OPENROUTER_TIMEOUT_SECONDS",
        "300",
    )
)


# ==========================================================
# Project paths and imports
# ==========================================================

# Expected location:
#
# PTRepair/
# └── src/
#     └── step_1_generate_resolution_strategies/
#         └── generate_resolution_strategies_demo.py
#
BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from step_0_preprocessing.simplify_pst_demo import (
    simplify_pst,
)


DEFAULT_PROMPT_FILE = (
    BASE_DIR
    / "data"
    / "input"
    / "prompts"
    / "generate_resolution_strategies_demo.txt"
)


# ==========================================================
# Configuration loading
# ==========================================================

def load_prompt(
    prompt: str | None = None,
    prompt_file: str | Path | None = None,
) -> str:
    """
    Return the prompt used for strategy generation.

    The prompt can be provided directly as a string. When omitted,
    it is loaded from a server-side prompt file.

    The prompt file is configuration input; no generated output is
    written to disk.
    """

    if prompt is not None:
        prompt = prompt.strip()

        if not prompt:
            raise ValueError(
                "The provided prompt cannot be empty."
            )

        return prompt

    path = (
        Path(prompt_file).expanduser().resolve()
        if prompt_file is not None
        else DEFAULT_PROMPT_FILE
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8",
    ).strip()

    if not content:
        raise ValueError(
            f"Prompt file is empty: {path}"
        )

    return content


def get_openrouter_api_key(
    api_key: str | None = None,
) -> str:
    """
    Return the OpenRouter API key.

    The preferred deployment configuration is the
    OPENROUTER_API_KEY environment variable.
    """

    resolved_key = (
        api_key
        or os.getenv("OPENROUTER_API_KEY")
    )

    if (
        not isinstance(resolved_key, str)
        or not resolved_key.strip()
    ):
        raise ValueError(
            "OpenRouter API key is missing. Set the "
            "OPENROUTER_API_KEY environment variable or pass "
            "api_key directly."
        )

    return resolved_key.strip()


# ==========================================================
# Input validation
# ==========================================================

def validate_compliance_result(
    compliance_result: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Validate and return violations and compliant context.

    Expected input:

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
    """

    if not isinstance(
        compliance_result,
        dict,
    ):
        raise TypeError(
            "The compliance result must be a dictionary."
        )

    violations = compliance_result.get(
        "violations",
        [],
    )

    resolution_context = compliance_result.get(
        "context",
        [],
    )

    if not isinstance(violations, list):
        raise TypeError(
            "The 'violations' field must contain a list."
        )

    if not isinstance(
        resolution_context,
        list,
    ):
        raise TypeError(
            "The 'context' field must contain a list."
        )

    for index, violation in enumerate(
        violations
    ):
        if not isinstance(violation, dict):
            raise TypeError(
                f"Violation at index {index} must be "
                "a dictionary."
            )

        requirement_id = violation.get(
            "requirement_id"
        )

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                f"Violation at index {index} has no valid "
                "'requirement_id'."
            )

    for index, requirement in enumerate(
        resolution_context
    ):
        if not isinstance(requirement, dict):
            raise TypeError(
                f"Context requirement at index {index} "
                "must be a dictionary."
            )

        requirement_id = requirement.get(
            "requirement_id"
        )

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                f"Context requirement at index {index} "
                "has no valid 'requirement_id'."
            )

    return violations, resolution_context


def validate_original_pst(
    original_pst: bytes,
) -> bytes:
    """
    Validate uploaded PST bytes.
    """

    if not isinstance(
        original_pst,
        bytes,
    ):
        raise TypeError(
            "The original PST must be provided as bytes."
        )

    if not original_pst.strip():
        raise ValueError(
            "The original PST is empty."
        )

    return original_pst


# ==========================================================
# PST simplification
# ==========================================================

def simplify_pst_in_memory(
    original_pst: bytes,
) -> str:
    """
    Simplify an XML PST without creating an output file.

    BytesIO provides a file-like object backed entirely by memory.

    This assumes simplify_pst() accepts a path-like or file-like
    object supported by the XML parser it uses.
    """

    pst_stream = io.BytesIO(
        original_pst
    )

    simplified_pst = simplify_pst(
        pst_stream
    )

    if not isinstance(
        simplified_pst,
        str,
    ):
        raise TypeError(
            "simplify_pst() must return the simplified PST "
            "as a string."
        )

    if not simplified_pst.strip():
        raise ValueError(
            "simplify_pst() returned an empty PST."
        )

    return simplified_pst


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
    Build the model prompt for one violation.
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
    Generate one resolution strategy through OpenRouter.
    """

    response = requests.post(
        url=(
            "https://openrouter.ai/api/v1/"
            "chat/completions"
        ),
        headers={
            "Authorization": (
                f"Bearer {api_key}"
            ),
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
            "OpenRouter returned a response that was not "
            "valid JSON.\n"
            f"Response:\n{response.text}"
        ) from error

    try:
        generated_text = (
            response_json["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as error:
        raise ValueError(
            "The OpenRouter response does not contain "
            "model output.\n"
            f"{json.dumps(response_json, indent=2, ensure_ascii=False)}"
        ) from error

    if not isinstance(
        generated_text,
        str,
    ):
        raise ValueError(
            "The model output is not a string."
        )

    generated_text = generated_text.strip()

    if not generated_text:
        raise ValueError(
            "The model returned an empty response."
        )

    try:
        return json.loads(
            generated_text
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "The model output is not valid JSON.\n"
            f"Line {error.lineno}, "
            f"column {error.colno}: "
            f"{error.msg}\n\n"
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
    Normalize model output into a flat strategy list.
    """

    if isinstance(
        generated_result,
        dict,
    ):
        nested_strategies = (
            generated_result.get(
                "resolution_strategies"
            )
        )

        if isinstance(
            nested_strategies,
            list,
        ):
            raw_strategies = (
                nested_strategies
            )
        else:
            raw_strategies = [
                generated_result
            ]

    elif isinstance(
        generated_result,
        list,
    ):
        raw_strategies = generated_result

    else:
        raw_strategies = [
            {
                "resolution_strategy":
                    generated_result
            }
        ]

    normalized: list[
        dict[str, Any]
    ] = []

    for index, strategy in enumerate(
        raw_strategies,
        start=1,
    ):
        if not isinstance(
            strategy,
            dict,
        ):
            strategy = {
                "resolution_strategy":
                    strategy
            }

        cleaned_strategy = {
            key: value
            for key, value in strategy.items()
            if key not in {
                "requirement_id",
                "resolution_strategies",
                "scenario_name",
            }
        }

        strategy_id = cleaned_strategy.get(
            "resolution_strategy_id"
        )

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            cleaned_strategy[
                "resolution_strategy_id"
            ] = f"{requirement_id}_RS{index}"

        normalized.append(
            {
                "requirement_id":
                    requirement_id,
                **cleaned_strategy,
            }
        )

    return normalized


# ==========================================================
# Public in-memory function
# ==========================================================

def generate_resolution_strategies(
    original_pst: bytes,
    compliance_result: dict[str, Any],
    api_key: str | None = None,
    prompt: str | None = None,
    prompt_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Generate resolution strategies completely in memory.

    Parameters
    ----------
    original_pst : bytes
        Original XML PST content.

    compliance_result : dict
        Parsed compliance result containing violations and context.

    api_key : str | None
        Optional OpenRouter API key. When omitted, the
        OPENROUTER_API_KEY environment variable is used.

    prompt : str | None
        Optional prompt content supplied directly.

    prompt_file : str | Path | None
        Optional server-side prompt file. Used only when prompt is
        not supplied directly.

    Returns
    -------
    list[dict[str, Any]]
        Generated normalized resolution strategies.

    Notes
    -----
    No generated output is written to disk.
    """

    validated_pst = validate_original_pst(
        original_pst
    )

    violations, resolution_context = (
        validate_compliance_result(
            compliance_result
        )
    )

    resolved_api_key = (
        get_openrouter_api_key(
            api_key
        )
    )

    base_prompt = load_prompt(
        prompt=prompt,
        prompt_file=prompt_file,
    )

    simplified_pst = simplify_pst_in_memory(
        validated_pst
    )

    accumulated_strategies: list[
        dict[str, Any]
    ] = []

    for index, violation in enumerate(
        violations,
        start=1,
    ):
        requirement_id = violation[
            "requirement_id"
        ]

        print(
            f"[{index}/{len(violations)}] "
            f"Generating strategy for "
            f"{requirement_id}..."
        )

        complete_prompt = build_prompt(
            base_prompt=base_prompt,
            pst=simplified_pst,
            violation=violation,
            resolution_context=(
                resolution_context
            ),
        )

        generated_result = (
            generate_resolution_strategy(
                api_key=resolved_api_key,
                prompt=complete_prompt,
            )
        )

        normalized = (
            normalize_resolution_strategies(
                requirement_id=(
                    requirement_id
                ),
                generated_result=(
                    generated_result
                ),
            )
        )

        accumulated_strategies.extend(
            normalized
        )

    return accumulated_strategies
