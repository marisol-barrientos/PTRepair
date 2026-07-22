# PTRepair

This repository contains the research prototype implementation of **PTRepair (Process Tree Repair)**, introduced in the paper *Optimizing Compliance Violation Resolution in Business Process Models*, accepted for publication at **ER 2026**.

PTRepair generates, applies, and validates repair strategies for compliance violations in business process models. It combines:

- Large Language Model-based strategy generation
- Rule-based process transformations
- Behavioral, structural, and PST validation
- Support for control-flow, data, resource, and temporal requirements

The prototype is currently being extended into:

> **PC-VERA: Process Compliance Verification, Extraction, and Repair Architecture**

PC-VERA brings requirement extraction, compliance verification, and process repair together in a web-based architecture.

---

## Run the API

Install the dependencies:

```bash
pip install -r requirements.txt
```

Set the OpenRouter API key:

```bash
export OPENROUTER_API_KEY="your-api-key"
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Open the interactive API documentation:

```text
http://localhost:8000/docs
```

---

## Endpoints

### `GET /health`

Returns the current service status.

```json
{
  "status": "running",
  "version": "1.3.0"
}
```

---

### `POST /comprepair/violations`

Identifies compliance violations from an event log.

#### Input

Send a `multipart/form-data` request containing one file:

| Field | Required content |
|---|---|
| `file` | YAML event log with a `.yaml` or `.yml` extension |

The YAML file contains the event log that will be checked against the configured compliance requirements.

#### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/violations \
  -F "file=@event_log.yaml"
```

#### Output

```json
{
  "violations": [],
  "context": []
}
```

- `violations` contains requirements that were not satisfied.
- `context` contains requirements that were satisfied.

---

### `POST /comprepair/repair`

Generates, applies, and validates repair strategies.

#### Input

Send a `multipart/form-data` request containing two files:

| Field | Required content |
|---|---|
| `original_pst` | Original Process Structured Tree as an `.xml` file |
| `compliance_result` | Compliance verification result as a UTF-8 `.json` file |

The `original_pst` file contains the process model to repair.

```xml
<?xml version="1.0" encoding="utf-8"?>
<process>
  ...
</process>
```

The `compliance_result` file must contain a JSON object with two arrays:

```json
{
  "violations": [
    {
      "requirement_id": "R2",
      "requirement": "Example violated requirement",
      "assurance": 80,
      "evidence": []
    }
  ],
  "context": [
    {
      "requirement_id": "R1",
      "requirement": "Example satisfied requirement",
      "assurance": 100
    }
  ]
}
```

The file may contain the complete JSON response returned by `/comprepair/violations`:

```json
{
  "violations": [...],
  "context": [...]
}
```

Additional top-level fields are accepted, but `violations` and `context` must both be present as arrays.

#### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/repair \
  -F "original_pst=@process.xml" \
  -F "compliance_result=@compliance_result.json"
```

#### Output

```json
{
  "resolution_strategies": [
    {
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "change_operations": []
    }
  ],
  "results": [
    {
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "pst_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>...",
      "validation": {
        "behavioral_validator": "success",
        "pst_validator": "success",
        "structural_validator": "success",
        "warnings": []
      },
      "failed_operation": null,
      "error_type": null,
      "error_message": null,
      "log": "..."
    }
  ]
}
```

Validation outcomes are reported explicitly through:

```json
{
  "behavioral_validator": "success",
  "pst_validator": "success",
  "structural_validator": "success"
}
```

If a validator reports a warning, its value changes to `"warning"` and the details are included in `validation.warnings`.

If a strategy cannot be applied:

- `pst_xml` is `null`
- `failed_operation` may identify the operation that failed
- `error_type` contains the exception type
- `error_message` contains the error description
- validator values remain `"not_executed"`

For applied strategies, `pst_xml` contains the repaired PST as a UTF-8 XML string.

Each strategy is applied independently to a fresh copy of the original PST. An error in one strategy does not stop the remaining strategies.

The endpoint returns JSON. Repaired PSTs can be displayed or downloaded by the web interface.

---

## Error Responses

Typical HTTP status codes:

- `400`: invalid file or input content
- `422`: required multipart field is missing
- `500`: unexpected server error
- `502`: external strategy-generation request failed

Example:

```json
{
  "detail": "The original PST must be an XML file."
}
```

---

## Current Status

The repository is under active development as part of the PC-VERA demonstration architecture.