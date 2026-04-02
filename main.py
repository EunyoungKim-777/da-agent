"""dtest-agent 진입점.

사용법:
    python main.py

환경변수(.env)를 로드하고, Phoenix tracing을 초기화한 뒤
PostgreSQL checkpointer와 함께 컴파일된 그래프를 실행한다.

thread_id를 고정하면 동일 세션을 이어서 재개할 수 있다.
"""

from __future__ import annotations

import asyncio
import uuid

from dotenv import load_dotenv

load_dotenv()

from src.agent.checkpointer import create_checkpointer
from src.agent.graph import create_compiled_graph
from src.agent.state import AgentState
from src.agent.tracer import init_tracing


async def run_agent(user_input: str, thread_id: str | None = None) -> None:
    """Agent를 초기화하고 단일 분석 세션을 실행한다.

    Args:
        user_input: 사용자 분석 요청 문자열
        thread_id: 체크포인트 thread ID (None이면 새 UUID 생성)
    """
    init_tracing()

    checkpointer = await create_checkpointer()
    graph = await create_compiled_graph(checkpointer)

    tid = thread_id or str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": tid,
            "hitl_enabled": True,   # False로 설정하면 HITL 없이 자동 진행
        }
    }

    initial_state: AgentState = {
        "user_input": user_input,
        "current_step": "planning",
        "plan": {},
        "step_plan": {},
        "hitl_action": None,
        "hitl_feedback": None,
        "jupyter_code": None,
        "jupyter_output": None,
        "analysis_result": {},
        "messages": [],
        "error": None,
    }

    print(f"[Agent 시작] thread_id={tid}")
    print(f"[사용자 입력] {user_input}\n")

    async for event in graph.astream(initial_state, config=config):
        for node_name, state_update in event.items():
            print(f"[{node_name}] 완료 → step={state_update.get('current_step', '-')}")


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            user_input="반도체 TEST 수율 데이터를 분석하고 불량 원인을 파악해줘.",
        )
    )
