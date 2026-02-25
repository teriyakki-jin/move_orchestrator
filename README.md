# Move Orchestrator
이사 이벤트 기반 AI 민원 오케스트레이터 MVP입니다.  
사용자가 "이사했어"처럼 자연어로 시작하면, 인터뷰 → 체크리스트/서비스 추천 → 신청서 초안 생성(HITL)까지 이어집니다.

## What It Does
- 멀티턴 인터뷰로 최소 정보 수집 (`move_date`, `to_region`, `household_type`)
- 이사 관련 태스크 그래프 생성 (P0/P1/P2)
- 근거 기반 서비스 카드 추천
- 전입신고 초안 생성 + 제출 전 HITL 게이트
- 세션 SQLite 영속성 (`sessions.db`)
- 비용 절감용 `chat-mock` 엔드포인트 제공

## Tech Stack
- Backend: Python, FastAPI, Uvicorn, Pydantic
- LLM: OpenAI (`gpt-4o-mini` 기본)
- Frontend: Next.js + TypeScript + Tailwind
- Storage: SQLite (session), in-memory draft store

## Quick Start
### 1) Backend
```bash
cd /mnt/d/develop/mvp_move_orchestrator
python3 -m pip install -r requirements.txt

# 기본 실행 (port 8000)
python3 main.py

# 또는 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend
```bash
cd /mnt/d/develop/mvp_move_orchestrator/frontend
npm install
npm run dev
```

프론트 API 주소 설정 (`frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Environment Variables
루트 `.env` 예시:
```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
MOCK_MODE=false
```

- `MOCK_MODE=true`: 백엔드 오케스트레이터가 목데이터 경로 사용
- 프론트에서는 UI 토글로 `/chat`와 `/chat-mock`를 전환 가능

## API Overview
### Health
- `GET /health`

### Chat
- `POST /api/v1/chat`
- `POST /api/v1/chat-mock`

Request:
```json
{
  "session_id": "",
  "user_message": "어제 강남구에서 판교로 이사했어요"
}
```

### Session 조회
- `GET /api/v1/sessions/{session_id}`

### Submit (HITL)
- `POST /api/v1/submit/{draft_id}`

Request:
```json
{
  "session_id": "uuid",
  "confirmed": true
}
```

## Project Structure
```text
mvp_move_orchestrator/
├── app/
│   ├── api/              # chat, chat-mock, submit, health
│   ├── orchestrator/     # 메인 로직, 세션 저장
│   ├── agents/           # triage/interview/evidence/form_fill/safety
│   ├── tools/            # search/detail/schema/draft
│   ├── schemas/          # API/도메인 스키마
│   └── core/             # config, openai client, mock data
├── frontend/             # Next.js UI
├── sessions.db           # SQLite session DB (runtime)
├── requirements.txt
└── main.py
```

## Notes
- 민감정보(주민번호/상세주소)는 채팅 입력 금지 정책을 적용합니다.
- 초안 생성 후 제출 단계는 사용자 확인(HITL)을 전제로 합니다.
- `sessions.db`, `.env`, 각종 handoff 문서는 `.gitignore`로 제외되어 있습니다.
