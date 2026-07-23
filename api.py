import io
import json
from functools import partial
from typing import Any

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)

from src.repair_demo import repair
from src.step_0_preprocessing.identify_violations import (
    identify_violations,
)


API_VERSION = "1.4.0"


app = FastAPI(
    title="CompRepair API",
    description="Compliance Repair Web Service",
    version=API_VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INPUT PARSING
# ============================================================

def parse_compliance_result(
    content: bytes,
) -> dict[str, Any]:
    """
    Decode and parse an uploaded compliance-result JSON file.
    """

    if not isinstance(content, bytes):
        raise TypeError(
            "The compliance result content must be provided as bytes."
        )

    if not content.strip():
        raise ValueError(
            "The compliance result file is empty."
        )

    try:
        text = content.decode("utf-8")

    except UnicodeDecodeError as error:
        raise ValueError(
            "The compliance result must use UTF-8 encoding."
        ) from error

    try:
        result = json.loads(text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The compliance result is not valid JSON. "
            f"Line {error.lineno}, column {error.colno}: "
            f"{error.msg}"
        ) from error

    if not isinstance(result, dict):
        raise TypeError(
            "The compliance result must contain a JSON object."
        )

    violations = result.get("violations")
    context = result.get("context")

    if not isinstance(violations, list):
        raise TypeError(
            "The compliance result field 'violations' must be a list."
        )

    if not isinstance(context, list):
        raise TypeError(
            "The compliance result field 'context' must be a list."
        )

    return result


# ============================================================
# BASIC ENDPOINTS
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def root() -> str:
    """
    Return a minimal service landing page.
    """

    return f"""
    <html>
        <head>
            <title>CompRepair API</title>
        </head>

        <body>
            <h2>CompRepair API</h2>

            <p><b>Status:</b> Running</p>
            <p><b>Version:</b> {API_VERSION}</p>

            <h3>Available endpoints</h3>

            <ul>
                <li>GET /health</li>
                <li>POST /comprepair/violations</li>
                <li>POST /comprepair/repair</li>
            </ul>

            <p>
                Interactive documentation:
                <a href="/docs">/docs</a>
            </p>
        </body>
    </html>
    """


@app.get("/health")
async def health() -> dict[str, str]:
    """
    Return the current API status and version.
    """

    return {
        "status": "running",
        "version": API_VERSION,
    }


# ============================================================
# VIOLATION IDENTIFICATION
# ============================================================

@app.post("/comprepair/violations")
async def identify_endpoint(
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a YAML event log and identify violations and context.

    Returns a JSON object containing:

    - violations
    - context
    """

    filename = file.filename or ""

    if not filename.lower().endswith(
        (".yaml", ".yml")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded event log must be "
                "a YAML file."
            ),
        )

    try:
        file_content = await file.read()

        if not file_content.strip():
            raise ValueError(
                "The uploaded event log is empty."
            )

        file_stream = io.BytesIO(
            file_content
        )

        result = await run_in_threadpool(
            identify_violations,
            file_stream,
        )

        if not isinstance(result, dict):
            raise TypeError(
                "Violation identification returned an invalid result."
            )

        violations = result.get(
            "violations",
            [],
        )

        context = result.get(
            "context",
            [],
        )

        if not isinstance(violations, list):
            raise TypeError(
                "Violation identification returned an invalid "
                "'violations' value."
            )

        if not isinstance(context, list):
            raise TypeError(
                "Violation identification returned an invalid "
                "'context' value."
            )

        return JSONResponse(
            content={
                "violations": violations,
                "context": context,
            },
            headers={
                "Cache-Control": "no-store",
            },
        )

    except (
        ValueError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Violation identification failed: "
                f"{error}"
            ),
        ) from error

    finally:
        await file.close()


# ============================================================
# REPAIR
# ============================================================

@app.post("/comprepair/repair")
async def repair_endpoint(
    original_pst: UploadFile = File(...),
    compliance_result: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload an original PST XML file and a compliance-result JSON file.

    Returns a JSON object containing one ``resolution_strategies``
    array.

    Each resolution strategy may contain:

    - requirement_id
    - resolution_strategy_id
    - change_description
    - change_risk
    - change_operations
    - status
    - repaired PST XML
    - validator outcomes
    - validation warnings
    - failed-operation details
    - error information
    - processing log

    Possible ``status`` values are:

    - success
    - warning
    - error

    When a repaired PST is available, ``pst_xml`` is returned as a
    UTF-8 string so it can be consumed directly by a JSON client.
    """

    pst_filename = (
        original_pst.filename or ""
    )

    result_filename = (
        compliance_result.filename or ""
    )

    if not pst_filename.lower().endswith(
        ".xml"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The original PST must be an XML file."
            ),
        )

    if not result_filename.lower().endswith(
        ".json"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The compliance result must be "
                "a JSON file."
            ),
        )

    try:
        pst_bytes = await original_pst.read()

        if not pst_bytes.strip():
            raise ValueError(
                "The uploaded PST is empty."
            )

        compliance_bytes = (
            await compliance_result.read()
        )

        compliance_data = (
            parse_compliance_result(
                compliance_bytes
            )
        )

        repair_call = partial(
            repair,
            original_pst=pst_bytes,
            compliance_result=compliance_data,
        )

        repair_result = await run_in_threadpool(
            repair_call
        )

        if not isinstance(repair_result, dict):
            raise TypeError(
                "The repair pipeline returned an invalid result."
            )

        resolution_strategies = repair_result.get(
            "resolution_strategies"
        )

        if not isinstance(
            resolution_strategies,
            list,
        ):
            raise TypeError(
                "The repair pipeline result must contain a "
                "'resolution_strategies' list."
            )

        return JSONResponse(
            content=repair_result,
            headers={
                "Cache-Control": "no-store",
            },
        )

    except (
        ValueError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Repair failed: {error}",
        ) from error

    finally:
        await original_pst.close()
        await compliance_result.close()