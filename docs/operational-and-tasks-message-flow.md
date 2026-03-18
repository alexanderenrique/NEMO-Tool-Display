# Operational / Tasks: Message Flow and ESP32 Display Behavior

This document describes the **operational** and **tasks** logic: what the VM server sends to the ESP32 over MQTT and what the display shows, including edge cases (e.g. tool has a task then goes to shutdown, or vice versa).

---

## 1. Where the logic lives

- **VM server (Python):** `vm_server/main.py`  
  - NEMO publishes to `nemo/tools/{tool_id}/{event_type}`. The server subscribes, then forwards to ESP32 on `nemo/esp32/{tool_id}/...` (status, operational, task).
- **ESP32 (C++):** `Display-Code/src/main.cpp`  
  - Subscribes to `nemo/esp32/{tool_id}/status`, `.../operational`, `.../task`, and `.../overall`.  
  - Holds independent state: `tool_operational`, `has_task`, `task_summary`, `problem_description`, plus status (enabled/disabled, user, time).  
  - Maintains a **per-task store** (multiple tasks keyed by `task_id`); `has_task` and the displayed summary/description are derived from that store.

---

## 2. NEMO topics → VM server handling

The VM server derives `event_type` from the **fourth** segment of the topic:

`nemo/tools/{tool_identifier}/{event_type}`

| NEMO topic (event_type) | VM server action |
|-------------------------|------------------|
| `nemo/tools/{id}/non-operational` | Sends **operational** message to ESP32 (see below). |
| `nemo/tools/{id}/operational`     | Sends **operational** message to ESP32. |
| `nemo/tools/{id}/tasks`          | Sends **task** message to ESP32 (with special case for `task_shutdown` + `cancelled`). |
| `nemo/tools/{id}/start`, `end`, `enabled`, `disabled`, `idle` | Sends **status** message only (no change to operational/task). |

Operational and task are **independent**: either can be sent in any order; the ESP32 merges them in its own state.

---

## 3. Messages sent to the ESP32

### 3.1 Operational message

**Topic:** `nemo/esp32/{tool_id}/operational`  
**When:** On NEMO `nemo/tools/{id}/non-operational` or `nemo/tools/{id}/operational`.

**Payload (JSON):**

```json
{
  "operational": true | false,
  "tool_id": <int>,
  "tool_name": "<string>",
  "timestamp": "<ISO8601>"
}
```

- `non-operational` → server sets `operational` from payload (default `False`).
- `operational` → server sets `operational` from payload (default `True`).

Published with **QoS 1**, **retain = true**, so reconnecting ESP32s get the last operational state.

---

### 3.2 Task message

**Topic:** `nemo/esp32/{tool_id}/task`  
**When:** On NEMO `nemo/tools/{id}/tasks`.

**Payload (JSON):**

```json
{
  "event": "<event_name>",
  "task_id": <id>,
  "tool_id": <int>,
  "task_summary": "<string>",
  "problem_description": "<string>"
}
```

**Special case – clear task:**  
If NEMO sends a **task** event with `event == "task_shutdown"` and `cancelled == true`, or with `resolved == true` (e.g. `task_updated`), the server sends a **clear** payload:

- `task_summary` and `problem_description` are sent as **empty strings**.
- `task_id` is still included when present from NEMO (so the ESP32 can clear only that task when multiple exist).

Otherwise:

- `task_summary` = `tool_data["task_summary"]` or `tool_data["description"]` or `event_name`.
- `problem_description` = `tool_data["problem_description"]` (or empty).
- `task_id` is forwarded so the ESP32 can add or update that task in its store.

Published with **QoS 1**, **retain = true**.

---

### 3.3 Status message (for context)

**Topic:** `nemo/esp32/{tool_id}/status`  
**When:** On NEMO `start` / `end` / `enabled` / `disabled` / `idle` (not operational/tasks).

**Payload (JSON):** Includes `event_type` (`"active"` | `"enabled"` | `"disabled"`), `user_name`, `timestamp`, `time_label`, `user_label`, `tool_name`, etc. This drives “Current User” / “Last User”, time, and the **border color** when the tool is operational (green / red / yellow).

---

## 4. What the ESP32 display shows

### 4.1 Multi-task store and message interpretation

The ESP32 keeps a **task store** (bounded list of tasks keyed by `task_id`). Each incoming **task** message is interpreted as:

- **Clear-one:** Payload has **empty** `task_summary` and `problem_description` and a **present** `task_id` (integer or string) → remove that `task_id` from the store. Other tasks are unchanged. If no tasks remain, `has_task` becomes false and task text is cleared from the problem description page.
- **Clear-all:** Payload has empty summary and description and **no** `task_id` (or null) → clear the entire store. Backward compatible with legacy “clear” messages that omit `task_id`.
- **Add/update:** Otherwise → add a new task or update the existing one for that `task_id`. Internal event names (e.g. `task_shutdown`, `task_updated`) are not shown as summary/description.

After each update, the ESP32 derives:

- **has_task** = true iff the store has at least one task.
- **task_summary** = aggregated string for display (summaries joined with a delimiter, e.g. `" | "`).
- **problem_description** = aggregated string for the Details tab (descriptions joined with `"\n\n---\n\n"`).

**Reconnect behavior:** The task topic is retained, so a reconnecting ESP32 receives only the **last** published message. That message represents a single event (one add/update or one clear). The full set of tasks is **not** restored on reconnect; the display will show at most one task (if the last message was an add/update) or none (if the last message was a clear). Full multi-task state is only built up as messages are received after connect.

### 4.2 State variables (from MQTT)

- **tool_operational** (from `.../operational`): `true` = normal screen, `false` = red “non-operational” screen.
- **has_task** (derived from task store): `true` iff at least one task is in the store.
- **task_summary**, **problem_description** (derived from task store): Aggregated task text; summary on Status tab (and on red screen), full description on Details tab.
- **last_status_enabled** (from `.../status`): Used only when **tool_operational** is true, to set border green (enabled) or red (disabled).
- **toolDisplayName**: From operational or status payloads; used in title and “{Tool} is non-operational”.

### 4.3 Main screen logic (`applyMainScreenState()`)

- **If `!tool_operational`:**
  - Hide **normal** container (white status view).
  - Show **non-operational** container (full red screen).
  - Title: **“{toolDisplayName} is non-operational”**.
  - Body: **task_summary** in `non_operational_task_label` (white text). If there is no task, this is empty.
  - Details tab: **problem_description** (or “No problem description.”).

- **If `tool_operational`:**
  - Show normal container, hide non-operational container.
  - Border color from **status** + **task**:
    - **Yellow** if `has_task`.
    - Else **green** if `last_status_enabled`, else **red**.

So:

- **Operational** message alone → switches between normal view and red “non-operational” view.
- **Task** message alone → updates task text and `has_task`; when operational, border turns yellow if there is a task.

---

## 5. Edge cases: task vs shutdown (non-operational)

### 5.1 Tool has a task, then is put into shutdown (non-operational)

1. NEMO had previously sent `nemo/tools/{id}/tasks` → ESP32 has `has_task = true`, `task_summary` / `problem_description` set.
2. NEMO sends `nemo/tools/{id}/non-operational` (tool goes to shutdown).
3. VM server sends **operational** with `operational: false` to `nemo/esp32/{id}/operational`.
4. **No** task message is sent; the last retained task message is still the current one.

**ESP32:**  
- Sets `tool_operational = false`.  
- `has_task`, `task_summary`, `problem_description` unchanged.  
- **Display:** Red screen “{Tool} is non-operational” with the **existing task summary** below. Details tab still shows the same problem description.

---

### 5.2 Tool is in shutdown (non-operational), then gets a task

1. NEMO had sent `nemo/tools/{id}/non-operational` → ESP32 has `tool_operational = false` (red screen).
2. NEMO sends `nemo/tools/{id}/tasks` with a new task (e.g. shutdown task).
3. VM server sends **task** to `nemo/esp32/{id}/task` with `task_summary` and `problem_description`.

**ESP32:**  
- `tool_operational` still false (no new operational message).  
- Updates `task_summary`, `problem_description`, `has_task = true`.  
- **Display:** Still red “non-operational” screen; the **task summary** (and Details tab) now show the new task.

---

### 5.3 Tool is in shutdown, then task is cancelled (task_shutdown cancelled)

1. Tool is non-operational and had one or more tasks (red screen with task text).
2. NEMO sends `nemo/tools/{id}/tasks` with `event == "task_shutdown"` and `cancelled == true` (and typically `task_id` for the cancelled task).
3. VM server sends **task** with **empty** `task_summary` and `problem_description` and the same `task_id` (when NEMO provided it).

**ESP32:**  
- **Clear-one** (if `task_id` present): Removes that task from the store. If other tasks remain, `has_task` stays true and the problem description page shows only the remaining task(s). If that was the last task, `has_task = false` and task text is cleared.  
- **Clear-all** (if `task_id` missing/null): Clears the entire store; `has_task = false`.  
- `tool_operational` unchanged (still false).  
- **Display:** Red “non-operational” screen; task summary and Details tab reflect remaining tasks or “No problem description.” when none remain.

---

### 5.4 Tool has a task, then is put back to operational (no shutdown)

1. ESP32 has `has_task = true`, `tool_operational = true` (normal screen, yellow border).
2. NEMO sends `nemo/tools/{id}/operational` with `operational: true`.
3. VM server sends **operational** with `operational: true`.

**ESP32:**  
- Stays `tool_operational = true`, `has_task` still true.  
- **Display:** Normal screen, **yellow border** (task), user/time from last status.

---

### 5.5 Tool is in shutdown, then brought back to operational (with or without task)

1. ESP32 had `tool_operational = false` (red screen), possibly with task text.
2. NEMO sends `nemo/tools/{id}/operational` with `operational: true`.
3. VM server sends **operational** with `operational: true`.

**ESP32:**  
- Sets `tool_operational = true`.  
- **Display:** Normal (white) screen. Border: **yellow** if `has_task`, else **green** if `last_status_enabled`, else **red**. Task text remains in state and on Details tab; if `has_task`, Status tab border is yellow.

---

## 6. Summary table

| Scenario | Message(s) to ESP32 | Display result |
|----------|---------------------|----------------|
| Tool goes non-operational (shutdown) | `.../operational` with `operational: false` | Red screen “{Tool} is non-operational” + current task summary (or empty). |
| Tool goes back operational | `.../operational` with `operational: true` | Normal screen; border yellow if task, else green/red from status. |
| New/updated task | `.../task` with summary + problem_description | Task text updated; if operational, border turns yellow; if non-operational, red screen shows new summary. |
| Task cancelled (task_shutdown, cancelled=true) | `.../task` with empty summary + problem_description (+ `task_id` for clear-one) | If `task_id` present: that task removed from store; `has_task` true iff other tasks remain; problem description shows remaining tasks. If no `task_id`: clear-all; `has_task = false`. |
| Task then shutdown | Only `.../operational` false | Red screen with existing task text. |
| Shutdown then task | Only `.../task` | Red screen with new task text. |
| Shutdown then task cancelled | Only `.../task` (empty) | Red screen, no task text. |

All operational and task messages are published with **retain = true**. A reconnecting ESP32 receives the latest operational message and the **last** task message only; multi-task state is not restored on reconnect (see §4.1).
