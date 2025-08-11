from typing import Self

from pydantic import Field, HttpUrl, computed_field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = Field(pattern=r'\d+:.{35}')
    bot_name: str = Field(default='OC Reference Bot')
    admin_id: int = Field()

    sentry_dsn: HttpUrl = Field()

    db_user: str = Field()
    db_pass: str = Field()
    db_host: str = Field()
    db_db: str = Field()

    healthcheck_url: str | None = Field(default=None)
    healthcheck_period: int = Field(default=120)

    proxy_url: str | None = Field(default=None)
    proxy_auth: str | None = Field(default=None)

    web_server_host: str | None = Field(default='127.0.0.1')  # 0.0.0.0 allows access from outside, 127.0.0.1 doesn't
    web_server_port: int | None = Field(default=8080)
    webhook_path: str | None = Field(default='/webhook')
    webhook_secret: str | None = Field(default='my-very-very-very-secret-webhook-string')
    webhook_base_url: HttpUrl | None = Field(default=None)
    webhook_enabled: bool = Field(default=False)

    @computed_field(return_type=dict)  # type: ignore[misc]
    @property
    def webhook_params(self) -> dict:
        webhook_url = str(self.webhook_base_url)
        if webhook_url.endswith('/') and self.webhook_path.startswith('/'):
            webhook_url += self.webhook_path[1:]
        else:
            webhook_url += self.webhook_path
        return {'url': webhook_url, 'secret_token': self.webhook_secret}

    @model_validator(mode='after')
    def webhook_settings_check(self) -> Self:
        if self.webhook_enabled:
            if not self.web_server_host:
                raise ValueError('Host is not defined for webhook')
            if not self.webhook_path:
                raise ValueError('Webhook path must be defined')
            if not self.webhook_base_url:
                raise ValueError('Base url of internal web server is not defined')
        return self


settings = Settings()
