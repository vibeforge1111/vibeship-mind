#!/bin/bash
# Mind hook: At session end, prompt Claude to summarize
# This runs as a Stop hook (when conversation ends)

cat << 'EOF'
<mind-hook>
Session ending. Before you go, use mind_log() to record:
1. Key decisions made this session
2. Important learnings or gotchas discovered
3. What's still open/incomplete

This ensures your work is remembered for next session.
</mind-hook>
EOF
