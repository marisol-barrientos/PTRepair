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

Open the API documentation at:

```text
http://localhost:8000/docs
```

---

## Endpoints

### `GET /health`

Returns the service status.

```json
{
  "status": "running",
  "version": "1.3.0"
}
```

---

### `POST /comprepair/violations`

Identifies compliance violations from a YAML event log.

#### Input

`multipart/form-data`

| Field | Description |
|---|---|
| `file` | YAML event log (`.yaml` or `.yml`) |

#### Example

```bash
curl -X POST \
  http://localhost:8000/comprepair/violations \
  -F "file=@event_log.yaml"
```

#### Output

```json
{
  "status": "success",
  "violations": ["..."],
  "context": ["..."]
}
```

---

### `POST /comprepair/repair`

Generates, applies, and validates repair strategies.

#### Input

`multipart/form-data`

| Field | Description |
|---|---|
| `original_pst` | Original PST XML file (`.xml`) |
| `compliance_result` | UTF-8 compliance-result file (`.json`) |

Expected JSON structure:

```json
{
  "violations": ["..."],
  "context": ["..."]
}
```

#### Example

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
      "change_operations": ["..."]
    }
  ],
  "results": [
    {
      "requirement_id": "R2",
      "resolution_strategy_id": "R2_RS1",
      "status": "success",
      "pst_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>...",
      "validation": {
        "status": "success",
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

Possible result statuses:

- `success`: strategy applied and validation passed
- `warning`: strategy applied, but validation produced warnings
- `error`: strategy could not be applied

Each strategy is applied to a fresh copy of the original PST. An error in one strategy does not stop the remaining strategies.

The endpoint returns JSON. Repaired PSTs are included as UTF-8 XML strings and can be displayed or downloaded directly in JavaScript.

---

## Error Responses

Typical responses:

- `400`: invalid file or input data
- `422`: missing multipart field
- `500`: unexpected server error
- `502`: external strategy-generation failure

Example:

```json
{
  "detail": "The original PST must be an XML file."
}
```

---

## Current Status

The repository is under active development. Ongoing work includes frontend integration, documentation, deployment configuration, examples, and demonstration scenarios.