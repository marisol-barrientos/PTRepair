import json
import time
import requests
from pathlib import Path

CURRENT_DIR = Path.cwd().resolve()
BASE_DIR = CURRENT_DIR

TARGET = "PTResolver"

while BASE_DIR.name != TARGET:
    # stop if we reached filesystem root
    if BASE_DIR.parent == BASE_DIR:
        raise FileNotFoundError(
            f"Could not find '{TARGET}' in parent directories."
        )

    BASE_DIR = BASE_DIR.parent

print("Project root:")
print(BASE_DIR)

SCENARIO_NAME = "02_de_masellis_loan_approval"

REQUIREMENT_ID = "R1"

MODEL = "openai/gpt-5.5"

API_KEY_FILE = (
    BASE_DIR
    / "config"
    / "api_keys.json"
)

with open(
    API_KEY_FILE,
    "r",
    encoding="utf-8"
) as f:

    api_config = json.load(f)

OPENROUTER_API_KEY = (
    api_config["OPENROUTER_API_KEY"]
)


PROMPT_FILE = (
    BASE_DIR
    / "data"
    / "input"
    / "prompts"
    / "V1_generate_resolution_strategies_no_process_change_operations_free_answer.txt"
)

PST_FILE = (
    BASE_DIR
    / "data"
    / "output"
    / "simplified_pst"
    / f"{SCENARIO_NAME}_simplified_pst.txt"
)

VIOLATIONS_FILE = (
    BASE_DIR
    / "data"
    / "output"
    / "compliance_violations_before_changes"
    / f"{SCENARIO_NAME}_ALL_violations.json"
)


RESOLUTION_CONTEXT_FILE = (
    BASE_DIR
    / "data"
    / "input"
    / "resolution_context"
    / f"{SCENARIO_NAME}_req_resolution_context.json"
)


OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "generated_resolution_strategies"
)

SCENARIO_OUTPUT_DIR = (
    OUTPUT_DIR
    / SCENARIO_NAME
)

JSON_DIR = (
    SCENARIO_OUTPUT_DIR
    / "resolution_strategies_clean"
)

RAW_DIR = (
    SCENARIO_OUTPUT_DIR
    / "raw"
)

FULL_RESPONSE_DIR = (
    SCENARIO_OUTPUT_DIR
    / "full_response"
)

METADATA_DIR = (
    SCENARIO_OUTPUT_DIR
    / "metadata"
)

PROBLEMS_DIR = (
    SCENARIO_OUTPUT_DIR
    / "problems"
)

JSON_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FULL_RESPONSE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

METADATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROBLEMS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

start_time = time.time()

problems_detected = []

with open(
    PROMPT_FILE,
    "r",
    encoding="utf-8"
) as f:

    BASE_PROMPT = f.read()

with open(
    PST_FILE,
    "r",
    encoding="utf-8"
) as f:

    pst = f.read()


with open(
    VIOLATIONS_FILE,
    "r",
    encoding="utf-8"
) as f:

    violations = json.load(f)


resolution_context = {}

if RESOLUTION_CONTEXT_FILE.exists():

    with open(
        RESOLUTION_CONTEXT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        resolution_context = json.load(f)

    print(
        f"Loaded resolution context requirements: "
        f"{len(resolution_context)}"
    )

else:

    print(
        "No resolution context file found."
    )


target_violation = None

for violation in violations:

    if violation["requirement_id"] == REQUIREMENT_ID:

        target_violation = violation

        break

if target_violation is None:

    raise ValueError(
        f"Violation '{REQUIREMENT_ID}' not found."
    )

print(
    f"Using violation: "
    f"{REQUIREMENT_ID}"
)


OUTPUT_PREFIX = (
    f"{SCENARIO_NAME}_RS_{REQUIREMENT_ID}"
)

print(
    "Output prefix:",
    OUTPUT_PREFIX
)

final_prompt = f"""{BASE_PROMPT}

============================================================
PROCESS STRUCTURED TREE
============================================================

{pst}

============================================================
DETECTED VIOLATION
============================================================

{json.dumps(target_violation, indent=2)}

============================================================
RESOLUTION CONTEXT REQUIREMENTS
============================================================

These requirements are currently satisfied and should remain
satisfied whenever possible.

Avoid introducing new violations of these requirements.

{json.dumps(resolution_context, indent=2)}

IMPORTANT:
- Return ONLY valid JSON
- Do not use markdown
- Do not use code fences
- Ensure output is parseable with json.loads()
"""

print(
    "\nSending request to model...\n"
)

try:

    response = requests.post(
        url=(
            "https://openrouter.ai/"
            "api/v1/chat/completions"
        ),
        headers={
            "Authorization": (
                f"Bearer "
                f"{OPENROUTER_API_KEY}"
            ),
            "Content-Type":
                "application/json",
        },
        data=json.dumps({
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            "temperature": 0,
            "reasoning": {
                "enabled": True
            }
        }),
        timeout=300
    )

except Exception as e:

    problems_detected.append(
        f"Request exception: {str(e)}"
    )

    raise e

# ============================================================
# CHECK RESPONSE
# ============================================================

if response.status_code != 200:

    problems_detected.append(
        f"HTTP {response.status_code}"
    )

    print("ERROR:")

    print(response.status_code)

    print(response.text)

    raise Exception(
        "API request failed"
    )

response_json = response.json()

print(
    "\n========== FULL RESPONSE ==========\n"
)

print(
    json.dumps(
        response_json,
        indent=2
    )
)

if "choices" not in response_json:

    problems_detected.append(
        "API response missing 'choices'"
    )

    raise ValueError(
        "API response does not contain "
        "'choices'. See printed response above."
    )

try:

    assistant_message = (
        response_json["choices"][0]["message"]
    )

    generated_text = (
        assistant_message["content"]
    )

except Exception as e:

    problems_detected.append(
        "Failed to extract assistant message"
    )

    raise e

parsed_json = None

try:

    parsed_json = json.loads(
        generated_text
    )

except Exception as e:

    problems_detected.append(
        "Model output is not valid JSON"
    )

raw_output_path = (
    RAW_DIR
    / f"{OUTPUT_PREFIX}_raw.txt"
)

with open(
    raw_output_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(generated_text)

if parsed_json is not None:

    json_output_path = (
        JSON_DIR
        / f"{OUTPUT_PREFIX}.json"
    )

    with open(
        json_output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            parsed_json,
            f,
            indent=2,
            ensure_ascii=False
        )

full_response_path = (
    FULL_RESPONSE_DIR
    / (
        f"{OUTPUT_PREFIX}"
        f"_full_response.json"
    )
)

with open(
    full_response_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        response_json,
        f,
        indent=2,
        ensure_ascii=False
    )

end_time = time.time()

execution_time_ms = round(
    (end_time - start_time) * 1000,
    2
)

usage = response_json.get(
    "usage",
    {}
)

metadata = {

    "model":
        MODEL,

    "scenario_name":
        SCENARIO_NAME,

    "requirement_id":
        REQUIREMENT_ID,

    "output_prefix":
        OUTPUT_PREFIX,

    "execution_time_milliseconds":
        execution_time_ms,

    "resolution_context_requirements":
        len(resolution_context),

    "problems_detected":
        problems_detected,

    "usage": {

        "prompt_tokens":
            usage.get(
                "prompt_tokens"
            ),

        "completion_tokens":
            usage.get(
                "completion_tokens"
            ),

        "total_tokens":
            usage.get(
                "total_tokens"
            ),

        "reasoning_tokens":
            usage.get(
                "reasoning_tokens"
            )
    }
}

metadata_path = (
    METADATA_DIR
    / (
        f"{OUTPUT_PREFIX}"
        f"_metadata.json"
    )
)

with open(
    metadata_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metadata,
        f,
        indent=2,
        ensure_ascii=False
    )

problem_log_path = (
    PROBLEMS_DIR
    / (
        f"{OUTPUT_PREFIX}"
        f"_problems.log"
    )
)

with open(
    problem_log_path,
    "w",
    encoding="utf-8"
) as f:

    if len(problems_detected) == 0:

        f.write(
            "No problems detected.\n"
        )

    else:

        for problem in problems_detected:

            f.write(problem + "\n")


if len(problems_detected) == 0:

    print("None")

else:

    for problem in problems_detected:

        print("-", problem)