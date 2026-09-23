import asyncio
import re
from typing import Any

import asyncpg


class PostgresCursor:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        rowcount: int,
        lastrowid: int | None = None,
    ):
        self._rows = rows
        self.rowcount = rowcount
        self.lastrowid = lastrowid

    async def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    async def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class PostgresConnection:
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def execute(
        self, query: str, parameters: tuple[Any, ...] | list[Any] = ()
    ) -> PostgresCursor:
        statement = _replace_placeholders(query)
        normalized = statement.lstrip().upper()
        if normalized.startswith("SELECT"):
            rows = await self._connection.fetch(statement, *parameters)
            return PostgresCursor([dict(row) for row in rows], len(rows))

        if re.search(r"\bRETURNING\b", normalized):
            rows = await self._connection.fetch(statement, *parameters)
            mapped_rows = [dict(row) for row in rows]
            lastrowid = mapped_rows[0].get("id") if mapped_rows else None
            return PostgresCursor(mapped_rows, len(mapped_rows), lastrowid)

        result = await self._connection.execute(statement, *parameters)
        rowcount_match = re.search(r"\s(\d+)$", result)
        rowcount = int(rowcount_match.group(1)) if rowcount_match else -1
        return PostgresCursor([], rowcount)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _replace_placeholders(query: str) -> str:
    index = 0

    def replace(_: re.Match[str]) -> str:
        nonlocal index
        index += 1
        return f"${index}"

    return re.sub(r"\?", replace, query)


_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_postgres_pool(database_url: str) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    return _pool


async def close_postgres_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
