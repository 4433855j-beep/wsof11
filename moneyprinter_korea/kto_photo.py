"""한국관광공사 관광사진 정보 API(PhotoGalleryService1) 클라이언트.

공공데이터포털에서 '한국관광공사_관광사진 정보'를 활용신청해 받은 인증키로
키워드(예: 서울, 한옥마을, 야경) 사진을 검색하고 내려받는다.
"""

from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

BASE_URL = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
APP_NAME = "MoneyPrinterKorea"
TIMEOUT = 30

# 공공데이터포털 표시 기준: 관광사진은 공공누리 제1유형·제3유형 자료가 섞여 제공된다.
LICENSE_NOTE = (
    "한국관광공사 관광사진(공공누리 제1유형 또는 제3유형). "
    "출처 표시 필수, 제3유형은 변경 금지 — 원본 페이지에서 유형 확인 후 사용"
)


class KtoPhotoError(RuntimeError):
    pass


@dataclass
class KtoPhoto:
    content_id: str
    title: str
    image_url: str
    location: str
    photographer: str
    keywords: str
    shot_month: str


def normalize_service_key(key: str) -> str:
    """'인코딩 키'(%2B 등 포함)를 넣어도 이중 인코딩되지 않도록 디코딩 키로 바꾼다."""
    key = key.strip()
    return urllib.parse.unquote(key) if "%" in key else key


def build_url(operation: str, service_key: str, **params) -> str:
    query = {
        "serviceKey": normalize_service_key(service_key),
        "MobileOS": "ETC",
        "MobileApp": APP_NAME,
        "_type": "json",
        **{k: v for k, v in params.items() if v is not None},
    }
    return f"{BASE_URL}/{operation}?{urllib.parse.urlencode(query)}"


def parse_items(payload: dict) -> list[KtoPhoto]:
    response = payload.get("response") or {}
    header = response.get("header") or {}
    if header.get("resultCode") != "0000":
        raise KtoPhotoError(
            f"관광사진 API 오류: {header.get('resultCode')} {header.get('resultMsg')}"
        )
    items = (response.get("body") or {}).get("items")
    if not items:
        return []
    item = items.get("item") if isinstance(items, dict) else None
    rows = item if isinstance(item, list) else [item] if item else []
    return [
        KtoPhoto(
            content_id=str(row.get("galContentId", "")),
            title=row.get("galTitle", ""),
            image_url=row.get("galWebImageUrl", ""),
            location=row.get("galPhotographyLocation", ""),
            photographer=row.get("galPhotographer", ""),
            keywords=row.get("galSearchKeyword", ""),
            shot_month=str(row.get("galPhotographyMonth", "")),
        )
        for row in rows
        if row.get("galWebImageUrl")
    ]


def _get_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise KtoPhotoError(f"관광사진 API 접속 실패: {e}") from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        # 인증키 오류 등은 JSON 대신 XML 오류 메시지로 돌아온다.
        msg = re.search(r"<returnAuthMsg>(.*?)</returnAuthMsg>", body)
        raise KtoPhotoError(
            f"관광사진 API 응답 오류: {msg.group(1) if msg else body[:200]}"
        ) from e


def search(service_key: str, keyword: str, count: int = 20, page: int = 1) -> list[KtoPhoto]:
    # arrange: A=제목순, B=조회순, C=수정일순, D=생성일순
    url = build_url(
        "gallerySearchList1",
        service_key,
        keyword=keyword,
        numOfRows=count,
        pageNo=page,
        arrange="B",
    )
    return parse_items(_get_json(url))


def _safe_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_")[:40] or "photo"


def download(photos: list[KtoPhoto], out_dir: str) -> list[str]:
    """사진을 저장하고 출처 목록(credits.csv)을 함께 남긴다. 저장된 파일 경로 목록을 반환."""
    os.makedirs(out_dir, exist_ok=True)
    saved: list[str] = []
    credits_path = os.path.join(out_dir, "credits.csv")
    new_file = not os.path.exists(credits_path)
    with open(credits_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["file", *KtoPhoto.__dataclass_fields__, "license"])
        for p in photos:
            ext = os.path.splitext(urllib.parse.urlparse(p.image_url).path)[1] or ".jpg"
            path = os.path.join(out_dir, f"kto_{p.content_id}_{_safe_name(p.title)}{ext}")
            if not os.path.exists(path):
                try:
                    with urllib.request.urlopen(p.image_url, timeout=TIMEOUT) as r, open(path, "wb") as out:
                        out.write(r.read())
                except (urllib.error.URLError, OSError) as e:
                    print(f"  ! 내려받기 실패: {p.title} ({e})")
                    continue
                writer.writerow([os.path.basename(path), *asdict(p).values(), LICENSE_NOTE])
            saved.append(path)
    return saved
