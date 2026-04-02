"""PostgreSQL Checkpoint 설정 모듈.

LangGraph의 PostgreSQL checkpointer를 초기화해 그래프 상태를 DB에 영속화한다.
HITL interrupt 이후 그래프 재개(resume)에 활용된다.
"""

from __future__ import annotations

import os
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

async def create_checkpointer() -> AsyncPostgresSaver:
    """AsyncPostgresSaver 인스턴스를 생성하고 스키마를 초기화한다.

    환경변수:
        POSTGRES_URL: PostgreSQL 연결 문자열
            (예: postgresql+psycopg://user:pass@host:5432/db)

    Returns:
        AsyncPostgresSaver: 초기화 완료된 LangGraph PostgreSQL checkpointer
    """
    postgres_url = os.environ["POSTGRES_URL"]

    # langgraph-checkpoint-postgres는 psycopg3 DSN 형식 사용
    # SQLAlchemy URL prefix 제거
    dsn = postgres_url.replace("postgresql+psycopg://", "postgresql://")

    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = AsyncConnectionPool(
        conninfo=dsn,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    return checkpointer
