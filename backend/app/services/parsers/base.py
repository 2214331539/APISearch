from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Protocol


class ParserAdapter(Protocol):
    supported_extensions: set[str]

    def parse_file(self, path: Path) -> List[Dict]:
        ...
