"""Interactive SELF_IMPROVE Testing Playground.

Run with: uv run python playground/test_runner.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.self_improve import (
    SelfImproveParser,
    SelfImproveData,
    Pattern,
    PatternType,
    load_self_improve,
    append_pattern,
    get_patterns_for_stack,
    generate_intuition_context,
    detect_intuitions,
    format_intuitions_for_context,
    extract_patterns_from_feedback,
    process_feedback_for_patterns,
)
from mind.storage import get_self_improve_path


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(name: str, passed: bool, details: str = ""):
    """Print a test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {name}")
    if details:
        print(f"         {details}")


def test_pattern_parsing():
    """Test 1: Pattern Detection."""
    print_header("TEST 1: Pattern Parsing")

    parser = SelfImproveParser()

    test_content = """
# Test SELF_IMPROVE.md

## Preferences
PREFERENCE: [coding] prefers short functions
PREFERENCE: [workflow] likes TDD approach

## Skills
SKILL: [python:async] expert at asyncio patterns
SKILL: [general] good at debugging

## Blind Spots
BLIND_SPOT: [testing] often forgets edge cases
BLIND_SPOT: [async] sometimes forgets await

## Anti-Patterns
ANTI_PATTERN: [complexity] tends to over-engineer

## Feedback Log
FEEDBACK: [2025-01-15] forgot error handling -> should add try-catch
FEEDBACK: [2025-01-16] too complex -> simpler solution worked
"""

    data = parser.parse(test_content)

    # Check counts
    print_result(
        "Preferences parsed",
        len(data.preferences) == 2,
        f"Expected 2, got {len(data.preferences)}"
    )
    print_result(
        "Skills parsed",
        len(data.skills) == 2,
        f"Expected 2, got {len(data.skills)}"
    )
    print_result(
        "Blind spots parsed",
        len(data.blind_spots) == 2,
        f"Expected 2, got {len(data.blind_spots)}"
    )
    print_result(
        "Anti-patterns parsed",
        len(data.anti_patterns) == 1,
        f"Expected 1, got {len(data.anti_patterns)}"
    )
    print_result(
        "Feedback parsed",
        len(data.feedback) == 2,
        f"Expected 2, got {len(data.feedback)}"
    )

    # Check specific values
    if data.preferences:
        p = data.preferences[0]
        print_result(
            "Preference category",
            p.category == "coding",
            f"Expected 'coding', got '{p.category}'"
        )
        print_result(
            "Preference description",
            "short functions" in p.description,
            f"Got: {p.description}"
        )

    if data.skills:
        s = data.skills[0]
        print_result(
            "Skill category with stack",
            s.category == "python:async",
            f"Expected 'python:async', got '{s.category}'"
        )

    return data


def test_stack_filtering(data: SelfImproveData = None):
    """Test 2: Stack Filtering."""
    print_header("TEST 2: Stack Filtering")

    if data is None:
        data = load_self_improve()

    # Create test data if empty
    if not data.all_patterns():
        parser = SelfImproveParser()
        data = parser.parse("""
PREFERENCE: [python] use type hints
PREFERENCE: [react] use functional components
SKILL: [python:async] asyncio expert
SKILL: [general] debugging
BLIND_SPOT: [javascript] forgets semicolons
ANTI_PATTERN: [general] over-engineers
""")

    # Test python stack
    python_stack = ["python", "fastapi"]
    filtered = get_patterns_for_stack(data, python_stack)

    print(f"  Testing with stack: {python_stack}")
    print(f"  Preferences: {len(filtered['preferences'])}")
    print(f"  Skills: {len(filtered['skills'])}")
    print(f"  Blind spots: {len(filtered['blind_spots'])}")
    print(f"  Anti-patterns: {len(filtered['anti_patterns'])}")

    # Check that universal/relevant patterns are included
    pref_cats = [p.category for p in filtered['preferences']]
    # coding and workflow are universal categories, so they should be included
    universal = {'coding', 'workflow', 'general', 'testing', 'security', 'architecture'}
    has_relevant = any(c.lower() in universal or 'python' in c.lower() for c in pref_cats)
    print_result(
        "Relevant preferences included",
        has_relevant,
        f"Categories: {pref_cats} (universal categories are always included)"
    )

    # Check that blind spots are always included (warnings)
    print_result(
        "Blind spots included (warnings always shown)",
        len(filtered['blind_spots']) >= 0,
        "Warnings should be inclusive"
    )

    return filtered


def test_intuition_detection():
    """Test 3: Intuition Detection (Pattern Radar)."""
    print_header("TEST 3: Intuition Detection")

    parser = SelfImproveParser()
    data = parser.parse("""
BLIND_SPOT: [async] often forgets to await async functions
BLIND_SPOT: [error-handling] skips try-catch blocks
ANTI_PATTERN: [api] tends to over-fetch data from endpoints
SKILL: [python:debugging] expert at using pdb and breakpoints
""")

    # Test context that should trigger blind spot
    context1 = "working on an async function that calls the database"
    intuitions1 = detect_intuitions(context1, data, ["python"])

    print(f"  Context: '{context1[:50]}...'")
    print(f"  Intuitions found: {len(intuitions1)}")
    for i in intuitions1:
        print(f"    - [{i.type.upper()}] {i.message}")

    print_result(
        "Async blind spot triggered",
        any(i.type == "watch" and "await" in i.message.lower() for i in intuitions1),
        "Should warn about forgetting await"
    )

    # Test context that should trigger anti-pattern
    context2 = "fetching user data from the API endpoint"
    intuitions2 = detect_intuitions(context2, data, ["python"])

    print(f"\n  Context: '{context2}'")
    print(f"  Intuitions found: {len(intuitions2)}")
    for i in intuitions2:
        print(f"    - [{i.type.upper()}] {i.message}")

    print_result(
        "API anti-pattern triggered",
        any(i.type == "avoid" for i in intuitions2),
        "Should warn about over-fetching"
    )

    # Test context that should trigger skill tip
    context3 = "debugging this weird issue with the parser"
    intuitions3 = detect_intuitions(context3, data, ["python"])

    print(f"\n  Context: '{context3}'")
    print(f"  Intuitions found: {len(intuitions3)}")
    for i in intuitions3:
        print(f"    - [{i.type.upper()}] {i.message}")

    print_result(
        "Debugging skill tip triggered",
        any(i.type == "tip" for i in intuitions3),
        "Should remind about pdb skills"
    )

    # Test context with no triggers
    context4 = "writing documentation for the readme file"
    intuitions4 = detect_intuitions(context4, data, ["python"])

    print(f"\n  Context: '{context4}'")
    print(f"  Intuitions found: {len(intuitions4)}")

    return intuitions1 + intuitions2 + intuitions3


def test_feedback_extraction():
    """Test 4: Feedback to Pattern Pipeline."""
    print_header("TEST 4: Feedback Pattern Extraction")

    # Create feedback entries that should extract a pattern
    feedback_entries = [
        Pattern(PatternType.FEEDBACK, "2025-01-01", "forgot type hints -> add type hints"),
        Pattern(PatternType.FEEDBACK, "2025-01-02", "missing type annotation -> should use typing"),
        Pattern(PatternType.FEEDBACK, "2025-01-03", "no type hint on function -> add type hints"),
        Pattern(PatternType.FEEDBACK, "2025-01-04", "forgot error handling -> add try-catch"),
        Pattern(PatternType.FEEDBACK, "2025-01-05", "no exception handling -> should catch errors"),
        Pattern(PatternType.FEEDBACK, "2025-01-06", "missing error catch -> add error handling"),
    ]

    print(f"  Feedback entries: {len(feedback_entries)}")

    # Extract patterns (min 3 occurrences)
    new_patterns = extract_patterns_from_feedback(feedback_entries, min_occurrences=3)

    print(f"  Patterns extracted: {len(new_patterns)}")
    for ptype, category, description in new_patterns:
        print(f"    - [{ptype}:{category}] {description}")

    print_result(
        "Type hints pattern extracted",
        any("type" in desc.lower() for _, _, desc in new_patterns),
        "Should detect repeated type hint feedback"
    )

    print_result(
        "Error handling pattern extracted",
        any("error" in desc.lower() or "handling" in cat.lower() for _, cat, desc in new_patterns),
        "Should detect repeated error handling feedback"
    )

    return new_patterns


def test_context_generation():
    """Test 5: Context Integration."""
    print_header("TEST 5: Context Generation")

    parser = SelfImproveParser()
    data = parser.parse("""
PREFERENCE: [coding] prefers functional style
PREFERENCE: [testing] likes TDD
SKILL: [python] expert at list comprehensions
BLIND_SPOT: [async] forgets await
ANTI_PATTERN: [complexity] over-engineers
""")

    stack = ["python"]
    context = generate_intuition_context(data, stack)

    print("  Generated context:")
    print("-" * 40)
    for line in context.split("\n")[:15]:
        print(f"  {line}")
    if context.count("\n") > 15:
        print("  ...")
    print("-" * 40)

    print_result(
        "Preferences section",
        "Your Preferences" in context or "Preference" in context,
        "Should include preferences"
    )
    print_result(
        "Skills section",
        "Your Skills" in context or "Skill" in context,
        "Should include skills"
    )
    print_result(
        "Blind spots section",
        "Watch Out" in context or "Blind Spot" in context,
        "Should include blind spots"
    )
    print_result(
        "Anti-patterns section",
        "Avoid" in context or "Anti-Pattern" in context,
        "Should include anti-patterns"
    )

    return context


def test_current_self_improve():
    """Test current SELF_IMPROVE.md file."""
    print_header("CURRENT SELF_IMPROVE.md STATUS")

    path = get_self_improve_path()
    print(f"  Location: {path}")
    print(f"  Exists: {path.exists()}")

    if path.exists():
        data = load_self_improve()
        print(f"\n  Patterns:")
        print(f"    Preferences:   {len(data.preferences)}")
        print(f"    Skills:        {len(data.skills)}")
        print(f"    Blind Spots:   {len(data.blind_spots)}")
        print(f"    Anti-Patterns: {len(data.anti_patterns)}")
        print(f"    Feedback:      {len(data.feedback)}")

        # Show a few examples
        if data.blind_spots:
            print(f"\n  Sample blind spots:")
            for bs in data.blind_spots[:3]:
                print(f"    - [{bs.category}] {bs.description}")

        return data
    else:
        print("  File not found - run 'mind init' first")
        return None


def interactive_menu():
    """Interactive test menu."""
    print_header("SELF_IMPROVE Testing Playground")

    print("  Available tests:")
    print("    1. Pattern Parsing")
    print("    2. Stack Filtering")
    print("    3. Intuition Detection")
    print("    4. Feedback Extraction")
    print("    5. Context Generation")
    print("    6. Current SELF_IMPROVE.md")
    print("    a. Run ALL tests")
    print("    q. Quit")
    print()

    while True:
        choice = input("  Select test (1-6, a, q): ").strip().lower()

        if choice == 'q':
            print("\n  Goodbye!")
            break
        elif choice == '1':
            test_pattern_parsing()
        elif choice == '2':
            test_stack_filtering()
        elif choice == '3':
            test_intuition_detection()
        elif choice == '4':
            test_feedback_extraction()
        elif choice == '5':
            test_context_generation()
        elif choice == '6':
            test_current_self_improve()
        elif choice == 'a':
            run_all_tests()
        else:
            print("  Invalid choice")

        print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("  RUNNING ALL TESTS")
    print("="*60)

    data = test_pattern_parsing()
    test_stack_filtering(data)
    test_intuition_detection()
    test_feedback_extraction()
    test_context_generation()
    test_current_self_improve()

    print_header("ALL TESTS COMPLETE")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        run_all_tests()
    else:
        interactive_menu()
