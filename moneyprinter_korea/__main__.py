"""한국 소재 내려받기 CLI.

예) python -m moneyprinter_korea 서울 야경 한옥마을 --count 15 --out ./korea_materials
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from . import kto_photo
from .keywords import to_video_terms


def load_key(config_path: str | None) -> str:
    key = os.environ.get("KTO_PHOTO_API_KEY", "")
    if key:
        return key
    if config_path and os.path.exists(config_path):
        # MoneyPrinterTurbo config.toml 의 kto_photo_api_keys = ["..."] 첫 번째 값
        with open(config_path, encoding="utf-8") as f:
            m = re.search(r'^\s*kto_photo_api_keys\s*=\s*\[\s*"([^"]+)"', f.read(), re.M)
        if m:
            return m.group(1)
    return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="한국관광공사 관광사진을 MoneyPrinterTurbo 로컬 소재로 내려받기")
    ap.add_argument("keywords", nargs="+", help="검색어(예: 서울 야경 한옥마을 제주)")
    ap.add_argument("--count", type=int, default=10, help="검색어별 사진 수 (기본 10)")
    ap.add_argument("--out", default="korea_materials", help="저장 폴더")
    ap.add_argument("--config", default="config.toml", help="MoneyPrinterTurbo config.toml 경로")
    args = ap.parse_args(argv)

    key = load_key(args.config)
    if not key:
        print("인증키가 없습니다. 환경변수 KTO_PHOTO_API_KEY 또는 config.toml 의 kto_photo_api_keys 를 설정하세요.")
        return 2

    total = 0
    for kw in args.keywords:
        try:
            photos = kto_photo.search(key, kw, count=args.count)
        except kto_photo.KtoPhotoError as e:
            print(f"[{kw}] {e}")
            continue
        saved = kto_photo.download(photos, args.out)
        total += len(saved)
        print(f"[{kw}] 사진 {len(saved)}장 저장 / Pexels·Pixabay 추천 영문 검색어: {', '.join(to_video_terms(kw))}")

    print(f"\n완료: {total}장 → {os.path.abspath(args.out)} (출처 목록: credits.csv)")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
