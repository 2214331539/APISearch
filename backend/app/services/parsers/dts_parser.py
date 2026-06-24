from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from parse_dts import parse_file


class DtsParserAdapter:
    supported_extensions = {".dts"}

    def parse_file(self, path: Path) -> List[Dict]:
        api = parse_file(str(path))
        api["source_type"] = "dts"
        return [api]
