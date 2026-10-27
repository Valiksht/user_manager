from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения и файла .env.
    """
    DEBUG: bool = True
    SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_TOKEN_LIFE_MINUTES: int = 30
    JWT_TOKEN_LIFE_MINUTES_DEBUD: int = 9999999999
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = 'team_manager'
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str

    model_config = ConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )

    @property
    def database_url(self) -> str:
        return "sqlite+aiosqlite:///test.db"

    # @property
    # def database_url(self) -> str:
    #     return (
    #         f'postgresql+asyncpg://'
    #         f'{self.POSTGRES_USER}:'
    #         f'{self.POSTGRES_PASSWORD}@'
    #         f'{self.POSTGRES_HOST}:'
    #         f'{self.POSTGRES_PORT}/'
    #         f'{self.POSTGRES_DB}'
    #     )

settings = Settings()