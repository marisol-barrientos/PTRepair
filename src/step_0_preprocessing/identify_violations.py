import io
import json
import re
import yaml
from collections import defaultdict


def identify_violations(log_source):
    """
    Identify failed compliance requirements from a YAML event log.

    Parameters
    ----------
    log_source : str | BinaryIO
        Either:
        - path to a .xes.yaml log file
        - a binary file object (e.g. FastAPI UploadFile.file)

    Returns
    -------
    list
        List of failed requirements.
    """

    requirements = defaultdict(lambda: {
        "requirement_id": None,
        "requirement": None,
        "assurance": None,
        "result": None,
        "evidence": []
    })

    # -------------------------------------------------------
    # Open the input depending on its type
    # -------------------------------------------------------
    if isinstance(log_source, str):
        stream = open(log_source, "r", encoding="utf-8")
    else:
        # FastAPI UploadFile.file is binary
        stream = io.TextIOWrapper(log_source, encoding="utf-8")

    with stream as f:
        documents = yaml.safe_load_all(f)

        for doc in documents:
            if not doc or "event" not in doc:
                continue

            event = doc["event"]

            req_id = event.get("concept:instance")

            # Ignore preprocessing events
            if req_id == "preprocessing":
                continue

            req = requirements[req_id]
            req["requirement_id"] = req_id

            lifecycle = event.get("lifecycle:transition", "")
            data = event.get("data", "")

            # -------------------------------------------------------
            # Requirement start
            # -------------------------------------------------------
            if lifecycle == "start":
                m = re.match(
                    r"Verifying Requirement\s+\S+:\s*(.*)",
                    data
                )
                if m:
                    req["requirement"] = m.group(1).strip()

            # -------------------------------------------------------
            # Requirement completion
            # -------------------------------------------------------
            elif lifecycle == "complete":
                m = re.search(
                    r"Requirement\s+\S+\s+is\s+(True|False)\s+with assurance level\s+(\d+)",
                    data
                )
                if m:
                    req["result"] = (m.group(1) == "True")
                    req["assurance"] = int(m.group(2))

            # -------------------------------------------------------
            # Intermediate evidence
            # -------------------------------------------------------
            else:
                req["evidence"].append(data)

    # -------------------------------------------------------
    # Keep only failed requirements
    # -------------------------------------------------------
    output = []

    for req in requirements.values():
        if req["result"] is False:
            output.append({
                "requirement_id": req["requirement_id"],
                "requirement": req["requirement"],
                "assurance": req["assurance"],
                "evidence": req["evidence"],
            })

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Identify failed compliance requirements from a YAML log."
    )

    parser.add_argument(
        "input",
        help="Input .xes.yaml log"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="identified_violations.json",
        help="Output JSON file"
    )

    args = parser.parse_args()

    failed = identify_violations(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            failed,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"Wrote {len(failed)} identified violations to {args.output}")