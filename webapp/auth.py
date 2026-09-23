import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    """Raised when Telegram Mini App init data is invalid."""


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_id: int
    username: str | None
    full_name: str


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
    now: int | None = None,
) -> TelegramIdentity:
    if not init_data or not bot_token:
        raise TelegramInitDataError("Telegram init data is missing")

    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Telegram init data hash is missing")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramInitDataError("Telegram init data hash is invalid")

    try:
        auth_date = int(values["auth_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TelegramInitDataError("Telegram auth date is invalid") from exc

    current_time = int(time.time()) if now is None else now
    if auth_date > current_time or current_time - auth_date > max_age_seconds:
        raise TelegramInitDataError("Telegram init data is expired")

    try:
        user = json.loads(values["user"])
        telegram_id = int(user["id"])
        first_name = str(user.get("first_name", "")).strip()
        last_name = str(user.get("last_name", "")).strip()
        full_name = " ".join(part for part in (first_name, last_name) if part)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TelegramInitDataError("Telegram user data is invalid") from exc

    if not full_name:
        full_name = str(user.get("username") or telegram_id)

    return TelegramIdentity(
        telegram_id=telegram_id,
        username=user.get("username"),
        full_name=full_name,
    )


def get_identity_from_payload(payload: Any, bot_token: str, max_age_seconds: int) -> TelegramIdentity:
    if not isinstance(payload, dict):
        raise TelegramInitDataError("Authentication payload is invalid")
    return validate_init_data(
        str(payload.get("init_data", "")),
        bot_token,
        max_age_seconds,
    )
