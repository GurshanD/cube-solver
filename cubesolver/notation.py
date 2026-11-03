"""Standard cube notation: U R F D L B, with ' for counter-clockwise and 2 for half turns.

Moves are indexed 0..17 as face*3 + k (k: 0 = clockwise, 1 = half, 2 = counter-clockwise).
"""

from __future__ import annotations

import random
import re

from .geometry import FACES

SUFFIX = ["", "2", "'"]
NAMES = [f + s for f in FACES for s in SUFFIX]
_TOKEN = re.compile(r"([URFDLB])(2'?|'2?|’|3)?", re.IGNORECASE)


def face(m: int) -> int:
    return m // 3


def inverse(m: int) -> int:
    return m // 3 * 3 + (2 - m % 3)


def parse(text: str) -> list[int]:
    """'R U R’ U2' -> [3, 0, 5, 1]. Accepts lowercase, smart quotes, R3 = R'."""
    text = (text or "").strip()
    if not text:
        return []
    moves = []
    for tok in text.replace(",", " ").split():
        m = _TOKEN.fullmatch(tok)
        if not m:
            # allow run-together like "RUR'U'"
            parts = _TOKEN.findall(tok)
            if "".join(a + b for a, b in parts).upper() != tok.upper():
                raise ValueError(f"I don't understand the move '{tok}'. Use U R F D L B with ' or 2")
            for f, s in parts:
                moves.append(_index(f, s))
            continue
        moves.append(_index(m.group(1), m.group(2) or ""))
    return moves


def _index(f: str, s: str) -> int:
    k = 0
    if s.startswith("2"):
        k = 1
    elif s in ("'", "’", "3", "'2"):
        k = 2 if s != "'2" else 1
    return FACES.index(f.upper()) * 3 + k


def format(moves) -> str:  # noqa: A001 - mirrors str.format naming on purpose
    return " ".join(NAMES[m] for m in moves)


def invert(moves) -> list[int]:
    return [inverse(m) for m in reversed(moves)]


def allowed_after(prev: int | None, m: int) -> bool:
    """Skip redundant sequences: same face twice (R R), and opposite faces in
    both orders (U D and D U do the same thing, so only allow U D)."""
    if prev is None:
        return True
    a, b = face(prev), face(m)
    return a != b and not (a % 3 == b % 3 and a > b)


def simplify(moves) -> list[int]:
    """Merge consecutive turns of the same face: R R -> R2, R R' -> (nothing)."""
    out: list[int] = []
    for m in moves:
        if out and face(out[-1]) == face(m):
            turns = (out[-1] % 3 + 1 + m % 3 + 1) % 4
            out.pop()
            if turns:
                out.append(face(m) * 3 + turns - 1)
        else:
            out.append(m)
    return out


def random_scramble(length: int, rng: random.Random | None = None, faces: str = FACES) -> list[int]:
    rng = rng or random.Random()
    allowed = [m for m in range(18) if FACES[face(m)] in faces]
    seq: list[int] = []
    while len(seq) < length:
        m = rng.choice(allowed)
        if allowed_after(seq[-1] if seq else None, m):
            seq.append(m)
    return seq
