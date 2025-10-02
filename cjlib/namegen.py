"""Random name generator for container images."""

import random
import re

# Word lists for name generation
ADJECTIVES = [
    "happy",
    "clever",
    "brave",
    "gentle",
    "swift",
    "bright",
    "calm",
    "bold",
    "quiet",
    "eager",
    "lucky",
    "witty",
    "kind",
    "wise",
    "free",
    "wild",
    "cool",
    "warm",
    "pure",
    "noble",
]

NOUNS = [
    "turtle",
    "falcon",
    "river",
    "mountain",
    "forest",
    "ocean",
    "wind",
    "star",
    "moon",
    "sun",
    "cloud",
    "thunder",
    "valley",
    "desert",
    "tiger",
    "eagle",
    "dolphin",
    "wolf",
    "bear",
    "fox",
]

# Pattern for valid names
NAME_PATTERN = re.compile(r"^cj-[a-z]+-[a-z]+$")


def generate_name() -> str:
    """Generate a random name in the format cj-{adjective}-{noun}.

    Returns:
        str: A randomly generated name like "cj-happy-turtle"
    """
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"cj-{adjective}-{noun}"


def is_valid_name(name: str) -> bool:
    """Check if a name matches the valid pattern cj-[a-z]+-[a-z]+.

    Args:
        name: The name to validate

    Returns:
        bool: True if the name is valid, False otherwise
    """
    return NAME_PATTERN.match(name) is not None
