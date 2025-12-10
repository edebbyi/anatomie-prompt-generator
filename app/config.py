from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    airtable_api_key: str = ""
    airtable_base_id: str = ""
    designers_table_id: str = ""
    colors_table_id: str = ""
    garments_table_id: str = ""
    prompt_structures_table_id: str = ""
    colors_active_view: str = ""
    garments_tops_view: str = ""
    garments_dresses_view: str = ""
    garments_outerwear_view: str = ""
    garments_pants_view: str = ""
    prompt_structures_active_view: str = ""

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.4

    service_url: str | None = None
    port: int = 8000

    # Optimizer integration
    optimizer_service_url: str = "https://optimizer-2ym2.onrender.com"
    preference_exploration_rate: float = 0.2


def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
