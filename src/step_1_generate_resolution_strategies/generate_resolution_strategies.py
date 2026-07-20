# ============================================================
# STEP 1 -  V2
# GENERATE RESOLUTION STRATEGIES
# ============================================================
#
# This script generates candidate resolution strategies for
# detected compliance violations using a Large Language Model
# (LLM).
#
# For a selected scenario and violated requirement, the script:
# - loads the simplified Process Structure Tree (PST)
# - loads the detected compliance violation
# - loads resolution context requirements
# - constructs a prompting context
# - queries the LLM for candidate repair strategies
# - stores the generated strategies and metadata
#
# The generated resolution strategies consist of sequences of
# change operations intended to mitigate or resolve the
# detected compliance violation while preserving already
# compliant requirements whenever possible.
#
# Output:
# - generated resolution strategies (.json)
# - raw LLM responses
# - metadata and execution statistics
#
# ============================================================

import json
import time
import requests
from pathlib import Path

# ============================================================
# DYNAMIC PROJECT ROOT DETECTION
# ============================================================

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

# ============================================================
# CONFIGURATION
# ============================================================

SCENARIO_NAME = "02_de_masellis_loan_approval"

REQUIREMENT_ID = "R1"

MODEL = "openai/gpt-5.5"

# ============================================================
# LOAD API KEY
# ============================================================

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

# ============================================================
# INPUT FILES
# ============================================================

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

# ============================================================
# RESOLUTION CONTEXT FILE
# ============================================================

RESOLUTION_CONTEXT_FILE = (
    BASE_DIR
    / "data"
    / "input"
    / "resolution_context"
    / f"{SCENARIO_NAME}_req_resolution_context.json"
)

# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

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

# ============================================================
# TIMER START
# ============================================================

start_time = time.time()

# ============================================================
# LOGGING VARIABLES
# ============================================================

problems_detected = []

# ============================================================
# LOAD BASE PROMPT
# ============================================================

with open(
    PROMPT_FILE,
    "r",
    encoding="utf-8"
) as f:

    BASE_PROMPT = f.read()

# ============================================================
# LOAD PST
# ============================================================

with open(
    PST_FILE,
    "r",
    encoding="utf-8"
) as f:

    pst = f.read()

# ============================================================
# LOAD VIOLATIONS
# ============================================================

with open(
    VIOLATIONS_FILE,
    "r",
    encoding="utf-8"
) as f:

    violations = json.load(f)

# ============================================================
# LOAD RESOLUTION CONTEXT
# ============================================================

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

# ============================================================
# FIND TARGET VIOLATION
# ============================================================

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

# ============================================================
# BUILD OUTPUT PREFIX
# ============================================================

OUTPUT_PREFIX = (
    f"{SCENARIO_NAME}_RS_{REQUIREMENT_ID}"
)

print(
    "Output prefix:",
    OUTPUT_PREFIX
)

# ============================================================
# BUILD PROMPT
# ============================================================

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

# ============================================================
# API REQUEST
# ============================================================

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

# ============================================================
# EXTRACT MODEL OUTPUT
# ============================================================

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

# ============================================================
# VALIDATE JSON
# ============================================================

parsed_json = None

try:

    parsed_json = json.loads(
        generated_text
    )

except Exception as e:

    problems_detected.append(
        "Model output is not valid JSON"
    )

    print(
        "\nERROR: Invalid JSON generated"
    )

    print(e)

# ============================================================
# SAVE RAW RESPONSE
# ============================================================

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

print(
    f"\nRaw response saved to:\n"
    f"{raw_output_path}"
)

# ============================================================
# SAVE PARSED JSON
# ============================================================

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

    print(
        f"\nJSON saved to:\n"
        f"{json_output_path}"
    )

# ============================================================
# SAVE FULL API RESPONSE
# ============================================================

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

print(
    f"\nFull API response saved to:\n"
    f"{full_response_path}"
)

# ============================================================
# EXECUTION TIME
# ============================================================

end_time = time.time()

execution_time_ms = round(
    (end_time - start_time) * 1000,
    2
)

# ============================================================
# TOKEN USAGE
# ============================================================

usage = response_json.get(
    "usage",
    {}
)

# ============================================================
# SAVE METADATA
# ============================================================

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

print(
    f"\nMetadata saved to:\n"
    f"{metadata_path}"
)

# ============================================================
# SAVE PROBLEM LOG
# ============================================================

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

print(
    f"\nProblem log saved to:\n"
    f"{problem_log_path}"
)

# ============================================================
# SUMMARY
# ============================================================

print(
    "\n========== EXECUTION SUMMARY ==========\n"
)

print(
    "Execution time (milliseconds):",
    execution_time_ms
)

print(
    "Prompt tokens:",
    usage.get("prompt_tokens")
)

print(
    "Completion tokens:",
    usage.get("completion_tokens")
)

print(
    "Total tokens:",
    usage.get("total_tokens")
)

print(
    "Reasoning tokens:",
    usage.get("reasoning_tokens")
)

print(
    "Resolution context requirements:",
    len(resolution_context)
)

print("\nProblems detected:")

if len(problems_detected) == 0:

    print("None")

else:

    for problem in problems_detected:

        print("-", problem)