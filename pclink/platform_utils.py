"""운영체제(Windows / macOS / Linux)별 동작 모음."""
import hashlib
import os
import shlex
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def _spawn(cmd: list[str]) -> None:
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WIN:
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def open_with_default_app(path: Path) -> None:
    """PC에서 파일/폴더를 기본 프로그램으로 연다."""
    if IS_WIN:
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif IS_MAC:
        _spawn(["open", str(path)])
    else:
        _spawn(["xdg-open", str(path)])


# ------------------------------------------------------------------ 앱 목록
def _app_id(kind: str, target: str) -> str:
    return hashlib.sha1(f"{kind}:{target}".encode()).hexdigest()[:16]


def discover_apps(custom: list[dict]) -> list[dict]:
    """PC에 설치된 프로그램(시작 메뉴/응용 프로그램 폴더)과 사용자 등록 프로그램 목록."""
    apps: list[dict] = []
    for item in custom:
        cmd = item.get("command")
        if isinstance(cmd, str):
            cmd = shlex.split(cmd, posix=not IS_WIN)
        if item.get("name") and cmd:
            apps.append({"id": _app_id("custom", " ".join(cmd)), "name": item["name"], "kind": "custom", "target": cmd})

    seen: set[str] = set()
    if IS_WIN:
        dirs = [
            Path(os.environ.get("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        ]
        for d in dirs:
            if not d.is_dir():
                continue
            for p in d.rglob("*"):
                if p.suffix.lower() in (".lnk", ".url") and "uninstall" not in p.stem.lower() and "제거" not in p.stem:
                    if p.stem.lower() in seen:
                        continue
                    seen.add(p.stem.lower())
                    apps.append({"id": _app_id("shortcut", str(p)), "name": p.stem, "kind": "shortcut", "target": str(p)})
    elif IS_MAC:
        for d in (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"):
            if not d.is_dir():
                continue
            for p in list(d.glob("*.app")) + list(d.glob("*/*.app")):
                if p.stem in seen:
                    continue
                seen.add(p.stem)
                apps.append({"id": _app_id("macapp", str(p)), "name": p.stem, "kind": "macapp", "target": str(p)})
    else:
        for d in (Path("/usr/share/applications"), Path.home() / ".local/share/applications", Path("/var/lib/flatpak/exports/share/applications")):
            if not d.is_dir():
                continue
            for p in d.glob("*.desktop"):
                info = _parse_desktop(p)
                if not info or info["name"] in seen:
                    continue
                seen.add(info["name"])
                apps.append({"id": _app_id("desktop", str(p)), "name": info["name"], "kind": "desktop", "target": info["exec"]})
    custom_count = len(custom)
    return apps[:custom_count] + sorted(apps[custom_count:], key=lambda a: a["name"].lower())


def _parse_desktop(p: Path) -> dict | None:
    name = exec_ = None
    in_entry = False
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            in_entry = line == "[Desktop Entry]"
            continue
        if not in_entry:
            continue
        if line.startswith("Name=") and name is None:
            name = line[5:]
        elif line.startswith("Exec="):
            exec_ = line[5:]
        elif line in ("NoDisplay=true", "Hidden=true"):
            return None
    if not name or not exec_:
        return None
    args = [a for a in shlex.split(exec_) if not (len(a) == 2 and a.startswith("%"))]
    return {"name": name, "exec": args} if args else None


def launch_app(app: dict) -> None:
    kind, target = app["kind"], app["target"]
    if kind == "shortcut":
        os.startfile(target)  # type: ignore[attr-defined]
    elif kind == "macapp":
        _spawn(["open", "-a", target])
    else:  # custom, desktop → 명령 목록
        _spawn(list(target))


# ------------------------------------------------------------------ 전원
def power_command(action: str) -> list[str]:
    if IS_WIN:
        table = {
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "restart": ["shutdown", "/r", "/t", "60"],
            "shutdown": ["shutdown", "/s", "/t", "60"],
            "cancel": ["shutdown", "/a"],
        }
    elif IS_MAC:
        table = {
            "lock": ["pmset", "displaysleepnow"],
            "sleep": ["pmset", "sleepnow"],
            "restart": ["osascript", "-e", 'tell application "System Events" to restart'],
            "shutdown": ["osascript", "-e", 'tell application "System Events" to shut down'],
        }
    else:
        table = {
            "lock": ["loginctl", "lock-session"],
            "sleep": ["systemctl", "suspend"],
            "restart": ["shutdown", "-r", "+1"],
            "shutdown": ["shutdown", "-h", "+1"],
            "cancel": ["shutdown", "-c"],
        }
    if action not in table:
        raise ValueError(action)
    return table[action]


def enable_dpi_awareness() -> None:
    """Windows 고해상도(배율) 환경에서 화면 캡처 좌표와 마우스 좌표를 일치시킨다."""
    if IS_WIN:
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
        except Exception:
            pass
