"""Hexagram identification for the engineering state machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

from .lines import LineSignal


# Binary strings are bottom -> top, matching the line order in lines.py.
CORE_HEXAGRAMS: Dict[str, str] = {
    "111111": "qian",      # 乾
    "000000": "kun",       # 坤
    "100100": "zhen",      # 震
    "010010": "kan",       # 坎
    "000001": "bo",        # 剥
    "100000": "fu",        # 复
    "101010": "jiji",      # 既济
    "010101": "weiji",     # 未济
}

DISPLAY_NAMES: Dict[str, str] = {
    "qian": "Qian / 乾",
    "kun": "Kun / 坤",
    "zhen": "Zhen / 震",
    "kan": "Kan / 坎",
    "bo": "Bo / 剥",
    "fu": "Fu / 复",
    "jiji": "Ji Ji / 既济",
    "weiji": "Wei Ji / 未济",
    "mixed": "Mixed / 杂卦态",
}


@dataclass(frozen=True)
class HexagramState:
    """A Yijing-style state derived from six engineering lines."""

    binary: str
    name: str
    display_name: str
    moving_lines: tuple[int, ...]
    changed_binary: str
    changed_name: str
    changed_display_name: str

    @property
    def is_core_state(self) -> bool:
        return self.name != "mixed"


def _name(binary: str) -> str:
    return CORE_HEXAGRAMS.get(binary, "mixed")


def identify_hexagram(lines: Sequence[LineSignal]) -> HexagramState:
    """Identify current state and changed state from line signals."""

    lines = list(lines)
    if len(lines) != 6:
        raise ValueError(f"identify_hexagram requires exactly 6 lines, got {len(lines)}")

    positions = [line.position for line in lines]
    if sorted(positions) != [1, 2, 3, 4, 5, 6]:
        raise ValueError(
            "identify_hexagram requires one line for each position 1..6; "
            f"got positions={positions!r}"
        )

    bits = [str(line.bit) for line in lines]
    binary = "".join(bits)
    moving_positions = tuple(line.position for line in lines if line.moving)

    changed_bits = bits[:]
    for position in moving_positions:
        index = position - 1
        changed_bits[index] = "0" if changed_bits[index] == "1" else "1"
    changed_binary = "".join(changed_bits)

    current_name = _name(binary)
    changed_name = _name(changed_binary)
    return HexagramState(
        binary=binary,
        name=current_name,
        display_name=DISPLAY_NAMES[current_name],
        moving_lines=moving_positions,
        changed_binary=changed_binary,
        changed_name=changed_name,
        changed_display_name=DISPLAY_NAMES[changed_name],
    )
