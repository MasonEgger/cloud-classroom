"""Configuration management for Cloud Classroom."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite:///./cloud_classroom.db"

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # App Configuration
    app_title: str = "Cloud Classroom"
    app_description: str = "Educational cloud resource management platform"
    app_version: str = "0.1.0"
    debug: bool = False

    # DigitalOcean
    digitalocean_token: str = ""

    # Email (for future use)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""


settings = Settings()
