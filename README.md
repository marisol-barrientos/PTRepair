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

Install dependencies:

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

Current API version:

```text
1.4.0
```

---

## Endpoints

## `GET /health`

Returns the service status and API version.

### Output

```json
{
  "status": "running",
  "version": "1.4.0"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | Current service status |
| `version` | string | API version |

---

## `POST /comprepair/violations`

Identifies compliance violations from a YAML compliance log.

### Input

Content type:

```text
multipart/form-data
```

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | yes | YAML compliance log with a `.yaml` or `.yml` extension |

### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/violations \
  -F "file=@compliance_log.yaml"
```

### Output

```json
{
  "violations": [],
  "context": []
}
```

| Field | Type | Description |
|---|---|---|
| `violations` | array | Requirements that were not satisfied |
| `context` | array | Requirements that were satisfied |

The exact fields inside each item depend on the compliance-verification component.

---

## `POST /comprepair/repair`

Generates, applies, and validates repair strategies.

### Input

Content type:

```text
multipart/form-data
```

| Field | Type | Required | Description |
|---|---|---|---|
| `original_pst` | file | yes | Original PST as an `.xml` file |
| `compliance_result` | file | yes | UTF-8 JSON file containing `violations` and `context` |

### `original_pst`

Example:

```xml
<?xml version="1.0" encoding="utf-8"?>
<process>
  ...
</process>
```

### `compliance_result`

Required structure:

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

Required top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `violations` | array | yes | Violated requirements |
| `context` | array | yes | Satisfied requirements |

Additional top-level fields are accepted.

The complete response from `/comprepair/violations` can be used directly.

### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/repair \
  -F "original_pst=@process.xml" \
  -F "compliance_result=@compliance_result.json"
```

---

## Generated Resolution Strategy

Before application, each generated strategy must contain:

```json
{
  "requirement_id": "R2",
  "resolution_strategy_id": "R2_RS1",
  "change_description": "Insert a review activity after approval.",
  "change_risk": {
    "value": "low",
    "reason": "The change adds one activity without restructuring the surrounding control flow."
  },
  "change_operations": [
    {
      "operation": "insert_after",
      "parameters": {
        "target_activity_label": "Approve request",
        "new_activity_label": "Review approval"
      }
    }
  ]
}
```

### Strategy fields

| Field | Type | Required | Description |
|---|---|---|---|
| `requirement_id` | string | yes | Identifier of the violated requirement |
| `resolution_strategy_id` | string | yes | Unique strategy identifier |
| `change_description` | string | yes | Summary of the proposed process change |
| `change_risk` | object | yes | Risk level and explanation |
| `change_operations` | array | yes | Ordered process-change operations |

### `change_risk`

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `value` | string | yes | `very_low`, `low`, `medium`, `high`, `very_high` |
| `reason` | string | yes | Non-empty explanation |

### `change_operations`

Each operation must contain:

| Field | Type | Required | Description |
|---|---|---|---|
| `operation` | string | yes | Supported operation name |
| `parameters` | object | yes | Parameters required by that operation |

Parameter names depend on the selected operation.

Each `resolution_strategy_id` must be unique within one repair request.

---

## Repair Output

The endpoint returns:

```json
{
  "resolution_strategies": [
    {
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "change_description": "Insert a review activity after approval.",
      "change_risk": {
        "value": "low",
        "reason": "The change adds one activity without restructuring the surrounding control flow."
      },
      "change_operations": [
        {
          "operation": "insert_after",
          "parameters": {
            "target_activity_label": "Approve request",
            "new_activity_label": "Review approval"
          }
        }
      ],
      "status": "success",
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

### Top-level field

| Field | Type | Description |
|---|---|---|
| `resolution_strategies` | array | Generated strategies combined with application and validation results |

### Result fields

| Field | Type | Description |
|---|---|---|
| `requirement_id` | string | Identifier of the violated requirement |
| `resolution_strategy_id` | string | Unique strategy identifier |
| `change_description` | string | Summary of the proposed repair |
| `change_risk` | object | Risk value and explanation |
| `change_operations` | array | Ordered operations used for the repair |
| `status` | string | `success`, `warning`, or `error` |
| `pst_xml` | string or null | Repaired PST as UTF-8 XML |
| `validation` | object | Validator statuses and warning messages |
| `failed_operation` | string or null | Operation that failed |
| `error_type` | string or null | Exception type |
| `error_message` | string or null | Error description |
| `log` | string | In-memory processing log |

### `validation`

| Field | Type | Possible values |
|---|---|---|
| `behavioral_validator` | string | `success`, `warning`, `not_executed` |
| `pst_validator` | string | `success`, `warning`, `not_executed` |
| `structural_validator` | string | `success`, `warning`, `not_executed` |
| `warnings` | array | Validation warning messages |

---

## Result Statuses

### `success`

The strategy was applied and all validators completed without warnings.

```json
{
  "status": "success",
  "pst_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>...",
  "validation": {
    "behavioral_validator": "success",
    "pst_validator": "success",
    "structural_validator": "success",
    "warnings": []
  },
  "failed_operation": null,
  "error_type": null,
  "error_message": null
}
```

### `warning`

The strategy was applied and `pst_xml` was generated, but at least one validator reported a warning.

```json
{
  "status": "warning",
  "pst_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>...",
  "validation": {
    "behavioral_validator": "warning",
    "pst_validator": "success",
    "structural_validator": "success",
    "warnings": [
      "BehavioralValidator: Example validation warning"
    ]
  },
  "failed_operation": null,
  "error_type": null,
  "error_message": null
}
```

### `error`

The strategy could not be applied.

```json
{
  "status": "error",
  "pst_xml": null,
  "validation": {
    "behavioral_validator": "not_executed",
    "pst_validator": "not_executed",
    "structural_validator": "not_executed",
    "warnings": []
  },
  "failed_operation": "insert_after",
  "error_type": "ValueError",
  "error_message": "Target activity was not found."
}
```

For error results:

- `pst_xml` is `null`.
- `failed_operation` may contain the failed operation name.
- `error_type` contains the exception type.
- `error_message` contains the error description.
- validator statuses remain `not_executed`.

---

## Processing Behavior

The repair pipeline:

1. validates the PST and compliance result;
2. generates resolution strategies;
3. validates the strategy schema;
4. applies each strategy to a fresh PST copy;
5. runs behavioral, PST, and structural validation;
6. converts repaired PST bytes to UTF-8 strings;
7. returns all strategy results as JSON.

No generated strategies, repaired PSTs, or logs are written to disk.

---

## Error Responses

| HTTP status | Meaning |
|---|---|
| `400` | Invalid file extension, empty file, malformed JSON, invalid input, or invalid strategy schema |
| `422` | Required multipart field is missing |
| `500` | Unexpected server or processing error |
| `502` | External strategy-generation request failed |

Example:

```json
{
  "detail": "The original PST must be an XML file."
}
```

```json
{
  "detail": "The compliance result is not valid JSON. Line 4, column 2: Expecting property name enclosed in double quotes"
}
```

---

## Current Status

The repository is under active development as part of the PC-VERA demonstration architecture.
