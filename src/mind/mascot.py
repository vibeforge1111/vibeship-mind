"""Mindful - Mind's ASCII mascot with emotions.

Uses ASCII-only characters for maximum compatibility across all terminals,
including Windows cp1252 encoding.
"""


# Mindful's expressions - eyes and mouth change with state
# ASCII-only for maximum compatibility (Windows cp1252, etc.)
EXPRESSIONS = {
    "idle": ("o  o", "--"),
    "happy": ("^  ^", "vv"),
    "thinking": ("o  o", "~~"),
    "success": ("^  ^", "vv"),
    "searching": ("o  o", ".."),
    "curious": ("o  o", "??"),
    "warning": ("O  O", "!!"),
    "alert": ("O  O", "<>"),
    "sleepy": ("-  -", ".."),
    "confused": ("o  o", "??"),
    "sad": ("v  v", "nn"),
    "shy": (".  .", "><"),
    "excited": ("*  *", "oo"),
    "focused": ("O  O", "--"),
    "error": ("x  x", "##"),
}

# Map Mind actions to emotions
ACTION_EMOTIONS = {
    "recall": "happy",
    "log": "success",
    "search": "searching",
    "session": "curious",
    "blocker": "confused",
    "remind": "excited",
    "reminders": "idle",
    "edges": "focused",
    "checkpoint": "thinking",
    "status": "idle",
    "warning": "warning",
    "error": "error",
    "new_session": "shy",
    "idle": "idle",
    "sleepy": "sleepy",
    "reinforce": "success",  # Pattern reinforcement
}


def get_mindful(emotion: str = "idle", message: str = "") -> str:
    """Get Mindful ASCII art with given emotion.

    Args:
        emotion: One of the EXPRESSIONS keys
        message: Optional message to show next to Mindful

    Returns:
        Multi-line string with Mindful ASCII art
    """
    eyes, mouth = EXPRESSIONS.get(emotion, EXPRESSIONS["idle"])

    lines = [
        "    .======.",
        f"   .| {eyes} |.",
        "   |'==||=='|",
        f"   |==={mouth}===|",
        "   '|======|'",
        "    '==||=='",
    ]

    if message:
        # Add message next to Mindful (middle line)
        padded_lines = []
        for i, line in enumerate(lines):
            if i == 2:  # Middle-ish line
                padded_lines.append(f"{line}  {message}")
            else:
                padded_lines.append(line)
        lines = padded_lines

    return "\n".join(lines)


def get_mindful_compact(emotion: str = "idle") -> str:
    """Get a compact single-line representation of Mindful.

    Args:
        emotion: One of the EXPRESSIONS keys

    Returns:
        Single-line string with Mindful face
    """
    eyes, mouth = EXPRESSIONS.get(emotion, EXPRESSIONS["idle"])
    return f"[{eyes}] {mouth}"


def mindful_says(action: str, message: str) -> str:
    """Get Mindful with appropriate emotion for an action, with message.

    Args:
        action: Mind action (recall, log, search, etc.)
        message: Message to display

    Returns:
        Multi-line string with Mindful and message
    """
    emotion = ACTION_EMOTIONS.get(action, "idle")
    return get_mindful(emotion, message=message)


def mindful_line(action: str, message: str) -> str:
    """Get a single-line Mindful output for terminal.

    Args:
        action: Mind action (recall, log, search, etc.)
        message: Message to display

    Returns:
        Single line: [mindful face] action | message
    """
    emotion = ACTION_EMOTIONS.get(action, "idle")
    eyes, mouth = EXPRESSIONS.get(emotion, EXPRESSIONS["idle"])
    face = f"({eyes[0]}{mouth}{eyes[-1]})"
    return f"{face} mind_{action} | {message}"


# Quick test
if __name__ == "__main__":
    print("=== Mindful Emotions ===\n")

    for emotion in ["idle", "happy", "thinking", "searching", "warning", "excited", "shy", "sleepy", "error"]:
        print(f"{emotion.upper()}:")
        print(get_mindful(emotion))
        print()

    print("=== Action Examples ===\n")
    print(mindful_says("recall", "Loaded 36 memories"))
    print()
    print(mindful_says("warning", "3 rejected approaches!"))
    print()

    print("=== Compact Lines ===\n")
    print(mindful_line("recall", "Loaded 36 memories"))
    print(mindful_line("log", "Experience -> SESSION.md"))
    print(mindful_line("warning", "3 rejected - slow down!"))
