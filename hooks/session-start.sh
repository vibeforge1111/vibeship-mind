#!/bin/bash
# Mind hook: At session start, remind Claude to call mind_recall()
# This runs as a SessionStart hook

cat << 'EOF'
<mind-hook>
IMPORTANT: Call mind_recall() NOW before doing anything else.
This loads your memory context and detects if this is a new session.
</mind-hook>
EOF
