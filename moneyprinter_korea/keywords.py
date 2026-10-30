"""한국 주제어 → Pexels/Pixabay 영문 검색어 변환.

Pexels·Pixabay는 영문 검색 품질이 높으므로, 한국 영상을 찾을 때는
'Korea'/'Seoul' 같은 지명을 붙인 영문 검색어를 MoneyPrinterTurbo의
'영상 키워드(video_terms)'에 넣는다.
"""

KOREA_TERMS: dict[str, list[str]] = {
    "정경": ["Korea landscape", "Korean countryside", "Korea mountains", "Jeju island"],
    "자연": ["Korea nature", "Korean mountain autumn", "Korea coast"],
    "도시": ["Seoul city", "Seoul skyline night", "Busan city", "Korea street"],
    "야경": ["Seoul night", "Han river night", "Busan night"],
    "전통": ["Gyeongbokgung palace", "Korean hanok", "Bukchon hanok village", "Korean traditional"],
    "정책": ["Korea government", "Korean office workers", "Korea public service", "Seoul city hall"],
    "복지": ["Korean elderly", "Korean family", "senior citizens Korea"],
    "교통": ["Seoul subway", "Korea bus", "Korea KTX train", "Seoul traffic"],
    "경제": ["Korea business", "Seoul business district", "Korea port container"],
    "교육": ["Korean students", "Korea school", "Korean university"],
    "농촌": ["Korea rice field", "Korean farm", "Korean village"],
    "대구": ["Daegu city", "Daegu monorail", "Daegu subway", "Daegu skyline"],
    "도시철도": ["Daegu monorail", "Daegu subway", "Korea subway train", "monorail city"],
}

# 배경 프리셋: 관광사진 검색어(한국관광공사)와 Pexels/Pixabay 영상 키워드 묶음
PRESETS: dict[str, dict[str, list[str]]] = {
    "daegu-metro": {
        "photo_keywords": [
            "대구 모노레일", "하늘열차", "대구 도시철도", "대구 지하철",
            "동대구역", "대구 3호선", "수성못", "대구 야경",
        ],
        # 대구 전용 영상이 적으므로 위에서부터 우선 사용. 아래 두 개는 대구가 아닐 수 있음
        "video_terms": [
            "Daegu monorail", "Daegu subway", "Daegu city", "Daegu skyline",
            "Korea subway train", "monorail city",
        ],
    },
}


def to_video_terms(topic: str) -> list[str]:
    """한국어 주제어를 영문 검색어 목록으로 바꾼다. 사전에 없으면 'Korea <주제>'를 쓴다."""
    # 긴 주제어 우선: '도시철도'가 '도시'(서울 도시 영상)로 잘못 매칭되지 않도록
    for key in sorted(KOREA_TERMS, key=len, reverse=True):
        if key in topic:
            return KOREA_TERMS[key]
    return [f"Korea {topic}"]
