"""인증(토큰 → 세션 쿠키), 무차별 대입 차단, 경로 검증, 감사 로그."""
from __future__ import annotations

import hmac
import json
import secrets
import threading
import time
from pathlib import Path

from fastapi import HTTPException, Request

from .config import Config, data_dir

SESSION_COOKIE = "pclink_session"
SESSION_TTL = 60 * 60 * 24 * 30  # 30일
MAX_FAILS = 5
LOCK_SECONDS = 300


class Auth:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._sessions: dict[str, float] = {}
        self._fails: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check_token(self, token: str, ip: str) -> bool:
        with self._lock:
            count, since = self._fails.get(ip, (0, 0.0))
            if count >= MAX_FAILS and time.time() - since < LOCK_SECONDS:
                raise HTTPException(429, "로그인 실패가 반복되어 5분간 차단되었습니다.")
        ok = hmac.compare_digest(token.encode(), self.cfg.token.encode())
        with self._lock:
            if ok:
                self._fails.pop(ip, None)
            else:
                count, since = self._fails.get(ip, (0, 0.0))
                if time.time() - since >= LOCK_SECONDS:
                    count = 0
                self._fails[ip] = (count + 1, time.time())
        return ok

    def new_session(self) -> str:
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[sid] = time.time() + SESSION_TTL
        return sid

    def drop_session(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def valid(self, request: Request) -> bool:
        sid = request.cookies.get(SESSION_COOKIE)
        if not sid:
            return False
        with self._lock:
            exp = self._sessions.get(sid)
            return bool(exp and exp > time.time())


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


# ---------------------------------------------------------------- 경로 검증
def resolve_path(cfg: Config, raw: str, follow_last: bool = True) -> Path:
    """사용자가 보낸 경로를 절대경로로 정규화하고 허용 범위인지 검사한다.

    follow_last=False 이면 마지막 항목이 바로가기(심볼릭 링크)여도 링크 자체를 가리킨다
    (삭제·이름변경·이동 시 링크 대상이 아닌 링크만 다루기 위함).
    """
    if not raw:
        raise HTTPException(400, "경로가 비어 있습니다.")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise HTTPException(400, "절대 경로만 사용할 수 있습니다.")
    if follow_last or path.parent == path or path.name in (".", ".."):
        path = path.resolve()
    else:
        path = path.parent.resolve() / path.name
    if cfg.allowed_roots and not any(_is_within(path, Path(r).expanduser().resolve()) for r in cfg.allowed_roots):
        raise HTTPException(403, "허용된 폴더 밖의 경로입니다.")
    return path


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- 감사 로그
_audit_lock = threading.Lock()


def audit(request: Request, action: str, **detail) -> None:
    line = json.dumps(
        {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "ip": client_ip(request), "action": action, **detail},
        ensure_ascii=False,
        default=str,
    )
    with _audit_lock:
        with open(data_dir() / "audit.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
