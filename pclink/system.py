"""시스템 정보·프로그램 실행·프로세스·전원·클립보드·터미널 API."""
import os
import platform
import socket
import subprocess
import time

import psutil
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from . import platform_utils as pu
from .security import audit, resolve_path


class LaunchBody(BaseModel):
    id: str


class KillBody(BaseModel):
    pid: int
    force: bool = False


class PowerBody(BaseModel):
    action: str
    confirm: bool = False


class ClipBody(BaseModel):
    text: str


class RunBody(BaseModel):
    command: str
    cwd: str = ""
    timeout: int = 30


def build_router(cfg) -> APIRouter:
    r = APIRouter(prefix="/api")
    app_cache: dict = {"time": 0.0, "items": []}

    def apps() -> list[dict]:
        if time.time() - app_cache["time"] > 300:
            app_cache["items"] = pu.discover_apps(cfg.apps)
            app_cache["time"] = time.time()
        return app_cache["items"]

    # ---------------------------------------------------------- 정보
    @r.get("/system/info")
    def info():
        vm = psutil.virtual_memory()
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            if "snap" in part.mountpoint:
                continue
            disks.append({"mount": part.mountpoint, "total": u.total, "used": u.used, "percent": u.percent})
        return {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": psutil.cpu_percent(interval=0.3),
            "cpu_count": psutil.cpu_count(),
            "memory": {"total": vm.total, "used": vm.used, "percent": vm.percent},
            "disks": disks,
            "battery": {"percent": bat.percent, "plugged": bat.power_plugged} if bat else None,
            "boot_time": psutil.boot_time(),
            "features": {
                "terminal": cfg.enable_terminal,
                "power": cfg.enable_power,
                "screen": cfg.enable_remote_screen,
            },
        }

    # ---------------------------------------------------------- 프로그램
    @r.get("/apps")
    def list_apps(refresh: bool = False):
        if refresh:
            app_cache["time"] = 0
        return {"items": [{"id": a["id"], "name": a["name"], "kind": a["kind"]} for a in apps()]}

    @r.post("/apps/launch")
    def launch(request: Request, body: LaunchBody):
        app = next((a for a in apps() if a["id"] == body.id), None)
        if not app:
            raise HTTPException(404, "프로그램을 찾을 수 없습니다. 목록을 새로고침하세요.")
        try:
            pu.launch_app(app)
        except OSError as e:
            raise HTTPException(500, f"실행 실패: {e}")
        audit(request, "launch", name=app["name"])
        return {"ok": True}

    # ---------------------------------------------------------- 프로세스
    @r.get("/processes")
    def processes(q: str = ""):
        items = []
        for p in psutil.process_iter(["pid", "name", "username", "memory_info", "cpu_percent", "create_time"]):
            i = p.info
            if not i["name"] or (q and q.lower() not in i["name"].lower()):
                continue
            items.append(
                {
                    "pid": i["pid"],
                    "name": i["name"],
                    "user": i["username"],
                    "memory": i["memory_info"].rss if i["memory_info"] else 0,
                    "cpu": i["cpu_percent"] or 0.0,
                }
            )
        items.sort(key=lambda x: x["memory"], reverse=True)
        return {"items": items[:300]}

    @r.post("/processes/kill")
    def kill(request: Request, body: KillBody):
        if body.pid in (0, os.getpid()):
            raise HTTPException(400, "이 프로세스는 종료할 수 없습니다.")
        try:
            p = psutil.Process(body.pid)
            name = p.name()
            p.kill() if body.force else p.terminate()
        except psutil.NoSuchProcess:
            raise HTTPException(404, "이미 종료된 프로세스입니다.")
        except psutil.AccessDenied:
            raise HTTPException(403, "권한이 없습니다(관리자 권한 프로세스).")
        audit(request, "kill", pid=body.pid, name=name, force=body.force)
        return {"ok": True}

    # ---------------------------------------------------------- 전원
    @r.post("/system/power")
    def power(request: Request, body: PowerBody):
        if not cfg.enable_power:
            raise HTTPException(403, "설정에서 전원 제어가 꺼져 있습니다.")
        if body.action in ("restart", "shutdown", "sleep") and not body.confirm:
            raise HTTPException(400, "확인(confirm)이 필요합니다.")
        try:
            cmd = pu.power_command(body.action)
        except ValueError:
            raise HTTPException(400, "지원하지 않는 동작입니다.")
        audit(request, "power", action=body.action)
        try:
            subprocess.Popen(cmd)
        except OSError as e:
            raise HTTPException(500, f"실행 실패: {e}")
        return {"ok": True}

    # ---------------------------------------------------------- 클립보드
    @r.get("/clipboard")
    def clip_get():
        return {"text": _pyperclip().paste()}

    @r.post("/clipboard")
    def clip_set(request: Request, body: ClipBody):
        _pyperclip().copy(body.text)
        audit(request, "clipboard_set", length=len(body.text))
        return {"ok": True}

    # ---------------------------------------------------------- 터미널(기본 비활성)
    @r.post("/terminal/run")
    def run(request: Request, body: RunBody):
        if not cfg.enable_terminal:
            raise HTTPException(403, "설정에서 터미널 기능이 꺼져 있습니다(config.json → enable_terminal).")
        cwd = str(resolve_path(cfg, body.cwd)) if body.cwd else os.path.expanduser("~")
        audit(request, "terminal", command=body.command, cwd=cwd)
        try:
            res = subprocess.run(
                body.command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                timeout=max(1, min(body.timeout, 300)),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(408, "시간 초과로 중단되었습니다.")
        enc = "cp949" if pu.IS_WIN else "utf-8"
        return {
            "code": res.returncode,
            "stdout": res.stdout.decode(enc, errors="replace")[-200_000:],
            "stderr": res.stderr.decode(enc, errors="replace")[-50_000:],
        }

    return r


def _pyperclip():
    try:
        import pyperclip  # type: ignore

        return pyperclip
    except ImportError:
        raise HTTPException(501, "pyperclip 이 설치되지 않았습니다(pip install pyperclip).")
