import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import endpoints.flow as flow_endpoint
from flow.flow_tracker import flow_tracker
from flow.statuses import Status
from flow.task.task import Task
from main import app


class InstantSuccessTask(Task):
    def __init__(self):
        super().__init__(name="instant-task", description="Instant success task")

    async def execute(self):
        self.status = Status.SUCCESS
        return self.status


def _reset_flow_tracker():
    with flow_tracker._lock:
        flow_tracker._flows.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_flow_tracker():
    _reset_flow_tracker()
    yield
    _reset_flow_tracker()


def test_healthcheck_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_flow_rejects_unknown_task(client):
    response = client.post(
        "/flow/run",
        json={
            "flow_id": "flow-unknown-task",
            "tasks": ["UnknownTask"],
            "conditions": [],
            "fail_result": [],
        },
    )

    assert response.status_code == 422
    assert "Unsupported task" in response.json()["detail"]


def test_run_flow_rejects_unknown_fail_result(client):
    response = client.post(
        "/flow/run",
        json={
            "flow_id": "flow-unknown-fail-result",
            "tasks": ["FetchData", "ProcessData"],
            "conditions": [True],
            "fail_result": ["NOT_VALID"],
        },
    )

    assert response.status_code == 422
    assert "Unsupported fail_result" in response.json()["detail"]


def test_run_flow_and_get_status(client):
    flow_id = "flow-endpoint-success"
    payload = {
        "flow_id": flow_id,
        "name": "Endpoint test flow",
        "tasks": ["FastTask"],
        "conditions": [],
        "fail_result": [],
    }

    with patch.dict(flow_endpoint.TASK_REGISTRY, {"fasttask": InstantSuccessTask}):
        run_response = client.post("/flow/run", json=payload)

    assert run_response.status_code == 200
    assert run_response.json()["id"] == flow_id

    status_response = client.get(f"/flow/{flow_id}")
    assert status_response.status_code == 200

    tracked_flow = status_response.json()
    assert tracked_flow["status"] == "completed"
    assert tracked_flow["tasks"][0]["status"] == "success"
