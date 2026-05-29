# ios-simulator-mcp

[![PyPI version](https://badge.fury.io/py/ios-simulator-mcp.svg)](https://badge.fury.io/py/ios-simulator-mcp)
[![Python Versions](https://img.shields.io/pypi/pyversions/ios-simulator-mcp.svg)](https://pypi.org/project/ios-simulator-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/adborroto/ios-simulator-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/adborroto/ios-simulator-mcp/actions/workflows/test.yml)

MCP server that gives AI assistants (Claude, Cursor, etc.) direct control over the iOS Simulator.

Built on `xcrun simctl` + AppleScript. 21 tools covering device management, UI interaction, app control, sensor simulation, logs, and video recording — no Appium, no WebDriver, no extra services.

**Platform:** macOS only · Requires Xcode with iOS Simulator installed

---

## Quick Install (Recommended)

Automatic installation that configures Claude Desktop, Claude Code, and Cursor:

```bash
curl -fsSL https://raw.githubusercontent.com/adborroto/ios-simulator-mcp/main/install.sh | bash
```

This will:
- Install the package via `uv`
- Auto-configure Claude Desktop
- Auto-configure Claude Code
- Auto-configure Cursor
- No manual JSON editing needed!

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/adborroto/ios-simulator-mcp/main/uninstall.sh | bash
```

---

## Manual Installation

### Quick run (no install)

[uv](https://docs.astral.sh/uv/) downloads and runs the package in an isolated environment:

```bash
uvx ios-simulator-mcp
```

### Install permanently

```bash
uv tool install ios-simulator-mcp
# or
pip install ios-simulator-mcp
```

### Configure your client

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ios-simulator": {
      "command": "uvx",
      "args": ["ios-simulator-mcp"]
    }
  }
}
```

Or run from Claude Code's terminal:

```bash
claude mcp add ios-simulator -- uvx ios-simulator-mcp
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ios-simulator": {
      "command": "uvx",
      "args": ["ios-simulator-mcp"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Cursor

Edit `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` globally):

```json
{
  "mcpServers": {
    "ios-simulator": {
      "command": "uvx",
      "args": ["ios-simulator-mcp"]
    }
  }
}
```

### VS Code (with Copilot / MCP extension)

Edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "ios-simulator": {
      "type": "stdio",
      "command": "uvx",
      "args": ["ios-simulator-mcp"]
    }
  }
}
```

### Pin a specific simulator (optional)

If you have multiple simulators and want to target a specific one without passing `udid` to every tool:

```json
{
  "mcpServers": {
    "ios-simulator": {
      "command": "uvx",
      "args": ["ios-simulator-mcp"],
      "env": {
        "IOS_SIM_DEFAULT_UDID": "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
      }
    }
  }
}
```

Get your UDID with `xcrun simctl list devices` or by asking the AI to call `list_simulators`.

---

## Accessibility permission (required for tap & swipe)

`tap` and `swipe` use AppleScript to send clicks to the Simulator window. macOS requires Accessibility access for the process running the MCP server — typically your terminal app or the MCP client itself.

Go to **System Settings → Privacy & Security → Accessibility** and add:
- Your terminal app (Terminal, iTerm2, Warp, etc.) if running Claude Code from the terminal
- Claude Desktop or Cursor if using those clients

Without this, `tap` and `swipe` will return an error. `take_screenshot`, `input_text`, and all other tools work without this permission.

---

## Tools reference

All tools accept an optional `udid` parameter. When omitted, the server auto-detects the booted simulator or falls back to `IOS_SIM_DEFAULT_UDID`.

---

### Device management

#### `list_simulators`

List all simulators known to Xcode, with their name, UDID, state, and runtime.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `runtime_filter` | string | — | Filter by runtime fragment, e.g. `"iOS 18"` |
| `state_filter` | string | — | Filter by state: `"Booted"` or `"Shutdown"` |

```
# Example prompt
"List all booted iOS 18 simulators"
→ calls list_simulators(runtime_filter="iOS 18", state_filter="Booted")
```

Returns: `devices[]`, `total`, `booted_count`, `booted[]`

---

#### `get_booted_simulator`

Returns the currently booted simulator(s). No parameters.

Useful at the start of a session to confirm which device is active before running other tools.

Returns: `booted[]`, `primary` (first booted device), `count`

---

#### `boot_simulator`

Boot a simulator by UDID. The UDID must come from `list_simulators`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `udid` | string | yes | Simulator UDID |

```
# Example prompt
"Boot the iPhone 16 Pro simulator"
→ calls list_simulators() first to find the UDID, then boot_simulator(udid="...")
```

> The Simulator app opens automatically. Allow a few seconds before interacting.

---

#### `shutdown_simulator`

Shutdown a booted simulator.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `udid` | string | auto | Simulator UDID |

---

### Screenshots & UI interaction

#### `take_screenshot`

Capture the current simulator screen and return it as an inline image.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `udid` | string | auto | Simulator UDID |

The image is returned directly to the AI so it can analyze the UI, read text, locate elements, and decide where to tap — no file path needed.

```
# Example workflow
1. take_screenshot()          → AI sees the current screen
2. tap(x=196, y=430)          → AI taps a button it located
3. take_screenshot()          → AI verifies the result
```

---

#### `tap`

Tap at a point on the simulator screen.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `x` | int | required | Horizontal position in logical pixels (from left edge of device screen) |
| `y` | int | required | Vertical position in logical pixels (from top edge of device screen) |
| `udid` | string | auto | Simulator UDID |

Coordinates use the same space as screenshots. `(0, 0)` is the top-left corner of the device screen (not the window chrome).

> Requires Accessibility permission — see above.

```
# Example prompt
"Tap the Login button"
→ AI calls take_screenshot() to see where Login is, then tap(x=196, y=512)
```

---

#### `swipe`

Perform a swipe gesture between two points.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `x1` | int | required | Start X |
| `y1` | int | required | Start Y |
| `x2` | int | required | End X |
| `y2` | int | required | End Y |
| `duration` | float | `0.5` | Swipe duration in seconds |
| `udid` | string | auto | Simulator UDID |

```
# Scroll down a list
swipe(x1=196, y1=600, x2=196, y2=200, duration=0.4)

# Swipe left (e.g. next page in onboarding)
swipe(x1=350, y1=400, x2=40, y2=400, duration=0.3)
```

> Requires Accessibility permission — see above.

---

#### `input_text`

Type text into the currently focused text field on the simulator.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | required | Text to type |
| `udid` | string | auto | Simulator UDID |

Tap the target field first to focus it, then call `input_text`.

```
# Tap the email field, then type
tap(x=196, y=280)
input_text(text="user@example.com")
```

---

### App control

#### `launch_app`

Launch an app on the simulator.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bundle_id` | string | required | App bundle ID (e.g. `com.example.MyApp`) |
| `udid` | string | auto | Simulator UDID |
| `wait_for_debugger` | bool | `false` | Pause on launch until a debugger attaches |

```
launch_app(bundle_id="com.example.MyApp")
```

---

#### `terminate_app`

Force-terminate a running app.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bundle_id` | string | required | App bundle ID |
| `udid` | string | auto | Simulator UDID |

---

#### `open_url`

Open a URL or deep link in the simulator. Useful for testing deep link routing without tapping through the UI.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | required | URL or deep link |
| `udid` | string | auto | Simulator UDID |

```
open_url(url="myapp://home/settings")
open_url(url="https://example.com")
```

---

#### `uninstall_app`

Remove an app and all its data from the simulator. Equivalent to long-pressing → Remove App on device.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bundle_id` | string | required | App bundle ID |
| `udid` | string | auto | Simulator UDID |

---

### Permissions

#### `grant_permission` / `revoke_permission`

Grant or revoke a privacy permission for an app without going through the system dialog.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bundle_id` | string | required | App bundle ID |
| `permission` | string | required | Permission name (see below) |
| `udid` | string | auto | Simulator UDID |

Available permissions: `all`, `calendar`, `camera`, `contacts`, `faceid`, `homekit`, `location`, `medialibrary`, `microphone`, `motion`, `photos`, `reminders`, `siri`

```
grant_permission(bundle_id="com.example.MyApp", permission="camera")
revoke_permission(bundle_id="com.example.MyApp", permission="photos")
```

---

### Sensor simulation

#### `set_location`

Override the GPS coordinates reported to all apps on the simulator.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `latitude` | float | required | Decimal degrees (e.g. `40.7128`) |
| `longitude` | float | required | Decimal degrees (e.g. `-74.0060`) |
| `udid` | string | auto | Simulator UDID |

```
set_location(latitude=48.8566, longitude=2.3522)  # Paris
```

---

#### `set_appearance`

Switch between light and dark mode.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | string | required | `"light"` or `"dark"` |
| `udid` | string | auto | Simulator UDID |

---

#### `set_battery`

Override the battery indicator in the status bar.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | int | required | Battery percentage `0`–`100` |
| `state` | string | `"charged"` | `"charged"`, `"charging"`, `"discharging"`, or `"unknown"` |
| `udid` | string | auto | Simulator UDID |

```
set_battery(level=15, state="discharging")  # test low-battery UI
```

---

### Logs

#### `get_logs`

Stream simulator system logs for a short period and return the captured lines. Useful for debugging crashes, reading print statements, and checking network errors.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `process` | string | — | Filter by process name, e.g. `"Runner"` or your app name |
| `keyword` | string | — | Keep only lines containing this string (case-insensitive) |
| `lines` | int | `100` | Max lines to return |
| `timeout_seconds` | int | `3` | How long to stream before stopping |
| `udid` | string | auto | Simulator UDID |

```
# Get the last 50 log lines from your app
get_logs(process="MyApp", lines=50)

# Find crash-related lines
get_logs(keyword="crash", timeout_seconds=5)

# Flutter / React Native: filter by your process
get_logs(process="Runner", keyword="ERROR")
```

Returns: `lines[]`, `count`, `stderr`

---

### Media & recording

#### `add_media`

Inject a photo or video file into the simulator's Photos library. Useful for testing image picker flows.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | required | Absolute path to an image or video file |
| `udid` | string | auto | Simulator UDID |

```
add_media(file_path="/Users/you/Desktop/test-photo.jpg")
```

---

#### `start_video_recording`

Start recording the simulator screen to an `.mp4` file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | string | `/tmp/sim_recording_<timestamp>.mp4` | Output file path |
| `udid` | string | auto | Simulator UDID |

Returns the output path and PID. Call `stop_video_recording()` to finalize the file.

---

#### `stop_video_recording`

Stop an active screen recording and save the file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `udid` | string | auto | Simulator UDID |

Returns: `output_path`, `size_bytes`

---

## Example workflows

### Test a login flow end-to-end

```
1. boot_simulator(udid="...")          boot iPhone 16 Pro
2. launch_app(bundle_id="com.myapp")  open the app
3. take_screenshot()                   confirm login screen is shown
4. tap(x=196, y=320)                  tap email field
5. input_text(text="test@example.com")
6. tap(x=196, y=390)                  tap password field
7. input_text(text="secret123")
8. tap(x=196, y=490)                  tap Login button
9. take_screenshot()                   verify logged-in state
```

### Test location-based features

```
1. grant_permission(bundle_id="com.myapp", permission="location")
2. set_location(latitude=40.7128, longitude=-74.0060)  New York
3. launch_app(bundle_id="com.myapp")
4. take_screenshot()                                   verify location shown
```

### Debug a crash

```
1. launch_app(bundle_id="com.myapp")
2. get_logs(process="MyApp", keyword="error", timeout_seconds=10)
   → returns relevant error lines
3. open_url(url="myapp://the-crashing-screen")
4. get_logs(process="MyApp", lines=200)
```

### Record a demo video

```
1. start_video_recording(output_path="/tmp/demo.mp4")
2. ... perform actions ...
3. stop_video_recording()   → returns /tmp/demo.mp4
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IOS_SIM_DEFAULT_UDID` | auto-detect | Pin a specific simulator UDID |
| `IOS_SIM_DEVICE_WIDTH` | auto-detect | Logical screen width in points, used for coordinate mapping in `tap`/`swipe`. Set this if your device is not in the built-in lookup table |
| `IOS_SIM_LOG_FILE` | stderr only | Path to write server logs in addition to stderr |

---

## Limitations

- **macOS only.** Requires Xcode 14+ with iOS Simulator.
- `tap` and `swipe` require Accessibility permission for the process running the server (terminal or MCP client). See [Accessibility permission](#accessibility-permission-required-for-tap--swipe).
- `tap` / `swipe` bring the Simulator window to the foreground.
- Device width auto-detection covers iPhone 12 and later. For older or iPad device types, set `IOS_SIM_DEVICE_WIDTH` manually.
- One video recording active per simulator at a time.

---

## License

MIT
