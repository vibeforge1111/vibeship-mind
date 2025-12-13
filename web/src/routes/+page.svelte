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
				<div class="flow-icon">&#9654;</div>
				<div class="flow-text">
					<strong>Start</strong>
					<span>mind_recall()</span>
				</div>
			</div>
			<div class="flow-arrow">&#8594;</div>
			<div class="flow-step">
				<div class="flow-icon">&#8987;</div>
				<div class="flow-text">
					<strong>Gap &gt; 30min?</strong>
					<span>promote + clear</span>
				</div>
			</div>
			<div class="flow-arrow">&#8594;</div>
			<div class="flow-step">
				<div class="flow-icon">&#9998;</div>
				<div class="flow-text">
					<strong>Work</strong>
					<span>mind_log()</span>
				</div>
			</div>
			<div class="flow-arrow">&#8594;</div>
			<div class="flow-step">
				<div class="flow-icon">&#128260;</div>
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

	<div class="tools-grid">
		<div class="tool-category">
			<div class="tool-category-header">Core</div>
			<div class="tool">
				<code>mind_recall()</code>
				<span>Load context - call first</span>
			</div>
			<div class="tool">
				<code>mind_log()</code>
				<span>Log to session or memory</span>
			</div>
		</div>
		<div class="tool-category">
			<div class="tool-category-header">Reading</div>
			<div class="tool">
				<code>mind_session()</code>
				<span>Check session state</span>
			</div>
			<div class="tool">
				<code>mind_search()</code>
				<span>Search memories</span>
			</div>
			<div class="tool">
				<code>mind_status()</code>
				<span>Check memory health</span>
			</div>
			<div class="tool">
				<code>mind_reminders()</code>
				<span>List pending reminders</span>
			</div>
		</div>
		<div class="tool-category">
			<div class="tool-category-header">Actions</div>
			<div class="tool">
				<code>mind_blocker()</code>
				<span>Log blocker + search</span>
			</div>
			<div class="tool">
				<code>mind_remind()</code>
				<span>Set time/context reminder</span>
			</div>
			<div class="tool">
				<code>mind_reminder_done()</code>
				<span>Mark reminder complete</span>
			</div>
			<div class="tool">
				<code>mind_edges()</code>
				<span>Check for gotchas</span>
			</div>
			<div class="tool">
				<code>mind_checkpoint()</code>
				<span>Force process memories</span>
			</div>
			<div class="tool">
				<code>mind_add_global_edge()</code>
				<span>Add cross-project gotcha</span>
			</div>
		</div>
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

	/* Tools */
	.tools-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-4);
		max-width: 900px;
		margin: 0 auto;
	}

	.tool-category {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.tool-category-header {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--green-dim);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding-bottom: var(--space-1);
		border-bottom: 1px solid var(--border);
	}

	.tool {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding: var(--space-2);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
	}

	.tool code {
		color: var(--green-dim);
		background: transparent;
		padding: 0;
		font-size: var(--text-sm);
	}

	.tool span {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
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
		font-size: var(--text-xl);
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
		color: var(--text-tertiary);
		font-size: var(--text-lg);
	}

	/* Mobile */
	@media (max-width: 600px) {
		.hero h1 {
			font-size: 2.5rem;
		}

		.feature-grid {
			grid-template-columns: 1fr;
		}

		.tools-grid {
			grid-template-columns: 1fr;
			gap: var(--space-6);
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
