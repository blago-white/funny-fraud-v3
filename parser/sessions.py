from dataclasses import dataclass, field


@dataclass
class LeadsGenerationSession:
    card: str
    count: int = 1
    ref_links: list[str] = None
    ref_link: str = None
