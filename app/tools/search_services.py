from ..db.services_db import SERVICES_DB


def search_services(query: str = "", region: str = "", tags: list[str] | None = None) -> list[dict]:
    """키워드/지역/태그로 서비스를 검색합니다."""
    tags = tags or []
    results = []

    for svc in SERVICES_DB.values():
        score = 0

        # 키워드 매칭
        if query:
            searchable = (
                svc["service_name"] + " " +
                " ".join(svc.get("tags", [])) + " " +
                svc.get("eligibility_summary", "")
            ).lower()
            if any(q.lower() in searchable for q in query.split()):
                score += 2

        # 태그 매칭
        if tags:
            svc_tags = svc.get("tags", [])
            matches = sum(1 for t in tags if t in svc_tags)
            score += matches

        # 지역 필터 (target_region이 "all"이면 모두 포함)
        if svc.get("target_region") == "all":
            score += 1

        if score > 0 or (not query and not tags):
            results.append({**svc, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return [{k: v for k, v in r.items() if k != "_score"} for r in results[:5]]
