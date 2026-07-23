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
# INPUT HELPERS
# ============================================================

def parse_compliance_result(
    content: bytes,
) -> dict[str, Any]:
    """
    Decode an uploaded UTF-8 JSON compliance result.

    Structural validation of ``violations`` and ``context`` is owned
    by the repair pipeline.
    """

    if not content.strip():
        raise ValueError(
            "The compliance result file is empty."
        )

    try:
        result = json.loads(
            content.decode("utf-8")
        )

    except UnicodeDecodeError as error:
        raise ValueError(
            "The compliance result must use UTF-8 encoding."
        ) from error

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

    return result


def require_extension(
    upload: UploadFile,
    allowed_extensions: tuple[str, ...],
    error_message: str,
) -> None:
    """
    Validate an uploaded filename extension.
    """

    filename = (
        upload.filename or ""
    ).lower()

    if not filename.endswith(
        allowed_extensions
    ):
        raise HTTPException(
            status_code=400,
            detail=error_message,
        )


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
    """

    require_extension(
        upload=file,
        allowed_extensions=(
            ".yaml",
            ".yml",
        ),
        error_message=(
            "The uploaded event log must be a YAML file."
        ),
    )

    try:
        file_content = await file.read()

        if not file_content.strip():
            raise ValueError(
                "The uploaded event log is empty."
            )

        result = await run_in_threadpool(
            identify_violations,
            io.BytesIO(file_content),
        )

        return JSONResponse(
            content={
                "violations": result.get(
                    "violations",
                    [],
                ),
                "context": result.get(
                    "context",
                    [],
                ),
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

    Returns:

    {
        "resolution_strategies": [...]
    }

    Each strategy result may include:

    - requirement_id
    - resolution_strategy_id
    - change_description
    - change_risk
    - change_operations
    - status
    - pst_xml
    - validation
    - failed_operation
    - error_type
    - error_message
    - log
    """

    require_extension(
        upload=original_pst,
        allowed_extensions=(
            ".xml",
        ),
        error_message=(
            "The original PST must be an XML file."
        ),
    )

    require_extension(
        upload=compliance_result,
        allowed_extensions=(
            ".json",
        ),
        error_message=(
            "The compliance result must be a JSON file."
        ),
    )

    try:
        pst_bytes = await original_pst.read()

        if not pst_bytes.strip():
            raise ValueError(
                "The uploaded PST is empty."
            )

        compliance_data = parse_compliance_result(
            await compliance_result.read()
        )

        repair_result = await run_in_threadpool(
            partial(
                repair,
                original_pst=pst_bytes,
                compliance_result=compliance_data,
            )
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