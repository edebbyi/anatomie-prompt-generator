"""
Preference Adapter
Stores and applies the global preference vector, structure scores, and 
structure-specific prompt insights received from the Optimizer via the Orchestrator.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class PreferenceAdapter:
    """
    Manages learned preferences from the Optimizer:
    - Global preference vector (attribute scores)
    - Structure scores (ML-predicted success probability)
    - Structure prompt insights (top-performing prompts per structure)
    - Exploration rate (balance novelty vs exploitation)
    """
    
    def __init__(self):
        self._preferences: Dict[str, float] = {}
        self._exploration_rate: float = 0.2
        self._structure_scores: Dict[str, float] = {}
        self._structure_prompt_insights: Dict[str, Dict[str, Any]] = {}
        self._last_updated: Optional[str] = None
        self._exploration_count: int = 0
        self._exploitation_count: int = 0
    
    def update(
        self, 
        preferences: Dict[str, float], 
        exploration_rate: Optional[float] = None,
        structure_scores: Optional[Dict[str, float]] = None,
        structure_prompt_insights: Optional[Dict[str, Any]] = None
    ):
        """
        Update preferences, scores, and insights.
        
        Args:
            preferences: Dict mapping attribute names to scores (0.0-1.0)
            exploration_rate: Optional override for exploration rate (0.0-1.0)
            structure_scores: Optional dict mapping structure_id to optimizer_score
            structure_prompt_insights: Optional dict mapping structure_id to prompt insights
        """
        self._preferences = dict(sorted(
            preferences.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        if exploration_rate is not None:
            self._exploration_rate = max(0.0, min(1.0, exploration_rate))
        
        if structure_scores is not None:
            self._structure_scores = dict(sorted(
                structure_scores.items(),
                key=lambda x: x[1],
                reverse=True
            ))
        
        if structure_prompt_insights is not None:
            self._structure_prompt_insights = structure_prompt_insights
        
        self._last_updated = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            f"Preferences updated: {len(self._preferences)} attributes, "
            f"{len(self._structure_scores)} structure scores, "
            f"{len(self._structure_prompt_insights)} structure insights, "
            f"exploration_rate={self._exploration_rate}"
        )
    
    def clear(self):
        """Reset all preferences to defaults."""
        self._preferences = {}
        self._exploration_rate = 0.2
        self._structure_scores = {}
        self._structure_prompt_insights = {}
        self._last_updated = datetime.now(timezone.utc).isoformat()
        self._exploration_count = 0
        self._exploitation_count = 0
        logger.info("Preferences cleared")
    
    # === PROPERTIES ===
    
    @property
    def has_preferences(self) -> bool:
        """Check if attribute preferences have been loaded."""
        return len(self._preferences) > 0
    
    @property
    def has_structure_scores(self) -> bool:
        """Check if optimizer scores are available for structures."""
        return len(self._structure_scores) > 0
    
    @property
    def has_structure_insights(self) -> bool:
        """Check if structure-specific prompt insights are available."""
        return len(self._structure_prompt_insights) > 0
    
    @property
    def exploration_rate(self) -> float:
        """Current exploration rate (0.0-1.0)."""
        return self._exploration_rate
    
    @property
    def last_updated(self) -> Optional[str]:
        """ISO timestamp of last update."""
        return self._last_updated
    
    @property
    def structures_with_scores_count(self) -> int:
        """Number of structures with optimizer scores."""
        return len(self._structure_scores)
    
    @property
    def structures_with_insights_count(self) -> int:
        """Number of structures with prompt insights."""
        return len(self._structure_prompt_insights)
    
    # === PREFERENCE METHODS ===
    
    def get_top_preferences(self, n: int = 20) -> Dict[str, float]:
        """Get top N preferences by score."""
        return dict(list(self._preferences.items())[:n])
    
    def get_preference_score(self, attribute: str) -> float:
        """Get score for a specific attribute (default 0.5 if unknown)."""
        return self._preferences.get(attribute, 0.5)
    
    # === STRUCTURE SCORE METHODS ===
    
    def get_structure_score(self, structure_id: str) -> Optional[float]:
        """Get optimizer score for a specific structure."""
        return self._structure_scores.get(structure_id)
    
    def get_top_structures(self, n: int = 10) -> Dict[str, float]:
        """Get top N structures by optimizer score."""
        return dict(list(self._structure_scores.items())[:n])
    
    def rank_structures(self, structure_ids: List[str]) -> List[Tuple[str, float]]:
        """
        Rank a list of structure IDs by their optimizer scores.
        
        Args:
            structure_ids: List of structure IDs to rank
            
        Returns:
            List of (structure_id, score) tuples, sorted by score descending.
            Structures without scores get a default of 0.5.
        """
        ranked = []
        for sid in structure_ids:
            score = self._structure_scores.get(sid, 0.5)
            ranked.append((sid, score))
        return sorted(ranked, key=lambda x: x[1], reverse=True)
    
    # === STRUCTURE INSIGHT METHODS ===
    
    def get_structure_insights(self, structure_id: str) -> Optional[Dict[str, Any]]:
        """
        Get prompt insights for a specific structure.
        
        Returns:
            Dict with 'top_prompts' and 'avg_success_rate', or None if not available
        """
        return self._structure_prompt_insights.get(structure_id)
    
    # === STYLE GUIDANCE ===
    
    def get_style_guidance(self, structure_id: Optional[str] = None) -> str:
        """
        Generate style guidance text for LLM prompt injection.
        
        Args:
            structure_id: Optional structure ID to include structure-specific examples
            
        Returns:
            Formatted string describing brand preferences for LLM context.
        """
        if not self._preferences:
            return ""
        
        guidance_parts = []
        
        # Global attribute preferences (score > 0.6 = strong preference)
        strong_preferences = [
            (attr, score) for attr, score in self._preferences.items() 
            if score > 0.6
        ][:10]
        
        # Attributes to avoid (score < 0.3)
        avoid_attributes = [
            attr for attr, score in self._preferences.items() 
            if score < 0.3
        ][:5]
        
        if strong_preferences:
            prefs_formatted = ", ".join(
                f"{attr.replace('_', ' ')} ({score:.1f})" 
                for attr, score in strong_preferences
            )
            guidance_parts.append(f"PREFERRED ATTRIBUTES (incorporate these): {prefs_formatted}")
        
        if avoid_attributes:
            avoid_formatted = ", ".join(attr.replace('_', ' ') for attr in avoid_attributes)
            guidance_parts.append(f"LESS FAVORED ATTRIBUTES (use sparingly): {avoid_formatted}")
        
        # Structure-specific prompt examples
        if structure_id and structure_id in self._structure_prompt_insights:
            insights = self._structure_prompt_insights[structure_id]
            top_prompts = insights.get("top_prompts", [])[:3]
            
            if top_prompts:
                examples = []
                for p in top_prompts:
                    preview = p.get("prompt_preview", "")[:120]
                    rate = p.get("success_rate", 0)
                    examples.append(f'  • "{preview}..." ({rate:.0%} success)')
                
                guidance_parts.append(
                    f"HIGH-PERFORMING PROMPTS FOR THIS STRUCTURE (use as inspiration):\n" + 
                    "\n".join(examples)
                )
        
        return "\n\n".join(guidance_parts) if guidance_parts else ""
    
    # === EXPLORATION ===
    
    def should_explore(self, rng) -> bool:
        """
        Determine if this batch should explore (novelty) vs exploit (use preferences).
        
        Args:
            rng: Random number generator instance
            
        Returns:
            True if should explore, False if should exploit
        """
        exploring = rng.random() < self._exploration_rate
        
        if exploring:
            self._exploration_count += 1
        else:
            self._exploitation_count += 1
        
        return exploring
    
    def get_exploration_stats(self) -> Dict[str, Any]:
        """Get exploration vs exploitation statistics."""
        total = self._exploration_count + self._exploitation_count
        return {
            "exploration_count": self._exploration_count,
            "exploitation_count": self._exploitation_count,
            "total_decisions": total,
            "actual_exploration_rate": round(self._exploration_count / total, 4) if total > 0 else 0,
            "configured_exploration_rate": self._exploration_rate
        }
    
    def reset_exploration_stats(self):
        """Reset exploration statistics."""
        self._exploration_count = 0
        self._exploitation_count = 0
    
    # === ADJECTIVE WEIGHTING ===
    
    def get_weighted_adjectives(self) -> List[Tuple[str, float]]:
        """
        Get adjectives weighted by preference score for variable filling.
        
        Returns:
            List of (adjective, weight) tuples sorted by weight descending.
        """
        if not self._preferences:
            return []
        
        adjective_map = {
            "oversized": "oversized",
            "tailored": "tailored",
            "relaxed_fit": "relaxed",
            "slim_fit": "slim",
            "cropped": "cropped",
            "elongated": "elongated",
            "boxy": "boxy",
            "fitted": "fitted",
            "flowy": "flowy",
            "structured": "structured",
            "minimalist": "minimalist",
            "earth_tones": "earth-toned",
            "monochromatic": "monochromatic",
            "tonal": "tonal",
            "muted": "muted",
            "neutral": "neutral",
            "luxe_hand": "luxurious",
            "refined_casual": "refined",
            "elevated_basic": "elevated",
            "travel_ready": "travel-ready",
            "versatile": "versatile",
            "lightweight": "lightweight",
            "drapey": "draped",
            "crisp": "crisp",
        }
        
        weighted = []
        for attr, score in self._preferences.items():
            if attr in adjective_map and score > 0.4:
                weighted.append((adjective_map[attr], score))
        
        return sorted(weighted, key=lambda x: x[1], reverse=True)


# Global singleton instance
_preference_adapter = PreferenceAdapter()


def get_preference_adapter() -> PreferenceAdapter:
    """Get the global preference adapter instance."""
    return _preference_adapter
