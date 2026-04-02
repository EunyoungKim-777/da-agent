"""Jupyter MCP 연동 공통 모듈.

Jupyter MCP 서버를 통해 Notebook Cell 단위로 코드를 실행하고 결과를 반환한다.
각 분석 단계(전처리/EDA/모델링/평가)에서 공통으로 사용한다.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from src.agent.tracer import get_tracer


JUPYTER_MCP_URL = os.environ.get("JUPYTER_MCP_URL", "http://jupyter-mcp.frodo.com")
JUPYTER_TOKEN = os.environ.get("JUPYTER_TOKEN", "")


async def execute_cell(
    code: str,
    notebook_path: str,
    kernel_id: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Jupyter MCP를 통해 단일 코드 셀을 실행하고 결과를 반환한다.

    Jupyter MCP 서버의 /execute 엔드포인트에 코드를 전송하고
    실행 결과(stdout, stderr, outputs)를 dict로 반환한다.

    Args:
        code: 실행할 Python 코드 문자열
        notebook_path: 결과를 저장할 Notebook 파일 경로 (서버 기준)
        kernel_id: 재사용할 커널 ID (None이면 새 커널 생성)
        timeout: 실행 타임아웃 (초)

    Returns:
        {
            "status": "ok" | "error",
            "stdout": str,
            "stderr": str,
            "outputs": list[dict],  # Jupyter output 형식
            "kernel_id": str,
        }
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("jupyter.execute_cell") as span:
        span.set_attribute("jupyter.code", code)
        span.set_attribute("jupyter.notebook_path", notebook_path)

        headers = {
            "Authorization": f"token {JUPYTER_TOKEN}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "code": code,
            "notebook_path": notebook_path,
        }
        if kernel_id:
            payload["kernel_id"] = kernel_id

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{JUPYTER_MCP_URL}/execute",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        span.set_attribute("jupyter.status", result.get("status", ""))
        span.set_attribute("jupyter.stdout", result.get("stdout", "")[:2000])
        return result


async def create_notebook(notebook_path: str) -> dict[str, Any]:
    """새 Jupyter Notebook을 생성한다.

    Args:
        notebook_path: 생성할 Notebook 파일 경로 (서버 기준)

    Returns:
        생성된 Notebook 메타데이터 dict
    """
    headers = {
        "Authorization": f"token {JUPYTER_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JUPYTER_MCP_URL}/notebooks",
            json={"path": notebook_path},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def save_notebook(notebook_path: str) -> dict[str, Any]:
    """현재 Notebook 상태를 서버에 저장한다.

    Args:
        notebook_path: 저장할 Notebook 파일 경로 (서버 기준)

    Returns:
        저장 결과 메타데이터 dict
    """
    headers = {
        "Authorization": f"token {JUPYTER_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JUPYTER_MCP_URL}/notebooks/save",
            json={"path": notebook_path},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
