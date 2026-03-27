import asyncio
import logging
import logging.handlers
import os
import traceback
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from config import settings
from handlers import router
from database import get_db, get_approved_telegram_ids

LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_handler = logging.handlers.RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "bot.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
log_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler],
)


async def errors_handler(event: ErrorEvent):
    logging.error(f"Ошибка: {event.exception}")
    logging.error(traceback.format_exc())


def get_seconds_until_saturday_19pm() -> int:
    now = datetime.now()
    days_until_saturday = (5 - now.weekday()) % 7
    if days_until_saturday == 0:
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if now >= target:
            days_until_saturday = 7
    target = now + timedelta(days=days_until_saturday)
    target = target.replace(hour=19, minute=0, second=0, microsecond=0)
    return int((target - now).total_seconds())


async def reminder_scheduler(bot: Bot):
    while True:
        seconds = get_seconds_until_saturday_19pm()
        logging.info(f"Следующее напоминание через {seconds // 3600} часов")
        await asyncio.sleep(seconds)

        try:
            async with get_db() as db:
                user_ids = await get_approved_telegram_ids(db)

            for user_id in user_ids:
                try:
                    await bot.send_message(
                        user_id,
                        "🛒 Напоминание: пора составить список покупок на неделю!",
                    )
                except Exception as e:
                    logging.error(f"Не удалось отправить напоминание {user_id}: {e}")

            logging.info(f"Напоминания отправлены {len(user_ids)} пользователям")
        except Exception as e:
            logging.error(f"Ошибка при отправке напоминаний: {e}")

        await asyncio.sleep(60)


async def main():
    if not settings.bot_token:
        logging.error("BOT_TOKEN не указан в .env файле")
        return

    logging.info(f"ADMIN_ID: {settings.admin_id}")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.error.register(errors_handler)
    dp.include_router(router)

    asyncio.create_task(reminder_scheduler(bot))

    logging.info("Бот запущен")

    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
