from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/reporter.db"
    secret_key: str = "change-this-to-a-random-secret"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
