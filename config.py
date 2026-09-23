from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    bot_token: str = ""
    admin_id: int = 0
    database_path: str = "/app/data/grocery.db"
    database_url: str = ""
    mini_app_url: str = ""
    mini_app_host: str = "0.0.0.0"
    mini_app_port: int = 8080
    telegram_init_data_max_age: int = 86400
    webapp_enabled: bool = False


settings = Settings()
