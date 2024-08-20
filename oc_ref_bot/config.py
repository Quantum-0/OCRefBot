from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = Field(pattern=r'\d+:.{35}')
    bot_name: str = Field(default='OC Reference Bot')
    admin_id: int = Field()


settings = Settings()
