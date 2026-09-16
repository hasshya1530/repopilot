from fastapi import FastAPI

app = FastAPI(
    title="RepoPilot API",
    version="0.1.0",
    description="Backend API for RepoPilot.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "repopilot-api",
    }
