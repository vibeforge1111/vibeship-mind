<script lang="ts">
	// Animated typing effect for the terminal
	let terminalLines = $state<string[]>([]);
	let currentLine = $state(0);

	const lines = [
		'> mind_recall()',
		'',
		'## Memory: Active',
		'Last captured: 2 hours ago',
		'',
		'## Reminders Due',
		'- Review auth flow when we work on login',
		'',
		'## Recent Decisions',
		'- file-based storage (simpler, git-trackable)',
		'- 12 focused MCP tools (memorable, purposeful)',
		'',
		'## Gotchas',
		'- Windows cp1252 -> use UTF-8',
		'',
		'## Continue From',
		'Last: two-layer memory system'
	];

	$effect(() => {
		if (currentLine < lines.length) {
			const timeout = setTimeout(() => {
				terminalLines = [...terminalLines, lines[currentLine]];
				currentLine++;
			}, currentLine === 0 ? 500 : 150);
			return () => clearTimeout(timeout);
		}
	});

	// Tool explorer state
	let selectedTool = $state('mind_recall');

	const tools = {
		mind_recall: {
			name: 'mind_recall()',
			category: 'core',
			desc: 'Load context at session start',
			output: `## Memory: Active
Last captured: 2 hours ago

## Reminders Due
- Review auth flow when we work on login

## Recent Decisions
- file-based storage (simpler, git-trackable)

## Continue From
Last: two-layer memory system`,
			explain: {
				what: "Loads everything Claude needs to remember about your project - past decisions, learnings, what you were working on, and any reminders.",
				auto: true,
				autoWhen: "Called automatically at the start of every session",
				manual: "Call manually if context feels stale or after long breaks"
			}
		},
		mind_log: {
			name: 'mind_log(msg, type)',
			category: 'core',
			desc: 'Log to SESSION or MEMORY',
			output: `> mind_log("using flexbox for layout", type="experience")

{
  "success": true,
  "logged": "using flexbox for layout",
  "type": "experience",
  "target": "SESSION.md"
}`,
			explain: {
				what: "Saves thoughts, decisions, and learnings as you work. Session types (experience, blocker) are temporary. Memory types (decision, learning) are permanent.",
				auto: false,
				autoWhen: null,
				manual: "Claude calls this throughout your session to remember what's happening"
			}
		},
		mind_session: {
			name: 'mind_session()',
			category: 'reading',
			desc: 'Check current session state',
			output: `## Experience
- trying flexbox approach
- user wants vibeship.co style

## Blockers
(none)

## Assumptions
- API returns JSON`,
			explain: {
				what: "Shows what's been logged in the current session - your experiences, blockers, rejected approaches, and assumptions.",
				auto: false,
				autoWhen: null,
				manual: "Useful to review what's happened so far or debug why Claude seems confused"
			}
		},
		mind_search: {
			name: 'mind_search(query)',
			category: 'reading',
			desc: 'Search across memories',
			output: `> mind_search("authentication")

Found 3 results:
- [decision] use JWT for auth tokens
- [learning] Safari blocks third-party cookies
- [problem] CORS issue with auth endpoint`,
			explain: {
				what: "Searches through all your project memories to find relevant past decisions, learnings, and problems.",
				auto: false,
				autoWhen: null,
				manual: "Ask Claude to search when you need to recall why something was done a certain way"
			}
		},
		mind_status: {
			name: 'mind_status()',
			category: 'reading',
			desc: 'Check memory health',
			output: `## Mind Status

Memory: 47 entries (12.3 KB)
Session: 4 items
Reminders: 2 pending
Stack: typescript, react

Health: OK`,
			explain: {
				what: "Quick health check - how many memories, file sizes, detected tech stack, and if everything's working.",
				auto: false,
				autoWhen: null,
				manual: "Run if Mind seems broken or you're curious about memory stats"
			}
		},
		mind_reminders: {
			name: 'mind_reminders()',
			category: 'reading',
			desc: 'List pending reminders',
			output: `## Pending Reminders

1. [tomorrow] Review PR #42
2. [context: "auth"] Add rate limiting
3. [in 3 days] Update dependencies`,
			explain: {
				what: "Shows all your pending reminders - both time-based (tomorrow, in 3 days) and context-triggered (when you mention X).",
				auto: true,
				autoWhen: "Due reminders shown automatically in mind_recall()",
				manual: "Check the full list anytime you want to see what's pending"
			}
		},
		mind_blocker: {
			name: 'mind_blocker(desc)',
			category: 'actions',
			desc: 'Log blocker + auto-search',
			output: `> mind_blocker("CORS error on API call")

Logged to SESSION.md

Searching memory for solutions...
Found: "Fixed CORS by adding proxy in vite.config"

Related gotcha: configure proxy for dev server`,
			explain: {
				what: "Logs what's blocking you AND automatically searches memory for related solutions. Two-in-one problem solver.",
				auto: false,
				autoWhen: null,
				manual: "Tell Claude you're stuck - it'll log it and try to find past solutions"
			}
		},
		mind_remind: {
			name: 'mind_remind(msg, when)',
			category: 'actions',
			desc: 'Set time or context reminder',
			output: `> mind_remind("add tests", when="when I mention auth")

{
  "success": true,
  "type": "context",
  "triggers_on": "auth",
  "message": "add tests"
}`,
			explain: {
				what: "Set reminders that trigger by time (tomorrow, in 3 days) or by context (when you mention a topic).",
				auto: false,
				autoWhen: null,
				manual: "Say 'remind me to...' and Claude will set it up automatically"
			}
		},
		mind_reminder_done: {
			name: 'mind_reminder_done(idx)',
			category: 'actions',
			desc: 'Mark reminder complete',
			output: `> mind_reminder_done(1)

{
  "success": true,
  "marked_done": "Review PR #42"
}`,
			explain: {
				what: "Marks a reminder as done so it stops showing up.",
				auto: true,
				autoWhen: "'Next session' reminders auto-mark when surfaced",
				manual: "Tell Claude you finished something it reminded you about"
			}
		},
		mind_edges: {
			name: 'mind_edges(intent)',
			category: 'actions',
			desc: 'Check for gotchas before coding',
			output: `> mind_edges("implement file upload")

## Warnings

[!] Max file size varies by hosting provider
[!] Safari handles FormData differently
[!] Consider chunked upload for large files

Proceed with caution.`,
			explain: {
				what: "Checks for known gotchas before you implement something risky. Like a senior dev warning you about edge cases.",
				auto: false,
				autoWhen: null,
				manual: "Ask before implementing tricky features like auth, file upload, payments"
			}
		},
		mind_checkpoint: {
			name: 'mind_checkpoint()',
			category: 'actions',
			desc: 'Force process pending memories',
			output: `Processing pending memories...

Indexed: 3 new entries
Promoted: 1 item from SESSION
Regenerated: MIND:CONTEXT

Done.`,
			explain: {
				what: "Forces Mind to process and index everything right now, instead of waiting for the next session.",
				auto: true,
				autoWhen: "Happens automatically on session gaps (>30 min)",
				manual: "Run after big changes if you want context updated immediately"
			}
		},
		mind_add_global_edge: {
			name: 'mind_add_global_edge()',
			category: 'actions',
			desc: 'Add cross-project gotcha',
			output: `> mind_add_global_edge(
    title="Safari FormData",
    description="Safari handles FormData differently",
    workaround="Use polyfill or manual boundary"
  )

{
  "success": true,
  "added_to": "global_edges.json",
  "applies_to": ["javascript", "typescript"]
}`,
			explain: {
				what: "Adds a gotcha that applies across ALL your projects - platform bugs, language quirks, things every project should know.",
				auto: false,
				autoWhen: null,
				manual: "When you hit a gotcha that's not project-specific (browser bugs, OS quirks)"
			}
		}
	};

	const categories = [
		{ id: 'core', label: 'Core' },
		{ id: 'reading', label: 'Reading' },
		{ id: 'actions', label: 'Actions' }
	];
</script>

<div class="hero">
	<h1>Give Claude a <span class="highlight">Mind</span></h1>
	<p class="subtitle">
		File-based memory that persists across sessions. No database, no cloud, no friction.
	</p>

	<div class="terminal">
		<div class="terminal-header">
			<span class="terminal-dot"></span>
			<span class="terminal-dot"></span>
			<span class="terminal-dot"></span>
			<span class="terminal-title">mind_recall()</span>
		</div>
		<div class="terminal-body">
			{#each terminalLines as line}
				{#if line.startsWith('>')}
					<div class="line command">{line}</div>
				{:else if line.startsWith('##')}
					<div class="line heading">{line}</div>
				{:else if line.startsWith('-')}
					<div class="line item">{line}</div>
				{:else if line.startsWith('Last')}
					<div class="line muted">{line}</div>
				{:else}
					<div class="line">{line}</div>
				{/if}
			{/each}
			<span class="cursor">_</span>
		</div>
	</div>

	<div class="cta">
		<a href="https://github.com/vibeforge1111/vibeship-mind" class="btn btn-primary btn-lg">
			Get Started
		</a>
	</div>
</div>

<section class="features">
	<h2>Why Mind?</h2>

	<div class="feature-grid">
		<div class="feature">
			<h3>2-Prompt Install</h3>
			<p>Clone the repo, tell Claude to add the MCP server. Done.</p>
		</div>

		<div class="feature">
			<h3>Fully Automated</h3>
			<p>Memory just works. Session gaps auto-detected, learnings auto-promoted, context auto-injected.</p>
		</div>

		<div class="feature">
			<h3>Two-Layer Memory</h3>
			<p>MEMORY.md for cross-session recall. SESSION.md for within-session focus.</p>
		</div>

		<div class="feature">
			<h3>Human Readable</h3>
			<p>Plain .md files you can open, edit, or git-track anytime. No black box.</p>
		</div>
	</div>
</section>

<section class="how-it-works">
	<h2>How It Works</h2>

	<div class="architecture-diagram">
		<div class="diagram-box project-box">
			<div class="diagram-label">YOUR PROJECT</div>
			<div class="diagram-inner">
				<div class="diagram-row">
					<div class="diagram-box small claude-box">
						<span>CLAUDE.md</span>
						<span class="small-text">context</span>
					</div>
					<div class="arrow-left">&#8592;</div>
					<div class="diagram-box small mind-box">
						<span>Mind</span>
						<span class="small-text">MCP</span>
					</div>
				</div>
				<div class="arrow-down">&#8595;</div>
				<div class="diagram-box files-box">
					<div class="diagram-label">.mind/</div>
					<div class="files-row">
						<div class="file-box">
							<span>MEMORY.md</span>
							<span class="small-text">permanent</span>
						</div>
						<div class="file-box">
							<span>SESSION.md</span>
							<span class="small-text">working</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div class="flow-section">
		<h3>Two-Layer Memory</h3>
		<div class="memory-layers">
			<div class="layer memory-layer">
				<div class="layer-header">MEMORY.md <span class="tag">permanent</span></div>
				<div class="layer-content">
					<div class="layer-item"><code>decision</code> "decided X because Y"</div>
					<div class="layer-item"><code>learning</code> "learned that X"</div>
					<div class="layer-item"><code>problem</code> "problem: X"</div>
					<div class="layer-item"><code>progress</code> "fixed: X"</div>
				</div>
			</div>
			<div class="promote-arrow">
				<span>&#8593;</span>
				<span class="small-text">promotes on session gap</span>
			</div>
			<div class="layer session-layer">
				<div class="layer-header">SESSION.md <span class="tag">ephemeral</span></div>
				<div class="layer-content">
					<div class="layer-item"><code>experience</code> raw moments, thoughts</div>
					<div class="layer-item"><code>blocker</code> things stopping progress</div>
					<div class="layer-item"><code>rejected</code> what didn't work</div>
					<div class="layer-item"><code>assumption</code> what I'm assuming</div>
				</div>
			</div>
		</div>
	</div>

	<div class="flow-section">
		<h3>Session Flow</h3>
		<div class="session-flow">
			<div class="flow-step">
				<div class="flow-icon">[&gt;</div>
				<div class="flow-text">
					<strong>Start</strong>
					<span>mind_recall()</span>
				</div>
			</div>
			<div class="flow-arrow">-&gt;</div>
			<div class="flow-step">
				<div class="flow-icon">[?]</div>
				<div class="flow-text">
					<strong>Gap &gt; 30min?</strong>
					<span>promote + clear</span>
				</div>
			</div>
			<div class="flow-arrow">-&gt;</div>
			<div class="flow-step">
				<div class="flow-icon">[+]</div>
				<div class="flow-text">
					<strong>Work</strong>
					<span>mind_log()</span>
				</div>
			</div>
			<div class="flow-arrow">-&gt;</div>
			<div class="flow-step">
				<div class="flow-icon">[~]</div>
				<div class="flow-text">
					<strong>Next session</strong>
					<span>repeat</span>
				</div>
			</div>
		</div>
	</div>
</section>

<section class="reminders">
	<h2>Smart Reminders</h2>
	<p class="section-subtitle">Time-based or context-triggered. Never forget what matters.</p>

	<div class="reminders-grid">
		<div class="reminder-type">
			<div class="reminder-header">Time-Based</div>
			<div class="reminder-examples">
				<div class="reminder-example">
					<code>"tomorrow"</code>
					<span>Next day</span>
				</div>
				<div class="reminder-example">
					<code>"in 3 days"</code>
					<span>Relative date</span>
				</div>
				<div class="reminder-example">
					<code>"next session"</code>
					<span>On next recall</span>
				</div>
				<div class="reminder-example">
					<code>"2025-12-25"</code>
					<span>Specific date</span>
				</div>
			</div>
		</div>
		<div class="reminder-type">
			<div class="reminder-header">Context-Based</div>
			<div class="reminder-examples">
				<div class="reminder-example">
					<code>"when I mention auth"</code>
					<span>Keyword trigger</span>
				</div>
				<div class="reminder-example">
					<code>"when we work on API"</code>
					<span>Topic trigger</span>
				</div>
			</div>
			<div class="reminder-note">
				Surfaces automatically when relevant keywords appear in conversation.
			</div>
		</div>
	</div>
</section>

<section class="files">
	<h2>Simple File Structure</h2>

	<pre><code>your-project/
├── .mind/
│   ├── MEMORY.md      # Long-term memory
│   ├── SESSION.md     # Current session focus
│   ├── REMINDERS.md   # Time & context reminders
│   └── state.json     # Timestamps
└── CLAUDE.md          # Context injected here</code></pre>
</section>

<section class="tools">
	<h2>12 MCP Tools</h2>
	<p class="section-subtitle">Click a command to see what it does</p>

	<div class="tool-explorer">
		<div class="tool-list">
			{#each categories as cat}
				<div class="tool-category-section">
					<div class="tool-category-label">{cat.label}</div>
					{#each Object.entries(tools).filter(([_, t]) => t.category === cat.id) as [key, tool]}
						<button
							class="tool-item"
							class:active={selectedTool === key}
							onclick={() => selectedTool = key}
						>
							<code>{tool.name}</code>
							<span>{tool.desc}</span>
						</button>
					{/each}
				</div>
			{/each}
		</div>
		<div class="tool-output-wrapper">
			<div class="tool-output">
				<div class="tool-output-header">
					<span class="tool-output-dot"></span>
					<span class="tool-output-dot"></span>
					<span class="tool-output-dot"></span>
					<span class="tool-output-title">{tools[selectedTool].name}</span>
				</div>
				<div class="tool-output-body">
					<pre>{tools[selectedTool].output}</pre>
				</div>
			</div>
			<div class="tool-explain">
				<div class="tool-explain-what">
					<p>{tools[selectedTool].explain.what}</p>
				</div>
				<div class="tool-explain-usage">
					{#if tools[selectedTool].explain.auto}
						<div class="usage-tag auto">
							<span class="tag-label">Auto</span>
							<span class="tag-desc">{tools[selectedTool].explain.autoWhen}</span>
						</div>
					{/if}
					<div class="usage-tag manual">
						<span class="tag-label">Manual</span>
						<span class="tag-desc">{tools[selectedTool].explain.manual}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<section class="get-started-cta">
	<h2>Ready to Give Claude a Mind?</h2>
	<p>5 commands. 2 minutes. Zero friction.</p>

	<div class="install-preview">
		<code>git clone https://github.com/vibeforge1111/vibeship-mind.git</code>
		<code>cd vibeship-mind && uv sync</code>
		<code>uv run mind init</code>
	</div>

	<div class="cta-buttons">
		<a href="/get-started" class="btn btn-primary btn-lg">
			Full Install Guide
		</a>
		<a href="https://github.com/vibeforge1111/vibeship-mind" class="btn btn-secondary btn-lg" target="_blank">
			View on GitHub
		</a>
	</div>
</section>

<footer>
	<p>
		Built by <a href="https://x.com/meta_alchemist" target="_blank">@meta_alchemist</a>
		&nbsp;·&nbsp;
		A <a href="https://vibeship.co" target="_blank">vibeship.co</a> project
	</p>
</footer>

<style>
	.hero {
		text-align: center;
		padding: var(--space-12) 0;
	}

	.hero h1 {
		font-size: 3.5rem;
		margin-bottom: var(--space-4);
	}

	.highlight {
		color: var(--green-dim);
	}

	.subtitle {
		font-size: var(--text-lg);
		color: var(--text-secondary);
		max-width: 500px;
		margin: 0 auto var(--space-8);
	}

	.terminal {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		max-width: 600px;
		margin: 0 auto var(--space-8);
		text-align: left;
	}

	.terminal-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		border-bottom: 1px solid var(--border);
	}

	.terminal-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--gray-400);
	}

	.terminal-title {
		margin-left: auto;
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.terminal-body {
		padding: var(--space-4);
		font-size: var(--text-sm);
		min-height: 280px;
	}

	.line {
		line-height: 1.8;
	}

	.line.command {
		color: var(--green-dim);
	}

	.line.heading {
		color: var(--text-primary);
		font-weight: 600;
		margin-top: var(--space-2);
	}

	.line.item {
		color: var(--text-secondary);
		padding-left: var(--space-4);
	}

	.line.muted {
		color: var(--text-tertiary);
	}

	.cursor {
		animation: blink 1s infinite;
		color: var(--green-dim);
	}

	@keyframes blink {
		0%, 50% { opacity: 1; }
		51%, 100% { opacity: 0; }
	}

	.cta {
		margin-top: var(--space-6);
	}

	/* Features */
	.features, .how-it-works, .reminders, .files, .tools {
		padding: var(--space-12) 0;
		border-top: 1px solid var(--border);
	}

	.section-subtitle {
		text-align: center;
		color: var(--text-secondary);
		margin-top: calc(-1 * var(--space-4));
		margin-bottom: var(--space-6);
	}

	section h2 {
		text-align: center;
		margin-bottom: var(--space-8);
	}

	.feature-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-6);
	}

	.feature {
		padding: var(--space-5);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
	}

	.feature h3 {
		font-family: var(--font-mono);
		font-size: var(--text-base);
		margin-bottom: var(--space-2);
		color: var(--green-dim);
	}

	.feature p {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	/* Reminders */
	.reminders-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-6);
		max-width: 700px;
		margin: 0 auto;
	}

	.reminder-type {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		padding: var(--space-4);
	}

	.reminder-header {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--green-dim);
		margin-bottom: var(--space-3);
		padding-bottom: var(--space-2);
		border-bottom: 1px solid var(--border);
	}

	.reminder-examples {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.reminder-example {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.reminder-example code {
		color: var(--text-primary);
		background: transparent;
		padding: 0;
		font-size: var(--text-sm);
	}

	.reminder-example span {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.reminder-note {
		margin-top: var(--space-3);
		padding-top: var(--space-2);
		border-top: 1px dashed var(--border);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		font-style: italic;
	}

	/* Files */
	.files pre {
		max-width: 400px;
		margin: 0 auto;
	}

	/* Tool Explorer */
	.tool-explorer {
		display: grid;
		grid-template-columns: 280px 1fr;
		gap: var(--space-4);
		max-width: 900px;
		margin: 0 auto;
		align-items: stretch;
	}

	.tool-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.tool-category-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.tool-category-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: var(--space-1) 0;
	}

	.tool-item {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: var(--space-2) var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		cursor: pointer;
		text-align: left;
		transition: all var(--transition-fast);
	}

	.tool-item:hover {
		border-color: var(--green-dim);
	}

	.tool-item.active {
		border-color: var(--green-dim);
		background: rgba(0, 196, 154, 0.1);
	}

	.tool-item code {
		color: var(--green-dim);
		background: transparent;
		padding: 0;
		font-size: var(--text-sm);
	}

	.tool-item span {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.tool-output {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-bottom: none;
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
	}

	.tool-output-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
	}

	.tool-output-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--gray-400);
	}

	.tool-output-title {
		margin-left: auto;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--green-dim);
	}

	.tool-output-body {
		padding: var(--space-4);
		flex: 1;
		overflow: auto;
	}

	.tool-output-body pre {
		margin: 0;
		background: transparent;
		border: none;
		padding: 0;
		font-size: var(--text-sm);
		color: var(--text-secondary);
		white-space: pre-wrap;
		line-height: 1.6;
	}

	.tool-output-wrapper {
		display: flex;
		flex-direction: column;
	}

	.tool-explain {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-top: 1px dashed var(--border);
		padding: var(--space-4);
		flex-shrink: 0;
		font-family: var(--font-sans);
	}

	.tool-explain-what {
		margin-bottom: var(--space-3);
		padding-bottom: var(--space-3);
		border-bottom: 1px dashed var(--border);
	}

	.tool-explain-what p {
		font-size: var(--text-lg);
		color: var(--text-primary);
		line-height: 1.6;
		margin: 0;
	}

	.tool-explain-usage {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.usage-tag {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.usage-tag .tag-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		text-transform: uppercase;
		padding: 2px 8px;
		border: 1px solid;
		flex-shrink: 0;
		min-width: 60px;
		text-align: center;
	}

	.usage-tag.auto .tag-label {
		color: var(--green-dim);
		border-color: var(--green-dim);
	}

	.usage-tag.manual .tag-label {
		color: var(--text-tertiary);
		border-color: var(--border);
	}

	.usage-tag .tag-desc {
		font-size: var(--text-lg);
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* Get Started CTA */
	.get-started-cta {
		padding: var(--space-12) 0;
		border-top: 1px solid var(--border);
		text-align: center;
		background: linear-gradient(180deg, transparent 0%, rgba(0, 255, 136, 0.02) 100%);
	}

	.get-started-cta h2 {
		margin-bottom: var(--space-2);
	}

	.get-started-cta > p {
		color: var(--text-secondary);
		margin-bottom: var(--space-6);
	}

	.install-preview {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-width: 500px;
		margin: 0 auto var(--space-6);
		text-align: left;
	}

	.install-preview code {
		display: block;
		padding: var(--space-2) var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		font-size: var(--text-sm);
		color: var(--green-dim);
	}

	.install-preview code::before {
		content: '$ ';
		color: var(--text-tertiary);
	}

	.cta-buttons {
		display: flex;
		gap: var(--space-3);
		justify-content: center;
		flex-wrap: wrap;
	}

	.btn-secondary {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-primary);
	}

	.btn-secondary:hover {
		border-color: var(--green-dim);
		color: var(--green-dim);
	}

	/* Footer */
	footer {
		padding: var(--space-8) 0;
		border-top: 1px solid var(--border);
		text-align: center;
	}

	footer p {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	footer a {
		color: var(--text-secondary);
	}

	/* Architecture Diagram */
	.architecture-diagram {
		display: flex;
		justify-content: center;
		margin-bottom: var(--space-8);
	}

	.diagram-box {
		border: 1px solid var(--border);
		background: var(--bg-secondary);
		padding: var(--space-4);
	}

	.project-box {
		max-width: 500px;
		width: 100%;
	}

	.diagram-label {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: var(--space-3);
		text-align: center;
	}

	.diagram-inner {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
	}

	.diagram-row {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.diagram-box.small {
		padding: var(--space-3);
		text-align: center;
		min-width: 100px;
	}

	.claude-box {
		border-color: var(--text-tertiary);
	}

	.mind-box {
		border-color: var(--green-dim);
		background: rgba(0, 255, 136, 0.05);
	}

	.files-box {
		width: 100%;
		background: var(--bg-primary);
	}

	.files-row {
		display: flex;
		gap: var(--space-3);
		justify-content: center;
	}

	.file-box {
		padding: var(--space-2) var(--space-3);
		border: 1px dashed var(--border);
		text-align: center;
	}

	.small-text {
		display: block;
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.arrow-left, .arrow-down {
		color: var(--green-dim);
		font-size: var(--text-lg);
	}

	/* Flow Sections */
	.flow-section {
		margin-top: var(--space-8);
	}

	.flow-section h3 {
		text-align: center;
		margin-bottom: var(--space-4);
		font-family: var(--font-mono);
		color: var(--green-dim);
	}

	/* Memory Layers */
	.memory-layers {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		max-width: 500px;
		margin: 0 auto;
	}

	.layer {
		width: 100%;
		border: 1px solid var(--border);
		background: var(--bg-secondary);
	}

	.layer-header {
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.memory-layer .layer-header {
		color: var(--green-dim);
	}

	.session-layer .layer-header {
		color: var(--text-secondary);
	}

	.tag {
		font-size: var(--text-xs);
		padding: 2px 6px;
		border: 1px solid currentColor;
		opacity: 0.6;
	}

	.layer-content {
		padding: var(--space-3);
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-2);
	}

	.layer-item {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	.layer-item code {
		color: var(--green-dim);
		background: transparent;
		padding: 0;
		margin-right: var(--space-1);
	}

	.promote-arrow {
		display: flex;
		flex-direction: column;
		align-items: center;
		color: var(--text-tertiary);
		padding: var(--space-2) 0;
	}

	.promote-arrow span:first-child {
		font-size: var(--text-lg);
		color: var(--green-dim);
	}

	/* Session Flow */
	.session-flow {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.flow-step {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		min-width: 100px;
	}

	.flow-icon {
		font-family: var(--font-mono);
		font-size: var(--text-base);
		color: var(--green-dim);
		margin-bottom: var(--space-1);
	}

	.flow-text {
		text-align: center;
	}

	.flow-text strong {
		display: block;
		font-size: var(--text-sm);
		color: var(--text-primary);
	}

	.flow-text span {
		font-size: var(--text-xs);
		color: var(--green-dim);
		font-family: var(--font-mono);
	}

	.flow-arrow {
		font-family: var(--font-mono);
		color: var(--text-tertiary);
		font-size: var(--text-base);
	}

	/* Mobile */
	@media (max-width: 600px) {
		.hero h1 {
			font-size: 2.5rem;
		}

		.feature-grid {
			grid-template-columns: 1fr;
		}

		.tool-explorer {
			grid-template-columns: 1fr;
			min-height: auto;
		}

		.tool-output {
			min-height: 300px;
		}

		.reminders-grid {
			grid-template-columns: 1fr;
		}

		.diagram-row {
			flex-direction: column;
		}

		.arrow-left {
			transform: rotate(-90deg);
		}

		.layer-content {
			grid-template-columns: 1fr;
		}

		.session-flow {
			flex-direction: column;
		}

		.flow-arrow {
			transform: rotate(90deg);
		}

		.files-row {
			flex-direction: column;
			align-items: center;
		}
	}
</style>
