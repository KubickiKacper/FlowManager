from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from flow.statuses import FailResult
from flow.flow_manager import FlowManager
from flow.flow_tracker import flow_tracker
from endpoints.utils import TASK_REGISTRY, FAIL_RESULT_REGISTRY

router = APIRouter(prefix="/flow", tags=["flow"])


class FlowRunRequest(BaseModel):
    flow_id: str = "flow123"
    name: str = "Data processing flow"
    tasks: list[str] = Field(
        default_factory=lambda: ["FetchData", "ProcessData", "StoreData"]
    )
    conditions: list[bool] = Field(default_factory=lambda: [True, True])
    fail_result: list[str] = Field(default_factory=lambda: ["END", "END"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flow_id": "flow123",
                "name": "Data processing flow",
                "tasks": ["FetchData", "ProcessData", "StoreData"],
                "conditions": [True, True],
                "fail_result": ["END", "END"],
            }
        }
    )


def _normalize_task_name(task_name: str) -> str:
    normalized = task_name.strip()
    if normalized.endswith("()"):
        normalized = normalized[:-2]
    return normalized.replace("_", "").replace(" ", "").lower()


def _normalize_fail_result(fail_result: str) -> str:
    normalized = fail_result.strip()
    if normalized.startswith("FailResult."):
        normalized = normalized.split(".", 1)[1]
    return normalized.replace("_", "").replace(" ", "").upper()


def _build_tasks(task_names: list[str]) -> list:
    tasks = []
    for task_name in task_names:
        task_cls = TASK_REGISTRY.get(_normalize_task_name(task_name))
        if task_cls is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported task '{task_name}'",
            )
        tasks.append(task_cls())
    return tasks


def _build_fail_results(fail_results: list[str]) -> list[FailResult]:
    parsed = []
    for fail_result in fail_results:
        parsed_result = FAIL_RESULT_REGISTRY.get(
            _normalize_fail_result(fail_result)
        )
        if parsed_result is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported fail_result '{fail_result}'",
            )
        parsed.append(parsed_result)
    return parsed


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Flow executed successfully"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Flow execution failed"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid flow configuration"
        },
    },
)
async def run_flow(
        payload: FlowRunRequest = Body(default=FlowRunRequest()),
):
    def _event_handler(event: str, event_payload: dict):
        flow_tracker.handle_event(payload.flow_id, event, event_payload)

    flow_kwargs = {
        "flow_id": payload.flow_id,
        "name": payload.name,
        "tasks": _build_tasks(payload.tasks),
        "conditions": payload.conditions,
        "fail_result": _build_fail_results(payload.fail_result),
        "event_handler": _event_handler,
    }

    try:
        flow_manager = FlowManager(**flow_kwargs)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    flow_tracker.initialize_flow(
        flow_id=flow_manager.id,
        name=flow_manager.name,
        tasks=flow_manager.tasks,
        conditions=flow_manager.conditions,
        fail_result=flow_manager.fail_result,
    )

    try:
        flow_response = await flow_manager.run()
    except Exception as exc:
        flow_tracker.mark_failed(flow_manager.id, str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"flow_id": flow_manager.id, "status": "failed"},
        )

    if flow_response is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"flow_id": flow_manager.id, "status": "failed"},
        )
    return flow_response


@router.get(
    "/{flow_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Tracked flow details"},
        status.HTTP_404_NOT_FOUND: {"description": "Flow not found"},
    },
)
async def get_flow(flow_id: str):
    flow_data = flow_tracker.get_flow(flow_id)
    if flow_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow '{flow_id}' not found",
        )
    return flow_data
