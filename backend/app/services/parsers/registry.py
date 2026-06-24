from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from app.services.parsers.dts_parser import DtsParserAdapter
from app.services.parsers.json_parser import JsonParserAdapter


class ParserRegistry:
    def __init__(self) -> None:
        self.adapters = [DtsParserAdapter(), JsonParserAdapter()]

    def parse_file(self, path: Path) -> List[Dict]:
        extension = path.suffix.lower()
        for adapter in self.adapters:
            if extension in adapter.supported_extensions:
                return adapter.parse_file(path)
        raise ValueError(f"Unsupported file extension: {extension}")
