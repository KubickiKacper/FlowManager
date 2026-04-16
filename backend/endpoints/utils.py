from flow.task.fetch_data import FetchData
from flow.task.process_data import ProcessData
from flow.task.store_data import StoreData
from flow.statuses import FailResult

TASK_REGISTRY = {
    "fetchdata": FetchData,
    "processdata": ProcessData,
    "storedata": StoreData,
}

FAIL_RESULT_REGISTRY = {
    "END": FailResult.END,
    "FORWARD": FailResult.FORWARD,
}