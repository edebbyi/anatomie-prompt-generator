import json
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import get_settings
from .preferences import get_preference_adapter


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Evolving Prompt Maker, an internal prompt designer for ANATOMIE, a luxury performance travel wear brand.

CONTEXT:
You receive data for designers, colors, garments, and prompt structures to generate fashion image prompts.

INPUT DATA STRUCTURE:
- designers: array of {{id, name, style}}
- colors: array of {{id, name}}
- garments_by_category: {{
    tops: [{{id, name, primary_design_elements[], technical_features[], premium_constructions[]}}],
    others: [same structure for dresses/outerwear/pants]
  }}
- prompt_structures: array of {{
    id, skeleton (template text),
    outlier_count, usage_count, avg_rating, z_score, age_weeks,
    ai_critique, renderer
  }}
- num_prompts: integer
- renderer: string (e.g., "Recraft")

YOUR TASK:
For each of the num_prompts to generate:

1. SELECTION (75% tops / 25% others):
   - Randomly select 1 designer
   - Randomly select 1 color
   - Randomly select 1 garment (75% probability from tops, 25% from others)

2. STRUCTURE SELECTION (Evolving Logic):
   - Prefer structures with:
     • Higher outlier_count (proven outlier generators)
     • Good avg_rating (>3.5)
     • Reasonable age_weeks (<12 weeks)
     • Positive z_score (>0)
   - 10-20% of the time, explore:
     • Newer structures (age_weeks < 4)
     • Less-used structures with positive ai_critique
   - AVOID structures with:
     • Very low avg_rating (<2.5)
     • Negative ai_critique mentions ("off-brand", "hallucinatory", "confusing", "generic")

3. PROMPT CONSTRUCTION:
   - Start with the selected structure's "skeleton" template text
   - Replace ALL variables using these rules:
     
     Variables to replace:
     ${{{{designer}}}} → selected designer name
     ${{{{color}}}} → selected color name
     ${{{{color.toLowerCase()}}}} → selected color name in lowercase
     ${{{{garmentName}}}} → selected garment name
     ${{{{pde1}}}} → first primary_design_element or ""
     ${{{{designElements}}}} → all primary_design_elements joined with ", " or ""
     ${{{{pcs}}}} → all premium_constructions joined with ", " or ""
     ${{{{tcs}}}} → all technical_features joined with ", " or ""
     ${{{{premiumConstruction}}}} → same as ${{{{pcs}}}}
     ${{{{technicalConstruction}}}} → same as ${{{{tcs}}}}
     ${{{{premiumConstructions}}}} → first 2 premium_constructions joined with ", " or ""
     ${{{{technicalConstructions}}}} → first 2 technical_features joined with ", " or ""
   
   - CRITICAL BRAND RULES:
     • If skeleton mentions example brands (Chanel, Dior, etc.), REPLACE with selected designer
     • If skeleton mentions specific garments (skirt, dress, etc.), REPLACE with actual garment type
     • NEVER output brands that weren't selected
     • NEVER output garment types that don't match the selected garment
   
   - Append " ---" to the end of the final prompt text

4. OUTPUT FORMAT:
   Return ONLY valid JSON (no markdown, no code blocks):
   {{{{
     "prompts": [
       {{{{
         "promptText": "complete prompt with all variables replaced and --- at end",
         "designerId": "recXXX",
         "garmentId": "recXXX",
         "promptStructureId": "recXXX",
         "renderer": "Recraft"
       }}}}
     ]
   }}}}

QUALITY RULES:
- Prompts must be vivid, production-ready fashion photography descriptions
- Ultra-modern travel wear aesthetic (not gym, not formal)
- Performance fabrics with tailored silhouettes
- Understated luxury with tonal hardware
- Visual-only descriptions (no text in images)
- 3:1 shirt-to-pant ratio maintained across all prompts

OUTPUT VALIDATION:
- prompts array length MUST equal num_prompts
- Every prompt MUST have all 5 fields (promptText, designerId, garmentId, promptStructureId, renderer)
- renderer value MUST match the input renderer exactly
- All IDs must be valid Airtable record IDs from the input data

{preference_guidance}"""


REQUIRED_PROMPT_KEYS = {"promptText", "designerId", "garmentId", "promptStructureId", "renderer"}


def _build_system_prompt(structure_id: Optional[str] = None, explore_mode: bool = False) -> str:
    """
    Build system prompt with preference guidance or exploration instructions.
    
    Args:
        structure_id: Optional structure ID for structure-specific prompt examples
        explore_mode: If True, encourage novelty instead of following preferences
        
    Returns:
        Complete system prompt with dynamic guidance inserted
    """
    adapter = get_preference_adapter()
    
    if explore_mode:
        preference_section = """
EXPLORATION MODE:
For this batch, prioritize CREATIVE VARIETY over consistency with past successes.
- Try unexpected color combinations
- Experiment with different compositional approaches
- Use adjectives and descriptors you haven't used recently
- Push the boundaries of the brand aesthetic while staying on-brand

This helps discover new directions that might become future favorites.
"""
        return SYSTEM_PROMPT.format(preference_guidance=preference_section)
    
    guidance = adapter.get_style_guidance(structure_id=structure_id)
    
    if guidance:
        preference_section = f"""
BRAND PREFERENCE GUIDANCE (learned from successful images):
{guidance}

When generating prompts, subtly incorporate these preferences into your descriptions.
This is NOT mandatory for every prompt — use judgment to create variety while trending toward preferred attributes.
For this structure specifically, draw inspiration from the high-performing prompt examples if provided.
"""
    else:
        preference_section = ""
    
    return SYSTEM_PROMPT.format(preference_guidance=preference_section)


def _select_garment(garments_by_category: Dict[str, List[Dict[str, Any]]], rng: random.Random) -> Dict[str, Any]:
    """Select garment with 75% tops / 25% others distribution."""
    tops = garments_by_category.get("tops") or []
    others = garments_by_category.get("others") or []
    if not tops and not others:
        raise ValueError("No garments available")
    if tops and (not others or rng.random() < 0.75):
        return rng.choice(tops)
    return rng.choice(others if others else tops)


def _fallback_structure_score(structure: Dict[str, Any]) -> float:
    """
    Fallback heuristic score when optimizer scores are not available.
    Uses Airtable fields directly.
    """
    score = 0
    score += float(structure.get("outlier_count") or 0) * 2
    score += float(structure.get("usage_count") or 0) * 0.1
    score += float(structure.get("avg_rating") or 0) * 2
    score += float(structure.get("z_score") or 0) * 3
    age = float(structure.get("age_weeks") or 0)
    score -= max(0, age - 4) * 0.2
    return score


def _select_structure(structures: List[Dict[str, Any]], rng: random.Random, explore_mode: bool = False) -> Dict[str, Any]:
    """
    Select a structure based on optimizer scores or exploration logic.
    
    Args:
        structures: List of available structures
        rng: Random number generator
        explore_mode: If True, favor newer/less-used structures for novelty
        
    Returns:
        Selected structure dict
    """
    if not structures:
        raise ValueError("No prompt structures available")
    
    adapter = get_preference_adapter()
    
    # EXPLORATION MODE: Pick from newer or less-used structures
    if explore_mode:
        exploratory = [
            s for s in structures 
            if (s.get("age_weeks") or 0) < 4 or (s.get("usage_count") or 0) < 10
        ]
        if exploratory:
            return rng.choice(exploratory)
        return rng.choice(structures)
    
    # EXPLOITATION MODE: Use optimizer scores if available
    if adapter.has_structure_scores:
        structure_ids = [s.get("id") for s in structures]
        ranked = adapter.rank_structures(structure_ids)
        
        weights = [max(score, 0.1) for _, score in ranked]  # Floor at 0.1 to avoid zero weights
        total = sum(weights)
        if total > 0:
            normalized_weights = [w / total for w in weights]
            id_to_struct = {s.get("id"): s for s in structures}
            ranked_structs = [id_to_struct[sid] for sid, _ in ranked if sid in id_to_struct]
            
            if ranked_structs:
                selected = rng.choices(ranked_structs, weights=normalized_weights[:len(ranked_structs)], k=1)[0]
                return selected
    
    # FALLBACK: Use heuristic scoring with WEIGHTED RANDOM selection
    # This ensures diversity - higher scoring structures are more likely
    # to be selected, but lower scoring ones still have a chance
    scored_structures = []
    for struct in structures:
        score = _fallback_structure_score(struct)
        scored_structures.append((struct, score))
    
    # Shift scores to be positive (minimum 0.1) for valid probability weights
    min_score = min(s for _, s in scored_structures)
    shift = abs(min_score) + 0.1 if min_score < 0 else 0.1
    
    weights = [score + shift for _, score in scored_structures]
    total = sum(weights)
    
    if total > 0:
        normalized_weights = [w / total for w in weights]
        selected = rng.choices(
            [struct for struct, _ in scored_structures], 
            weights=normalized_weights, 
            k=1
        )[0]
        return selected
    
    # Ultimate fallback: random choice
    return rng.choice(structures)


def _build_variable_map(designer: Dict[str, Any], color: Dict[str, Any], garment: Dict[str, Any]) -> Dict[str, str]:
    """Build variable map for skeleton template filling."""
    design_elements = garment.get("primary_design_elements") or []
    technical_features = garment.get("technical_features") or []
    premium_constructions = garment.get("premium_constructions") or []

    return {
        "designer": designer.get("name", ""),
        "color": (color.get("name") or ""),
        "garmentName": garment.get("name", ""),
        "pde1": design_elements[0] if design_elements else "",
        "designElements": ", ".join(design_elements) if design_elements else "",
        "pcs": ", ".join(premium_constructions) if premium_constructions else "",
        "tcs": ", ".join(technical_features) if technical_features else "",
        "premiumConstruction": ", ".join(premium_constructions) if premium_constructions else "",
        "technicalConstruction": ", ".join(technical_features) if technical_features else "",
        "premiumConstructions": ", ".join(premium_constructions[:2]) if premium_constructions else "",
        "technicalConstructions": ", ".join(technical_features[:2]) if technical_features else "",
    }


def _fill_skeleton(skeleton: str, variables: Dict[str, str]) -> str:
    """Fill skeleton template with variables."""
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key == "color.toLowerCase()":
            return variables.get("color", "").lower()
        return str(variables.get(key, ""))

    return re.sub(r"\$\{([^}]+)\}", replacer, skeleton)


def _create_llm_client(api_key: str | None) -> Any:
    """Create OpenAI client."""
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def _call_llm(
    client: Any, 
    payload: Dict[str, Any], 
    settings,
    structure_id: Optional[str] = None,
    explore_mode: bool = False
) -> str:
    """Call LLM with dynamic system prompt."""
    system_prompt = _build_system_prompt(structure_id=structure_id, explore_mode=explore_mode)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload)},
    ]
    retries = 2
    delay = 1
    for attempt in range(retries):
        try:
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                response = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    temperature=settings.openai_temperature,
                    timeout=30,
                )
            elif hasattr(client, "create"):
                response = client.create(
                    messages=messages,
                    model=settings.openai_model,
                    temperature=settings.openai_temperature,
                    timeout=30,
                )
            else:
                raise ValueError("Invalid LLM client")
            return response.choices[0].message.content
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    return ""


def _generate_locally(
    prompt_contexts: List[Dict[str, Any]], 
    renderer: str,
    explore_mode: bool = False
) -> List[Dict[str, Any]]:
    """Generate prompts locally without LLM (fallback mode)."""
    adapter = get_preference_adapter()
    prompts: List[Dict[str, Any]] = []
    
    for ctx in prompt_contexts:
        variables = _build_variable_map(ctx["designer"], ctx["color"], ctx["garment"])
        
        # Inject preference-based adjective if preferences loaded and NOT in explore mode
        if adapter.has_preferences and not explore_mode:
            weighted_adjs = adapter.get_weighted_adjectives()
            if weighted_adjs:
                top_adjs = weighted_adjs[:3]
                weights = [adj[1] for adj in top_adjs]
                total = sum(weights)
                if total > 0:
                    normalized_weights = [w / total for w in weights]
                    selected = random.choices(top_adjs, weights=normalized_weights, k=1)[0]
                    variables["preferenceAdjective"] = selected[0]
        
        text = _fill_skeleton(ctx["prompt_structure"]["skeleton"], variables).strip()
        if not text.endswith("---"):
            text = f"{text} ---"
        
        prompts.append(
            {
                "promptText": text,
                "designerId": ctx["designer"]["id"],
                "garmentId": ctx["garment"]["id"],
                "promptStructureId": ctx["prompt_structure"]["id"],
                "renderer": renderer,
            }
        )
    return prompts


def generate_prompts_with_llm(
    *,
    num_prompts: int,
    renderer: str,
    designers: List[Dict[str, Any]],
    colors: List[Dict[str, Any]],
    garments_by_category: Dict[str, List[Dict[str, Any]]],
    prompt_structures: List[Dict[str, Any]],
    llm_client: Any | None = None,
    rng: random.Random | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate fashion image prompts using LLM or local fallback.
    
    Uses optimizer scores and preferences when exploiting,
    favors novelty when exploring.
    """
    rng = rng or random
    filtered_structures = [s for s in prompt_structures if s.get("renderer") == renderer]
    
    if not filtered_structures:
        raise ValueError(f"No prompt structures found for renderer {renderer}")
    if not designers or not colors:
        raise ValueError("Designers and colors are required")
    
    # Determine if this batch should be in exploration mode
    adapter = get_preference_adapter()
    explore_mode = adapter.should_explore(rng) if adapter.has_preferences else False
    
    if explore_mode:
        logger.info(f"Exploration mode activated for batch of {num_prompts} prompts")
    else:
        logger.info(f"Exploitation mode for batch of {num_prompts} prompts")

    def build_contexts(count: int, explore: bool = False) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for _ in range(count):
            designer = rng.choice(designers)
            color = rng.choice(colors)
            garment = _select_garment(garments_by_category, rng)
            structure = _select_structure(filtered_structures, rng, explore_mode=explore)
            contexts.append(
                {
                    "designer": designer,
                    "color": color,
                    "garment": garment,
                    "prompt_structure": structure,
                }
            )
        return contexts

    prompt_contexts = build_contexts(num_prompts, explore=explore_mode)

    if llm_client is None:
        return {"prompts": _generate_locally(prompt_contexts, renderer, explore_mode=explore_mode)}

    settings = get_settings()
    attempts = 2
    prompts_accum: List[Dict[str, Any]] = []
    contexts_remaining = prompt_contexts
    target = num_prompts

    for attempt in range(attempts):
        try:
            # Get the most common structure ID from contexts for guidance
            structure_ids = [ctx["prompt_structure"]["id"] for ctx in contexts_remaining]
            primary_structure_id = max(set(structure_ids), key=structure_ids.count) if structure_ids else None
            
            attempt_payload = {
                "num_prompts": len(contexts_remaining),
                "renderer": renderer,
                "prompt_structures": filtered_structures,
                "prompt_contexts": contexts_remaining,
                "explore_mode": explore_mode,
            }
            raw_content = _call_llm(
                llm_client, 
                attempt_payload, 
                settings, 
                structure_id=primary_structure_id,
                explore_mode=explore_mode
            )
            data = json.loads(raw_content)
            prompts = data.get("prompts", [])
            for prompt in prompts:
                if len(prompts_accum) >= target:
                    break
                if REQUIRED_PROMPT_KEYS - prompt.keys():
                    continue
                if prompt.get("renderer") != renderer:
                    continue
                prompts_accum.append(prompt)
            if len(prompts_accum) >= target:
                return {"prompts": prompts_accum[:target]}
            remaining_needed = target - len(prompts_accum)
            contexts_remaining = build_contexts(remaining_needed, explore=explore_mode)
        except json.JSONDecodeError:
            if attempt == attempts - 1:
                break
            continue
        except Exception:
            if attempt == attempts - 1:
                break
            continue

    raise ValueError("LLM could not return required prompt count")
