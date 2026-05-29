#!/usr/bin/env python3
"""
iOS Simulator MCP Server — exposes xcrun simctl controls to Claude and Cursor.

Provides tools for device management, UI interaction, app control,
sensor simulation, and log/recording access on macOS iOS Simulators.
"""

import base64
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

load_dotenv()

_log_file = os.environ.get("IOS_SIM_LOG_FILE")
_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
if _log_file:
    _handlers.append(logging.FileHandler(_log_file))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger("ios_simulator_mcp")

IOS_SIM_DEFAULT_UDID = os.environ.get("IOS_SIM_DEFAULT_UDID", "").strip()

# Logical screen widths by simulator device type identifier suffix.
# Used to convert simulator coordinates to macOS screen coordinates.
# Covers iPhone 12+ (earlier models not supported by current Xcode simulator).
_DEVICE_LOGICAL_WIDTHS: dict[str, int] = {
    # SE
    "iPhone-SE": 375,
    "iPhone-SE-(2nd-generation)": 375,
    "iPhone-SE-(3rd-generation)": 375,
    # Mini
    "iPhone-12-mini": 375,
    "iPhone-13-mini": 375,
    # Standard / Pro (390pt)
    "iPhone-12": 390,
    "iPhone-12-Pro": 390,
    "iPhone-13": 390,
    "iPhone-13-Pro": 390,
    "iPhone-14": 390,
    # Standard / Pro (393pt, iPhone 14 Pro+)
    "iPhone-14-Pro": 393,
    "iPhone-15": 393,
    "iPhone-15-Pro": 393,
    "iPhone-16": 393,
    "iPhone-16-Pro": 393,
    # Plus / Pro Max (428-430pt)
    "iPhone-12-Pro-Max": 428,
    "iPhone-13-Pro-Max": 428,
    "iPhone-14-Plus": 428,
    "iPhone-14-Pro-Max": 430,
    "iPhone-15-Plus": 430,
    "iPhone-15-Pro-Max": 430,
    "iPhone-16-Plus": 430,
    "iPhone-16-Pro-Max": 430,
}
_device_width_cache: dict[str, int] = {}

# Track active video recording processes: udid -> (pid, output_path)
_recording_procs: dict[str, tuple[int, str]] = {}

mcp = FastMCP("ios-simulator")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(args: list[str], timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess and return the result."""
    logger.info("run: %s", " ".join(args))
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def _resolve_udid(udid: Optional[str]) -> str:
    """Return provided udid, env default, or auto-detect the first Booted simulator."""
    if udid:
        return udid
    if IOS_SIM_DEFAULT_UDID:
        return IOS_SIM_DEFAULT_UDID

    result = _run(["xcrun", "simctl", "list", "devices", "--json"])
    data = json.loads(result.stdout)
    for runtime_devices in data.get("devices", {}).values():
        for device in runtime_devices:
            if device.get("state") == "Booted":
                logger.info("auto-resolved udid: %s (%s)", device["udid"], device["name"])
                return device["udid"]

    raise RuntimeError(
        "No booted simulator found. Boot one with boot_simulator() or pass udid explicitly."
    )


def _simctl(*args: str, timeout: int = 30) -> dict[str, Any]:
    """Run xcrun simctl <args> and return stdout/stderr/exit_code."""
    cmd = ["xcrun", "simctl"] + list(args)
    try:
        result = _run(cmd, timeout=timeout, check=False)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Command timed out after {timeout}s", "exit_code": -1, "success": False}
    except Exception as e:
        logger.error("simctl error: %s", e)
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "success": False}


def _get_device_logical_width(udid: str) -> int:
    """Return the logical screen width (pts) for a given simulator UDID.

    Priority: IOS_SIM_DEVICE_WIDTH env var → device type lookup → 393 default.
    Results are cached per UDID to avoid redundant simctl calls.
    """
    override = os.environ.get("IOS_SIM_DEVICE_WIDTH")
    if override:
        return int(override)

    if udid in _device_width_cache:
        return _device_width_cache[udid]

    try:
        result = _run(["xcrun", "simctl", "list", "devices", "--json"])
        data = json.loads(result.stdout)
        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("udid") == udid:
                    dt_id = device.get("deviceTypeIdentifier", "")
                    # "com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro" → "iPhone-16-Pro"
                    type_name = dt_id.split(".")[-1]
                    width = _DEVICE_LOGICAL_WIDTHS.get(type_name, 393)
                    _device_width_cache[udid] = width
                    logger.info("device width: %s → %dpt (type=%s)", udid, width, type_name)
                    return width
    except Exception as e:
        logger.warning("could not detect device width: %s, falling back to 393", e)

    _device_width_cache[udid] = 393
    return 393


# ─── Device Management ────────────────────────────────────────────────────────

@mcp.tool()
def list_simulators(
    runtime_filter: Optional[str] = None,
    state_filter: Optional[str] = None,
) -> dict[str, Any]:
    """List all available iOS simulators with their name, UDID, and state.

    Args:
        runtime_filter: Filter by runtime name fragment (e.g. 'iOS 17', 'iOS 18')
        state_filter: Filter by state: 'Booted', 'Shutdown', or None for all
    """
    result = _run(["xcrun", "simctl", "list", "devices", "--json"])
    data = json.loads(result.stdout)

    devices = []
    for runtime, runtime_devices in data.get("devices", {}).items():
        if runtime_filter and runtime_filter.lower() not in runtime.lower():
            continue
        for device in runtime_devices:
            if state_filter and device.get("state") != state_filter:
                continue
            devices.append({
                "udid": device["udid"],
                "name": device["name"],
                "state": device.get("state", "Unknown"),
                "runtime": runtime,
                "is_available": device.get("isAvailable", False),
            })

    booted = [d for d in devices if d["state"] == "Booted"]
    return {
        "devices": devices,
        "total": len(devices),
        "booted_count": len(booted),
        "booted": booted,
    }


@mcp.tool()
def get_booted_simulator() -> dict[str, Any]:
    """Get the currently booted simulator(s). Returns the primary booted device.

    This is the device used automatically when no udid is specified in other tools.
    """
    result = _run(["xcrun", "simctl", "list", "devices", "--json"])
    data = json.loads(result.stdout)

    booted = []
    for runtime, runtime_devices in data.get("devices", {}).items():
        for device in runtime_devices:
            if device.get("state") == "Booted":
                booted.append({
                    "udid": device["udid"],
                    "name": device["name"],
                    "state": "Booted",
                    "runtime": runtime,
                })

    if not booted:
        return {"booted": [], "primary": None, "message": "No simulator is currently booted."}

    return {
        "booted": booted,
        "primary": booted[0],
        "count": len(booted),
    }


@mcp.tool()
def boot_simulator(udid: str) -> dict[str, Any]:
    """Boot an iOS simulator by its UDID.

    Args:
        udid: The simulator UDID (get it from list_simulators)
    """
    return _simctl("boot", udid)


@mcp.tool()
def shutdown_simulator(udid: Optional[str] = None) -> dict[str, Any]:
    """Shutdown a booted iOS simulator.

    Args:
        udid: Simulator UDID. If omitted, shuts down the currently booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("shutdown", dev)


# ─── UI Control ───────────────────────────────────────────────────────────────

@mcp.tool()
def take_screenshot(udid: Optional[str] = None) -> list:
    """Take a screenshot of the simulator screen and return it as an image.

    The image is returned inline so the AI can visually analyse the current UI state.

    Args:
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name

    try:
        result = _run(["xcrun", "simctl", "io", dev, "screenshot", path])
        if result.returncode != 0:
            return [TextContent(type="text", text=f"Screenshot failed: {result.stderr}")]

        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        logger.info("screenshot captured: %s bytes (udid=%s)", len(data), dev)
        return [ImageContent(type="image", data=data, mimeType="image/png")]
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _get_simulator_window_bounds() -> tuple[int, int, int, int] | None:
    """Return (win_x, win_y, win_w, win_h) of the frontmost Simulator window via AppleScript."""
    script = (
        'tell application "System Events" to tell process "Simulator" '
        'to get {position, size} of window 1'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        parts = [int(p.strip()) for p in result.stdout.strip().split(",")]
        return parts[0], parts[1], parts[2], parts[3]
    except Exception as e:
        logger.warning("get_simulator_window_bounds failed: %s", e)
        return None


def _sim_to_screen(
    sim_x: int, sim_y: int,
    win_x: int, win_y: int, win_w: int, win_h: int,
    device_width: int = 393,
) -> tuple[int, int]:
    """Convert simulator logical coordinates to macOS screen coordinates."""
    title_bar_h = 28
    bezel_left = max((win_w - device_width) // 2, 0)
    screen_x = win_x + bezel_left + sim_x
    screen_y = win_y + title_bar_h + sim_y
    return screen_x, screen_y


@mcp.tool()
def tap(
    x: int,
    y: int,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Send a tap gesture at screen coordinates on the simulator.

    Uses AppleScript / System Events to click the Simulator window at the
    given logical screen coordinates (same coordinate space as screenshots).

    Args:
        x: Horizontal coordinate in points (from left of device screen)
        y: Vertical coordinate in points (from top of device screen)
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    device_width = _get_device_logical_width(dev)

    subprocess.run(["osascript", "-e", 'tell application "Simulator" to activate'],
                   capture_output=True, timeout=5)
    time.sleep(0.2)

    bounds = _get_simulator_window_bounds()
    if not bounds:
        return {"success": False, "error": "Could not determine Simulator window bounds via AppleScript"}

    win_x, win_y, win_w, win_h = bounds
    sx, sy = _sim_to_screen(x, y, win_x, win_y, win_w, win_h, device_width)

    script = f'tell application "System Events" to click at {{{sx}, {sy}}}'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)

    logger.info("tap: sim(%d,%d) → screen(%d,%d), win=(%d,%d,%dx%d), device_width=%d",
                x, y, sx, sy, win_x, win_y, win_w, win_h, device_width)

    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip(), "screen_x": sx, "screen_y": sy}

    return {"success": True, "sim_x": x, "sim_y": y, "screen_x": sx, "screen_y": sy}


@mcp.tool()
def input_text(
    text: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Type text into the currently focused field on the simulator.

    Args:
        text: The text string to type. Spaces must be URL-encoded as %20 if needed.
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("io", dev, "sendstring", text)


@mcp.tool()
def swipe(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration: float = 0.5,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Perform a swipe gesture on the simulator screen.

    Args:
        x1: Start X coordinate
        y1: Start Y coordinate
        x2: End X coordinate
        y2: End Y coordinate
        duration: Swipe duration in seconds (default 0.5)
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    device_width = _get_device_logical_width(dev)

    subprocess.run(["osascript", "-e", 'tell application "Simulator" to activate'],
                   capture_output=True, timeout=5)
    time.sleep(0.2)

    bounds = _get_simulator_window_bounds()
    if not bounds:
        return {"success": False, "error": "Could not determine Simulator window bounds via AppleScript"}

    win_x, win_y, win_w, win_h = bounds
    sx1, sy1 = _sim_to_screen(x1, y1, win_x, win_y, win_w, win_h, device_width)
    sx2, sy2 = _sim_to_screen(x2, y2, win_x, win_y, win_w, win_h, device_width)

    steps = max(int(duration * 60), 5)
    script = f"""
tell application "System Events"
    tell process "Simulator"
        set startX to {sx1}
        set startY to {sy1}
        set endX to {sx2}
        set endY to {sy2}
        set steps to {steps}
        click at {{startX, startY}}
        delay 0.05
        repeat with i from 0 to steps
            set px to startX + (endX - startX) * i / steps
            set py to startY + (endY - startY) * i / steps
            click at {{px as integer, py as integer}}
            delay {round(duration / steps, 4)}
        end repeat
    end tell
end tell
"""
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)

    logger.info("swipe: sim(%d,%d)->(%d,%d) → screen(%d,%d)->(%d,%d), device_width=%d",
                x1, y1, x2, y2, sx1, sy1, sx2, sy2, device_width)

    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}

    return {"success": True, "from": {"sim_x": x1, "sim_y": y1}, "to": {"sim_x": x2, "sim_y": y2}}


# ─── App & Deep-Link Control ──────────────────────────────────────────────────

@mcp.tool()
def launch_app(
    bundle_id: str,
    udid: Optional[str] = None,
    wait_for_debugger: bool = False,
) -> dict[str, Any]:
    """Launch an app on the simulator by bundle identifier.

    Args:
        bundle_id: The app bundle ID (e.g. 'com.example.MyApp')
        udid: Simulator UDID. If omitted, uses the booted simulator.
        wait_for_debugger: If true, pause on launch until a debugger attaches
    """
    dev = _resolve_udid(udid)
    args = ["launch", dev, bundle_id]
    if wait_for_debugger:
        args.append("--wait-for-debugger")
    return _simctl(*args)


@mcp.tool()
def terminate_app(
    bundle_id: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Terminate a running app on the simulator.

    Args:
        bundle_id: The app bundle ID (e.g. 'com.example.MyApp')
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("terminate", dev, bundle_id)


@mcp.tool()
def open_url(
    url: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Open a URL or deep link in the simulator.

    Useful for deep link navigation without manually tapping through the UI.

    Args:
        url: URL or deep link to open (e.g. 'myapp://home', 'https://example.com')
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("openurl", dev, url)


@mcp.tool()
def grant_permission(
    bundle_id: str,
    permission: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Grant a privacy permission to an app on the simulator.

    Args:
        bundle_id: The app bundle ID (e.g. 'com.example.MyApp')
        permission: Permission name. One of: all, calendar, camera, contacts,
                    faceid, homekit, location, medialibrary, microphone,
                    motion, photos, reminders, siri
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("privacy", dev, "grant", permission, bundle_id)


@mcp.tool()
def revoke_permission(
    bundle_id: str,
    permission: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Revoke a privacy permission from an app on the simulator.

    Args:
        bundle_id: The app bundle ID (e.g. 'com.example.MyApp')
        permission: Permission name. One of: all, calendar, camera, contacts,
                    faceid, homekit, location, medialibrary, microphone,
                    motion, photos, reminders, siri
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("privacy", dev, "revoke", permission, bundle_id)


@mcp.tool()
def uninstall_app(
    bundle_id: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Uninstall an app from the simulator (clears all app data).

    Args:
        bundle_id: The app bundle ID (e.g. 'com.example.MyApp')
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("uninstall", dev, bundle_id)


# ─── Sensor Simulation ────────────────────────────────────────────────────────

@mcp.tool()
def set_location(
    latitude: float,
    longitude: float,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Override the GPS location reported to apps on the simulator.

    Args:
        latitude: GPS latitude in decimal degrees (e.g. 40.7128)
        longitude: GPS longitude in decimal degrees (e.g. -74.0060)
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    return _simctl("location", dev, "set", f"{latitude},{longitude}")


@mcp.tool()
def set_appearance(
    mode: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Switch the simulator between light and dark mode.

    Args:
        mode: 'light' or 'dark'
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    if mode not in ("light", "dark"):
        return {"error": "mode must be 'light' or 'dark'", "success": False}
    dev = _resolve_udid(udid)
    return _simctl("ui", dev, "appearance", mode)


@mcp.tool()
def set_battery(
    level: int,
    state: str = "charged",
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Override the battery status bar indicator on the simulator.

    Args:
        level: Battery percentage 0-100
        state: Battery state: 'charged', 'charging', 'discharging', 'unknown'
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    if not 0 <= level <= 100:
        return {"error": "level must be between 0 and 100", "success": False}
    valid_states = ("charged", "charging", "discharging", "unknown")
    if state not in valid_states:
        return {"error": f"state must be one of {valid_states}", "success": False}
    dev = _resolve_udid(udid)
    return _simctl(
        "status_bar", dev, "override",
        "--batteryLevel", str(level),
        "--batteryState", state,
    )


# ─── Logs & Recording ─────────────────────────────────────────────────────────

@mcp.tool()
def get_logs(
    process: Optional[str] = None,
    keyword: Optional[str] = None,
    lines: int = 100,
    timeout_seconds: int = 3,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Capture recent system logs from the simulator for debugging crashes and errors.

    Streams logs briefly then stops, returning the captured output.

    Args:
        process: Filter by process name (e.g. 'Runner', 'MyApp')
        keyword: Filter lines containing this keyword (case-insensitive)
        lines: Maximum number of log lines to return (default 100)
        timeout_seconds: How long to stream logs before stopping (default 3s)
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)
    cmd = ["xcrun", "simctl", "spawn", dev, "log", "stream", "--style", "compact"]
    if process:
        cmd += ["--process", process]
    if keyword:
        cmd += ["--predicate", f'eventMessage CONTAINS[c] "{keyword}"']

    logger.info("get_logs: %s (timeout=%ds)", " ".join(cmd), timeout_seconds)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(timeout_seconds)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=5)

        log_lines = stdout.splitlines()
        if keyword:
            log_lines = [l for l in log_lines if keyword.lower() in l.lower()]
        log_lines = log_lines[-lines:]

        return {
            "lines": log_lines,
            "count": len(log_lines),
            "stderr": stderr.strip()[:500] if stderr else "",
        }
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"lines": [], "count": 0, "error": "Log stream timed out"}
    except Exception as e:
        logger.error("get_logs error: %s", e)
        return {"lines": [], "count": 0, "error": str(e)}


@mcp.tool()
def add_media(
    file_path: str,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Inject a photo or video file into the simulator's photo library.

    Useful for testing image upload flows without needing real photos.

    Args:
        file_path: Absolute path to the image or video file to inject
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))
    if not os.path.isfile(resolved):
        return {"error": f"File not found: {resolved}", "success": False}
    dev = _resolve_udid(udid)
    return _simctl("addmedia", dev, resolved)


@mcp.tool()
def start_video_recording(
    output_path: Optional[str] = None,
    udid: Optional[str] = None,
) -> dict[str, Any]:
    """Start recording the simulator screen to a video file.

    Call stop_video_recording() to end the recording and save the file.

    Args:
        output_path: Path for the output .mp4 file. Defaults to /tmp/sim_recording_<timestamp>.mp4
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)

    if dev in _recording_procs:
        pid, path = _recording_procs[dev]
        return {
            "error": f"Already recording for {dev} (pid={pid}). Call stop_video_recording first.",
            "success": False,
            "output_path": path,
        }

    if not output_path:
        output_path = f"/tmp/sim_recording_{int(time.time())}.mp4"

    output_path = os.path.realpath(os.path.expanduser(output_path))
    cmd = ["xcrun", "simctl", "io", dev, "recordVideo", output_path]
    logger.info("start_video_recording: %s -> %s", dev, output_path)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _recording_procs[dev] = (proc.pid, output_path)

    time.sleep(0.5)
    if proc.poll() is not None:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        del _recording_procs[dev]
        return {"error": f"Recording process exited immediately: {stderr}", "success": False}

    return {
        "success": True,
        "pid": proc.pid,
        "output_path": output_path,
        "message": "Recording started. Call stop_video_recording() to save.",
    }


@mcp.tool()
def stop_video_recording(udid: Optional[str] = None) -> dict[str, Any]:
    """Stop an active screen recording and save the video file.

    Args:
        udid: Simulator UDID. If omitted, uses the booted simulator.
    """
    dev = _resolve_udid(udid)

    if dev not in _recording_procs:
        return {"error": f"No active recording for simulator {dev}", "success": False}

    pid, output_path = _recording_procs.pop(dev)
    logger.info("stop_video_recording: pid=%d, path=%s", pid, output_path)

    try:
        os.kill(pid, signal.SIGINT)
        time.sleep(1.5)

        if os.path.isfile(output_path):
            size = os.path.getsize(output_path)
            return {
                "success": True,
                "output_path": output_path,
                "size_bytes": size,
                "message": f"Video saved to {output_path}",
            }
        return {
            "success": False,
            "output_path": output_path,
            "error": "Recording stopped but output file was not found.",
        }
    except ProcessLookupError:
        return {"error": f"Process {pid} not found (already stopped?)", "success": False}
    except Exception as e:
        logger.error("stop_video_recording error: %s", e)
        return {"error": str(e), "success": False}


def main() -> None:
    logger.info(
        "Starting iOS Simulator MCP server (default_udid=%s)",
        IOS_SIM_DEFAULT_UDID or "auto-detect booted",
    )
    mcp.run()


if __name__ == "__main__":
    main()
