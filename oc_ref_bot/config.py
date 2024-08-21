from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = Field(pattern=r'\d+:.{35}')
    bot_name: str = Field(default='OC Reference Bot')
    admin_id: int = Field()
    sentry_dsn: HttpUrl = Field()
    db_user: str
    db_pass: str
    db_host: str
    db_db: str


settings = Settings()
