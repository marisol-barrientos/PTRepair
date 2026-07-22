from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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

            <h3>Available endpoint</h3>

            <ul>
                <li>POST /comprepair/identify-violations</li>
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
    return {"status": "running"}


@app.post("/comprepair/violations")
async def identify_endpoint(
    file: UploadFile = File(...)
):
    """
    Upload a .xes.yaml event log and identify failed requirements.
    """

    try:

        violations = identify_violations(file.file)

        return JSONResponse(
            content={
                "status": "success",
                "count": len(violations),
                "violations": violations,
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