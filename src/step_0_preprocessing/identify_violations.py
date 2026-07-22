import io
import json
import re
from collections import defaultdict
from typing import BinaryIO, Union

import yaml


def identify_violations(log_source: Union[str, BinaryIO]) -> dict:
    """
    Identify failed and compliant requirements from a YAML event log.

    Parameters
    ----------
    log_source : str | BinaryIO
        Either:
        - path to a .xes.yaml log file
        - a binary file object, such as FastAPI UploadFile.file

    Returns
    -------
    dict
        Dictionary containing:
        - violations: failed requirements with assurance and evidence
        - context: compliant requirements with ID, description, and assurance
    """

    requirements = defaultdict(
        lambda: {
            "requirement_id": None,
            "requirement": None,
            "assurance": None,
            "result": None,
            "evidence": [],
        }
    )

    # -------------------------------------------------------
    # Open the input depending on its type
    # -------------------------------------------------------
    if isinstance(log_source, str):
        stream = open(log_source, "r", encoding="utf-8")
    else:
        # FastAPI UploadFile.file is normally binary.
        stream = io.TextIOWrapper(log_source, encoding="utf-8")

    with stream as f:
        documents = yaml.safe_load_all(f)

        for doc in documents:
            if not doc or "event" not in doc:
                continue

            event = doc["event"]
            req_id = event.get("concept:instance")

            # Ignore events without a requirement ID.
            if not req_id:
                continue

            # Ignore preprocessing events.
            if req_id == "preprocessing":
                continue

            req = requirements[req_id]
            req["requirement_id"] = req_id

            lifecycle = event.get("lifecycle:transition", "")
            data = event.get("data", "")

            # Ensure data can be processed safely.
            if data is None:
                data = ""
            elif not isinstance(data, str):
                data = str(data)

            # -------------------------------------------------------
            # Requirement start
            # -------------------------------------------------------
            if lifecycle == "start":
                match = re.match(
                    r"Verifying Requirement\s+\S+:\s*(.*)",
                    data,
                )

                if match:
                    req["requirement"] = match.group(1).strip()

            # -------------------------------------------------------
            # Requirement completion
            # -------------------------------------------------------
            elif lifecycle == "complete":
                match = re.search(
                    r"Requirement\s+\S+\s+is\s+(True|False)"
                    r"\s+with assurance level\s+(\d+)",
                    data,
                )

                if match:
                    req["result"] = match.group(1) == "True"
                    req["assurance"] = int(match.group(2))

            # -------------------------------------------------------
            # Intermediate evidence
            # -------------------------------------------------------
            else:
                req["evidence"].append(data)

    # -------------------------------------------------------
    # Separate failed and compliant requirements
    # -------------------------------------------------------
    violations = []
    context = []

    for req in requirements.values():
        if req["result"] is False:
            violations.append(
                {
                    "requirement_id": req["requirement_id"],
                    "requirement": req["requirement"],
                    "assurance": req["assurance"],
                    "evidence": req["evidence"],
                }
            )

        elif req["result"] is True:
            context.append(
                {
                    "requirement_id": req["requirement_id"],
                    "requirement": req["requirement"],
                    "assurance": req["assurance"],
                }
            )

    return {
        "violations": violations,
        "context": context,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Identify failed and compliant requirements from a YAML log."
        )
    )

    parser.add_argument(
        "input",
        help="Input .xes.yaml log",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="identified_violations.json",
        help="Output JSON file",
    )

    args = parser.parse_args()

    result = identify_violations(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print(
        f"Wrote {len(result['violations'])} identified violations "
        f"and {len(result['context'])} compliant requirements "
        f"to {args.output}"
    )

