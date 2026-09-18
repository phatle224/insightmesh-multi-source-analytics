"""InsightMesh API application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.errors import install_error_handlers
from api.request_id import request_id_middleware
from persistence.database import engine

app = FastAPI(title="InsightMesh", version="0.1.0")
app.middleware("http")(request_id_middleware)
install_error_handlers(app)


@app.get("/api/v1/health", response_model=None)
def health(request: Request) -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SET statement_timeout = 3000"))
            vector = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar_one()
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            if not vector or not revision:
                raise RuntimeError("Database foundation incomplete")
    except (SQLAlchemyError, RuntimeError):
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "request_id": request.state.request_id},
        )
    return JSONResponse(content={"status": "ok", "service": "backend"})
