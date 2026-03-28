"""Capo hierarchy for ThookAI agent orchestration.

Each Capo manages a domain of agents and provides coordination,
error handling, and decision-making for its area of responsibility.

- ContentCapo: Thinker, Writer, Designer, Video, Voice
- IntelligenceCapo: Scout, Analyst, Planner
- IdentityCapo: QC, Anti-Repetition, Fatigue Shield, Learning
"""

from agents.capos.content_capo import (
    run_content_creation,
    run_hook_debate,
    run_media_creation,
)
from agents.capos.intelligence_capo import (
    run_research,
    get_scheduling_intelligence,
)
from agents.capos.identity_capo import (
    run_identity_check,
    run_quality_control,
    record_learning_signal,
)

__all__ = [
    "run_content_creation",
    "run_hook_debate",
    "run_media_creation",
    "run_research",
    "get_scheduling_intelligence",
    "run_identity_check",
    "run_quality_control",
    "record_learning_signal",
]
