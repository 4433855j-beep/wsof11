"""원격 화면 보기 + 마우스/키보드 조작 API (mss, Pillow, pyautogui 필요)."""
import io
import sys
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from .security import audit

ALLOWED_KEYS = {
    "enter", "esc", "tab", "backspace", "delete", "space", "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown", "win", "command", "ctrl", "alt", "shift", "option",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "volumeup", "volumedown", "volumemute", "playpause", "nexttrack", "prevtrack", "printscreen",
}


class MouseBody(BaseModel):
    action: str  # move | click | right | double | scroll | down | up
    x: float = 0.5  # 화면 대비 비율 0~1
    y: float = 0.5
    amount: int = 0  # scroll


class KeyBody(BaseModel):
    text: str = ""
    keys: list[str] = []  # 동시에 누를 키 조합 예: ["ctrl", "c"]


def _require(name: str):
    try:
        return __import__(name)
    except (ImportError, SystemExit, Exception) as e:  # pyautogui 는 리눅스에서 tkinter 없으면 SystemExit
        raise HTTPException(501, f"{name} 를 사용할 수 없습니다(pip install -r requirements-optional.txt): {e}")


def build_router(cfg) -> APIRouter:
    r = APIRouter(prefix="/api/screen")

    def check():
        if not cfg.enable_remote_screen:
            raise HTTPException(403, "설정에서 원격 화면 기능이 꺼져 있습니다.")

    def gui():
        g = _require("pyautogui")
        g.FAILSAFE = False
        g.PAUSE = 0
        return g

    @r.get("/shot")
    def shot(quality: int = 60, width: int = 1280):
        check()
        mss = _require("mss")
        _require("PIL")
        from PIL import Image

        with mss.mss() as s:
            mon = s.monitors[1]  # 주 모니터
            raw = s.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        w = max(320, min(width, img.width))
        if img.width > w:
            img = img.resize((w, round(img.height * w / img.width)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=max(20, min(quality, 90)))
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @r.post("/mouse")
    def mouse(body: MouseBody):
        check()
        g = gui()
        sw, sh = g.size()
        x = int(max(0.0, min(body.x, 1.0)) * (sw - 1))
        y = int(max(0.0, min(body.y, 1.0)) * (sh - 1))
        a = body.action
        if a == "move":
            g.moveTo(x, y)
        elif a == "click":
            g.click(x, y)
        elif a == "right":
            g.click(x, y, button="right")
        elif a == "double":
            g.doubleClick(x, y)
        elif a == "down":
            g.mouseDown(x, y)
        elif a == "up":
            g.mouseUp(x, y)
        elif a == "scroll":
            g.scroll(int(body.amount), x=x, y=y)
        else:
            raise HTTPException(400, "지원하지 않는 동작입니다.")
        return {"ok": True}

    @r.post("/keyboard")
    def keyboard(request: Request, body: KeyBody):
        check()
        g = gui()
        if body.keys:
            keys = [k.lower() for k in body.keys]
            if sys.platform == "darwin":  # macOS: Windows 키 → Command, Ctrl 단축키 → Command
                keys = ["command" if k in ("win", "ctrl") else k for k in keys]
            for k in keys:
                if k not in ALLOWED_KEYS and not (len(k) == 1 and k.isprintable()):
                    raise HTTPException(400, f"지원하지 않는 키: {k}")
            g.hotkey(*keys)
        if body.text:
            _type_text(g, body.text)
        audit(request, "keyboard", keys=body.keys, length=len(body.text))
        return {"ok": True}

    return r


def _type_text(g, text: str) -> None:
    """한글 등 비ASCII 문자는 pyautogui.write 로 입력되지 않으므로 클립보드 붙여넣기로 처리."""
    if text.isascii():
        g.write(text, interval=0.01)
        return
    try:
        import pyperclip  # type: ignore
    except ImportError:
        raise HTTPException(501, "한글 입력에는 pyperclip 이 필요합니다(pip install pyperclip).")
    old = pyperclip.paste()
    pyperclip.copy(text)
    g.hotkey("command" if sys.platform == "darwin" else "ctrl", "v")
    time.sleep(0.2)
    pyperclip.copy(old)
