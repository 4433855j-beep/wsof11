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
}


def to_video_terms(topic: str) -> list[str]:
    """한국어 주제어를 영문 검색어 목록으로 바꾼다. 사전에 없으면 'Korea <주제>'를 쓴다."""
    for key, terms in KOREA_TERMS.items():
        if key in topic:
            return terms
    return [f"Korea {topic}"]
