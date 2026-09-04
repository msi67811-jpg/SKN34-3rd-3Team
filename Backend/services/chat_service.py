from datetime import datetime

from fastapi import HTTPException

from core import store

SUGGESTED = {
    "tax": [
        "부가가치세는 언제 신고하나요?",
        "간이과세자와 일반과세자 차이는 무엇인가요?",
        "청년창업 세액감면 대상인지 알고 싶어요.",
    ],
    "expense": [
        "커피 영수증도 경비처리가 되나요?",
        "노트북 구매는 어떻게 비용 처리하나요?",
        "접대비와 복리후생비는 어떻게 구분하나요?",
    ],
    "saving": [
        "1인 창업자가 당장 챙길 절세 포인트는?",
        "홈택스에서 확인할 공제 항목이 있나요?",
        "사업용 계좌를 꼭 써야 하나요?",
    ],
    "policy": [
        "지금 신청 가능한 청년 창업 지원금이 있나요?",
        "예비창업패키지 자격 조건을 알려주세요.",
        "서울 거주 창업자가 받을 수 있는 정책은?",
    ],
}

MOCK_ANSWERS = {
    "tax": "세금 일정과 신고 유형은 사업자 등록 유형에 따라 달라집니다. 현재는 LLM 연동 전이라 샘플 안내입니다. 실제 신고 전에는 국세청 자료 또는 세무 전문가 확인이 필요합니다.",
    "expense": "사업과 직접 관련된 지출은 증빙이 있으면 경비로 볼 여지가 있습니다. 현재는 OCR/LLM 연동 전 샘플 답변이며, 최종 인정 여부는 세무서·세무사 확인이 필요합니다.",
    "saving": "장부 구분, 사업용 계좌, 감면 요건 확인이 기본입니다. 본 답변은 목업이며 세무 자문을 대체하지 않습니다.",
    "policy": "사용자 나이·지역·업력을 기준으로 샘플 정책을 안내합니다. 실제 자격은 공고문 원문을 확인해야 합니다.",
}

MOCK_SOURCES = [
    {
        "title": "국세청 홈택스 세금 일정(샘플)",
        "url": "https://www.hometax.go.kr",
        "excerpt": "부가가치세·종합소득세 신고 일정은 사업자 유형에 따라 다릅니다.",
    },
    {
        "title": "K-Startup 지원사업 안내(샘플)",
        "url": "https://www.k-startup.go.kr",
        "excerpt": "정부·지자체 창업 지원사업 공고와 신청 방법을 확인할 수 있습니다.",
    },
]


def suggested_questions(category: str) -> list[str]:
    return SUGGESTED.get(category, SUGGESTED["tax"])


def send_message(user_id: int, category: str, question: str) -> dict:
    if category not in SUGGESTED:
        raise HTTPException(status_code=400, detail="지원하지 않는 카테고리입니다.")
    mid = store.next_id("chat")
    answer = MOCK_ANSWERS[category]
    user = store.users.get(user_id, {})
    profile = store.business_profiles.get(user_id, {})
    context = f"{user.get('name') or '회원'}님"
    if user.get("region"):
        context += f"({user['region']}"
        if profile.get("industry"):
            context += f", {profile['industry']}"
        context += ")"
    full_answer = f"{context} 질문: “{question}”\n\n{answer}"
    store.chat_messages[mid] = {
        "id": mid,
        "user_id": user_id,
        "category": category,
        "question": question,
        "answer": full_answer,
        "created_at": datetime.now(),
    }
    store.answer_sources[mid] = list(MOCK_SOURCES)
    return {"messageId": mid, "answer": full_answer}


def get_sources(message_id: int) -> list[dict]:
    if message_id not in store.chat_messages:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다.")
    return store.answer_sources.get(message_id, [])


def list_messages(user_id: int, category: str | None = None) -> list[dict]:
    rows = [m for m in store.chat_messages.values() if m["user_id"] == user_id]
    if category:
        rows = [m for m in rows if m["category"] == category]
    return sorted(rows, key=lambda m: m["created_at"])
