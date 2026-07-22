import io
import json
import zipfile
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
    StreamingResponse,
)

from src.repair_demo import repair
from src.step_0_preprocessing.identify_violations import (
    identify_violations,
)


app = FastAPI(
    title="CompRepair API",
    description="Compliance Repair Web Service",
    version="1.3.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_safe_filename(
    value: str,
) -> str:
    """
    Convert an identifier into a safe filename.
    """

    safe_value = "".join(
        character
        if (
            character.isalnum()
            or character in {"-", "_"}
        )
        else "_"
        for character in value
    )

    return safe_value.strip("_") or "unnamed"


def parse_compliance_result(
    content: bytes,
) -> dict[str, Any]:
    """
    Decode and parse an uploaded compliance-result JSON file.
    """

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

    return result


def create_repair_zip(
    repair_result: dict[str, Any],
) -> io.BytesIO:
    """
    Create the complete repair output as an in-memory ZIP archive.
    """

    zip_buffer = io.BytesIO()

    strategies = repair_result.get(
        "resolution_strategies",
        [],
    )

    results = repair_result.get(
        "results",
        [],
    )

    summary = repair_result.get(
        "summary",
        {},
    )

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "generated_resolution_strategies.json",
            json.dumps(
                {
                    "resolution_strategies": strategies,
                },
                indent=2,
                ensure_ascii=False,
            ),
        )

        archive.writestr(
            "repair_summary.json",
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False,
            ),
        )

        for result in results:
            requirement_id = str(
                result.get(
                    "requirement_id",
                    "unknown_requirement",
                )
            )

            strategy_id = str(
                result.get(
                    "resolution_strategy_id",
                    "unknown_strategy",
                )
            )

            filename = (
                f"{make_safe_filename(requirement_id)}_"
                f"{make_safe_filename(strategy_id)}"
            )

            pst_xml = result.get(
                "pst_xml"
            )

            if isinstance(pst_xml, bytes):
                archive.writestr(
                    f"psts/{filename}.xml",
                    pst_xml,
                )

            log_content = result.get(
                "log",
                "",
            )

            if not isinstance(
                log_content,
                str,
            ):
                log_content = str(
                    log_content
                )

            archive.writestr(
                f"logs/{filename}.log",
                log_content,
            )

    zip_buffer.seek(0)

    return zip_buffer


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def root():
    return """
    <html>
        <head>
            <title>CompRepair API</title>
        </head>

        <body>
            <h2>CompRepair API</h2>

            <p><b>Status:</b> Running</p>

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
async def health():
    return {
        "status": "running",
        "version": "1.3.0",
    }


@app.post("/comprepair/violations")
async def identify_endpoint(
    file: UploadFile = File(...),
):
    """
    Upload a YAML event log and identify violations and context.
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

        violations = result.get(
            "violations",
            [],
        )

        context = result.get(
            "context",
            [],
        )

        return JSONResponse(
            content={
                "status": "success",
                "violations": violations,
                "context": context,
            }
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


@app.post("/comprepair/repair")
async def repair_endpoint(
    original_pst: UploadFile = File(...),
    compliance_result: UploadFile = File(...),
):
    """
    Upload an original PST XML and a compliance-result JSON file.

    Returns an in-memory ZIP archive containing generated strategies,
    repaired PSTs, validation metrics, and logs.
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

        repair_result = await run_in_threadpool(
            repair,
            pst_bytes,
            compliance_data,
        )

        zip_buffer = create_repair_zip(
            repair_result
        )

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="comprepair_results.zip"'
                ),
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