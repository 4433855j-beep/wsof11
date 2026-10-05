"""실행: python -m pclink

노트북에서 실행하면 접속 주소와 QR 코드를 보여준다. 휴대폰으로 QR을 찍으면 바로 로그인된다.
"""
import argparse
import socket
import sys

import uvicorn

from .app import create_app
from .config import load_config
from .platform_utils import enable_dpi_awareness


def lan_ips() -> list[str]:
    ips = []
    try:
        import psutil

        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family == socket.AF_INET and not a.address.startswith(("127.", "169.254.")):
                    ips.append(a.address)
    except Exception:
        pass
    return ips or ["127.0.0.1"]


def print_qr(url: str) -> None:
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.print_ascii(invert=True)
    except ImportError:
        print("  (QR 표시: pip install qrcode)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pclink", description="휴대폰으로 노트북 원격 조작")
    parser.add_argument("--port", type=int)
    parser.add_argument("--host")
    parser.add_argument("--show-token", action="store_true", help="접속 코드만 출력")
    parser.add_argument("--reset-token", action="store_true", help="접속 코드를 새로 발급(기존 휴대폰 로그아웃)")
    args = parser.parse_args()

    cfg = load_config()
    if args.reset_token:
        cfg.token = ""
        cfg.save()
        cfg = load_config()
        print("새 접속 코드가 발급되었습니다.")
    if args.show_token:
        print(cfg.token)
        return
    if args.port:
        cfg.port = args.port
    if args.host:
        cfg.host = args.host

    enable_dpi_awareness()
    scheme = "https" if cfg.cert_file and cfg.key_file else "http"
    print("=" * 60)
    print(" PC Link 실행 중 — 휴대폰과 노트북이 같은 와이파이에 있어야 합니다")
    print(f" 설정 파일: {cfg.path}")
    print(f" 접속 코드: {cfg.token}")
    for ip in lan_ips():
        print(f" 휴대폰 주소: {scheme}://{ip}:{cfg.port}")
    first = f"{scheme}://{lan_ips()[0]}:{cfg.port}/#token={cfg.token}"
    print(" 아래 QR을 휴대폰 카메라로 찍으면 자동 로그인됩니다:")
    print_qr(first)
    print(" 종료: Ctrl+C")
    print("=" * 60)
    sys.stdout.flush()

    uvicorn.run(
        create_app(cfg),
        host=cfg.host,
        port=cfg.port,
        log_level="warning",
        ssl_certfile=cfg.cert_file or None,
        ssl_keyfile=cfg.key_file or None,
    )


if __name__ == "__main__":
    main()
