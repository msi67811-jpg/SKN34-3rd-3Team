# =========================================================
# 국가법령정보센터 API로 법령 "전체 조문"을 수집 + DB 적재
#
# ✏️ 변경사항: 기존엔 키워드(청년/창업 등)로 걸러서 일부만 저장했지만,
#    - 데이터 양이 부담될 정도로 크지 않고
#    - 미리 거르면 관련 조문을 놓칠 위험이 있고
#    - 실제 관련성 판단은 나중에 LLM/RAG 검색 시점에 하는 게 더 안전해서
#    이번 버전은 "전체 조문을 다 저장"하는 방식으로 바꿨습니다.
# =========================================================

import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

OC = os.getenv("LAW_API_KEY")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "startup_platform",
    "user": "admin",
    "password": "admin1234",
}

# 여기에 수집하고 싶은 법령을 계속 추가
LAWS_TO_COLLECT = [
    {"name": "조세특례제한법", "mst": "280409"},
    {"name": "조세특례제한법 시행령", "mst": "287181"},
    {"name": "조세특례제한법 시행규칙", "mst": "284611"},
    {"name": "소득세법", "mst": "280405"},
    {"name": "소득세법 시행령", "mst": "286211"},
    {"name": "소득세법 시행규칙", "mst": "286379"},
    {"name": "부가가치세법", "mst": "276117"},
    {"name": "부가가치세법 시행령", "mst": "283641"},
    {"name": "부가가치세법 시행규칙", "mst": "284995"},
    {"name": "국세기본법", "mst": "288571"},
    {"name": "국세기본법 시행령", "mst": "283623"},
    {"name": "국세기본법 시행규칙", "mst": "284607"},
    {"name": "법인세법", "mst": "280349"},
    {"name": "법인세법 시행령", "mst": "283635"},
    {"name": "법인세법 시행규칙", "mst": "287787"},
    {"name": "조세범 처벌법", "mst": "224875"},
    {"name": "관세법", "mst": "288689"},
    {"name": "관세법 시행령", "mst": "283621"},
    {"name": "관세법 시행규칙", "mst": "288525"},
]

def fetch_law_body(mst):
    url = "http://www.law.go.kr/DRF/lawService.do"
    params = {"OC": OC, "target": "law", "MST": mst, "type": "JSON"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def extract_all_articles(law_json, law_name):
    try:
        articles = law_json["법령"]["조문"]["조문단위"]
    except KeyError:
        print(f"⚠️ [{law_name}] 예상한 구조와 다릅니다. 최상위 키: {law_json.keys()}")
        return []

    rows = []
    for article in articles:
        title = article.get("조문제목", "") or ""
        content = article.get("조문내용", "") or ""

        if not content.strip():
            continue 

        rows.append({
            "title": f"{law_name} 제{article.get('조문번호','?')}조 {title}".strip(),
            "law_name": law_name,
            "content": content,
            "source": "https://www.law.go.kr",
        })

    print(f"  └ [{law_name}] 전체 {len(articles)}개 조문 중 {len(rows)}개 저장 대상 (빈 조문 제외)")
    return rows


def insert_tax_documents(rows):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    inserted = 0
    for row in rows:
        cur.execute("SELECT 1 FROM tax_documents WHERE title = %s", (row["title"],))
        if cur.fetchone():
            continue

        cur.execute(
            """
            INSERT INTO tax_documents (title, law_name, content, source)
            VALUES (%(title)s, %(law_name)s, %(content)s, %(source)s)
            """,
            row,
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  └ 신규 {inserted}건 저장 (중복 {len(rows) - inserted}건은 건너뜀)")


if __name__ == "__main__":
    for law in LAWS_TO_COLLECT:
        print(f"[{law['name']}] 수집 시작...")
        law_json = fetch_law_body(law["mst"])
        rows = extract_all_articles(law_json, law["name"])
        insert_tax_documents(rows)
        time.sleep(1)

    print("전체 법령 수집 완료!")