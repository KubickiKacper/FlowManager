import logging
import asyncio

from .task import Task
from flow.statuses import Status

logger = logging.getLogger(__name__)


class ProcessData(Task):
    def __init__(self):
        super().__init__(name="task2", description="Process data")

    async def execute(self):
        logger.info("processing data")
        await asyncio.sleep(5)
        logger.info("data processed")
        self.status = Status.SUCCESS
        return self.get_status()
