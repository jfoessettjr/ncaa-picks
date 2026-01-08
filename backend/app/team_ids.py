import re
import unicodedata

# optional: hard-coded overrides for known tricky schools
# key = normalized input (after basic cleanup), value = canonical id you want
OVERRIDES = {
    "st johns": "st-johns-ny",
    "miami": "miami-fl",
    "usc": "southern-california",
    "ucla": "ucla",
    "pitt": "pittsburgh",
    "lsu": "louisiana-state",
    "unc": "north-carolina",
}

_RE_PUNCT = re.compile(r"[^a-z0-9\s-]")
_RE_WS = re.compile(r"\s+")

def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

def canonical_team_id(team_name: str) -> str:
    """
    Turn a team name like 'Michigan St.' into a stable id like 'michigan-state'.
    """
    s = _ascii(team_name or "").lower().strip()

    # normalize common abbreviations/variants
    s = s.replace("&", " and ")
    s = s.replace("st.", "state")
    s = s.replace("st ", "state ")
    s = s.replace(" mt.", " mount")
    s = s.replace(" mt ", " mount ")

    # remove punctuation (keep letters/numbers/spaces/hyphens)
    s = _RE_PUNCT.sub("", s)

    # collapse whitespace
    s = _RE_WS.sub(" ", s).strip()

    # apply overrides (after cleanup)
    if s in OVERRIDES:
        return OVERRIDES[s]

    # slugify spaces -> hyphens
    return s.replace(" ", "-")
