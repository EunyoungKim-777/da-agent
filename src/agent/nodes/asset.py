"""결과 저장(Asset Saving) 노드 모듈.

최종 승인 후 Notebook, 모델, 분석 결과를 저장한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agent.nodes.jupyter import save_notebook
from src.agent.state import AgentState
from src.agent.tracer import traced


@traced("save_assets")
async def save_assets(
    state: AgentState, config: RunnableConfig
) -> dict[str, Any]:
    """분석 결과물(Notebook, 모델, 결과 JSON)을 최종 저장한다.

    전체 분석 플랜과 단계별 결과를 취합해 최종 리포트를 구성하고,
    Jupyter Notebook을 저장한 뒤 결과 파일 경로를 반환한다.

    State 입력:
        plan: 전체 분석 플랜
        analysis_result: 단계별 누적 결과
        jupyter_code: 마지막 단계 코드

    State 출력:
        current_step: "saving"
        analysis_result: "summary" 항목 추가 (저장 경로, 완료 시각 등)
    """
    # TODO: save_notebook() 호출, 모델 파일 저장, 결과 JSON 직렬화 구현
    return {
        "current_step": "saving",
        "analysis_result": {
            **state.get("analysis_result", {}),
            "summary": {},
        },
    }
