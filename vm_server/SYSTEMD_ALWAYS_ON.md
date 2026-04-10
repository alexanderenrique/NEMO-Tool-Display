# Always-on VM: Mosquitto + `main.py` with systemd

Use this on your Linux VM so the MQTT broker and NEMO server **start at boot** and **restart after crashes or power loss** (once the machine is back up).

**No path placeholders in the unit files:** install with **`ln -sf`** from your checkout (see step 3). Runner scripts resolve `vm_server` from their own location, so the repo folder can be named `NEMO-Tool-Display` or anything else. **`User=` / `Group=` are optional** on both services (omit or leave commented for root; set them for production least-privilege).

---

## 1. One-time prep

1. **Install Mosquitto** (if needed), e.g. on Ubuntu:
   ```bash
   sudo apt-get update && sudo apt-get install -y mosquitto mosquitto-clients
   ```
2. **Confirm the broker binary path** (default in `systemd/run-nemo-mosquitto.sh` is `/usr/sbin/mosquitto`). If yours differs:
   ```bash
   command -v mosquitto
   ```
   Add `Environment=MOSQUITTO_BIN=…` under `[Service]` in `nemo-mosquitto.service` (use the path from `command -v`), or edit `MOSQUITTO_BIN` in `systemd/run-nemo-mosquitto.sh`.
3. **Finish app setup** from `vm_server` (venv, `config.env`, passwords, etc.) using `./setup.sh` or your usual process so `mqtt/config/mosquitto.conf` and `mqtt/config/passwd` exist and are valid.
4. **Permissions**: if you set `User=` / `Group=` on `nemo-mosquitto.service`, that account must read `mqtt/config/passwd` and read/write `mqtt/data/` and `mqtt/log/`. Fix ownership if needed:
   ```bash
   sudo chown -R YOUR_USER:YOUR_GROUP /path/to/vm_server/mqtt
   ```

---

## 2. Stop the stock Mosquitto service (avoid port conflicts)

The distro `mosquitto` package often enables its own unit with a **different** config. That conflicts with NEMO’s listeners on **1883** and **1886**.

```bash
sudo systemctl disable --now mosquitto 2>/dev/null || true
```

Optional (stronger—prevents accidental start):

```bash
sudo systemctl mask mosquitto
```

To undo later: `sudo systemctl unmask mosquitto`.

---

## 3. Install custom unit files

From your checkout, **`cd` into `vm_server`** and **symlink** (not copy) the runner scripts and units so systemd runs the real files in your tree—no manual path edits.

```bash
cd /path/to/vm_server

sudo ln -sf "$PWD/systemd/run-nemo-mosquitto.sh" /etc/systemd/system/nemo-mosquitto-exec.sh
sudo ln -sf "$PWD/systemd/run-nemo-vm-server.sh" /etc/systemd/system/nemo-vm-server-exec.sh
sudo ln -sf "$PWD/systemd/nemo-mosquitto.service" /etc/systemd/system/nemo-mosquitto.service
sudo ln -sf "$PWD/systemd/nemo-vm-server.service" /etc/systemd/system/nemo-vm-server.service

sudo systemctl daemon-reload
```

If you **copy** the `.sh` files into `/etc/systemd/system/` instead of symlinking, they will **not** find `vm_server` (the script’s parent directory must be `vm_server/systemd/` inside the checkout).

---

## 4. Enable and start (boot + restart policy)

Start **Mosquitto first**, then the Python server (`nemo-vm-server` already **Requires** `nemo-mosquitto`):

```bash
sudo systemctl enable nemo-mosquitto.service
sudo systemctl enable nemo-vm-server.service

sudo systemctl start nemo-mosquitto.service
sudo systemctl start nemo-vm-server.service
```

Check status:

```bash
systemctl status nemo-mosquitto.service
systemctl status nemo-vm-server.service
```

---

## 5. After reboot or power loss

If both units are **enabled**, they start automatically when networking is up. Verify:

```bash
sudo reboot
# after login:
systemctl is-active nemo-mosquitto.service nemo-vm-server.service
```

---

## 6. Logs and troubleshooting

| Component | Where to look |
|-----------|----------------|
| Mosquitto (systemd) | `journalctl -u nemo-mosquitto.service -f` |
| Mosquitto (file) | `vm_server/mqtt/log/mosquitto.log` |
| `main.py` (systemd) | `journalctl -u nemo-vm-server.service -f` |
| `main.py` (app log) | `vm_server/nemo_server.log` |

Common issues:

- **Ports in use**: something else (including old `mosquitto.service`) still bound to 1883/1886—finish step 2 and reboot once.
- **Permission denied** on `passwd` or `mqtt/data`: fix `chown`/`chmod` for your service user.
- **Wrong cwd / paths**: `mosquitto.conf` uses paths relative to `vm_server`. Use the **symlink** install for the runner scripts so they `cd` to the correct `vm_server`.

---

## 7. Interaction with `quick_restart.sh` / manual `mosquitto -d`

If you use systemd for production, **do not** also start Mosquitto or `main.py` from scripts for the same ports. Before using `./quick_restart.sh` for debugging:

```bash
sudo systemctl stop nemo-vm-server.service
sudo systemctl stop nemo-mosquitto.service
```

When done debugging, start the units again (step 4).

---

## 8. Optional: stricter restarts

Both units use `Restart=on-failure`. If a process exits with status **0** on a bug, systemd will not restart it. The Python app already retries many failures internally; for Mosquitto, prefer fixing the root cause. If you truly need **always** restart even on clean exit, you can switch to `Restart=always` in the unit (use with care—you must use `systemctl stop` for intentional shutdowns).
