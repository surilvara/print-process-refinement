"""Parse magazine folder names into a publication context block.

Convention (from open_src/src/publication.py):
    <magazine_name>_<YYYY-MM-DD>
    <magazine_name>_<YYYY-MM>
Optionally suffixed with `_v2` etc.

Folder name is split on the last date-looking token; everything before is the
publication name (lowercase, country embedded by convention like
'vogue_uk', 'financial_times_uk').
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_DATE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}(?:-\d{2})?)(?P<suffix>(?:_.+)?)$")


@dataclass(frozen=True)
class PublicationContext:
    folder_name: str
    publication_name: str | None
    issue_date: str | None  # ISO date, may be year-month if day absent
    country: str | None  # best-effort: last underscore token of name
    suffix: str | None  # e.g. 'v2'

    def to_dict(self) -> dict:
        return asdict(self)


def parse(folder_name: str) -> PublicationContext:
    parts = folder_name.split("_")
    # Scan from the right for a date-like token.
    for i in range(len(parts) - 1, -1, -1):
        m = _DATE_RE.match("_".join(parts[i:]))
        if m:
            name = "_".join(parts[:i]) or None
            suffix = (m.group("suffix") or "").lstrip("_") or None
            country = name.split("_")[-1] if name and "_" in name else None
            return PublicationContext(
                folder_name=folder_name,
                publication_name=name,
                issue_date=m.group("date"),
                country=country,
                suffix=suffix,
            )
    # No date found — use whole name as publication name.
    return PublicationContext(
        folder_name=folder_name,
        publication_name=folder_name,
        issue_date=None,
        country=None,
        suffix=None,
    )
