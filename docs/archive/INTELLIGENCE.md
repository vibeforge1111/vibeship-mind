# Mind Intelligence Features

## Overview

Two zero-friction intelligence features that make Mind smarter without requiring any special syntax or explicit actions from the user.

1. **Implicit Relationship Detection** - Automatically links related entities
2. **Temporal Marker Detection** - Flags decisions that may need revisiting

Both work with loose parsing and natural language.

---

## 1. Implicit Relationship Detection

### What It Does

Automatically detects when entities reference each other, without requiring WikiLinks or special syntax.

**Input (natural writing):**
```markdown
## Dec 12

decided JWT over sessions because simpler.

hit Safari cookie problem - ITP blocking cross-domain.

decided to move auth to same domain because of the Safari issue.
```

**Mind detects:**
```
JWT decision <- mentioned in -> same-domain decision
Safari issue <- caused -> same-domain decision
```

**Output in MIND:CONTEXT:**
```markdown
## Recent Decisions
- JWT over sessions (Dec 12) - simpler
- Move auth to same domain (Dec 12)
  └─ Related: Safari cookies issue

## Open Issues
- Safari cookies - ITP blocking
  └─ Led to: same-domain auth decision
```

---

### Implementation

#### Relation Types

```python
from enum import Enum
from dataclasses import dataclass

class RelationType(Enum):
    MENTIONS = "mentions"           # Entity A mentions entity B
    CAUSED_BY = "caused_by"         # Decision caused by issue
    LEADS_TO = "leads_to"           # Issue led to decision
    BLOCKS = "blocks"               # Issue blocks progress
    RESOLVES = "resolves"           # Decision/learning resolves issue
    RELATES_TO = "relates_to"       # General relationship

@dataclass
class Relation:
    source_id: str
    target_id: str
    type: RelationType
    confidence: float              # 0.0 - 1.0
    evidence: str                  # The text that triggered detection
```

#### Detection Patterns

```python
# Causal patterns - detect "because of", "due to", etc.
CAUSAL_PATTERNS = [
    r'because\s+(?:of\s+)?(?:the\s+)?(.+?)(?:\.|,|$)',
    r'due\s+to\s+(?:the\s+)?(.+?)(?:\.|,|$)',
    r'since\s+(?:the\s+)?(.+?)(?:\.|,|$)',
    r'after\s+(?:the\s+)?(.+?)(?:\.|,|$)',
    r'from\s+(?:the\s+)?(.+?)(?:issue|problem|bug)(?:\.|,|$)',
]

# Resolution patterns - detect "fixed by", "resolved with", etc.
RESOLUTION_PATTERNS = [
    r'(?:fixed|resolved|solved)\s+(?:by|with|using)\s+(.+?)(?:\.|,|$)',
    r'(?:fixed|resolved|solved)\s+(?:the\s+)?(.+?)(?:\.|,|$)',
    r'workaround:?\s+(.+?)(?:\.|,|$)',
]

# Blocking patterns - detect "blocked by", "waiting on", etc.
BLOCKING_PATTERNS = [
    r'blocked\s+(?:by|on)\s+(.+?)(?:\.|,|$)',
    r'waiting\s+(?:for|on)\s+(.+?)(?:\.|,|$)',
    r'need(?:s)?\s+(.+?)\s+(?:first|before)(?:\.|,|$)',
]
```

#### Relation Detector

```python
class RelationDetector:
    def __init__(self):
        self.patterns = {
            RelationType.CAUSED_BY: CAUSAL_PATTERNS,
            RelationType.RESOLVES: RESOLUTION_PATTERNS,
            RelationType.BLOCKS: BLOCKING_PATTERNS,
        }
    
    def detect_relations(self, entities: list[Entity]) -> list[Relation]:
        """Detect implicit relationships between entities."""
        relations = []
        
        # Build title index for matching
        title_index = {e.id: e.title.lower() for e in entities}
        
        for entity in entities:
            content_lower = entity.content.lower()
            
            # 1. Check for causal/resolution/blocking patterns
            for rel_type, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content_lower, re.I)
                    for match in matches:
                        referenced_text = match.group(1).strip()
                        
                        # Find matching entity
                        target = self._find_matching_entity(
                            referenced_text, 
                            entities, 
                            exclude_id=entity.id
                        )
                        
                        if target:
                            relations.append(Relation(
                                source_id=entity.id,
                                target_id=target.id,
                                type=rel_type,
                                confidence=0.8,
                                evidence=match.group(0)
                            ))
            
            # 2. Check for title mentions (weaker signal)
            for other in entities:
                if other.id == entity.id:
                    continue
                
                # Check if other entity's title appears in this content
                if self._title_appears_in(other.title, content_lower):
                    relations.append(Relation(
                        source_id=entity.id,
                        target_id=other.id,
                        type=RelationType.MENTIONS,
                        confidence=0.6,
                        evidence=f"mentions '{other.title}'"
                    ))
        
        # Deduplicate and keep highest confidence
        return self._deduplicate_relations(relations)
    
    def _find_matching_entity(
        self, 
        text: str, 
        entities: list[Entity],
        exclude_id: str
    ) -> Optional[Entity]:
        """Find entity that matches referenced text."""
        text_lower = text.lower()
        
        best_match = None
        best_score = 0.0
        
        for entity in entities:
            if entity.id == exclude_id:
                continue
            
            title_lower = entity.title.lower()
            
            # Exact match
            if title_lower in text_lower or text_lower in title_lower:
                score = 0.9
            # Keyword overlap
            else:
                title_words = set(title_lower.split())
                text_words = set(text_lower.split())
                overlap = len(title_words & text_words)
                if overlap >= 2:
                    score = 0.5 + (overlap * 0.1)
                else:
                    continue
            
            if score > best_score:
                best_score = score
                best_match = entity
        
        return best_match if best_score >= 0.5 else None
    
    def _title_appears_in(self, title: str, content: str) -> bool:
        """Check if title meaningfully appears in content."""
        title_lower = title.lower()
        
        # Skip very short/common titles
        if len(title_lower) < 4:
            return False
        
        # Check for title as phrase
        if title_lower in content:
            return True
        
        # Check for significant word overlap (2+ words)
        title_words = set(title_lower.split())
        content_words = set(content.split())
        
        # Remove common words
        common = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'for', 'with'}
        title_words -= common
        
        overlap = len(title_words & content_words)
        return overlap >= 2
    
    def _deduplicate_relations(self, relations: list[Relation]) -> list[Relation]:
        """Keep highest confidence relation for each source-target pair."""
        best = {}
        for rel in relations:
            key = (rel.source_id, rel.target_id)
            if key not in best or rel.confidence > best[key].confidence:
                best[key] = rel
        return list(best.values())
```

#### Integration with Context Generator

```python
# In context.py

class ContextGenerator:
    def __init__(self, ...):
        self.relation_detector = RelationDetector()
    
    def generate(self, project_path: str, entities: list[Entity]) -> str:
        # Detect relationships
        relations = self.relation_detector.detect_relations(entities)
        
        # Build relation index
        relations_by_source = defaultdict(list)
        for rel in relations:
            relations_by_source[rel.source_id].append(rel)
        
        # Generate context with relationships
        context = self._build_context(
            entities=entities,
            relations=relations_by_source
        )
        
        return context
    
    def _format_decision_with_relations(
        self, 
        decision: Entity,
        relations: list[Relation],
        entities_by_id: dict
    ) -> str:
        """Format a decision with its relationships."""
        
        lines = [f"- {decision.title} ({decision.date})"]
        
        if decision.reasoning:
            lines[0] += f" - {decision.reasoning}"
        
        # Add related items
        related = []
        for rel in relations:
            target = entities_by_id.get(rel.target_id)
            if target and rel.confidence >= 0.6:
                if rel.type == RelationType.CAUSED_BY:
                    related.append(f"Due to: {target.title}")
                elif rel.type == RelationType.RESOLVES:
                    related.append(f"Resolves: {target.title}")
                elif rel.type == RelationType.MENTIONS:
                    related.append(target.title)
        
        if related:
            lines.append(f"  └─ Related: {', '.join(related)}")
        
        return '\n'.join(lines)
```

---

## 2. Temporal Marker Detection

### What It Does

Detects decisions marked with time-bound language ("for MVP", "temporary", "for now") and surfaces them when they may need revisiting.

**Input:**
```markdown
## Dec 1
decided JWT for MVP - simpler than OAuth

## Dec 5
using SQLite for now, will migrate to Postgres later

## Dec 10
quick fix for the auth bug - need proper solution
```

**After 14 days, MIND:CONTEXT shows:**
```markdown
## Decisions Needing Review
📋 "JWT for MVP" (14d ago) - marked as temporary
📋 "SQLite for now" (10d ago) - marked as temporary

## Quick Fixes Still Active
⚠️ "auth bug quick fix" (5d ago) - needs proper solution
```

---

### Implementation

#### Temporal Markers

```python
from dataclasses import dataclass
from enum import Enum

class TemporalType(Enum):
    MVP = "mvp"                    # "for MVP", "MVP only"
    TEMPORARY = "temporary"        # "for now", "temporary"
    QUICK_FIX = "quick_fix"        # "quick fix", "hack"
    PLACEHOLDER = "placeholder"    # "placeholder", "stub"
    REVISIT = "revisit"            # "revisit later", "come back to"

@dataclass
class TemporalMarker:
    type: TemporalType
    matched_text: str
    needs_review_after_days: int
```

#### Detection Patterns

```python
TEMPORAL_PATTERNS = {
    TemporalType.MVP: {
        "patterns": [
            r'\bfor\s+(?:the\s+)?mvp\b',
            r'\bmvp\s+(?:only|version|approach)\b',
            r'\bjust\s+(?:for\s+)?mvp\b',
            r'\buntil\s+(?:after\s+)?(?:the\s+)?mvp\b',
        ],
        "review_after_days": 14,
    },
    TemporalType.TEMPORARY: {
        "patterns": [
            r'\bfor\s+now\b',
            r'\btemporar(?:y|ily)\b',
            r'\bshort[\s-]?term\b',
            r'\buntil\s+we\b',
            r'\bfor\s+the\s+time\s+being\b',
            r'\bwill\s+(?:change|migrate|update|fix)\s+later\b',
        ],
        "review_after_days": 14,
    },
    TemporalType.QUICK_FIX: {
        "patterns": [
            r'\bquick\s+(?:fix|hack|solution|workaround)\b',
            r'\bhacky?\b',
            r'\bbandaid\b',
            r'\bband[\s-]?aid\b',
            r'\bduct[\s-]?tape\b',
            r'\bnot\s+(?:a\s+)?proper\b',
            r'\bneeds?\s+(?:a\s+)?proper\s+(?:fix|solution)\b',
        ],
        "review_after_days": 7,
    },
    TemporalType.PLACEHOLDER: {
        "patterns": [
            r'\bplaceholder\b',
            r'\bstub\b',
            r'\btodo:?\s+(?:replace|implement|finish)\b',
            r'\bwill\s+implement\s+(?:later|properly)\b',
        ],
        "review_after_days": 7,
    },
    TemporalType.REVISIT: {
        "patterns": [
            r'\brevisit\s+(?:this\s+)?later\b',
            r'\bcome\s+back\s+to\b',
            r'\bneed\s+to\s+(?:re)?think\b',
            r'\breconsider\s+(?:this\s+)?later\b',
        ],
        "review_after_days": 7,
    },
}
```

#### Temporal Marker Detector

```python
class TemporalMarkerDetector:
    def detect(self, content: str) -> list[TemporalMarker]:
        """Detect temporal markers in content."""
        markers = []
        content_lower = content.lower()
        
        for marker_type, config in TEMPORAL_PATTERNS.items():
            for pattern in config["patterns"]:
                if match := re.search(pattern, content_lower):
                    markers.append(TemporalMarker(
                        type=marker_type,
                        matched_text=match.group(0),
                        needs_review_after_days=config["review_after_days"]
                    ))
                    break  # One match per type is enough
        
        return markers
    
    def needs_review(self, entity: Entity, markers: list[TemporalMarker]) -> bool:
        """Check if entity with temporal markers needs review."""
        if not markers:
            return False
        
        age_days = (datetime.now() - entity.created_at).days
        
        for marker in markers:
            if age_days >= marker.needs_review_after_days:
                return True
        
        return False
    
    def get_review_reason(self, markers: list[TemporalMarker]) -> str:
        """Get human-readable review reason."""
        if not markers:
            return ""
        
        marker = markers[0]  # Primary marker
        
        reasons = {
            TemporalType.MVP: "marked as MVP-only",
            TemporalType.TEMPORARY: "marked as temporary",
            TemporalType.QUICK_FIX: "was a quick fix",
            TemporalType.PLACEHOLDER: "is a placeholder",
            TemporalType.REVISIT: "marked for revisiting",
        }
        
        return reasons.get(marker.type, "has temporal marker")
```

#### Integration with Parser

```python
# In parser.py

class Parser:
    def __init__(self):
        self.temporal_detector = TemporalMarkerDetector()
    
    def parse(self, content: str) -> ParseResult:
        entities = []
        
        for line_num, line in enumerate(content.split('\n')):
            if entity := self._try_parse_decision(line, line_num):
                # Detect temporal markers
                entity.temporal_markers = self.temporal_detector.detect(line)
                entities.append(entity)
            # ... other entity types
        
        return ParseResult(entities=entities, ...)
```

#### Integration with Context Generator

```python
# In context.py

def _build_review_section(
    self, 
    entities: list[Entity],
    detector: TemporalMarkerDetector
) -> Optional[str]:
    """Build 'Decisions Needing Review' section."""
    
    needs_review = []
    quick_fixes = []
    
    for entity in entities:
        if entity.type != 'decision':
            continue
        
        if not entity.temporal_markers:
            continue
        
        if not detector.needs_review(entity, entity.temporal_markers):
            continue
        
        age_days = (datetime.now() - entity.created_at).days
        reason = detector.get_review_reason(entity.temporal_markers)
        
        # Separate quick fixes (more urgent)
        is_quick_fix = any(
            m.type == TemporalType.QUICK_FIX 
            for m in entity.temporal_markers
        )
        
        entry = f"{entity.title} ({age_days}d ago) - {reason}"
        
        if is_quick_fix:
            quick_fixes.append(f"⚠️ {entry}")
        else:
            needs_review.append(f"📋 {entry}")
    
    sections = []
    
    if needs_review:
        sections.append("## Decisions Needing Review")
        sections.extend(needs_review)
    
    if quick_fixes:
        sections.append("\n## Quick Fixes Still Active")
        sections.extend(quick_fixes)
    
    return '\n'.join(sections) if sections else None
```

---

## MIND:CONTEXT Output

With both features, MIND:CONTEXT becomes:

```markdown
<!-- MIND:CONTEXT -->
## Memory: ✓ Active
Last captured: 5 min ago

## Session Context
Last active: 2 hours ago

## Project State
- Goal: Ship v1 dashboard
- Stack: SvelteKit, FastAPI
- Blocked: None

## Recent Decisions
- Move auth to same domain (Dec 12)
  └─ Related: Safari cookies issue
- JWT over sessions (Dec 10) - simpler
- CSS animations (Dec 10)
  └─ Related: Dashboard hero

## Decisions Needing Review
📋 "JWT for MVP" (14d ago) - marked as MVP-only
📋 "SQLite for now" (10d ago) - marked as temporary

## Quick Fixes Still Active
⚠️ "Auth redirect hack" (5d ago) - was a quick fix

## Open Issues
- Safari cookies - ITP blocking
  └─ Led to: same-domain decision

## Gotchas
- Safari ITP blocks cross-domain after 7 days
- Vercel Edge: use Web Crypto, not Node crypto

## Continue From
Last: Dashboard hero section
Next: Node connections
<!-- MIND:END -->
```

---

## Database Schema Additions

```sql
-- Add to extracted table
ALTER TABLE extracted ADD COLUMN temporal_markers JSON;
-- e.g., [{"type": "mvp", "matched_text": "for mvp"}]

-- Relations table
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type TEXT NOT NULL,           -- mentions, caused_by, resolves, etc.
    confidence REAL NOT NULL,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_id) REFERENCES extracted(id),
    FOREIGN KEY (target_id) REFERENCES extracted(id)
);

CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
```

---

## Testing

### Relation Detection Tests

```python
def test_causal_relation_detection():
    entities = [
        Entity(id="1", type="decision", title="Move to same domain", 
               content="decided to move auth to same domain because of Safari issue"),
        Entity(id="2", type="issue", title="Safari cookies issue",
               content="Safari ITP blocking cross-domain cookies"),
    ]
    
    detector = RelationDetector()
    relations = detector.detect_relations(entities)
    
    assert len(relations) == 1
    assert relations[0].source_id == "1"
    assert relations[0].target_id == "2"
    assert relations[0].type == RelationType.CAUSED_BY

def test_mention_detection():
    entities = [
        Entity(id="1", type="decision", title="Use JWT",
               content="decided JWT, simpler than the OAuth approach"),
        Entity(id="2", type="decision", title="OAuth approach",
               content="originally considered OAuth"),
    ]
    
    detector = RelationDetector()
    relations = detector.detect_relations(entities)
    
    assert any(r.type == RelationType.MENTIONS for r in relations)
```

### Temporal Marker Tests

```python
def test_mvp_marker_detection():
    detector = TemporalMarkerDetector()
    
    markers = detector.detect("decided JWT for MVP - simpler")
    assert len(markers) == 1
    assert markers[0].type == TemporalType.MVP

def test_quick_fix_detection():
    detector = TemporalMarkerDetector()
    
    markers = detector.detect("quick fix for auth bug")
    assert len(markers) == 1
    assert markers[0].type == TemporalType.QUICK_FIX
    assert markers[0].needs_review_after_days == 7

def test_needs_review():
    detector = TemporalMarkerDetector()
    
    old_entity = Entity(
        created_at=datetime.now() - timedelta(days=15),
        temporal_markers=[TemporalMarker(
            type=TemporalType.MVP,
            matched_text="for mvp",
            needs_review_after_days=14
        )]
    )
    
    assert detector.needs_review(old_entity, old_entity.temporal_markers)
    
    new_entity = Entity(
        created_at=datetime.now() - timedelta(days=5),
        temporal_markers=[TemporalMarker(
            type=TemporalType.MVP,
            matched_text="for mvp", 
            needs_review_after_days=14
        )]
    )
    
    assert not detector.needs_review(new_entity, new_entity.temporal_markers)
```

---

## Summary

| Feature | Implementation | Output |
|---------|----------------|--------|
| Implicit Relations | Regex on causal/resolution patterns + title matching | "Related:" lines in MIND:CONTEXT |
| Temporal Markers | Regex on time-bound language | "Decisions Needing Review" section |

Both features:
- Zero friction (no special syntax)
- Work with loose parsing
- Make MIND:CONTEXT smarter
- Fail gracefully (no detection = no output)
