import pytest

from app import airtable_client


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.ok = status_code == 200

    def json(self):
        return self._json

    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"status {self.status_code}")


def test_fetch_designers_returns_list(monkeypatch):
    mock_data = {
        "records": [
            {"id": "rec1", "fields": {"Designer Name": "Prada", "Design Style": ["Minimalist", "Luxury"]}},
            {"id": "rec2", "fields": {"Designer Name": "Dior", "Design Style": ["Classic"]}},
        ]
    }

    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponse(mock_data)

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("DESIGNERS_TABLE_ID", "designers")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    designers = airtable_client.fetch_designers()
    assert isinstance(designers, list)
    assert len(designers) == 2
    assert designers[0]["id"] == "rec1"
    assert designers[0]["name"] == "Prada"
    assert designers[0]["style"] == ["Minimalist", "Luxury"]


def test_fetch_designers_handles_empty(monkeypatch):
    mock_data = {"records": []}

    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponse(mock_data)

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("DESIGNERS_TABLE_ID", "designers")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    designers = airtable_client.fetch_designers()
    assert designers == []


def test_fetch_colors_from_active_view(monkeypatch):
    calls = []
    mock_data = {
        "records": [
            {"id": "recC", "fields": {"Old Color Name": "cream"}},
        ]
    }

    def mock_get(url, headers=None, params=None, timeout=None):
        calls.append(params.get("view"))
        return MockResponse(mock_data)

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("COLORS_TABLE_ID", "colors")
    monkeypatch.setenv("COLORS_ACTIVE_VIEW", "viw7kjImAZgZCVBje")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    colors = airtable_client.fetch_colors()
    assert calls[-1] == "viw7kjImAZgZCVBje"
    assert len(colors) == 1
    assert colors[0]["id"] == "recC"
    assert colors[0]["name"] == "cream"


def test_fetch_garments_returns_tops_and_others(monkeypatch):
    responses = {
        "viwANZNpTkFuLwEHi": {
            "records": [{"id": "top1", "fields": {"Garment Name": "Top", "Primary Design Element": ["A"], "Technical Feature": ["T1"], "Premium Construction": ["P1"]}}]
        },
        "viwFIq6VKwySvYUl9": {
            "records": [{"id": "dress1", "fields": {"Garment Name": "Dress", "Primary Design Element": ["B"], "Technical Feature": ["T2"], "Premium Construction": ["P2"]}}]
        },
        "viwzLgMjOfwjEpDwV": {
            "records": [{"id": "outer1", "fields": {"Garment Name": "Coat", "Primary Design Element": [], "Technical Feature": [], "Premium Construction": []}}]
        },
        "viw8eJkORvEypL11v": {
            "records": [{"id": "pant1", "fields": {"Garment Name": "Pant", "Primary Design Element": ["C"], "Technical Feature": ["T3"], "Premium Construction": ["P3"]}}]
        },
    }
    call_log = []

    def mock_get(url, headers=None, params=None, timeout=None):
        view = params.get("view")
        call_log.append(view)
        return MockResponse(responses[view])

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("GARMENTS_TABLE_ID", "garments")
    monkeypatch.setenv("GARMENTS_TOPS_VIEW", "viwANZNpTkFuLwEHi")
    monkeypatch.setenv("GARMENTS_DRESSES_VIEW", "viwFIq6VKwySvYUl9")
    monkeypatch.setenv("GARMENTS_OUTERWEAR_VIEW", "viwzLgMjOfwjEpDwV")
    monkeypatch.setenv("GARMENTS_PANTS_VIEW", "viw8eJkORvEypL11v")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    garments = airtable_client.fetch_garments_by_category()
    assert set(call_log) == set(responses.keys())
    assert "tops" in garments and "others" in garments
    assert len(garments["tops"]) == 1
    assert len(garments["others"]) == 3
    for garment in garments["tops"] + garments["others"]:
        assert "id" in garment
        assert "name" in garment
        assert "primary_design_elements" in garment
        assert "technical_features" in garment
        assert "premium_constructions" in garment


def test_fetch_prompt_structures_filters_by_renderer(monkeypatch):
    mock_data = {
        "records": [
            {"id": "rec1", "fields": {"Renderer": "Recraft", "Skeleton": "template 1", "outlier_count": 1, "usage_count": 1, "avg_rating": 4.0, "z_score": 1.0, "age_weeks": 2, "AI Critique": "good"}},
            {"id": "rec2", "fields": {"Renderer": "Other", "Skeleton": "template 2", "outlier_count": 1, "usage_count": 1, "avg_rating": 4.0, "z_score": 1.0, "age_weeks": 2, "AI Critique": "good"}},
        ]
    }

    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponse(mock_data)

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("PROMPT_STRUCTURES_TABLE_ID", "structures")
    monkeypatch.setenv("PROMPT_STRUCTURES_ACTIVE_VIEW", "view")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    structures = airtable_client.fetch_prompt_structures(renderer="Recraft")
    assert all(s["renderer"] == "Recraft" for s in structures)


def test_fetch_prompt_structures_includes_metadata(monkeypatch):
    mock_data = {
        "records": [
            {"id": "rec1", "fields": {"Renderer": "Recraft", "Skeleton": "template 1", "outlier_count": 5, "usage_count": 120, "avg_rating": 3.8, "z_score": 1.8, "age_weeks": 3, "AI Critique": "Strong"}},
        ]
    }

    def mock_get(url, headers=None, params=None, timeout=None):
        return MockResponse(mock_data)

    monkeypatch.setenv("AIRTABLE_API_KEY", "key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base")
    monkeypatch.setenv("PROMPT_STRUCTURES_TABLE_ID", "structures")
    monkeypatch.setenv("PROMPT_STRUCTURES_ACTIVE_VIEW", "view")
    monkeypatch.setattr(airtable_client.requests, "get", mock_get)

    structures = airtable_client.fetch_prompt_structures(renderer="Recraft")
    assert len(structures) == 1
    structure = structures[0]
    for key in ["skeleton", "outlier_count", "usage_count", "avg_rating", "z_score", "age_weeks", "ai_critique"]:
        assert key in structure

