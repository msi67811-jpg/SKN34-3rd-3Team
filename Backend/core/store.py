from datetime import date, datetime, timedelta

from core.config import ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_EMAIL, DEMO_PASSWORD
from core.security import hash_password

_next_ids: dict[str, int] = {}


def next_id(name: str) -> int:
    _next_ids[name] = _next_ids.get(name, 0) + 1
    return _next_ids[name]


users: dict[int, dict] = {}
users_by_email: dict[str, int] = {}
admins: dict[int, dict] = {}
admins_by_email: dict[str, int] = {}
business_profiles: dict[int, dict] = {}
tax_infos: dict[int, dict] = {}
chat_messages: dict[int, dict] = {}
answer_sources: dict[int, list[dict]] = {}
reminders: dict[int, dict] = {}
tax_reduction_results: dict[int, dict] = {}
receipts: dict[int, dict] = {}
receipt_extractions: dict[int, dict] = {}
expenses: dict[int, dict] = {}
saved_policies: dict[int, dict] = {}
tax_documents: dict[int, dict] = {}
policies: dict[int, dict] = {}
announcements: dict[int, dict] = {}
announcement_summaries: dict[int, dict] = {}
calendar_events: dict[int, dict] = {}
notifications: dict[int, dict] = {}


def _user(email: str, password: str, name: str, age: int, region: str) -> dict:
    uid = next_id("user")
    row = {
        "id": uid,
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "age": age,
        "region": region,
        "phone": "",
        "status": "active",
        "created_at": datetime.now(),
    }
    users[uid] = row
    users_by_email[email] = uid
    return row


def _admin(email: str, password: str) -> dict:
    aid = next_id("admin")
    row = {
        "id": aid,
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
        "created_at": datetime.now(),
    }
    admins[aid] = row
    admins_by_email[email] = aid
    return row


def seed() -> None:
    if users:
        return

    demo = _user(DEMO_EMAIL, DEMO_PASSWORD, "김창업", 29, "서울")
    business_profiles[demo["id"]] = {
        "id": next_id("biz"),
        "user_id": demo["id"],
        "business_type": "간이과세자",
        "industry": "소프트웨어",
        "business_registered_at": date(2024, 3, 1),
        "founded_at": date(2024, 3, 1),
    }
    tax_infos[demo["id"]] = {
        "id": next_id("taxinfo"),
        "user_id": demo["id"],
        "tax_type": "부가가치세",
        "details": "분기 예정·확정 신고 대상",
        "updated_at": datetime.now(),
    }

    admin = _admin(ADMIN_EMAIL, ADMIN_PASSWORD)

    policy_rows = [
        {
            "title": "예비창업패키지",
            "region": "전국",
            "industry": "전 업종",
            "target": "예비창업자 및 업력 3년 미만 창업자",
            "benefit": "사업화 자금 최대 1억원, 멘토링",
            "eligibility_rule": "age<=39,founded_years<=3",
            "source": "창업진흥원",
            "apply_start_date": date(2026, 3, 1),
            "apply_end_date": date(2026, 3, 31),
            "apply_method": "K-Startup 온라인 신청",
        },
        {
            "title": "청년창업사관학교",
            "region": "서울",
            "industry": "소프트웨어",
            "target": "만 39세 이하 청년 창업자",
            "benefit": "창업 공간, 교육, 사업화 지원금",
            "eligibility_rule": "age<=39,region=서울",
            "source": "중소벤처기업부",
            "apply_start_date": date(2026, 4, 1),
            "apply_end_date": date(2026, 4, 20),
            "apply_method": "사관학교 홈페이지 접수",
        },
        {
            "title": "서울 청년창업 지원금",
            "region": "서울",
            "industry": "전 업종",
            "target": "서울 거주 만 39세 이하 1인 창업자",
            "benefit": "사업비 최대 2천만원",
            "eligibility_rule": "age<=39,region=서울",
            "source": "서울산업진흥원",
            "apply_start_date": date(2026, 9, 1),
            "apply_end_date": date(2026, 9, 30),
            "apply_method": "서울기업지원센터 신청",
        },
        {
            "title": "소상공인 정책자금",
            "region": "전국",
            "industry": "도소매",
            "target": "소상공인 사업자",
            "benefit": "저금리 정책자금 대출",
            "eligibility_rule": "business_type!=미등록",
            "source": "소상공인시장진흥공단",
            "apply_start_date": date(2026, 1, 2),
            "apply_end_date": date(2026, 12, 15),
            "apply_method": "소진공 온라인 신청",
        },
        {
            "title": "청년창업 세액감면 안내 사업",
            "region": "전국",
            "industry": "소프트웨어",
            "target": "청년 창업 중소기업",
            "benefit": "소득세·법인세 감면 상담 및 신청 지원",
            "eligibility_rule": "age<=39,founded_years<=5",
            "source": "국세청",
            "apply_start_date": date(2026, 1, 1),
            "apply_end_date": date(2026, 12, 31),
            "apply_method": "홈택스 또는 세무서 방문",
        },
    ]

    for item in policy_rows:
        pid = next_id("policy")
        policies[pid] = {
            "id": pid,
            "admin_id": admin["id"],
            "title": item["title"],
            "region": item["region"],
            "industry": item["industry"],
            "target": item["target"],
            "benefit": item["benefit"],
            "eligibility_rule": item["eligibility_rule"],
            "source": item["source"],
            "created_at": datetime.now(),
        }
        aid = next_id("announcement")
        announcements[aid] = {
            "id": aid,
            "policy_id": pid,
            "raw_content": f"{item['title']} 공고문. 신청기간 {item['apply_start_date']} ~ {item['apply_end_date']}. {item['benefit']}",
            "source_url": "https://www.k-startup.go.kr",
            "apply_start_date": item["apply_start_date"],
            "apply_end_date": item["apply_end_date"],
            "apply_method": item["apply_method"],
            "created_at": datetime.now(),
        }
        announcement_summaries[aid] = {
            "id": next_id("summary"),
            "announcement_id": aid,
            "target": item["target"],
            "benefit": item["benefit"],
            "period": f"{item['apply_start_date']} ~ {item['apply_end_date']}",
            "documents": "사업계획서, 주민등록등본, 사업자등록증(해당 시)",
            "notes": "샘플 데이터이며 실제 공고와 다를 수 있습니다.",
            "source": item["source"],
        }

    tax_dates = [
        ("부가가치세 1기 예정 신고", date(2026, 4, 25), "1~3월분 예정 신고·납부"),
        ("종합소득세 확정 신고", date(2026, 5, 31), "2025년 귀속 종합소득세"),
        ("부가가치세 1기 확정 신고", date(2026, 7, 27), "1~6월분 확정 신고·납부"),
        ("부가가치세 2기 예정 신고", date(2026, 10, 26), "7~9월분 예정 신고·납부"),
        ("원천세 9월분 신고", date(2026, 10, 12), "원천징수세 납부"),
    ]
    for title, due, desc in tax_dates:
        eid = next_id("event")
        calendar_events[eid] = {
            "id": eid,
            "event_type": "TAX",
            "business_type": "간이과세자",
            "policy_id": None,
            "title": title,
            "due_date": due,
            "description": desc,
        }

    for policy in policies.values():
        announcement = next(
            (a for a in announcements.values() if a["policy_id"] == policy["id"]),
            None,
        )
        if not announcement:
            continue
        eid = next_id("event")
        calendar_events[eid] = {
            "id": eid,
            "event_type": "POLICY",
            "business_type": None,
            "policy_id": policy["id"],
            "title": f"{policy['title']} 신청 마감",
            "due_date": announcement["apply_end_date"],
            "description": f"{policy['source']} · {policy['region']}",
        }

    tax_documents[next_id("taxdoc")] = {
        "id": 1,
        "admin_id": admin["id"],
        "title": "부가가치세법 개요(샘플)",
        "content": "부가가치세는 재화·용역 공급에 대해 부과된다. 본 문서는 샘플이다.",
        "source": "국세청",
        "created_at": datetime.now(),
    }

    tomorrow = datetime.now() + timedelta(days=1)
    reminder_event = next(
        (e for e in calendar_events.values() if e["event_type"] == "TAX"),
        None,
    )
    if reminder_event:
        rid = next_id("reminder")
        reminders[rid] = {
            "id": rid,
            "user_id": demo["id"],
            "event_id": reminder_event["id"],
            "notify_at": tomorrow.replace(hour=9, minute=0, second=0, microsecond=0),
            "created_at": datetime.now(),
        }


seed()
