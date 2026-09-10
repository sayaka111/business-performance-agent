"""Conservative SQL identifier handling; values remain bound parameters."""

import re
from ..models.schemas import BoundaryError


def quote(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*", identifier
    ):
        raise BoundaryError("data_unavailable", "Invalid SQL identifier in mapping")
    return '"' + identifier + '"'
