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

def build_batch_prompt(
    base_prompt: str,
    pst: str,
    violations: list[dict[str, Any]],
    resolution_context: list[dict[str, Any]],
) -> str:
    """
    Build one model prompt containing the PST once and all detected
    violations.

    The model is instructed to generate exactly one resolution
    strategy for each violation.
    """

    return f"""{base_prompt}

============================================================
PROCESS STRUCTURED TREE
============================================================

{pst}

============================================================
DETECTED VIOLATIONS
============================================================

{json.dumps(violations, indent=2, ensure_ascii=False)}

============================================================
RESOLUTION CONTEXT REQUIREMENTS
============================================================

The following requirements are currently satisfied.

The generated repairs should preserve these requirements whenever
possible and should avoid introducing new violations.

{json.dumps(resolution_context, indent=2, ensure_ascii=False)}

============================================================
OUTPUT REQUIREMENTS
============================================================

IMPORTANT:

- Generate exactly ONE resolution strategy for EACH detected violation
- Return one strategy for every requirement_id listed above
- Preserve the exact requirement_id from each violation
- Do not generate strategies for unknown requirement IDs
- Return ONLY valid JSON
- Do not use markdown
- Do not use code fences
- Do not add explanatory text outside the JSON
- Ensure the response is parseable using json.loads()

Return a JSON object using exactly this top-level structure:

{{
  "resolution_strategies": [
    {{
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "resolution_strategy": "Description of the repair strategy"
    }}
  ]
}}
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

def normalize_batch_resolution_strategies(
    violations: list[dict[str, Any]],
    generated_result: Any,
) -> list[dict[str, Any]]:
    """
    Normalize and validate strategies generated for a batch of
    violations.

    Exactly one strategy must be returned for every expected
    requirement ID.
    """

    if not isinstance(generated_result, dict):
        raise TypeError(
            "The model output must be a JSON object."
        )

    raw_strategies = generated_result.get(
        "resolution_strategies"
    )

    if not isinstance(raw_strategies, list):
        raise ValueError(
            "The model output must contain a "
            "'resolution_strategies' list."
        )

    expected_requirement_ids = [
        violation["requirement_id"].strip()
        for violation in violations
    ]

    expected_requirement_id_set = set(
        expected_requirement_ids
    )

    if len(expected_requirement_id_set) != len(
        expected_requirement_ids
    ):
        raise ValueError(
            "The violations list contains duplicate "
            "requirement IDs."
        )

    normalized_by_requirement_id: dict[
        str,
        dict[str, Any],
    ] = {}

    for index, strategy in enumerate(
        raw_strategies
    ):
        if not isinstance(strategy, dict):
            raise TypeError(
                f"Resolution strategy at index {index} must "
                "be a JSON object."
            )

        requirement_id = strategy.get(
            "requirement_id"
        )

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                f"Resolution strategy at index {index} has "
                "no valid 'requirement_id'."
            )

        requirement_id = requirement_id.strip()

        if requirement_id not in (
            expected_requirement_id_set
        ):
            raise ValueError(
                "The model returned a strategy for an unknown "
                f"requirement ID: {requirement_id!r}."
            )

        if requirement_id in (
            normalized_by_requirement_id
        ):
            raise ValueError(
                "The model returned more than one strategy for "
                f"requirement ID {requirement_id!r}."
            )

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
            ] = f"{requirement_id}_RS1"
        else:
            cleaned_strategy[
                "resolution_strategy_id"
            ] = strategy_id.strip()

        normalized_by_requirement_id[
            requirement_id
        ] = {
            "requirement_id": requirement_id,
            **cleaned_strategy,
        }

    missing_requirement_ids = [
        requirement_id
        for requirement_id in expected_requirement_ids
        if requirement_id
        not in normalized_by_requirement_id
    ]

    if missing_requirement_ids:
        raise ValueError(
            "The model did not return a strategy for the "
            "following requirement IDs: "
            + ", ".join(missing_requirement_ids)
        )

    return [
        normalized_by_requirement_id[
            requirement_id
        ]
        for requirement_id in expected_requirement_ids
    ]


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
    Generate one resolution strategy per violation using one model
    request.

    The simplified PST is included only once in the model prompt,
    rather than once for every violation.

    Parameters
    ----------
    original_pst : bytes
        Original XML PST content.

    compliance_result : dict
        Parsed compliance result containing violations and compliant
        context requirements.

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
        One normalized resolution strategy for every violation.

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

    if not violations:
        return []

    resolved_api_key = get_openrouter_api_key(
        api_key
    )

    base_prompt = load_prompt(
        prompt=prompt,
        prompt_file=prompt_file,
    )

    simplified_pst = simplify_pst_in_memory(
        validated_pst
    )

    complete_prompt = build_batch_prompt(
        base_prompt=base_prompt,
        pst=simplified_pst,
        violations=violations,
        resolution_context=resolution_context,
    )

    print(
        "Generating resolution strategies for "
        f"{len(violations)} violation(s) in one request..."
    )

    generated_result = generate_resolution_strategy(
        api_key=resolved_api_key,
        prompt=complete_prompt,
    )

    return normalize_batch_resolution_strategies(
        violations=violations,
        generated_result=generated_result,
    )
