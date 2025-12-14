"""Mindful - Mind's ASCII mascot with emotions."""

import os
import sys


def can_use_unicode() -> bool:
    """Check if terminal supports Unicode output.

    Returns True by default. Set MIND_ASCII=1 to force ASCII fallback.
    Set MIND_UNICODE=1 to force Unicode even on Windows.
    """
    # Allow forcing ASCII via env var
    if os.environ.get("MIND_ASCII", "").lower() in ("1", "true", "yes"):
        return False

    # Allow forcing Unicode via env var (overrides Windows detection)
    if os.environ.get("MIND_UNICODE", "").lower() in ("1", "true", "yes"):
        return True

    # Check if stdout encoding supports Unicode
    # Windows cp1252 doesn't support box drawing characters
    try:
        encoding = sys.stdout.encoding or ""
        if encoding.lower() in ("cp1252", "cp1251", "ascii", "latin-1", "latin1"):
            return False
    except Exception:
        pass

    return True


# Mindful's expressions - eyes and mouth change with state
EXPRESSIONS = {
    "idle": ("◎  ◎", "╧╧"),
    "happy": ("◠  ◠", "◡◡"),
    "thinking": ("◎  ◎", "~~"),
    "success": ("^  ^", "▽▽"),
    "searching": ("◎  ◎", ".."),
    "curious": ("◎  ◎", "??"),
    "warning": ("◉  ◉", "!!"),
    "alert": ("●  ●", "<>"),
    "sleepy": ("ᴗ  ᴗ", ".."),
    "confused": ("◎  ◎", "??"),
    "sad": ("◡  ◡", "nn"),
    "shy": ("◦  ◦", "><"),
    "excited": ("★  ★", "○○"),
    "focused": ("◉  ◉", "──"),
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

# ASCII fallback for Windows cp1252
EXPRESSIONS_ASCII = {
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


def get_mindful(emotion: str = "idle", fancy: bool = True, message: str = "") -> str:
    """Get Mindful ASCII art with given emotion.

    Args:
        emotion: One of the EXPRESSIONS keys
        fancy: Use Unicode box drawing (False for ASCII fallback)
        message: Optional message to show next to Mindful

    Returns:
        Multi-line string with Mindful ASCII art
    """
    expressions = EXPRESSIONS if fancy else EXPRESSIONS_ASCII
    eyes, mouth = expressions.get(emotion, expressions["idle"])

    if fancy:
        lines = [
            "    ╔══════╗",
            f"   ╔╣ {eyes} ╠╗",
            "   ║╚══╤╤══╝║",
            f"   ╠═══{mouth}═══╣",
            "   ╚╤══════╤╝",
            "    ╘══╧╧══╛",
        ]
    else:
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


def get_mindful_compact(emotion: str = "idle", fancy: bool = True) -> str:
    """Get a compact single-line representation of Mindful.

    Args:
        emotion: One of the EXPRESSIONS keys
        fancy: Use Unicode characters (False for ASCII fallback)

    Returns:
        Single-line string with Mindful face
    """
    expressions = EXPRESSIONS if fancy else EXPRESSIONS_ASCII
    eyes, mouth = expressions.get(emotion, expressions["idle"])

    if fancy:
        return f"╔╣ {eyes} ╠╗ {mouth}"
    else:
        return f"[{eyes}] {mouth}"


def mindful_says(action: str, message: str, fancy: bool = True) -> str:
    """Get Mindful with appropriate emotion for an action, with message.

    Args:
        action: Mind action (recall, log, search, etc.)
        message: Message to display
        fancy: Use Unicode (False for ASCII fallback)

    Returns:
        Multi-line string with Mindful and message
    """
    emotion = ACTION_EMOTIONS.get(action, "idle")
    return get_mindful(emotion, fancy, message)


def mindful_line(action: str, message: str, fancy: bool = True) -> str:
    """Get a single-line Mindful output for terminal.

    Args:
        action: Mind action (recall, log, search, etc.)
        message: Message to display
        fancy: Use Unicode (False for ASCII fallback)

    Returns:
        Single line: [mindful face] action | message
    """
    emotion = ACTION_EMOTIONS.get(action, "idle")
    expressions = EXPRESSIONS if fancy else EXPRESSIONS_ASCII
    eyes, mouth = expressions.get(emotion, expressions["idle"])

    if fancy:
        face = f"({eyes[0]}{mouth}{eyes[-1]})"
    else:
        face = f"({eyes[0]}{mouth}{eyes[-1]})"

    return f"{face} mind_{action} | {message}"


# Quick test
if __name__ == "__main__":
    fancy = can_use_unicode()
    print(f"=== Mindful Emotions (fancy={fancy}) ===\n")

    for emotion in ["idle", "happy", "thinking", "searching", "warning", "excited", "shy", "sleepy", "error"]:
        print(f"{emotion.upper()}:")
        print(get_mindful(emotion, fancy=fancy))
        print()

    print("=== Action Examples ===\n")
    print(mindful_says("recall", "Loaded 36 memories", fancy=fancy))
    print()
    print(mindful_says("warning", "3 rejected approaches!", fancy=fancy))
    print()

    print("=== Compact Lines ===\n")
    print(mindful_line("recall", "Loaded 36 memories", fancy=fancy))
    print(mindful_line("log", "Experience -> SESSION.md", fancy=fancy))
    print(mindful_line("warning", "3 rejected - slow down!", fancy=fancy))
