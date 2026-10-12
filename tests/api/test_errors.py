"""HTTP error contract."""

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from nexo_ai.api.middleware.correlation import CORRELATION_ID_HEADER
from nexo_ai.api.schemas.problem import ProblemDetails
from nexo_ai.main import create_app
from tests.conftest import build_settings


def _app_with_probe_routes() -> FastAPI:
    app = create_app(build_settings())

    @app.get("/__test__/items/{item_id}")
    def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @app.get("/__test__/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("token=super-secret")

    @app.get("/__test__/structured-error")
    def structured_error() -> dict[str, str]:
        raise HTTPException(status_code=400, detail=cast(str, {"reason": "hidden"}))

    return app


def test_unknown_route_is_a_problem_document() -> None:
    app = create_app(build_settings())
    with TestClient(app) as client:
        response = client.get("/missing", headers={CORRELATION_ID_HEADER: "missing-1"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = ProblemDetails.model_validate(response.json())
    assert problem.status == 404
    assert problem.title == "Not Found"
    assert problem.instance == "/missing"
    assert problem.correlation_id == "missing-1"
    assert "Traceback" not in response.text


def test_validation_error_omits_the_rejected_input() -> None:
    app = _app_with_probe_routes()
    with TestClient(app) as client:
        response = client.get("/__test__/items/not-a-number")
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    payload = response.json()
    problem = ProblemDetails.model_validate(payload)
    assert problem.detail == "A requisição é inválida."
    assert problem.errors is not None
    assert problem.errors[0].loc[-1] == "item_id"
    assert "input" not in payload["errors"][0]
    assert "Traceback" not in response.text


def test_non_text_http_error_uses_a_generic_detail() -> None:
    app = _app_with_probe_routes()
    with TestClient(app) as client:
        response = client.get("/__test__/structured-error")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "A requisição não pôde ser processada."
    assert "hidden" not in response.text


def test_unhandled_exception_does_not_expose_the_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app_with_probe_routes()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test__/boom", headers={CORRELATION_ID_HEADER: "boom-1"})
    captured = capsys.readouterr()
    logs = captured.out + captured.err
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = ProblemDetails.model_validate(response.json())
    assert problem.detail == "Ocorreu um erro interno."
    assert problem.correlation_id == "boom-1"
    assert "super-secret" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
    assert "super-secret" not in logs
    assert "Traceback" not in logs
    assert '"error_type": "RuntimeError"' in logs
