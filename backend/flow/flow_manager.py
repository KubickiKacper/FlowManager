import logging

from .statuses import Status, FailResult
from .task.fetch_data import FetchData
from .task.process_data import ProcessData
from .task.store_data import StoreData
from .task.task import Task

logger = logging.getLogger(__name__)


class FlowManager:
    def __init__(
        self,
        flow_id: str = "flow123",
        name: str = "Data processing flow",
        tasks: list[Task] | None = None,
        conditions: list[bool] | None = None,
        fail_result: list[FailResult] | None = None,
    ):
        self.id = flow_id
        self.name = name
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
        outcomes = []
        for index, task in enumerate(self.tasks):
            status = await task.execute()
            if status is Status.FAILED:
                if index >= len(self.fail_result):
                    logger.error("Task failed: %s", task.name)
                    return None

                fail_result = self.fail_result[index]
                if fail_result is FailResult.END:
                    logger.error("Task failed: %s", task.name)
                    return None
                if fail_result is FailResult.FORWARD:
                    logger.warning("Task failed: %s, moving to next task", task.name)

            outcomes.append(status)

            if index < len(self.conditions):
                condition = self.conditions[index]

                if not condition:
                    logger.error(
                        "Condition failed after %s", task.name
                    )
                    return None

        logger.info("Flow completed")

        return self._build_completed_flow_payload(outcomes)
