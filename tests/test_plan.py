import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json

from dotenv import load_dotenv
load_dotenv()

from tests.inputs.planning_inputs import PLANNING_INPUTS
from src.agent.graph import create_compiled_graph
from src.agent.state import AgentState

# 실행할 입력 케이스 인덱스 (0 ~ len(PLANNING_INPUTS)-1)
INPUT_INDEX = 2


async def test():
    graph = await create_compiled_graph(checkpointer=None)

    config = {
        "configurable": {
            "thread_id": "test-001",
            "hitl_enabled": False,
        }
    }

    initial_state: AgentState = {
        "user_input": PLANNING_INPUTS[INPUT_INDEX],
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
    print(f"[테스트 입력 #{INPUT_INDEX}] {PLANNING_INPUTS[INPUT_INDEX]}\n")
    async for event in graph.astream(initial_state, config=config):
        for node_name, state_update in event.items():
            print(f"[{node_name}]")
            if state_update.get("plan"):
                print(json.dumps(state_update["plan"], ensure_ascii=False, indent=2))
            if state_update.get("error"):
                print(f"에러: {state_update['error']}")


asyncio.run(test())
