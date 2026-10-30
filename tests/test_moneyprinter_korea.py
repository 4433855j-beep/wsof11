import csv
import io
import urllib.parse

import pytest

from moneyprinter_korea import kto_photo
from moneyprinter_korea.__main__ import load_key
from moneyprinter_korea.keywords import to_video_terms

SAMPLE = {
    "response": {
        "header": {"resultCode": "0000", "resultMsg": "OK"},
        "body": {
            "items": {
                "item": [
                    {
                        "galContentId": "1204940",
                        "galTitle": "남한산성",
                        "galWebImageUrl": "http://tong.visitkorea.or.kr/cms2/a.jpg",
                        "galPhotographyLocation": "경기도 광주시",
                        "galPhotographer": "한국관광공사 홍길동",
                        "galSearchKeyword": "남한산성, 성곽",
                    },
                    {"galContentId": "2", "galTitle": "이미지 없음"},
                ]
            }
        },
    }
}


def test_build_url_decodes_encoded_key():
    url = kto_photo.build_url("gallerySearchList1", "abc%2Bdef%3D%3D", keyword="서울")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert url.startswith(kto_photo.BASE_URL + "/gallerySearchList1?")
    assert q["serviceKey"] == ["abc+def=="]
    assert q["keyword"] == ["서울"]
    assert q["_type"] == ["json"] and q["MobileOS"] == ["ETC"]


def test_parse_items_skips_rows_without_image():
    photos = kto_photo.parse_items(SAMPLE)
    assert len(photos) == 1
    assert photos[0].title == "남한산성"
    assert photos[0].photographer == "한국관광공사 홍길동"


def test_parse_items_single_item_and_empty():
    single = {"response": {"header": {"resultCode": "0000"}, "body": {"items": {"item": SAMPLE["response"]["body"]["items"]["item"][0]}}}}
    assert len(kto_photo.parse_items(single)) == 1
    empty = {"response": {"header": {"resultCode": "0000"}, "body": {"items": ""}}}
    assert kto_photo.parse_items(empty) == []


def test_parse_items_error_code():
    with pytest.raises(kto_photo.KtoPhotoError):
        kto_photo.parse_items({"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}}})


def test_download_writes_credits(tmp_path, monkeypatch):
    monkeypatch.setattr(kto_photo.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"jpg"))
    saved = kto_photo.download(kto_photo.parse_items(SAMPLE), str(tmp_path))
    assert len(saved) == 1 and open(saved[0], "rb").read() == b"jpg"
    rows = list(csv.DictReader(open(tmp_path / "credits.csv", encoding="utf-8-sig")))
    assert rows[0]["photographer"] == "한국관광공사 홍길동"
    assert "공공누리" in rows[0]["license"]


def test_load_key_from_config(tmp_path, monkeypatch):
    monkeypatch.delenv("KTO_PHOTO_API_KEY", raising=False)
    cfg = tmp_path / "config.toml"
    cfg.write_text('[app]\nkto_photo_api_keys = ["my-key"]\n', encoding="utf-8")
    assert load_key(str(cfg)) == "my-key"


def test_to_video_terms():
    assert "Seoul city" in to_video_terms("도시 풍경")
    assert to_video_terms("반도체") == ["Korea 반도체"]


def test_daegu_metro_preset(monkeypatch, tmp_path):
    from moneyprinter_korea import __main__ as cli
    from moneyprinter_korea.keywords import PRESETS

    searched = []
    monkeypatch.setenv("KTO_PHOTO_API_KEY", "k")
    monkeypatch.setattr(cli.kto_photo, "search", lambda key, kw, count: searched.append(kw) or [])
    monkeypatch.setattr(cli.kto_photo, "download", lambda photos, out: [])
    cli.main(["--preset", "daegu-metro", "--out", str(tmp_path)])
    assert searched == PRESETS["daegu-metro"]["photo_keywords"]
    assert "Daegu monorail" in to_video_terms("대구 도시철도")
