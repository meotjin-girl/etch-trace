# TRACE Agent

Agent는 하나의 LangGraph ReAct 에이전트다. 참고한 [LangChain ReAct template](https://github.com/langchain-ai/react-agent)처럼 `agent` 모델 노드가 도구 호출을 결정하고, `ToolNode`가 실행한 뒤 결과를 다시 모델에 넣는다. 도구 호출이 더 없으면 한국어 최종 답변을 반환한다.

## 구조

```text
agent/main.py         내부 HTTP API와 task별 동시성 잠금
agent/react_agent.py  Agent↔ToolNode ReAct 순환, prompt, checkpoint conversation
agent/tools.py        MCP Tool 정의와 공개 TOOL_NAMES 목록
agent/evidence.py     Business/RAG/Physics MCP adapter
agent/alert_text.py   고정 경보 텍스트 파싱
agent/dev_chat.py     UI 없이 Agent API를 부르는 plain-text 시험 클라이언트
```

현재 Tools는 `search_cases`, `analyze_metrics`, `search_documents`, `search_sop`, `evaluate_etch_physics`, `list_investigations`, `record_selection`이다. 실제 목록은 `agent/tools.py`의 `TOOL_NAMES`와 `build_tools()`에서 확인할 수 있다. Business·RAG·Physics MCP는 `EvidenceProvider` 뒤에서 호출하며, Agent가 업무 DB에 직접 접속하지 않는다.

`POST /internal/tasks/{task_id}/run`에서 `task_id`가 대화 ID이자 LangGraph 체크포인터 `thread_id`다. 경보/첫 user 요청과 이어지는 사용자 발화는 모두 이 같은 ID로 보내면 같은 대화 기록을 사용한다. `{question}` 또는 `{resume:...}` 구형 Backend 봉투도 호환되며 내부적으로 user turn으로 바꾼다. 응답의 `response`는 최종 자연어 답이다.

## 실행과 텍스트 시험

저장소 루트의 `.env`에 `OPENAI_API_KEY`, `OPENAI_MODEL`, `INTERNAL_API_KEY`를 설정한다.

```sh
docker compose -f compose.yaml up -d --build backend agent business-mcp rag-mcp physics-mcp
docker compose exec agent python -m agent.dev_chat
```

경보 텍스트로 시작할 때는 다음을 실행한다. 이후 한 줄씩 후속 질문을 입력하면 동일 대화 ID에 붙는다. `/exit`로 종료한다.

```sh
docker compose exec agent python -m agent.dev_chat --role system
```

## 검증

```sh
cd agent
uv sync --group dev
uv run pytest -q
uv run ruff check .
uv run basedpyright
```

테스트는 모델 서버 없이 모의 LLM tool-call 응답을 사용해 Agent→ToolNode→Agent 경로와 대화 체크포인트를 검증한다. LangSmith 추적은 루트 `.env`에 `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`를 설정하고 재시작하면 켜진다. 사용자 질문과 MCP 결과가 trace에 남을 수 있으므로 민감 데이터 대신 합성 데이터로 먼저 확인한다.
