import asyncio
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from flow.flow_manager import FlowManager
from flow.statuses import FailResult, Status
from flow.task.task import Task


class InstantTask(Task):
    def __init__(self, name: str, outcome: Status):
        super().__init__(name=name, description=f"{name} description")
        self._outcome = outcome
        self.executed = False

    async def execute(self):
        self.executed = True
        self.status = self._outcome
        return self.status


def test_run_returns_payload_when_conditions_pass():
    tasks = [InstantTask("task-a", Status.SUCCESS), InstantTask("task-b", Status.SUCCESS)]

    manager = FlowManager(
        flow_id="flow-pass",
        name="pass flow",
        tasks=tasks,
        conditions=[True],
        fail_result=[FailResult.END],
    )

    payload = asyncio.run(manager.run())

    assert payload is not None
    assert payload["id"] == "flow-pass"
    assert payload["start_task"] == "task-a"
    assert len(payload["tasks"]) == 2
    assert tasks[0].executed is True
    assert tasks[1].executed is True


def test_run_stops_when_condition_fails_and_fail_result_is_end():
    tasks = [InstantTask("task-a", Status.SUCCESS), InstantTask("task-b", Status.SUCCESS)]

    manager = FlowManager(
        flow_id="flow-end",
        name="end flow",
        tasks=tasks,
        conditions=[False],
        fail_result=[FailResult.END],
    )

    payload = asyncio.run(manager.run())

    assert payload is None
    assert tasks[0].executed is True
    assert tasks[1].executed is False


def test_run_moves_forward_when_condition_fails_and_fail_result_is_forward():
    tasks = [InstantTask("task-a", Status.SUCCESS), InstantTask("task-b", Status.SUCCESS)]

    manager = FlowManager(
        flow_id="flow-forward",
        name="forward flow",
        tasks=tasks,
        conditions=[False],
        fail_result=[FailResult.FORWARD],
    )

    payload = asyncio.run(manager.run())

    assert payload is not None
    assert tasks[0].executed is True
    assert tasks[1].executed is True


def test_init_raises_when_transition_lengths_do_not_match():
    with pytest.raises(ValueError):
        FlowManager(
            flow_id="flow-invalid",
            tasks=[InstantTask("single", Status.SUCCESS)],
            conditions=[True],
            fail_result=[FailResult.END],
        )
