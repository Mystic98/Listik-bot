import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from webapp.auth import TelegramInitDataError, validate_init_data


def build_init_data(bot_token: str, auth_date: int = 1_700_000_000) -> str:
    values = {
        "auth_date": str(auth_date),
        "query_id": "AAEAAAE",
        "user": json.dumps(
            {
                "id": 123456,
                "first_name": "Иван",
                "last_name": "Петров",
                "username": "ivan_petrov",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(values)


def test_validate_init_data_returns_identity() -> None:
    identity = validate_init_data(
        build_init_data("test-token"),
        "test-token",
        max_age_seconds=100,
        now=1_700_000_050,
    )

    assert identity.telegram_id == 123456
    assert identity.username == "ivan_petrov"
    assert identity.full_name == "Иван Петров"


def test_validate_init_data_rejects_invalid_hash() -> None:
    init_data = build_init_data("test-token").replace("hash=", "hash=0", 1)

    with pytest.raises(TelegramInitDataError, match="hash is invalid"):
        validate_init_data(init_data, "test-token", max_age_seconds=100, now=1_700_000_050)


def test_validate_init_data_rejects_expired_payload() -> None:
    with pytest.raises(TelegramInitDataError, match="expired"):
        validate_init_data(
            build_init_data("test-token", auth_date=1_700_000_000),
            "test-token",
            max_age_seconds=10,
            now=1_700_000_050,
        )
