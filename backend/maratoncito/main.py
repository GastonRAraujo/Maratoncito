"""HTTP application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from . import __version__
from .api import router
from .services import get_service


class SystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    status: str
    capabilities: dict[str, bool]


app = FastAPI(title="Maratoncito API", version=__version__)
app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/system/status", response_model=SystemStatus, tags=["system"])
def system_status() -> SystemStatus:
    return SystemStatus(
        name="Maratoncito",
        version=__version__,
        status="p1-development",
        capabilities=get_service().capabilities(),
    )


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    @app.get("/", include_in_schema=False)
    def homepage() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")
