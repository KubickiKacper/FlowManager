from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from flow.statuses import FailResult
from flow.flow_manager import FlowManager
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Invalid flow configuration"
        },
    },
)
async def run_flow(
        payload: FlowRunRequest = Body(default=FlowRunRequest()),
):
    flow_kwargs = {
        "flow_id": payload.flow_id,
        "name": payload.name,
        "tasks": _build_tasks(payload.tasks),
        "conditions": payload.conditions,
        "fail_result": _build_fail_results(payload.fail_result),
    }

    try:
        flow_manager = FlowManager(**flow_kwargs)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    flow_response = await flow_manager.run()
    if flow_response is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"flow_id": flow_manager.id, "status": "failed"},
        )
    return flow_response
