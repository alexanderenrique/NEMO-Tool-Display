# Operational / Tasks: Message Flow and ESP32 Display Behavior

This document describes the **operational** and **tasks** logic: what the VM server sends to the ESP32 over MQTT and what the display shows, including edge cases (e.g. tool has a task then goes to shutdown, or vice versa).

---

## 1. Where the logic lives

- **VM server (Python):** `vm_server/main.py`  
  - NEMO publishes to `nemo/tools/{tool_id}/{event_type}`. The server subscribes, then forwards to ESP32 on `nemo/esp32/{tool_id}/...` (status, operational, task).
- **ESP32 (C++):** `Display-Code/src/main.cpp`  
  - Subscribes to `nemo/esp32/{tool_id}/status`, `.../operational`, `.../task`, and `.../overall`.  
  - Holds independent state: `tool_operational`, `has_task`, `task_summary`, `problem_description`, plus status (enabled/disabled, user, time).

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
If NEMO sends a **task** event with `event == "task_shutdown"` and `cancelled == true`, or with `resolved == true` (e.g. `task_updated`), the server **clears** the task on the display:

- `task_summary` and `problem_description` are sent as **empty strings**.
- ESP32 will set `has_task = false` and clear task text.

Otherwise:

- `task_summary` = `tool_data["task_summary"]` or `tool_data["description"]` or `event_name`.
- `problem_description` = `tool_data["problem_description"]` (or empty).

Published with **QoS 1**, **retain = true**.

---

### 3.3 Status message (for context)

**Topic:** `nemo/esp32/{tool_id}/status`  
**When:** On NEMO `start` / `end` / `enabled` / `disabled` / `idle` (not operational/tasks).

**Payload (JSON):** Includes `event_type` (`"active"` | `"enabled"` | `"disabled"`), `user_name`, `timestamp`, `time_label`, `user_label`, `tool_name`, etc. This drives “Current User” / “Last User”, time, and the **border color** when the tool is operational (green / red / yellow).

---

## 4. What the ESP32 display shows

### 4.1 State variables (from MQTT)

- **tool_operational** (from `.../operational`): `true` = normal screen, `false` = red “non-operational” screen.
- **has_task** (from `.../task`): `true` if `task_summary` or `problem_description` is non-empty.
- **task_summary**, **problem_description**: Task text; summary on Status tab (and on red screen), full description on Details tab.
- **last_status_enabled** (from `.../status`): Used only when **tool_operational** is true, to set border green (enabled) or red (disabled).
- **toolDisplayName**: From operational or status payloads; used in title and “{Tool} is non-operational”.

### 4.2 Main screen logic (`applyMainScreenState()`)

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

1. Tool is non-operational and had a task (red screen with task text).
2. NEMO sends `nemo/tools/{id}/tasks` with `event == "task_shutdown"` and `cancelled == true`.
3. VM server sends **task** with **empty** `task_summary` and `problem_description` to clear the task.

**ESP32:**  
- Sets `task_summary = ""`, `problem_description = ""`, `has_task = false`.  
- `tool_operational` unchanged (still false).  
- **Display:** Red “non-operational” screen with **no** task text below the title. Details tab shows “No problem description.”

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
| Task cancelled (task_shutdown, cancelled=true) | `.../task` with empty summary + problem_description | `has_task = false`; task text cleared; red screen (if non-operational) shows only title. |
| Task then shutdown | Only `.../operational` false | Red screen with existing task text. |
| Shutdown then task | Only `.../task` | Red screen with new task text. |
| Shutdown then task cancelled | Only `.../task` (empty) | Red screen, no task text. |

All operational and task messages are published with **retain = true**, so a reconnecting ESP32 receives the latest operational and task state and shows the correct screen and border color immediately.
