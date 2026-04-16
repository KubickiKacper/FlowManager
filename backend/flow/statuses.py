from enum import Enum

class Status(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class FailResult(Enum):
    END = "end the flow"
    FORWARD = "move forward"
