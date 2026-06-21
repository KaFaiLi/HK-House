"""28Hse source-specific intermediate model.

28Hse's data API is fronted by Cloudflare Turnstile and its exact JSON shape is
only visible once authenticated in a browser. This model is intentionally loose:
it accepts whatever fields the captured endpoint returns and the parser maps the
common ones. Tighten the typing once a real payload is captured.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Hse28Listing(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: dict[str, Any] = {}

    @classmethod
    def of(cls, raw: dict[str, Any]) -> "Hse28Listing":
        return cls(data=raw)
