"""설정 파일 로드/저장.

설정 파일 위치: ~/.pclink/config.json (환경변수 PCLINK_HOME 으로 변경 가능)
최초 실행 시 무작위 접속 토큰을 생성해 저장한다.
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path


def data_dir() -> Path:
    base = os.environ.get("PCLINK_HOME")
    path = Path(base) if base else Path.home() / ".pclink"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Config:
    # 휴대폰에서 최초 1회 입력(또는 QR 스캔)하는 접속 토큰
    token: str = ""
    host: str = "0.0.0.0"
    port: int = 8765
    # 비어 있으면 PC 전체 드라이브 접근 허용, 값이 있으면 해당 폴더 하위만 허용
    allowed_roots: list[str] = field(default_factory=list)
    # 위험 기능 on/off
    enable_terminal: bool = False
    enable_power: bool = True
    enable_remote_screen: bool = True
    # 사용자가 직접 등록하는 실행 프로그램 [{"name": "메모장", "command": ["notepad.exe"]}]
    apps: list[dict] = field(default_factory=list)
    # HTTPS 인증서(선택)
    cert_file: str = ""
    key_file: str = ""

    @property
    def path(self) -> Path:
        return data_dir() / "config.json"

    def save(self) -> None:
        self.path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass


def load_config() -> Config:
    path = data_dir() / "config.json"
    cfg = Config()
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {k: v for k, v in raw.items() if k in Config.__dataclass_fields__}
        cfg = Config(**known)
    if not cfg.token or len(cfg.token) < 16:
        cfg.token = secrets.token_urlsafe(24)
        cfg.save()
    return cfg
