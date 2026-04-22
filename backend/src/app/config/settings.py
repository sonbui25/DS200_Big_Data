from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ds200"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_schema: str = "public"

    aws_region: str = "ap-southeast-1"
    aws_default_region: str = "ap-southeast-1"
    aws_s3_bucket: str = ""
    aws_s3_transcripts_prefix: str = "transcripts"
    aws_s3_comments_prefix: str = "comments"
    aws_s3_audio_prefix: str = "audio"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""

    youtube_data_api_key: str = ""
    youtube_max_results_per_product: int = 1

    llm_provider: str = "gemini"
    llm_api_key: str = ""
    mobilecity_cookie: str = ""
    mobilecity_csrf_token: str = ""
    mobilecity_max_pages_per_slug: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
