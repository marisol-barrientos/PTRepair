import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError as error:
    raise ImportError(
        "The Gemini client is not installed. Install it with 'pip install google-genai'."
    ) from error

from src.step_1_generate_resolution_strategies.generate_resolution_strategies_demo import (
    build_batch_prompt,
    load_prompt,
    normalize_batch_resolution_strategies,
    simplify_pst_in_memory,
    validate_compliance_result,
    validate_original_pst,
)


MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash-lite",
)

REQUEST_TIMEOUT_SECONDS = int(
    os.getenv(
        "GEMINI_TIMEOUT_SECONDS",
        "180",
    )
)

MAX_EVIDENCE_ITEMS_PER_VIOLATION = int(
    os.getenv(
        "GEMINI_MAX_EVIDENCE_ITEMS",
        "6",
    )
)

MAX_EVIDENCE_CHARS = int(
    os.getenv(
        "GEMINI_MAX_EVIDENCE_CHARS",
        "280",
    )
)

MAX_CONTEXT_ITEMS = int(
    os.getenv(
        "GEMINI_MAX_CONTEXT_ITEMS",
        "30",
    )
)


def get_gemini_api_key(
    api_key: str | None = None,
) -> str:
    """
    Return the Gemini API key.

    The preferred deployment configuration is the GEMINI_API_KEY
    environment variable.
    """

    resolved_key = (
        api_key
        or os.getenv("GEMINI_API_KEY")
    )

    if (
        not isinstance(resolved_key, str)
        or not resolved_key.strip()
    ):
        raise ValueError(
            "Gemini API key is missing. Set the GEMINI_API_KEY "
            "environment variable or pass api_key directly."
        )

    return resolved_key.strip()


def _strip_json_fences(text: str) -> str:
    """
    Strip optional markdown code fences around JSON output.
    """

    stripped = text.strip()

    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    return stripped


def _truncate_text(value: Any, max_chars: int) -> str:
    text = str(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _compact_for_prompt(
    violations: list[dict[str, Any]],
    resolution_context: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Reduce prompt payload size to improve generation latency.

    Requirement IDs are preserved exactly so output mapping remains stable.
    """

    compact_violations: list[dict[str, Any]] = []
    for violation in violations:
        evidence = violation.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = [evidence]

        compact_evidence = [
            _truncate_text(item, MAX_EVIDENCE_CHARS)
            for item in evidence[:MAX_EVIDENCE_ITEMS_PER_VIOLATION]
        ]

        compact_violations.append(
            {
                "requirement_id": violation.get("requirement_id"),
                "requirement": violation.get("requirement"),
                "assurance": violation.get("assurance"),
                "evidence": compact_evidence,
            }
        )

    compact_context: list[dict[str, Any]] = []
    for item in resolution_context[:MAX_CONTEXT_ITEMS]:
        compact_context.append(
            {
                "requirement_id": item.get("requirement_id"),
                "requirement": item.get("requirement"),
                "assurance": item.get("assurance"),
            }
        )

    return compact_violations, compact_context


def generate_resolution_strategy(
    api_key: str,
    prompt: str,
) -> Any:
    """
    Generate one resolution strategy through Gemini.
    """

    client = genai.Client(api_key=api_key)

    def _call_model() -> Any:
        return client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_model)

        try:
            response = future.result(
                timeout=REQUEST_TIMEOUT_SECONDS
            )

        except FutureTimeoutError as error:
            raise TimeoutError(
                "Gemini generation timed out after "
                f"{REQUEST_TIMEOUT_SECONDS}s. "
                "Try a smaller prompt, fewer violations, or increase "
                "GEMINI_TIMEOUT_SECONDS."
            ) from error

    elapsed_seconds = time.perf_counter() - start_time
    print(
        "Gemini response received in "
        f"{elapsed_seconds:.2f}s"
    )

    generated_text = getattr(response, "text", None)

    if not isinstance(generated_text, str):
        raise ValueError(
            "The Gemini response does not contain text output. "
            f"Response type: {type(response).__name__}"
        )

    generated_text = _strip_json_fences(generated_text)

    if not generated_text:
        raise ValueError(
            "The Gemini model returned an empty response."
        )

    try:
        return json.loads(generated_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The Gemini model output is not valid JSON.\n"
            f"Line {error.lineno}, "
            f"column {error.colno}: "
            f"{error.msg}\n\n"
            f"Model output:\n{generated_text}"
        ) from error


def generate_resolution_strategies(
    original_pst: bytes,
    compliance_result: dict[str, Any],
    api_key: str | None = None,
    prompt: str | None = None,
    prompt_file: str | None = None,
) -> list[dict[str, Any]]:
    """
    Gemini-backed variant that generates one resolution strategy
    per violation in one request.

    Signature mirrors generate_resolution_strategies_demo.py so the
    caller can swap imports only.
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

    resolved_api_key = get_gemini_api_key(
        api_key
    )

    base_prompt = load_prompt(
        prompt=prompt,
        prompt_file=prompt_file,
    )

    simplified_pst = simplify_pst_in_memory(
        validated_pst
    )

    prompt_violations, prompt_context = _compact_for_prompt(
        violations=violations,
        resolution_context=resolution_context,
    )

    complete_prompt = build_batch_prompt(
        base_prompt=base_prompt,
        pst=simplified_pst,
        violations=prompt_violations,
        resolution_context=prompt_context,
    )

    print(
        "Generating resolution strategies for "
        f"{len(violations)} violation(s) in one Gemini request..."
    )

    generated_result = generate_resolution_strategy(
        api_key=resolved_api_key,
        prompt=complete_prompt,
    )

    return normalize_batch_resolution_strategies(
        violations=violations,
        generated_result=generated_result,
    )
