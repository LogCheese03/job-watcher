"""The title rule: decides whether a posting is in the watched role (finance analyst).

A title is in the role when it contains one of the INCLUDE patterns and none of
the EXCLUDE patterns. Matching is case-insensitive and on whole words.
"""
import re

INCLUDE = [
    r"financial analyst",
    r"finance analyst",
    r"fp&a",
    r"fp & a",
    r"financial planning",
    r"corporate finance",
    r"credit analyst",
    r"credit risk analyst",
    r"treasury analyst",
    r"investment analyst",
    r"finance associate",
    r"financial associate",
    r"finance (?:business )?partner",
    r"(?:finance|financial) rotation(?:al)? program",
]

# Titles that use finance words but are a different job.
EXCLUDE = [
    r"intern(?:ship)?",
    r"engineer",
    r"developer",
    r"recruiter",
    r"sales",
]

_INCLUDE_RE = re.compile(r"\b(?:" + "|".join(INCLUDE) + r")\b", re.IGNORECASE)
_EXCLUDE_RE = re.compile(r"\b(?:" + "|".join(EXCLUDE) + r")\b", re.IGNORECASE)


def in_role(title):
    title = title or ""
    return bool(_INCLUDE_RE.search(title)) and not _EXCLUDE_RE.search(title)
