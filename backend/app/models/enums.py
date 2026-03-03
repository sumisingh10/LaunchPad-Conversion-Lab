"""ORM model definitions for enums.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from enum import Enum


class CampaignObjective(str, Enum):
    """Enumeration for campaign objective values."""
    CTR = "CTR"
    ATC = "ATC"
    CONVERSION = "CONVERSION"


class CampaignStatus(str, Enum):
    """Enumeration for campaign status values."""
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class VariantSource(str, Enum):
    """Enumeration for variant source values."""
    HUMAN = "HUMAN"
    CODEX_GENERATED = "CODEX_GENERATED"
    CODEX_PATCHED = "CODEX_PATCHED"


class CreatedBySystem(str, Enum):
    """ORM model for created by system."""
    USER = "USER"
    CODEX = "CODEX"
    SYSTEM = "SYSTEM"


class MetricSource(str, Enum):
    """Enumeration for metric source values."""
    SIMULATED = "SIMULATED"
    IMPORTED = "IMPORTED"


class RecommendationStatus(str, Enum):
    """Enumeration for recommendation status values."""
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ChangeType(str, Enum):
    """Enumeration for change type values."""
    COPY = "COPY"
    LAYOUT = "LAYOUT"
    TRUST_SIGNAL = "TRUST_SIGNAL"
    CTA = "CTA"
    CONFIG = "CONFIG"
    CODE = "CODE"


class LiftEventType(str, Enum):
    """Enumeration for lift event type values."""
    RECOMMENDATION_CREATED = "RECOMMENDATION_CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    METRICS_SIMULATED = "METRICS_SIMULATED"


class ActorType(str, Enum):
    """Enumeration for actor type values."""
    USER = "USER"
    SYSTEM = "SYSTEM"
    CODEX = "CODEX"


class FeedbackSentiment(str, Enum):
    """Enumeration for feedback sentiment values."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
