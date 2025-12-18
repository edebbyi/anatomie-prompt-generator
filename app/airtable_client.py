import time
from typing import Any, Dict, List

import requests

from .config import get_settings


AIRTABLE_API_URL = "https://api.airtable.com/v0"


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _fetch_records(table_id: str, view: str | None = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.airtable_base_id:
        raise ValueError("Missing AIRTABLE_BASE_ID (set it in your .env)")
    if not settings.airtable_api_key:
        raise ValueError("Missing AIRTABLE_API_KEY (set it in your .env)")
    if not table_id:
        raise ValueError("Missing Airtable table id (check your .env variables)")
    url = f"{AIRTABLE_API_URL}/{settings.airtable_base_id}/{table_id}"
    params = {"view": view} if view else None
    retries = 3
    delay = 1
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=_headers(settings.airtable_api_key), params=params, timeout=15)
            if response.status_code == 401:
                raise RuntimeError("Invalid Airtable credentials. Check AIRTABLE_API_KEY.")
            response.raise_for_status()
            payload = response.json()
            return payload.get("records", []) if isinstance(payload, dict) else []
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    return []


def fetch_designers() -> List[Dict[str, Any]]:
    records = _fetch_records(get_settings().designers_table_id)
    designers: List[Dict[str, Any]] = []
    for record in records:
        fields = record.get("fields", {})
        styles = fields.get("Design Style") or []
        if isinstance(styles, str):
            styles = [styles]
        designers.append(
            {
                "id": record.get("id", ""),
                "name": fields.get("Designer Name", ""),
                "style": styles,
            }
        )
    return designers


def fetch_colors() -> List[Dict[str, str]]:
    settings = get_settings()
    records = _fetch_records(settings.colors_table_id, settings.colors_active_view)
    colors: List[Dict[str, str]] = []
    for record in records:
        fields = record.get("fields", {})
        colors.append(
            {
                "id": record.get("id", ""),
                "name": (fields.get("Old Color Name") or "").strip(),
            }
        )
    return colors


def _map_garment(record: Dict[str, Any]) -> Dict[str, Any]:
    fields = record.get("fields", {})
    return {
        "id": record.get("id", ""),
        "name": fields.get("Garment Name", ""),
        "primary_design_elements": fields.get("Primary Design Element") or [],
        "technical_features": fields.get("Technical Feature") or [],
        "premium_constructions": fields.get("Premium Construction") or [],
    }


def fetch_garments_by_category() -> Dict[str, List[Dict[str, Any]]]:
    settings = get_settings()
    tops_records = _fetch_records(settings.garments_table_id, settings.garments_tops_view)
    dresses_records = _fetch_records(settings.garments_table_id, settings.garments_dresses_view)
    outerwear_records = _fetch_records(settings.garments_table_id, settings.garments_outerwear_view)
    pants_records = _fetch_records(settings.garments_table_id, settings.garments_pants_view)

    tops = [_map_garment(rec) for rec in tops_records]
    others = [_map_garment(rec) for rec in dresses_records + outerwear_records + pants_records]

    return {"tops": tops, "others": others}


def fetch_prompt_structures(renderer: str) -> List[Dict[str, Any]]:
    settings = get_settings()
    records = _fetch_records(settings.prompt_structures_table_id, settings.prompt_structures_active_view)
    structures: List[Dict[str, Any]] = []
    for record in records:
        fields = record.get("fields", {})
        if fields.get("Renderer") != renderer:
            continue
        structures.append(
            {
                "id": record.get("id", ""),
                "structureId": fields.get("Structure ID") or "",
                "renderer": fields.get("Renderer", ""),
                "skeleton": fields.get("Skeleton", "") or fields.get("skeleton", ""),
                "outlier_count": fields.get("outlier_count") or 0,
                "usage_count": fields.get("usage_count") or 0,
                "avg_rating": fields.get("avg_rating") or 0,
                "z_score": fields.get("z_score") or 0,
                "age_weeks": fields.get("age_weeks") or 0,
                "ai_critique": fields.get("AI Critique") or fields.get("ai_critique") or "",
                "comments": fields.get("Comments") or "",
            }
        )
    return structures
