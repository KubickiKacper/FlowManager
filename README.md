# Flow Manager

## Quick start (Docker)

```bash
make run
```

Open:
- Frontend: `http://127.0.0.1:5173`
- API docs (through frontend): `http://127.0.0.1:5173/docs`
- API docs (backend direct): `http://127.0.0.1:8000/docs`

## Quick start (local dev)

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Run tests:

```bash
make test
```

## Expected Deliverables

### Explanation of the flow design

How do the tasks depend on one another?
- Tasks are executed in order (`task1 -> task2 -> task3` by default).
- Each transition between tasks uses:
  - `conditions[i]`: expected result of the current task (`True` = success, `False` = failure).
  - `fail_result[i]`: what to do if condition check fails (`END` or `FORWARD`).

How is the success or failure of a task evaluated?
- Every task returns a `Status` value from `execute()` (`success` or `failed`).
- `FlowManager` converts that to a boolean with `_is_task_success(...)`.
- Then it checks: `condition_passed = (is_success == expected_success)`.

What happens if a task fails or succeeds?
- If the condition passes: flow moves to the next task.
- If the condition fails and `fail_result=FORWARD`: flow still moves forward.
- If the condition fails and `fail_result=END`: flow stops and is marked as failed.
- If all tasks finish without an `END` stop: flow is marked as completed.
