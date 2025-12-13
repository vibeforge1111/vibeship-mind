#!/bin/bash
# Mind hook: After git commit, prompt Claude to log what was decided/learned
# This runs as a PostToolUse hook for Bash commands containing "git commit"

# Read input from stdin (Claude Code passes JSON)
INPUT=$(cat)

# Check if this was a git commit
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)

if echo "$TOOL_INPUT" | grep -q "git commit"; then
    # Output context that will be injected into Claude's next response
    cat << 'EOF'
<mind-hook>
You just made a git commit. Before continuing, use mind_log() to record:
- What decision did you make? (use type: "decision")
- What did you learn? (use type: "learning")

Be specific. Example: mind_log("chose SvelteKit over Next.js for static site - simpler routing", type="decision")
</mind-hook>
EOF
fi
