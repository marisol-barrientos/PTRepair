from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from src.step_0_preprocessing.identify_violations import identify_violations


app = FastAPI(
    title="CompRepair API",
    description="Compliance Repair Web Service",
    version="1.0.0",
)

# Allow requests from any origin.
# Restrict this list in production if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
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
    }


@app.post("/comprepair/violations")
async def identify_endpoint(
    file: UploadFile = File(...),
):
    """
    Upload a .xes.yaml event log and identify failed and compliant
    requirements.

    The response contains:

    - violations: failed requirements
    - context: compliant requirements
    """

    try:
        result = identify_violations(file.file)

        violations = result.get("violations", [])
        context = result.get("context", [])

        return JSONResponse(
            content={
                "status": "success",
                "violation_count": len(violations),
                "context_count": len(context),
                "violations": violations,
                "context": context,
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
            },
        )

    finally:
        await file.close()
