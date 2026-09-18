from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.errors import AppError, install_error_handlers
from api.request_id import request_id_middleware
from api.settings import LOCAL_ENCRYPTION_KEY, Settings


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)

    @app.get("/known-error")
    def known_error() -> None:
        raise AppError("not_ready", "Resource is not ready", status_code=409)

    @app.get("/unexpected-error")
    def unexpected_error() -> None:
        raise RuntimeError("secret internal context")

    return app


def test_request_id_is_preserved_for_safe_client_value() -> None:
    client = TestClient(build_test_app())
    response = client.get("/known-error", headers={"X-Request-ID": "client-request-123"})

    assert response.status_code == 409
    assert response.headers["X-Request-ID"] == "client-request-123"
    assert response.json() == {
        "error": {
            "code": "not_ready",
            "message": "Resource is not ready",
            "retryable": False,
        },
        "request_id": "client-request-123",
    }


def test_unsafe_request_id_is_replaced() -> None:
    client = TestClient(build_test_app())
    response = client.get("/known-error", headers={"X-Request-ID": "unsafe value\n"})

    assert response.headers["X-Request-ID"] != "unsafe value\n"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_unexpected_error_does_not_leak_exception_message() -> None:
    client = TestClient(build_test_app(), raise_server_exceptions=False)
    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal context" not in response.text


def test_production_rejects_local_encryption_key() -> None:
    try:
        Settings(
            APP_ENV="production",
            PGHOST="db",
            PGPORT=5432,
            PGDATABASE="app",
            PGUSER="app",
            PGPASSWORD="password",
            CREDENTIAL_ENCRYPTION_KEY=LOCAL_ENCRYPTION_KEY,
        )
    except ValueError as exc:
        assert "local credential encryption key" in str(exc)
    else:
        raise AssertionError("Production accepted the documented local-only encryption key")
