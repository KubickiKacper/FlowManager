import logging
import asyncio

from .task import Task
from flow.statuses import Status

logger = logging.getLogger(__name__)


class FetchData(Task):
    def __init__(self):
        super().__init__(name="task1", description="Fetching data")

    async def execute(self):
        logger.info("fetching data")
        await asyncio.sleep(5)
        logger.info("data fetched")
        self.status = Status.SUCCESS
        return self.get_status()
