# SELF_IMPROVE Testing Playground

## Quick Start

```bash
# From vibeship-mind directory
cd playground
uv run python test_runner.py
```

## What We're Testing

### 1. Pattern Detection
Does Mind correctly parse patterns from SELF_IMPROVE.md?

| Test | Input | Expected |
|------|-------|----------|
| Preference parsing | `PREFERENCE: [coding] prefers short functions` | Pattern with type=PREFERENCE, category=coding |
| Skill parsing | `SKILL: [python:async] good at asyncio` | Pattern with type=SKILL, category=python:async |
| Blind spot parsing | `BLIND_SPOT: [testing] forgets edge cases` | Pattern with type=BLIND_SPOT |
| Anti-pattern parsing | `ANTI_PATTERN: [complexity] over-engineers` | Pattern with type=ANTI_PATTERN |
| Feedback parsing | `FEEDBACK: [2025-01-01] context -> correction` | Pattern with date parsed |

### 2. Stack Filtering
Do patterns filter correctly based on project stack?

| Test | Pattern Category | Project Stack | Should Match? |
|------|-----------------|---------------|---------------|
| Exact match | `python` | `[python, fastapi]` | Yes |
| Partial match | `python:async` | `[python]` | Yes |
| Universal | `general` | `[rust]` | Yes |
| No match | `react` | `[python]` | No (unless blind_spot/anti_pattern) |
| Warnings always | `react` (blind_spot) | `[python]` | Yes (warnings included) |

### 3. Intuition Detection (Pattern Radar)
Do the right warnings surface based on context?

| Test | Pattern | Context | Expected Intuition |
|------|---------|---------|-------------------|
| Blind spot trigger | `BLIND_SPOT: [async] forgets await` | "working on async function" | WATCH: You tend to forget await |
| Anti-pattern trigger | `ANTI_PATTERN: [api] over-fetches data` | "fetching from API" | AVOID: Watch out for over-fetching |
| Skill tip | `SKILL: [python:debugging] good at pdb` | "debugging this issue" | TIP: Remember you're good at pdb |
| No trigger | `BLIND_SPOT: [react] forgets keys` | "working on python" | Nothing |

### 4. Feedback Loop
Does feedback get captured and patterns extracted?

| Test | Action | Expected |
|------|--------|----------|
| Log feedback | `mind_log("x -> y", type="feedback")` | Entry in SELF_IMPROVE.md Feedback Log |
| Pattern extraction | 3+ similar feedback entries | New pattern promoted |
| No duplicate | Same pattern text | Skipped, not duplicated |

### 5. Context Integration
Does MIND:CONTEXT include self-improvement data?

| Test | Setup | Expected in Context |
|------|-------|---------------------|
| Preferences shown | Add 3 preferences | Top 3 in "Your Preferences" section |
| Blind spots shown | Add blind spots | All in "Watch Out" section |
| Intuitions shown | Trigger pattern | "Intuition (Pattern Radar)" section |

## Manual Test Scenarios

### Scenario A: New User
1. Fresh SELF_IMPROVE.md (empty)
2. Run `mind patterns` -> should show "No patterns found" with help
3. Run `mind self` -> should show zeros
4. Add a pattern manually
5. Run `mind patterns` -> should show the pattern

### Scenario B: Pattern Radar in Action
1. Add: `BLIND_SPOT: [error-handling] forgets try-catch blocks`
2. Start a session with context mentioning "error handling"
3. Run `mind_recall()` -> should see WATCH intuition

### Scenario C: Feedback to Pattern Pipeline
1. Log 3+ feedback entries about same thing (e.g., type hints)
2. Run pattern extraction
3. Check if new PREFERENCE was created

### Scenario D: Stack-Aware Filtering
1. Add python-specific and react-specific patterns
2. In a python project, run `mind_recall()`
3. Should see python patterns, not react patterns
4. Blind spots should appear regardless

## Test Runner Commands

```bash
# Run all unit tests
uv run pytest tests/test_self_improve.py -v

# Run specific test
uv run pytest tests/test_self_improve.py::test_pattern_parsing -v

# Interactive playground
uv run python playground/test_runner.py

# Manual CLI tests
uv run mind patterns
uv run mind feedback
uv run mind self
uv run mind patterns --type blind_spot
uv run mind patterns --json
```

## Success Criteria

- [ ] All pattern types parse correctly
- [ ] Stack filtering includes relevant patterns only
- [ ] Intuitions trigger on matching context
- [ ] Feedback logs to SELF_IMPROVE.md
- [ ] Pattern extraction works with 3+ occurrences
- [ ] CLI commands show correct data
- [ ] MIND:CONTEXT includes self-improvement sections
- [ ] No crashes on empty/missing files
