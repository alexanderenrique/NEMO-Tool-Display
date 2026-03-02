# PlatformIO Cheat Sheet

Quick reference for common PlatformIO CLI commands in the project root.

pio run -t clean
pio run -t upload
pio device monitor

## Build & run

| Command | Description |
|--------|-------------|
| `pio run` | Build the project (compile only) |
| `pio run -t upload` | Build and upload firmware to the device |
| `pio run -t upload -e esp32dev` | Build and upload for a specific environment |

## Clean

| Command | Description |
|--------|-------------|
| `pio run -t clean` | Remove build artifacts (`.pio/build/`) for current env |
| `pio run -t fullclean` | Deep clean (build dirs + tool cache for this project) |

## Device & monitor

| Command | Description |
|--------|-------------|
| `pio device list` | List connected serial ports / boards |
| `pio device monitor` | Open serial monitor (default 9600 baud) |
| `pio device monitor -b 115200` | Serial monitor at 115200 baud |
| `pio run -t upload && pio device monitor` | Upload then open monitor |

## Environments

| Command | Description |
|--------|-------------|
| `pio run -e esp32dev` | Build for environment `esp32dev` (see `platformio.ini`) |
| `pio run -e env1 -e env2` | Build for multiple environments |

## Libraries & dependencies

| Command | Description |
|--------|-------------|
| `pio pkg install` | Install dependencies from `platformio.ini` |
| `pio pkg update` | Update installed libraries |
| `pio lib list` | List libraries used by the project |

## Shortcuts

- **Build:** `pio run`
- **Clean:** `pio run -t clean`
- **Upload:** `pio run -t upload`
- **Monitor:** `pio device monitor`

Run `pio run -t help` for all targets (e.g. `uploadfs`, `size`, etc.) for the current environment.
