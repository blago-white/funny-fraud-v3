from dataclasses import dataclass, field


@dataclass
class LeadsGenerationSession:
    ref_link: str
    card: str
    count: int = 1
