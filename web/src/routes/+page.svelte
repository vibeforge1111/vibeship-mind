<script lang="ts">
	// Animated typing effect for the terminal
	let terminalLines = $state<string[]>([]);
	let currentLine = $state(0);

	const lines = [
		'> mind_recall()',
		'',
		'Welcome back. Last session was 3 days ago.',
		'',
		'## I Remember',
		'- You prefer Tailwind over CSS modules',
		'- We chose Zustand because Redux felt heavy',
		'- The auth bug was a Safari cookie issue',
		'',
		'## You Asked Me to Remind You',
		'- "Add rate limiting before launch"',
		'',
		'## Where We Left Off',
		'Implementing the checkout flow. Payment API was working.'
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
	<h1>Give Claude a <span class="highlight">Mind<span class="claude-underline"></span></span></h1>
	<p class="subtitle">
		Memory for Claude Code that persists across sessions.
		Decisions, learnings, and reminders.
		Install in 2 minutes with 2 prompts. Free for now.
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
				{:else if line.startsWith('Welcome')}
					<div class="line welcome">{line}</div>
				{:else if line.startsWith('##')}
					<div class="line heading">{line}</div>
				{:else if line.startsWith('-')}
					<div class="line item">{line}</div>
				{:else if line.startsWith('Implementing')}
					<div class="line continue">{line}</div>
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
	<p class="section-subtitle">Without memory, Claude starts every session blank. These problems go away.</p>

	<div class="feature-grid">
		<div class="feature">
			<h3>Rabbit Holes</h3>
			<p>Claude goes down the wrong path for an hour before you notice. Mind tracks what's been tried so it doesn't loop.</p>
		</div>

		<div class="feature">
			<h3>Doesn't Remember You</h3>
			<p>Your preferences, your stack, your way of doing things - gone every session. Mind remembers who it's working with.</p>
		</div>

		<div class="feature">
			<h3>Session Memory Lost</h3>
			<p>Terminal closes. All that context? Vanished. Mind persists what matters between sessions.</p>
		</div>

		<div class="feature">
			<h3>Forgets What's Built</h3>
			<p>Claude references features that don't exist, or rebuilds things you have. Mind tracks what's done vs not.</p>
		</div>

		<div class="feature">
			<h3>Spaghetti Code</h3>
			<p>No memory means disconnected updates. Claude patches on patches. Mind keeps the full picture for coherent changes.</p>
		</div>

		<div class="feature feature-highlight">
			<h3>2 Minutes to Fix All This</h3>
			<p>3 commands to install. 2 prompts to configure. These problems stop. Fully automated after.</p>
		</div>
	</div>
</section>

<section class="how-it-works">
	<h2>How It Works</h2>
	<p class="section-subtitle">MCP tools run locally, filtering what's worth remembering into the right place.</p>

	<div class="architecture-flow">
		<!-- Claude Code -->
		<div class="arch-box claude-code-box">
			<div class="arch-label">Claude Code</div>
			<div class="arch-desc">Working on your project</div>
		</div>

		<div class="arch-connector">
			<span class="connector-line"></span>
			<span class="connector-label">calls MCP tools</span>
		</div>

		<!-- MCP Tools -->
		<div class="arch-box mcp-box">
			<div class="arch-label">Mind MCP Server</div>
			<div class="mcp-tools-grid">
				<code>mind_recall()</code>
				<code>mind_log()</code>
				<code>mind_search()</code>
				<code>mind_blocker()</code>
				<code>mind_remind()</code>
				<code>mind_edges()</code>
			</div>
			<div class="arch-desc">12 commands Claude can call when needed</div>
		</div>

		<div class="arch-connector">
			<span class="connector-line"></span>
			<span class="connector-label">filters &amp; routes</span>
		</div>

		<!-- Storage Layer -->
		<div class="arch-box storage-box">
			<div class="arch-label">.mind/ folder</div>
			<div class="storage-split">
				<div class="storage-side long-term">
					<div class="storage-header">Long-term Memory</div>
					<div class="storage-file">MEMORY.md</div>
					<div class="storage-items">
						<span>decisions</span>
						<span>learnings</span>
						<span>problems solved</span>
					</div>
					<div class="storage-note">Persists forever. Worth remembering.</div>
				</div>
				<div class="storage-divider"></div>
				<div class="storage-side short-term">
					<div class="storage-header">Short-term Memory</div>
					<div class="storage-file">SESSION.md</div>
					<div class="storage-items">
						<span>experiences</span>
						<span>assumptions</span>
						<span>current blockers</span>
					</div>
					<div class="storage-note">Clears on session end. Working memory.</div>
				</div>
			</div>
		</div>

		<div class="arch-connector">
			<span class="connector-line"></span>
			<span class="connector-label">injects context</span>
		</div>

		<!-- Context Output -->
		<div class="arch-box context-box">
			<div class="arch-label">CLAUDE.md</div>
			<div class="arch-desc">Fresh context loaded every session</div>
		</div>
	</div>

	<div class="flow-section">
		<h3>The Filtering Logic</h3>
		<p class="flow-explanation">
			When Claude logs something, Mind decides where it goes based on whether it's useful long-term:
		</p>
		<div class="filter-examples">
			<div class="filter-example">
				<div class="filter-input">"We decided to use Zustand for state"</div>
				<div class="filter-right">
					<div class="filter-arrow">→</div>
					<div class="filter-output memory">MEMORY.md <span class="why">future sessions need this</span></div>
				</div>
			</div>
			<div class="filter-example">
				<div class="filter-input">"Trying the flexbox approach now"</div>
				<div class="filter-right">
					<div class="filter-arrow">→</div>
					<div class="filter-output session">SESSION.md <span class="why">only matters right now</span></div>
				</div>
			</div>
			<div class="filter-example">
				<div class="filter-input">"Safari doesn't support :has() in older versions"</div>
				<div class="filter-right">
					<div class="filter-arrow">→</div>
					<div class="filter-output memory">MEMORY.md <span class="why">gotcha worth keeping</span></div>
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
	<p>3 commands + 1 prompt. Zero friction.</p>

	<div class="install-steps">
		<div class="install-step">
			<div class="step-label">1. Install</div>
			<div class="install-preview">
				<code>git clone https://github.com/vibeforge1111/vibeship-mind.git</code>
				<code>cd vibeship-mind && uv sync</code>
				<code>uv run mind init</code>
			</div>
		</div>

		<div class="install-step">
			<div class="step-label">2. Tell Claude Code to connect</div>
			<div class="prompt-box">
				<p>"Add Mind MCP server to my config"</p>
			</div>
		</div>
	</div>

	<div class="cta-buttons">
		<a href="https://github.com/vibeforge1111/vibeship-mind" class="btn btn-primary btn-lg" target="_blank">
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
		position: relative;
		display: inline-block;
	}

	.claude-underline {
		position: absolute;
		bottom: calc(0.15em + 2px);
		left: -3%;
		width: 115%;
		height: 3px;
		background: linear-gradient(90deg, transparent 0%, #D97757 8%, #D97757 60%, transparent 100%);
		transform: rotate(-3deg) skewX(-15deg);
	}

	.subtitle {
		font-size: var(--text-lg);
		color: var(--text-secondary);
		max-width: 500px;
		margin: 0 auto var(--space-8);
	}

	.terminal {
		background: var(--terminal-bg);
		border: 1px solid var(--terminal-border);
		max-width: 600px;
		margin: 0 auto var(--space-8);
		text-align: left;
		box-shadow: var(--terminal-shadow);
	}

	.terminal-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		border-bottom: 1px solid var(--terminal-border);
		background: var(--terminal-header);
	}

	.terminal-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}

	.terminal-dot:nth-child(1) { background: #ff5f56; }
	.terminal-dot:nth-child(2) { background: #ffbd2e; }
	.terminal-dot:nth-child(3) { background: #27ca40; }

	.terminal-title {
		margin-left: auto;
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		opacity: 0.7;
	}

	.terminal-body {
		padding: var(--space-4);
		font-size: var(--text-sm);
		min-height: 280px;
	}

	.line {
		line-height: 1.8;
		color: var(--terminal-text);
	}

	.line.command {
		color: var(--terminal-command);
	}

	.line.heading {
		color: var(--terminal-heading);
		font-weight: 600;
		margin-top: var(--space-2);
	}

	.line.item {
		color: var(--terminal-item);
		padding-left: var(--space-4);
	}

	.line.welcome {
		color: var(--terminal-muted);
		font-style: italic;
	}

	.line.continue {
		color: var(--terminal-item);
	}

	.cursor {
		animation: blink 1s infinite;
		color: var(--terminal-command);
	}

	@keyframes blink {
		0%, 50% { opacity: 1; }
		51%, 100% { opacity: 0; }
	}

	.cta {
		margin-top: var(--space-6);
	}

	/* Features */
	.features, .how-it-works, .reminders, .tools {
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

	.feature-highlight {
		border-color: var(--green-dim);
		background: var(--bg-tertiary);
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
		opacity: 0.93;
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
		background: var(--terminal-bg);
		border: 1px solid var(--terminal-border);
		border-bottom: none;
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		box-shadow: var(--terminal-shadow);
	}

	.tool-output-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border-bottom: 1px solid var(--terminal-border);
		background: var(--terminal-header);
	}

	.tool-output-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}

	.tool-output-dot:nth-child(1) { background: #ff5f56; }
	.tool-output-dot:nth-child(2) { background: #ffbd2e; }
	.tool-output-dot:nth-child(3) { background: #27ca40; }

	.tool-output-title {
		margin-left: auto;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--green-dim);
		opacity: 0.8;
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
		font-size: var(--text-base);
		color: var(--terminal-item);
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
		opacity: 0.93;
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

	.install-steps {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
		max-width: 550px;
		margin: 0 auto var(--space-6);
	}

	.install-step {
		text-align: left;
	}

	.step-label {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--green-dim);
		margin-bottom: var(--space-2);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.install-preview {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.install-preview code {
		display: block;
		padding: var(--space-2) var(--space-3);
		background: var(--terminal-bg);
		border: 1px solid var(--terminal-border);
		font-size: var(--text-sm);
		color: var(--terminal-command);
	}

	.install-preview code::before {
		content: '$ ';
		color: var(--terminal-muted);
	}

	.prompt-box {
		padding: var(--space-3) var(--space-4);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-left: 3px solid var(--green-dim);
	}

	.prompt-box p {
		margin: 0;
		font-size: var(--text-base);
		color: var(--text-secondary);
		font-style: italic;
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

	/* Architecture Flow */
	.architecture-flow {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0;
		max-width: 600px;
		margin: 0 auto var(--space-8);
	}

	.arch-box {
		width: 100%;
		border: 1px solid var(--border);
		background: var(--bg-secondary);
		padding: var(--space-4);
		text-align: center;
	}

	.arch-label {
		font-family: var(--font-mono);
		font-size: var(--text-base);
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.arch-desc {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	.claude-code-box {
		border-color: #D97757;
		background: rgba(217, 119, 87, 0.05);
	}

	.claude-code-box .arch-label {
		color: #D97757;
	}

	.mcp-box {
		border-color: var(--green-dim);
		background: rgba(0, 196, 154, 0.05);
	}

	.mcp-box .arch-label {
		color: var(--green-dim);
	}

	.mcp-tools-grid {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		justify-content: center;
		margin: var(--space-3) 0;
	}

	.mcp-tools-grid code {
		font-size: var(--text-xs);
		color: var(--green-dim);
		background: var(--bg-primary);
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--border);
	}

	.storage-box {
		background: var(--bg-primary);
	}

	.storage-split {
		display: flex;
		gap: var(--space-4);
		margin-top: var(--space-3);
	}

	.storage-side {
		flex: 1;
		padding: var(--space-3);
		border: 1px dashed var(--border);
	}

	.storage-side.long-term {
		border-color: var(--green-dim);
	}

	.storage-side.short-term {
		border-color: var(--orange);
	}

	.storage-header {
		font-size: var(--text-xs);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: var(--space-2);
	}

	.long-term .storage-header {
		color: var(--green-dim);
	}

	.short-term .storage-header {
		color: var(--orange);
	}

	.storage-file {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.storage-items {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		margin-bottom: var(--space-2);
	}

	.storage-items span {
		font-size: var(--text-xs);
		color: var(--text-secondary);
	}

	.storage-note {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		font-style: italic;
	}

	.storage-divider {
		width: 1px;
		background: var(--border);
	}

	.context-box {
		border-color: var(--text-tertiary);
	}

	.arch-connector {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--space-2) 0;
	}

	.connector-line {
		width: 2px;
		height: 20px;
		background: var(--border);
	}

	.connector-label {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		margin-top: var(--space-1);
	}

	/* Filter Examples */
	.flow-explanation {
		text-align: center;
		color: var(--text-secondary);
		margin-bottom: var(--space-4);
		font-size: var(--text-sm);
	}

	.filter-examples {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		max-width: 600px;
		margin: 0 auto;
	}

	.filter-example {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
	}

	.filter-input {
		flex: 1;
		font-size: var(--text-sm);
		color: var(--text-secondary);
		font-style: italic;
	}

	.filter-right {
		display: flex;
		align-items: center;
		gap: 2px;
		margin-left: auto;
		margin-right: var(--space-4);
	}

	.filter-arrow {
		color: var(--text-tertiary);
		font-size: var(--text-lg);
		flex-shrink: 0;
	}

	.filter-output {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 140px;
		text-align: right;
	}

	.filter-output.memory {
		color: var(--green-dim);
	}

	.filter-output.session {
		color: var(--orange);
	}

	.filter-output .why {
		font-family: var(--font-sans);
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		font-style: italic;
	}

	.small-text {
		display: block;
		font-size: var(--text-xs);
		color: var(--text-tertiary);
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

		.storage-split {
			flex-direction: column;
		}

		.storage-divider {
			width: 100%;
			height: 1px;
		}

		.filter-example {
			flex-direction: column;
			text-align: center;
		}

		.filter-right {
			margin-left: 0;
			margin-right: 0;
			flex-direction: column;
			gap: var(--space-1);
		}

		.filter-arrow {
			transform: rotate(90deg);
		}

		.filter-output {
			text-align: center;
		}
	}
</style>
