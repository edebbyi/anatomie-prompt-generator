from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    airtable_api_key: str = Field(default="", validation_alias=AliasChoices("AIRTABLE_API_KEY", "VITE_AIRTABLE_API_KEY"))
    airtable_base_id: str = Field(default="", validation_alias=AliasChoices("AIRTABLE_BASE_ID", "VITE_AIRTABLE_BASE_ID"))
    designers_table_id: str = Field(
        default="", validation_alias=AliasChoices("DESIGNERS_TABLE_ID", "VITE_DESIGNERS_TABLE_ID", "VITE_AIRTABLE_DESIGNERS_TABLE")
    )
    colors_table_id: str = Field(
        default="", validation_alias=AliasChoices("COLORS_TABLE_ID", "VITE_COLORS_TABLE_ID", "VITE_AIRTABLE_COLORS_TABLE")
    )
    garments_table_id: str = Field(
        default="", validation_alias=AliasChoices("GARMENTS_TABLE_ID", "VITE_GARMENTS_TABLE_ID", "VITE_AIRTABLE_GARMENTS_TABLE")
    )
    prompt_structures_table_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "PROMPT_STRUCTURES_TABLE_ID",
            "VITE_PROMPT_STRUCTURES_TABLE_ID",
            "VITE_AIRTABLE_STRUCTURES_TABLE",
        ),
    )
    colors_active_view: str = Field(
        default="", validation_alias=AliasChoices("COLORS_ACTIVE_VIEW", "VITE_COLORS_ACTIVE_VIEW", "VITE_VIEW_COLORS_ACTIVE")
    )
    garments_tops_view: str = Field(
        default="",
        validation_alias=AliasChoices("GARMENTS_TOPS_VIEW", "VITE_GARMENTS_TOPS_VIEW", "VITE_VIEW_GARMENTS_TOPS"),
    )
    garments_dresses_view: str = Field(
        default="",
        validation_alias=AliasChoices("GARMENTS_DRESSES_VIEW", "VITE_GARMENTS_DRESSES_VIEW", "VITE_VIEW_GARMENTS_DRESSES"),
    )
    garments_outerwear_view: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GARMENTS_OUTERWEAR_VIEW",
            "VITE_GARMENTS_OUTERWEAR_VIEW",
            "VITE_VIEW_GARMENTS_OUTERWEAR",
        ),
    )
    garments_pants_view: str = Field(
        default="",
        validation_alias=AliasChoices("GARMENTS_PANTS_VIEW", "VITE_GARMENTS_PANTS_VIEW", "VITE_VIEW_GARMENTS_PANTS"),
    )
    prompt_structures_active_view: str = Field(
        default="",
        validation_alias=AliasChoices(
            "PROMPT_STRUCTURES_ACTIVE_VIEW",
            "VITE_PROMPT_STRUCTURES_ACTIVE_VIEW",
            "VITE_VIEW_STRUCTURES_ACTIVE",
        ),
    )

    openai_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "VITE_OPENAI_API_KEY"))
    openai_model: str = Field(default="gpt-4o-mini", validation_alias=AliasChoices("OPENAI_MODEL", "VITE_OPENAI_MODEL"))
    openai_temperature: float = Field(
        default=0.4, validation_alias=AliasChoices("OPENAI_TEMPERATURE", "VITE_OPENAI_TEMPERATURE")
    )

    service_url: str | None = Field(default=None, validation_alias=AliasChoices("SERVICE_URL", "VITE_APP_URL"))
    port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "VITE_PORT"))

    # Optimizer integration
    optimizer_service_url: str = "https://optimizer-2ym2.onrender.com"
    preference_exploration_rate: float = 0.2


def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
