"""Environment variable configuration for Stage 2 production system."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Production configuration loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://fte:fte_password@localhost:5432/fte_crm",
        description="PostgreSQL connection string",
    )
    db_min_pool_size: int = Field(default=5, description="Minimum DB pool connections")
    db_max_pool_size: int = Field(default=20, description="Maximum DB pool connections")

    # Kafka
    kafka_brokers: str = Field(
        default="localhost:9092", description="Kafka broker addresses"
    )
    kafka_group_id: str = Field(
        default="fte-workers", description="Kafka consumer group ID"
    )

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model name")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model"
    )

    # Twilio (WhatsApp)
    twilio_account_sid: str = Field(default="", description="Twilio Account SID")
    twilio_auth_token: str = Field(default="", description="Twilio Auth Token")
    twilio_whatsapp_from: str = Field(
        default="whatsapp:+14155238886", description="Twilio WhatsApp sender number"
    )

    # Gmail
    gmail_credentials_json: str = Field(
        default="", description="Path to Gmail API credentials JSON"
    )
    gmail_pubsub_topic: str = Field(
        default="", description="Google Pub/Sub topic for Gmail notifications"
    )
    gmail_user_id: str = Field(default="me", description="Gmail user ID")

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="fte-local-dev-secret-change-in-prod",
        description="JWT signing key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=60, description="Token expiry minutes")

    # API
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated CORS allowed origins",
    )
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
