from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock

from flow.statuses import FailResult
from flow.task.task import Task


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FlowTracker:
    def __init__(self):
        self._flows: dict[str, dict] = {}
        self._lock = RLock()

    def initialize_flow(
        self,
        flow_id: str,
        name: str,
        tasks: list[Task],
        conditions: list[bool],
        fail_result: list[FailResult],
    ):
        now = _utc_now_iso()
        flow_data = {
            "id": flow_id,
            "name": name,
            "status": "pending",
            "created_at": now,
            "started_at": None,
            "updated_at": now,
            "finished_at": None,
            "current_task": None,
            "tasks": [
                {
                    "name": task.name,
                    "description": task.description,
                    "status": "pending",
                }
                for task in tasks
            ],
            "conditions": self._build_conditions(tasks, conditions, fail_result),
            "result": None,
            "error": None,
        }

        with self._lock:
            self._flows[flow_id] = flow_data

    def handle_event(self, flow_id: str, event: str, payload: dict):
        with self._lock:
            flow = self._flows.get(flow_id)
            if flow is None:
                return

            now = _utc_now_iso()
            flow["updated_at"] = now

            if event == "flow_started":
                flow["status"] = "running"
                flow["started_at"] = flow["started_at"] or now
                return

            if event == "task_started":
                index = payload["index"]
                if 0 <= index < len(flow["tasks"]):
                    flow["tasks"][index]["status"] = "running"
                    flow["current_task"] = flow["tasks"][index]["name"]
                return

            if event == "task_finished":
                index = payload["index"]
                success = payload.get("success", False)
                if 0 <= index < len(flow["tasks"]):
                    flow["tasks"][index]["status"] = "success" if success else "failed"
                return

            if event == "condition_evaluated":
                index = payload["index"]
                passed = payload.get("passed", False)
                if 0 <= index < len(flow["conditions"]):
                    flow["conditions"][index]["status"] = (
                        "passed" if passed else "failed"
                    )
                return

            if event == "flow_failed":
                flow["status"] = "failed"
                flow["finished_at"] = now
                flow["current_task"] = None
                flow["error"] = payload.get("error", "Flow failed")
                return

            if event == "flow_completed":
                flow["status"] = "completed"
                flow["finished_at"] = now
                flow["current_task"] = None
                flow["result"] = payload.get("payload")
                flow["error"] = None

    def mark_failed(self, flow_id: str, error_message: str):
        self.handle_event(flow_id, "flow_failed", {"error": error_message})

    def get_flow(self, flow_id: str) -> dict | None:
        with self._lock:
            flow = self._flows.get(flow_id)
            if flow is None:
                return None
            return deepcopy(flow)

    @staticmethod
    def _build_conditions(
        tasks: list[Task],
        conditions: list[bool],
        fail_result: list[FailResult],
    ) -> list[dict]:
        condition_data = []
        for index, condition in enumerate(conditions):
            failure_target = "end"
            if fail_result[index] is FailResult.FORWARD and index + 1 < len(tasks):
                failure_target = tasks[index + 1].name

            condition_data.append(
                {
                    "name": f"condition_{tasks[index].name}_result",
                    "source_task": tasks[index].name,
                    "expected_result": "successful" if condition else "failed",
                    "status": "pending",
                    "target_task_success": tasks[index + 1].name,
                    "target_task_failure": failure_target,
                }
            )
        return condition_data


flow_tracker = FlowTracker()
