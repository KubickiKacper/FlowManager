import logging
import asyncio

from .task import Task

from flow.statuses import Status

logger = logging.getLogger(__name__)


class StoreData(Task):
    def __init__(self):
        super().__init__(name="task3", description="Storing data")

    async def execute(self):
        logger.info("storing data")
        await asyncio.sleep(5)
        logger.info("data stored")
        self.status = Status.SUCCESS
        return self.get_status()
