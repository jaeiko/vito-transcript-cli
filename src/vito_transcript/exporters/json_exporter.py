"""Raw RTZR response JSON rendering."""

import json
from collections.abc import Mapping
from typing import Any


def render_json(payload: Mapping[str, Any]) -> str:
    """Render the complete raw RTZR payload as UTF-8-friendly JSON."""
    return json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n"
