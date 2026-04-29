# Always-on VM: Mosquitto + `main.py` with systemd

Use this on your Linux VM so the MQTT broker and NEMO server **start at boot** and **restart after crashes or power loss** (once the machine is back up).

**Paths live in the unit files:** open `systemd/nemo-mosquitto.service`, `systemd/nemo-vm-server.service`, and `systemd/nemo-api-sync.service`, set `NEMO_VM_SERVER_DIR` to the absolute path of your `vm-server` directory, and set `MOSQUITTO_BIN` if `mosquitto` is not at `/usr/sbin/mosquitto`. **`User=` / `Group=` are optional** on all services (omit or leave commented for root; set them for production least-privilege).

---

## 1. One-time prep

1. **Install Mosquitto** (if needed), e.g. on Ubuntu:
   ```bash
   sudo apt-get update && sudo apt-get install -y mosquitto mosquitto-clients
   ```
2. **Confirm the broker binary path** if you are unsure:
   ```bash
   command -v mosquitto
   ```
   Put that path in `MOSQUITTO_BIN=` under `[Service]` in `nemo-mosquitto.service`.
3. **Finish app setup** from `vm-server` (venv, `config.env`, passwords, etc.) using `./setup.sh` or your usual process so `mqtt/config/mosquitto.conf` and `mqtt/config/passwd` exist and are valid. **`mosquitto.conf` is gitignored**—a clone has only `mosquitto.conf.example` until you run setup or copy it; without the real file, `nemo-mosquitto` will refuse to start.
4. **Permissions**: the distro `mosquitto` binary **drops to the `mosquitto` system user** after start (even when systemd does **not** set `User=`). Files created by `./setup.sh` are usually owned by your login user, with `mqtt/config/passwd` at mode `600`, so the broker cannot read the password file or write `mqtt/log/mosquitto.log`. Fix once (adjust the path):
   ```bash
   sudo chown -R mosquitto:mosquitto /path/to/vm-server/mqtt/data /path/to/vm-server/mqtt/log
   sudo chown mosquitto:mosquitto /path/to/vm-server/mqtt/config/passwd
   sudo chmod 600 /path/to/vm-server/mqtt/config/passwd
   ```
   Keep `mqtt/config/mosquitto.conf` readable by `mosquitto` (e.g. `644`, or root:`mosquitto` and `640`). If you instead set `User=` / `Group=` in the unit file, use that account everywhere above instead of `mosquitto`.

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

1. Edit **`Environment=NEMO_VM_SERVER_DIR=...`** (and **`MOSQUITTO_BIN=...`** if needed) in the unit files under `vm-server/systemd/`.
2. Copy (or symlink) the units into `/etc/systemd/system/`:

```bash
sudo cp /opt/NEMO-Tool-Display/vm-server/systemd/nemo-mosquitto.service /etc/systemd/system/
sudo cp /opt/NEMO-Tool-Display/vm-server/systemd/nemo-vm-server.service /etc/systemd/system/
sudo cp /opt/NEMO-Tool-Display/vm-server/systemd/nemo-api-sync.service /etc/systemd/system/

sudo systemctl daemon-reload
```

If you previously installed **`nemo-mosquitto-exec.sh`** or **`nemo-vm-server-exec.sh`** under `/etc/systemd/system/`, remove those files or symlinks; they are no longer used.

---

## 4. Enable and start (boot + restart policy)

Start **Mosquitto first**, then the Python server (`nemo-vm-server` already **Requires** `nemo-mosquitto`):

```bash
sudo systemctl enable nemo-mosquitto.service
sudo systemctl start nemo-mosquitto.service


sudo systemctl enable nemo-vm-server.service
sudo systemctl start nemo-vm-server.service


sudo systemctl enable nemo-api-sync.service
sudo systemctl start nemo-api-sync.service
```

Check status:

```bash
systemctl status nemo-mosquitto.service
systemctl status nemo-vm-server.service
systemctl status nemo-api-sync.service
```

---

## 5. After reboot or power loss

If both units are **enabled**, they start automatically when networking is up. Verify:

```bash
sudo reboot
# after login:
systemctl is-active nemo-mosquitto.service nemo-vm-server.service nemo-api-sync.service
```

---

## 6. Logs and troubleshooting

| Component | Where to look |
|-----------|----------------|
| Mosquitto (systemd) | `journalctl -u nemo-mosquitto.service -f` |
| Mosquitto (file) | `vm-server/mqtt/log/mosquitto.log` |
| `main.py` (systemd) | `journalctl -u nemo-vm-server.service -f` |
| `main.py` (app log) | `vm-server/nemo_server.log` |
| API sync + next reservations (systemd) | `journalctl -u nemo-api-sync.service -f` |

Common issues:

- **Ports in use**: something else (including old `mosquitto.service`) still bound to 1883/1886—finish step 2 and reboot once.
- **Unable to open** `passwd` or **log file** under `mqtt/log/`: almost always the `mosquitto` user (privilege drop) vs. files owned by your admin account—use the `chown` commands in step 1.4.
- **Wrong cwd / paths**: `WorkingDirectory` must be your `vm-server` root so paths inside `mosquitto.conf` (e.g. `mqtt/data/`) resolve correctly.

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
