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

Returns the current service status and API version.

#### Example response

```json
{
  "status": "running",
  "version": "1.4.0"
}
```

---

### `POST /comprepair/violations`

Identifies compliance violations from a compliance log.

#### Input

Send a `multipart/form-data` request containing one file:

| Field | Required content |
|---|---|
| `file` | YAML compliance log with a `.yaml` or `.yml` extension |

#### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/violations \
  -F "file=@compliance_log.yaml"
```

#### Output

The endpoint returns a JSON object with two arrays:

```json
{
  "violations": [],
  "context": []
}
```

- `violations` contains requirements that were not satisfied.
- `context` contains requirements that were satisfied.

The exact fields inside each violation or context item depend on the compliance-verification component.

---

### `POST /comprepair/repair`

Generates, applies, and validates repair strategies.

Each generated strategy is applied independently to a fresh in-memory copy of the original PST. A failure in one strategy does not stop the remaining strategies.

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

The `compliance_result` file must contain a JSON object with both `violations` and `context` arrays:

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

The complete JSON response returned by `/comprepair/violations` can be used directly:

```json
{
  "violations": ["..."],
  "context": ["..."]
}
```

Additional top-level fields are accepted, but:

- `violations` must be present and must be an array.
- `context` must be present and must be an array.
- The JSON file must use UTF-8 encoding.

#### Example request

```bash
curl -X POST \
  http://localhost:8000/comprepair/repair \
  -F "original_pst=@process.xml" \
  -F "compliance_result=@compliance_result.json"
```

---

## Resolution Strategy Schema

The strategy-generation component produces resolution strategies with the following structure:

```json
{
  "resolution_strategies": [
    {
      "requirement_id": "Identifier of the violated requirement.",
      "resolution_strategy_id": "Unique identifier of the resolution strategy.",
      "change_description": "Brief summary of the proposed process changes.",
      "change_risk": {
        "value": "very_low",
        "reason": "Explanation of the assigned risk level and its possible impact."
      },
      "change_operations": [
        {
          "operation": "Name of the change operation.",
          "parameters": {
            "parameter_name": "Parameter value required by the operation."
          }
        }
      ]
    }
  ]
}
```

`change_risk.value` must be one of:

```text
very_low
low
medium
high
very_high
```

Each `resolution_strategy_id` must be unique within one repair request.

Every change operation must contain:

- `operation`: a supported operation name
- `parameters`: an object containing the parameters required by that operation

The required parameter names depend on the selected operation.

---

## Repair Output

The endpoint returns one JSON object containing a `resolution_strategies` array.

Each item combines the generated resolution strategy with its application and validation result.

#### Example successful result

```json
{
  "resolution_strategies": [
    {
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "change_description": "Insert a review activity after the approval activity.",
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

Each result can contain the following fields:

| Field | Description |
|---|---|
| `requirement_id` | Identifier of the violated requirement |
| `resolution_strategy_id` | Unique identifier of the strategy |
| `change_description` | Summary of the proposed repair |
| `change_risk` | Assigned risk value and explanation |
| `change_operations` | Ordered operations used to repair the PST |
| `status` | Overall result: `success`, `warning`, or `error` |
| `pst_xml` | Repaired PST as a UTF-8 XML string, or `null` |
| `validation` | Individual validator outcomes and warnings |
| `failed_operation` | Name of the operation that failed, when available |
| `error_type` | Exception type for an application failure |
| `error_message` | Description of the application failure |
| `log` | Text log for the strategy |

---

## Result Statuses

### `success`

The strategy was applied and all validators completed without warnings.

```json
{
  "status": "success",
  "validation": {
    "behavioral_validator": "success",
    "pst_validator": "success",
    "structural_validator": "success",
    "warnings": []
  }
}
```

### `warning`

The strategy was applied and a repaired PST was generated, but one or more validators reported warnings.

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
  }
}
```

Results with warnings still contain `pst_xml`.

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
  "error_message": "Target activity was not found.",
  "log": "..."
}
```

For failed strategies:

- `status` is `error`.
- `pst_xml` is `null`.
- `failed_operation` may identify the operation that failed.
- `error_type` contains the exception type.
- `error_message` contains the error description.
- Validator values remain `not_executed`.

---

## Processing Behavior

The repair pipeline performs the following steps:

1. Validate the original PST input.
2. Validate the compliance result.
3. Generate resolution strategies.
4. Validate the complete resolution-strategy schema.
5. Apply each strategy to a fresh copy of the original PST.
6. Run behavioral, PST, and structural validation.
7. Combine the original strategy metadata with the application result.
8. Convert repaired PST bytes to UTF-8 strings for the API response.

All processing is performed in memory. The repair pipeline does not write generated strategies, repaired PSTs, or logs to disk.

The endpoint returns JSON. Repaired PST strings can be displayed directly or saved as XML files by a client application.

---

## Error Responses

Typical HTTP status codes:

- `400`: invalid file extension, malformed input, invalid schema, or unsupported content
- `422`: a required multipart field is missing
- `500`: unexpected server or processing error
- `502`: external strategy-generation request failed

#### Example

```json
{
  "detail": "The original PST must be an XML file."
}
```

Other input errors may include:

```json
{
  "detail": "The compliance result field 'violations' must be a list."
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