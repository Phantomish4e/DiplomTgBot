from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False
    )

    bot_token: str
    yandex_api_key: str


settings = Settings()