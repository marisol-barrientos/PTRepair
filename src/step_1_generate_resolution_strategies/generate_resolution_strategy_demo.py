import json
import time
from pathlib import Path
from typing import Any

import requests


SCENARIO_NAME = "02_de_masellis_loan_approval"
MODEL = "openai/gpt-5.5"
TARGET_PROJECT_DIR = "PTResolver"
REQUEST_TIMEOUT_SECONDS = 300


def find_project_root(start_dir: Path, target_name: str) -> Path:
    current = start_dir.resolve()

    while current.name != target_name:
        if current.parent == current:
            raise FileNotFoundError(
                f"Could not find '{target_name}' in parent directories."
            )
        current = current.parent

    return current


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def build_prompt(
    base_prompt: str,
    pst: str,
    violation: dict[str, Any],
    resolution_context: Any,
) -> str:
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

These requirements are currently satisfied and should remain
satisfied whenever possible.

Avoid introducing new violations of these requirements.

{json.dumps(resolution_context, indent=2, ensure_ascii=False)}

IMPORTANT:
- Generate exactly ONE resolution strategy for this requirement
- Return ONLY valid JSON
- Do not use markdown
- Do not use code fences
- Ensure output is parseable with json.loads()
"""


def generate_resolution_strategy(
    api_key: str,
    prompt: str,
) -> Any:
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "reasoning": {"enabled": True},
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    response_json = response.json()

    try:
        generated_text = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("API response does not contain model output.") from error

    try:
        return json.loads(generated_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Model output is not valid JSON.\n"
            f"Requirement output:\n{generated_text}"
        ) from error


def attach_requirement_id(
    requirement_id: str,
    strategy: Any,
) -> dict[str, Any]:
    """Create one consistently identifiable entry per requirement."""
    if isinstance(strategy, dict):
        return {
            "requirement_id": requirement_id,
            **strategy,
        }

    return {
        "requirement_id": requirement_id,
        "resolution_strategy": strategy,
    }


def main() -> None:
    start_time = time.time()
    base_dir = find_project_root(Path.cwd(), TARGET_PROJECT_DIR)

    print(f"Project root: {base_dir}")

    api_key_file = base_dir / "config" / "api_keys.json"
    prompt_file = (
        base_dir
        / "data"
        / "input"
        / "prompts"
        / "generate_resolution_strategies_demo.txt"
    )
    pst_file = (
        base_dir
        / "data"
        / "output"
        / "simplified_pst"
        / f"{SCENARIO_NAME}_simplified_pst.txt"
    )
    violations_file = (
        base_dir
        / "data"
        / "output"
        / "compliance_violations_before_changes"
        / f"{SCENARIO_NAME}_ALL_violations.json"
    )
    resolution_context_file = (
        base_dir
        / "data"
        / "input"
        / "resolution_context"
        / f"{SCENARIO_NAME}_req_resolution_context.json"
    )
    json_dir = (
        base_dir
        / "data"
        / "output"
        / "generated_resolution_strategies"
        / SCENARIO_NAME
        / "resolution_strategies_clean"
    )
    output_file = json_dir / f"{SCENARIO_NAME}_resolution_strategies.json"

    api_key = load_json(api_key_file)["OPENROUTER_API_KEY"]
    base_prompt = load_text(prompt_file)
    pst = load_text(pst_file)
    violations = load_json(violations_file)

    resolution_context = (
        load_json(resolution_context_file)
        if resolution_context_file.exists()
        else {}
    )

    if not isinstance(violations, list):
        raise TypeError("The violations file must contain a JSON array.")

    accumulated_strategies: list[dict[str, Any]] = []

    for index, violation in enumerate(violations, start=1):
        requirement_id = violation.get("requirement_id")
        if not requirement_id:
            raise ValueError(
                f"Violation at index {index - 1} has no 'requirement_id'."
            )

        print(
            f"[{index}/{len(violations)}] Generating strategy for "
            f"{requirement_id}..."
        )

        prompt = build_prompt(
            base_prompt=base_prompt,
            pst=pst,
            violation=violation,
            resolution_context=resolution_context,
        )
        strategy = generate_resolution_strategy(
            api_key=api_key,
            prompt=prompt,
        )
        accumulated_strategies.append(
            attach_requirement_id(requirement_id, strategy)
        )

    consolidated_output = {
        "scenario_name": SCENARIO_NAME,
        "resolution_strategies": accumulated_strategies,
    }

    json_dir.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            consolidated_output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    elapsed_seconds = round(time.time() - start_time, 2)
    print(f"Saved {len(accumulated_strategies)} strategies to: {output_file}")
    print(f"Execution time: {elapsed_seconds} seconds")


if __name__ == "__main__":
    main()