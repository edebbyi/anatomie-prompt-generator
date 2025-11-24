import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def mock_airtable_data(monkeypatch):
    monkeypatch.setattr(
        "app.airtable_client.fetch_designers",
        lambda: [{"id": "recDesigner1", "name": "Prada", "style": ["Minimalist"]}],
    )
    monkeypatch.setattr(
        "app.airtable_client.fetch_colors",
        lambda: [{"id": "recColor1", "name": "cream"}],
    )
    monkeypatch.setattr(
        "app.airtable_client.fetch_garments_by_category",
        lambda: {
            "tops": [
                {
                    "id": "recTop1",
                    "name": "Safari Jacket",
                    "primary_design_elements": ["Convertible Sleeves"],
                    "technical_features": ["Moisture-wicking"],
                    "premium_constructions": ["French Seams"],
                }
            ],
            "others": [
                {
                    "id": "recOther1",
                    "name": "Travel Pant",
                    "primary_design_elements": ["Pleated Front"],
                    "technical_features": ["Quick-dry"],
                    "premium_constructions": ["Reinforced Stress Points"],
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.airtable_client.fetch_prompt_structures",
        lambda renderer: [
            {
                "id": "recStruct1",
                "skeleton": "${designer} designs ${garmentName} ${color} ---",
                "outlier_count": 5,
                "usage_count": 120,
                "avg_rating": 4.0,
                "z_score": 1.2,
                "age_weeks": 2,
                "ai_critique": "Strong",
                "renderer": renderer,
            }
        ],
    )


def test_generate_prompts_endpoint_success(monkeypatch, client):
    mock_airtable_data(monkeypatch)
    monkeypatch.setattr(
        "app.llm_agent.generate_prompts_with_llm",
        lambda **kwargs: {
            "prompts": [
                {
                    "promptText": "text",
                    "designerId": "recDesigner1",
                    "garmentId": "recTop1",
                    "promptStructureId": "recStruct1",
                    "renderer": "Recraft",
                }
                for _ in range(5)
            ]
        },
    )

    response = client.post(
        "/generate-prompts",
        json={"num_prompts": 5, "renderer": "Recraft"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert len(data["prompts"]) == 5
    assert all(p["renderer"] == "Recraft" for p in data["prompts"])


def test_missing_num_prompts_returns_422(client):
    response = client.post("/generate-prompts", json={"renderer": "Recraft"})
    assert response.status_code == 422


def test_invalid_renderer_returns_error(client):
    response = client.post("/generate-prompts", json={"num_prompts": 2, "renderer": ""})
    assert response.status_code == 422


def test_airtable_failure_returns_500(monkeypatch, client):
    monkeypatch.setattr(
        "app.airtable_client.fetch_designers",
        lambda: (_ for _ in ()).throw(Exception("failed")),
    )
    response = client.post("/generate-prompts", json={"num_prompts": 1, "renderer": "Recraft"})
    assert response.status_code == 500
    assert "error" in response.json()


def test_llm_malformed_json_returns_500(monkeypatch, client):
    mock_airtable_data(monkeypatch)
    monkeypatch.setattr(
        "app.llm_agent.generate_prompts_with_llm",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("bad json")),
    )
    response = client.post("/generate-prompts", json={"num_prompts": 1, "renderer": "Recraft"})
    assert response.status_code == 500
    assert "error" in response.json()

