from dataclasses import dataclass, field


@dataclass
class LeadsGenerationSession:
    ref_link: str
    card: str
    proxy: str | None = None
    proxies: list[str] = field(default_factory=list)
    count: int = 1
