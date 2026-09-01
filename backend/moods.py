"""
Mood catalog for the app.

Each mood carries:
- emoji / color for the UI
- a set of `seed_queries`: phrases used to pull relevant material out of the
  Cognee knowledge graph (built from the PDFs).
"""

from typing import TypedDict


class Mood(TypedDict):
    id: str
    label: str
    emoji: str
    color: str
    seed_queries: list[str]


MOODS: list[Mood] = [
    {
        "id": "anxious",
        "label": "Anxious",
        "emoji": "🌀",
        "color": "#FF6B35",
        "seed_queries": [
            "fear of the future",
            "restlessness and worry",
            "mind constantly thinking ahead",
        ],
    },
    {
        "id": "angry",
        "label": "Angry",
        "emoji": "🔥",
        "color": "#E93CAC",
        "seed_queries": [
            "anger and how to transform it",
            "reacting versus responding",
            "energy of rage",
        ],
    },
    {
        "id": "sad",
        "label": "Sad",
        "emoji": "🌧️",
        "color": "#5B6EE1",
        "seed_queries": [
            "sadness and grief",
            "loneliness",
            "accepting sorrow without resisting it",
        ],
    },
    {
        "id": "lost",
        "label": "Lost / Confused",
        "emoji": "🧭",
        "color": "#9B5DE5",
        "seed_queries": [
            "not knowing your path",
            "searching for meaning",
            "confusion about life direction",
        ],
    },
    {
        "id": "jealous",
        "label": "Jealous",
        "emoji": "💚",
        "color": "#2EC4B6",
        "seed_queries": [
            "jealousy in relationships",
            "comparing yourself to others",
            "possessiveness and love",
        ],
    },
    {
        "id": "guilty",
        "label": "Guilty",
        "emoji": "⚖️",
        "color": "#FFD23F",
        "seed_queries": [
            "guilt and conditioning",
            "self-judgment",
            "forgiving yourself",
        ],
    },
    {
        "id": "stuck",
        "label": "Stuck",
        "emoji": "🪨",
        "color": "#8D5A2B",
        "seed_queries": [
            "feeling stuck and repetition",
            "breaking old patterns",
            "resistance to change",
        ],
    },
    {
        "id": "lonely",
        "label": "Lonely",
        "emoji": "🌙",
        "color": "#3A86FF",
        "seed_queries": [
            "aloneness versus loneliness",
            "being comfortable alone",
            "solitude",
        ],
    },
    {
        "id": "overwhelmed",
        "label": "Overwhelmed",
        "emoji": "🌊",
        "color": "#FB5607",
        "seed_queries": [
            "too much to handle",
            "the mind's clutter and busyness",
            "living moment to moment",
        ],
    },
    {
        "id": "joyful",
        "label": "Joyful",
        "emoji": "✨",
        "color": "#FFBE0B",
        "seed_queries": [
            "celebration and gratitude",
            "living totally in the moment",
            "sharing your joy",
        ],
    },
]


def get_mood(mood_id: str) -> Mood | None:
    return next((m for m in MOODS if m["id"] == mood_id), None)


