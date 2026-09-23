import pytest

from database_backend import PostgresConnection, _replace_placeholders


class FakeAsyncpgConnection:
    def __init__(self):
        self.fetch_calls = []
        self.execute_calls = []

    async def fetch(self, statement, *parameters):
        self.fetch_calls.append((statement, parameters))
        if "RETURNING" in statement:
            return [{"id": 42}]
        return [{"id": 1, "name": "молоко"}]

    async def execute(self, statement, *parameters):
        self.execute_calls.append((statement, parameters))
        return "UPDATE 1"


def test_replace_placeholders() -> None:
    assert _replace_placeholders("SELECT * FROM items WHERE id = ? AND room_id = ?") == (
        "SELECT * FROM items WHERE id = $1 AND room_id = $2"
    )


@pytest.mark.asyncio
async def test_postgres_connection_reads_rows() -> None:
    connection = FakeAsyncpgConnection()
    cursor = await PostgresConnection(connection).execute(
        "SELECT * FROM items WHERE id = ?", (42,)
    )

    assert await cursor.fetchone() == {"id": 1, "name": "молоко"}
    assert connection.fetch_calls == [("SELECT * FROM items WHERE id = $1", (42,))]


@pytest.mark.asyncio
async def test_postgres_connection_handles_returning_and_rowcount() -> None:
    connection = FakeAsyncpgConnection()
    adapter = PostgresConnection(connection)
    inserted = await adapter.execute(
        "INSERT INTO items (name) VALUES (?) RETURNING id", ("молоко",)
    )
    updated = await adapter.execute("UPDATE items SET name = ? WHERE id = ?", ("сыр", 42))

    assert inserted.lastrowid == 42
    assert updated.rowcount == 1
    assert connection.execute_calls == [
        ("UPDATE items SET name = $1 WHERE id = $2", ("сыр", 42))
    ]
