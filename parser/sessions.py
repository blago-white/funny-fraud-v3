from dataclasses import dataclass, field
from enum import Enum


class SessionStrategy(Enum):
    DEFAULT = "D"
    SBER_ID = "S"


@dataclass
class LeadsGenerationSession:
    card: str
    count: int = 1
    ref_links: list[str] = None
    ref_link: str = None
    strategy: SessionStrategy = SessionStrategy.DEFAULT
