from functools import cached_property

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://gridsignal_writer@localhost:5440/gridsignal_db"
    read_database_url: str = "postgresql+psycopg://gridsignal_reader@localhost:5440/gridsignal_db"
    migration_database_url: str = "postgresql+psycopg://postgres@localhost:5440/gridsignal_db"
    cors_origins: str = "http://localhost:3001,http://127.0.0.1:3001"
    neso_resource_id: str = "177f6fa4-ae49-4182-81ea-0c6b35f26ca6"
    requests_per_minute: int = 600
    collection_interval_hours: int = Field(0, ge=0, le=24)
    collection_schedule_minute: int = Field(23, ge=0, le=59)
    collection_grace_minutes: int = Field(60, ge=0, le=180)

    @field_validator("collection_interval_hours")
    @classmethod
    def validate_collection_interval(cls, value):
        if value and 24 % value:
            raise ValueError("Collection interval must divide the 24-hour UTC schedule")
        return value

    @cached_property
    def origins(self):
        return self.cors_origins.split(",")


settings = Settings()
