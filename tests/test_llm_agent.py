import json
import random

import pytest

from app import llm_agent


class FakeLLMResponse:
    def __init__(self, content):
        self.choices = [type("msg", (), {"message": type("m", (), {"content": content})})]


class FakeLLMClient:
    def __init__(self, response_content):
        self.response_content = response_content
        self.last_messages = None
        self.calls = 0

    def chat(self):
        return self

    def completions(self):
        return self

    def create(self, messages=None, model=None, temperature=None, timeout=None):
        self.last_messages = messages
        self.calls += 1
        return FakeLLMResponse(self.response_content)


def base_data():
    designers = [{"id": "recDesigner1", "name": "Prada", "style": ["Minimalist"]}]
    colors = [{"id": "recColor1", "name": "cream"}]
    garments = {
        "tops": [
            {
                "id": "recGarmentTop",
                "name": "Safari Jacket",
                "primary_design_elements": ["Convertible Sleeves"],
                "technical_features": ["Moisture-wicking"],
                "premium_constructions": ["French Seams"],
            }
        ],
        "others": [
            {
                "id": "recGarmentOther",
                "name": "Travel Pant",
                "primary_design_elements": ["Pleated Front"],
                "technical_features": ["Quick-dry"],
                "premium_constructions": ["Reinforced Stress Points"],
            }
        ],
    }
    structures = [
        {
            "id": "recStruct",
            "skeleton": "${designer} designs ${garmentName} in ${color} ---",
            "outlier_count": 5,
            "usage_count": 120,
            "avg_rating": 4.0,
            "z_score": 1.2,
            "age_weeks": 2,
            "ai_critique": "Strong performer",
            "renderer": "Recraft",
        }
    ]
    return designers, colors, garments, structures


def test_generate_prompts_returns_correct_count(monkeypatch):
    designers, colors, garments, structures = base_data()
    payload = {"prompts": []}
    for i in range(3):
        payload["prompts"].append(
            {
                "promptText": f"Prompt {i}",
                "designerId": designers[0]["id"],
                "garmentId": garments["tops"][0]["id"],
                "promptStructureId": structures[0]["id"],
                "renderer": "Recraft",
            }
        )
    fake_client = FakeLLMClient(json.dumps(payload))

    result = llm_agent.generate_prompts_with_llm(
        num_prompts=3,
        renderer="Recraft",
        designers=designers,
        colors=colors,
        garments_by_category=garments,
        prompt_structures=structures,
        llm_client=fake_client,
    )
    assert "prompts" in result
    assert len(result["prompts"]) == 3


def test_generate_prompts_includes_required_fields():
    designers, colors, garments, structures = base_data()
    payload = {
        "prompts": [
            {
                "promptText": "text",
                "designerId": designers[0]["id"],
                "garmentId": garments["tops"][0]["id"],
                "promptStructureId": structures[0]["id"],
                "renderer": "Recraft",
            }
        ]
    }
    fake_client = FakeLLMClient(json.dumps(payload))

    result = llm_agent.generate_prompts_with_llm(
        num_prompts=1,
        renderer="Recraft",
        designers=designers,
        colors=colors,
        garments_by_category=garments,
        prompt_structures=structures,
        llm_client=fake_client,
    )
    prompt = result["prompts"][0]
    for key in ["promptText", "designerId", "garmentId", "promptStructureId", "renderer"]:
        assert key in prompt


def test_only_matching_renderer_structures_sent_to_llm():
    designers, colors, garments, _ = base_data()
    structures = [
        {
            "id": "recA",
            "skeleton": "A",
            "outlier_count": 1,
            "usage_count": 1,
            "avg_rating": 4.0,
            "z_score": 1.0,
            "age_weeks": 1,
            "ai_critique": "good",
            "renderer": "ImageFX",
        },
        {
            "id": "recB",
            "skeleton": "B",
            "outlier_count": 1,
            "usage_count": 1,
            "avg_rating": 4.0,
            "z_score": 1.0,
            "age_weeks": 1,
            "ai_critique": "good",
            "renderer": "Recraft",
        },
    ]
    payload = {"prompts": [
        {
            "promptText": "text",
            "designerId": designers[0]["id"],
            "garmentId": garments["tops"][0]["id"],
            "promptStructureId": "recA",
            "renderer": "ImageFX",
        }
    ]}
    fake_client = FakeLLMClient(json.dumps(payload))

    llm_agent.generate_prompts_with_llm(
        num_prompts=1,
        renderer="ImageFX",
        designers=designers,
        colors=colors,
        garments_by_category=garments,
        prompt_structures=structures,
        llm_client=fake_client,
    )
    user_message = fake_client.last_messages[-1]["content"]
    payload_sent = json.loads(user_message)
    assert all(ps["renderer"] == "ImageFX" for ps in payload_sent["prompt_structures"])


def test_garment_sampling_distribution():
    designers, colors, garments, structures = base_data()
    garments["tops"].append(
        {
            "id": "recGarmentTop2",
            "name": "Luxe Tee",
            "primary_design_elements": ["Boxy Fit"],
            "technical_features": ["Cooling"],
            "premium_constructions": ["Bonded Seams"],
        }
    )
    garments["others"].append(
        {
            "id": "recGarmentOther2",
            "name": "Cargo Pant",
            "primary_design_elements": ["Utility Pockets"],
            "technical_features": ["Water-resistant"],
            "premium_constructions": ["Double Stitching"],
        }
    )

    class EchoClient(FakeLLMClient):
        def create(self, messages=None, model=None, temperature=None, timeout=None):
            self.last_messages = messages
            payload = json.loads(messages[-1]["content"])
            prompts = []
            for ctx in payload["prompt_contexts"]:
                prompts.append(
                    {
                        "promptText": f"{ctx['designer']['name']} {ctx['garment']['name']} ---",
                        "designerId": ctx["designer"]["id"],
                        "garmentId": ctx["garment"]["id"],
                        "promptStructureId": ctx["prompt_structure"]["id"],
                        "renderer": payload["renderer"],
                    }
                )
            return FakeLLMResponse(json.dumps({"prompts": prompts}))

    fake_client = EchoClient("")
    random.seed(0)
    result = llm_agent.generate_prompts_with_llm(
        num_prompts=100,
        renderer="Recraft",
        designers=designers,
        colors=colors,
        garments_by_category=garments,
        prompt_structures=structures,
        llm_client=fake_client,
    )
    prompts = result["prompts"]
    tops_ids = {g["id"] for g in garments["tops"]}
    tops_count = sum(1 for p in prompts if p["garmentId"] in tops_ids)
    assert 60 <= tops_count <= 90  # reasonable variance around 75%

