import { useEffect, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(
  /\/$/,
  ""
);
const FLOW_RUN_ENDPOINT = `${API_BASE_URL}/flow/run`;
const FLOW_STATUS_ENDPOINT = (flowId) =>
  `${API_BASE_URL}/flow/${encodeURIComponent(flowId)}`;

const AVAILABLE_TASKS = ["FetchData", "ProcessData", "StoreData"];
const TERMINAL_STATES = new Set(["completed", "failed"]);
const FALLBACK_FLOW_NAME = "Data processing flow";

const defaultTransition = () => ({
  condition: true,
  failResult: "END",
});

const buildDefaultTransitions = (taskCount) =>
  Array.from(
    { length: Math.max(taskCount - 1, 0) },
    () => defaultTransition()
  );

const buildFlowId = () => `flow-${Date.now()}`;

const safeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const syncTransitions = (currentTransitions, taskCount) => {
  const expectedSize = Math.max(taskCount - 1, 0);
  if (currentTransitions.length === expectedSize) {
    return currentTransitions;
  }
  if (currentTransitions.length > expectedSize) {
    return currentTransitions.slice(0, expectedSize);
  }
  const missing = expectedSize - currentTransitions.length;
  return [
    ...currentTransitions,
    ...Array.from({ length: missing }, () => defaultTransition()),
  ];
};

const formatDate = (rawDate) => {
  if (!rawDate) {
    return "n/a";
  }
  const parsed = new Date(rawDate);
  if (Number.isNaN(parsed.getTime())) {
    return rawDate;
  }
  return parsed.toLocaleString();
};

const prettyStatus = (status) => {
  if (!status) {
    return "unknown";
  }
  return status.replace(/_/g, " ");
};

export default function App() {
  const [flowId, setFlowId] = useState(() => buildFlowId());
  const [flowName, setFlowName] = useState(FALLBACK_FLOW_NAME);
  const [tasks, setTasks] = useState(AVAILABLE_TASKS);
  const [transitions, setTransitions] = useState(() =>
    buildDefaultTransitions(AVAILABLE_TASKS.length)
  );
  const [trackedFlowId, setTrackedFlowId] = useState("");
  const [lookupFlowId, setLookupFlowId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [statusSnapshot, setStatusSnapshot] = useState(null);
  const [message, setMessage] = useState("");

  const payloadPreview = {
    flow_id: flowId || "<flow-id>",
    name: flowName || FALLBACK_FLOW_NAME,
    tasks,
    conditions: transitions.map((transition) => transition.condition),
    fail_result: transitions.map((transition) => transition.failResult),
  };

  useEffect(() => {
    if (!trackedFlowId || !isPolling) {
      return undefined;
    }

    let cancelled = false;
    let intervalId = 0;

    const fetchSnapshot = async () => {
      try {
        const response = await fetch(FLOW_STATUS_ENDPOINT(trackedFlowId));

        if (response.status === 404) {
          if (!isSubmitting) {
            setMessage(`Flow '${trackedFlowId}' does not exist.`);
            setIsPolling(false);
          }
          return;
        }

        const body = await safeJson(response);
        if (!response.ok) {
          throw new Error(
            (body && body.detail) ||
              `Status request failed with ${response.status}`
          );
        }

        if (cancelled) {
          return;
        }

        setStatusSnapshot(body);
        if (TERMINAL_STATES.has(body.status)) {
          setIsPolling(false);
        }
      } catch (error) {
        if (!cancelled) {
          setMessage(error.message || "Cannot fetch flow status.");
          setIsPolling(false);
        }
      }
    };

    void fetchSnapshot();
    intervalId = window.setInterval(fetchSnapshot, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [trackedFlowId, isPolling, isSubmitting]);

  const handleTaskToggle = (taskName) => {
    setTasks((currentTasks) => {
      const exists = currentTasks.includes(taskName);
      const nextTasks = exists
        ? currentTasks.filter((task) => task !== taskName)
        : [...currentTasks, taskName];

      if (nextTasks.length === 0) {
        return currentTasks;
      }

      setTransitions((currentTransitions) =>
        syncTransitions(currentTransitions, nextTasks.length)
      );
      return nextTasks;
    });
  };

  const handleTransitionChange = (index, key, value) => {
    setTransitions((currentTransitions) =>
      currentTransitions.map((transition, transitionIndex) =>
        transitionIndex === index
          ? { ...transition, [key]: value }
          : transition
      )
    );
  };

  const handleRunFlow = async (event) => {
    event.preventDefault();

    const normalizedFlowId = flowId.trim() || buildFlowId();
    const normalizedFlowName = flowName.trim() || FALLBACK_FLOW_NAME;
    if (!flowId.trim()) {
      setFlowId(normalizedFlowId);
    }
    if (!flowName.trim()) {
      setFlowName(normalizedFlowName);
    }

    const payload = {
      flow_id: normalizedFlowId,
      name: normalizedFlowName,
      tasks,
      conditions: transitions.map((transition) => transition.condition),
      fail_result: transitions.map((transition) => transition.failResult),
    };

    setMessage("");
    setStatusSnapshot(null);
    setTrackedFlowId(normalizedFlowId);
    setLookupFlowId(normalizedFlowId);
    setIsPolling(true);
    setIsSubmitting(true);

    try {
      const response = await fetch(FLOW_RUN_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const body = await safeJson(response);
      if (!response.ok) {
        if (response.status === 422) {
          setIsPolling(false);
        }
        throw new Error(
          (body && body.detail) || `Run request failed with ${response.status}`
        );
      }

      setMessage(`Flow '${normalizedFlowId}' finished request cycle.`);
    } catch (error) {
      setMessage(error.message || "Cannot run flow.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTrackFlow = (event) => {
    event.preventDefault();
    const targetFlowId = lookupFlowId.trim();
    if (!targetFlowId) {
      setMessage("Provide flow ID to track.");
      return;
    }
    setMessage("");
    setStatusSnapshot(null);
    setTrackedFlowId(targetFlowId);
    setIsPolling(true);
  };

  const currentStatus = statusSnapshot?.status || (isPolling ? "running" : "idle");

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="hero">
        <p className="kicker">Flow Manager</p>
        <h1>Run and Track Pipeline Execution</h1>
        <p>
          Submit a flow configuration, then poll execution state in real time to
          drive frontend progress UI.
        </p>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>Run Flow</h2>
          <form onSubmit={handleRunFlow} className="form-grid">
            <label>
              Flow ID
              <input
                value={flowId}
                onChange={(event) => setFlowId(event.target.value)}
                placeholder="flow-123"
              />
            </label>

            <label>
              Flow Name
              <input
                value={flowName}
                onChange={(event) => setFlowName(event.target.value)}
                placeholder={FALLBACK_FLOW_NAME}
              />
            </label>

            <fieldset>
              <legend>Tasks</legend>
              <div className="chip-row">
                {AVAILABLE_TASKS.map((taskName) => (
                  <label className="chip" key={taskName}>
                    <input
                      type="checkbox"
                      checked={tasks.includes(taskName)}
                      onChange={() => handleTaskToggle(taskName)}
                    />
                    <span>{taskName}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend>Transitions</legend>
              {transitions.length === 0 && (
                <p className="muted">No transitions for a single-task flow.</p>
              )}
              {transitions.map((transition, index) => (
                <div className="transition-row" key={`transition-${index}`}>
                  <p className="transition-title">
                    {tasks[index]} {"->"} {tasks[index + 1]}
                  </p>
                  <label>
                    Condition
                    <select
                      value={String(transition.condition)}
                      onChange={(event) =>
                        handleTransitionChange(
                          index,
                          "condition",
                          event.target.value === "true"
                        )
                      }
                    >
                      <option value="true">True (proceed on success)</option>
                      <option value="false">False (proceed on failure)</option>
                    </select>
                  </label>
                  <label>
                    Fail Result
                    <select
                      value={transition.failResult}
                      onChange={(event) =>
                        handleTransitionChange(
                          index,
                          "failResult",
                          event.target.value
                        )
                      }
                    >
                      <option value="END">END</option>
                      <option value="FORWARD">FORWARD</option>
                    </select>
                  </label>
                </div>
              ))}
            </fieldset>

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Running..." : "Run Flow"}
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Track Flow</h2>
          <form onSubmit={handleTrackFlow} className="track-form">
            <input
              value={lookupFlowId}
              onChange={(event) => setLookupFlowId(event.target.value)}
              placeholder="flow ID to track"
            />
            <button type="submit">Track</button>
          </form>

          <div className="status-bar">
            <span className={`status-pill status-${currentStatus}`}>
              {prettyStatus(currentStatus)}
            </span>
            {isPolling ? <span className="pulse">polling</span> : null}
          </div>

          {trackedFlowId && (
            <p className="muted">
              Tracking: <strong>{trackedFlowId}</strong>
            </p>
          )}

          {message && <p className="message">{message}</p>}

          {statusSnapshot ? (
            <div className="snapshot">
              <div className="snapshot-grid">
                <p>
                  <span>Created</span>
                  {formatDate(statusSnapshot.created_at)}
                </p>
                <p>
                  <span>Started</span>
                  {formatDate(statusSnapshot.started_at)}
                </p>
                <p>
                  <span>Updated</span>
                  {formatDate(statusSnapshot.updated_at)}
                </p>
                <p>
                  <span>Finished</span>
                  {formatDate(statusSnapshot.finished_at)}
                </p>
              </div>

              <h3>Tasks</h3>
              <ul className="task-list">
                {statusSnapshot.tasks.map((task) => (
                  <li key={task.name}>
                    <div>
                      <strong>{task.name}</strong>
                      <small>{task.description}</small>
                    </div>
                    <span className={`status-chip status-${task.status}`}>
                      {prettyStatus(task.status)}
                    </span>
                  </li>
                ))}
              </ul>

              <h3>Conditions</h3>
              {statusSnapshot.conditions.length === 0 ? (
                <p className="muted">No conditions in this flow.</p>
              ) : (
                <ul className="condition-list">
                  {statusSnapshot.conditions.map((condition) => (
                    <li key={condition.name}>
                      <strong>{condition.name}</strong>
                      <span>{condition.expected_result}</span>
                      <span
                        className={`status-chip status-${condition.status || "pending"}`}
                      >
                        {prettyStatus(condition.status || "pending")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {statusSnapshot.error && (
                <p className="error-text">Error: {statusSnapshot.error}</p>
              )}
            </div>
          ) : (
            <p className="muted">No snapshot yet. Run or track a flow ID.</p>
          )}
        </section>
      </main>

      <section className="panel payload-preview">
        <h2>Payload Preview</h2>
        <pre>{JSON.stringify(payloadPreview, null, 2)}</pre>
      </section>
    </div>
  );
}
