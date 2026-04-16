from flow.statuses import Status


class Task:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.status = Status.PENDING

    async def execute(self):
        raise NotImplementedError

    def get_status(self):
        return self.status
