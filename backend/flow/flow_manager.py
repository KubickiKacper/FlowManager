import logging
from collections.abc import Callable

from .statuses import Status, FailResult
from .task.fetch_data import FetchData
from .task.process_data import ProcessData
from .task.store_data import StoreData
from .task.task import Task

logger = logging.getLogger(__name__)

FlowEventHandler = Callable[[str, dict], None]


class FlowManager:
    def __init__(
        self,
        flow_id: str = "flow123",
        name: str = "Data processing flow",
        tasks: list[Task] | None = None,
        conditions: list[bool] | None = None,
        fail_result: list[FailResult] | None = None,
        event_handler: FlowEventHandler | None = None,
    ):
        self.id = flow_id
        self.name = name
        self._event_handler = event_handler
        self.tasks = tasks or [FetchData(), ProcessData(), StoreData()]
        if not self.tasks:
            raise ValueError("Flow must contain at least one task")

        expected_transitions = len(self.tasks) - 1
        self.conditions = (
            conditions if conditions is not None else [True] * expected_transitions
        )
        self.fail_result = (
            fail_result
            if fail_result is not None
            else [FailResult.END] * expected_transitions
        )

        if len(self.conditions) != expected_transitions:
            raise ValueError(
                "conditions length must match number of task transitions"
            )
        if len(self.fail_result) != expected_transitions:
            raise ValueError(
                "fail_result length must match number of task transitions"
            )

    def _emit_event(self, event: str, **payload):
        if self._event_handler is None:
            return
        self._event_handler(event, payload)

    def _is_task_success(self, status) -> bool:
        if isinstance(status, Status):
            return status == Status.SUCCESS
        return bool(status)

    def _get_failure_target(self, index: int) -> str:
        if self.fail_result[index] is FailResult.END:
            return "end"
        elif self.fail_result[index] is FailResult.FORWARD:
            return self.tasks[index + 1].name
        return "end"

    def _build_completed_flow_payload(self, outcomes) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_task": self.tasks[0].name,
            "tasks": [{"name": task.name, "description": task.description} for task in self.tasks],
            "conditions": [
                {
                    "name": f"condition_{self.tasks[index].name}_result",
                    "description": (
                        f"Evaluate the result of {self.tasks[index].name}. "
                        f"If {'successful' if self.conditions[index] else 'failed'}, "
                        f"proceed to {self.tasks[index + 1].name}; "
                        f"otherwise, {self.fail_result[index].value}."
                    ),
                    "source_task": self.tasks[index].name,
                    "outcome": outcomes[index],
                    "target_task_success": self.tasks[index + 1].name,
                    "target_task_failure": self._get_failure_target(index)
                } for index, condition in enumerate(self.conditions)]
        }

    async def run(self) -> dict | None:
        self._emit_event("flow_started")

        outcomes = []
        for index, task in enumerate(self.tasks):
            self._emit_event("task_started", index=index, task_name=task.name)
            status = await task.execute()
            is_success = self._is_task_success(status)
            self._emit_event(
                "task_finished",
                index=index,
                task_name=task.name,
                status=getattr(status, "value", str(status)),
                success=is_success,
            )

            outcomes.append(status)

            if index >= len(self.conditions):
                continue

            expected_success = self.conditions[index]
            condition_passed = is_success == expected_success
            self._emit_event(
                "condition_evaluated",
                index=index,
                source_task=task.name,
                passed=condition_passed,
                expected_result="successful" if expected_success else "failed",
                actual_result="successful" if is_success else "failed",
            )

            if condition_passed:
                continue

            fail_result = self.fail_result[index]
            if fail_result is FailResult.FORWARD:
                logger.warning(
                    "Condition failed after %s, moving to next task", task.name
                )
                continue

            logger.error("Condition failed after %s", task.name)
            self._emit_event(
                "flow_failed",
                index=index,
                task_name=task.name,
                error=f"Condition failed after {task.name}",
            )
            return None

        logger.info("Flow completed")
        flow_payload = self._build_completed_flow_payload(outcomes)
        self._emit_event("flow_completed", payload=flow_payload)

        return flow_payload
