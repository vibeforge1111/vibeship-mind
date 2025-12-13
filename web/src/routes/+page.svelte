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
		'## Recent Decisions',
		'- use file-based storage (simpler, git-trackable)',
		'- skip database (too much friction)',
		'',
		'## Gotchas',
		'- Windows cp1252 encoding -> use UTF-8',
		'',
		'## Continue From',
		'Last: implementing context reminders'
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

	<div class="steps">
		<div class="step">
			<div class="step-num">1</div>
			<div class="step-content">
				<h3>Claude writes memories</h3>
				<p>Decisions, problems, learnings get captured to MEMORY.md as Claude works.</p>
			</div>
		</div>

		<div class="step">
			<div class="step-num">2</div>
			<div class="step-content">
				<h3>Context auto-injected</h3>
				<p>CLAUDE.md gets a MIND:CONTEXT section with summarized memory.</p>
			</div>
		</div>

		<div class="step">
			<div class="step-num">3</div>
			<div class="step-content">
				<h3>Next session recalls</h3>
				<p>mind_recall() loads fresh context. Claude knows what happened before.</p>
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
	<h2>10 MCP Tools</h2>

	<div class="tools-grid">
		<div class="tool">
			<code>mind_recall()</code>
			<span>Load context - call first</span>
		</div>
		<div class="tool">
			<code>mind_session()</code>
			<span>Check session state</span>
		</div>
		<div class="tool">
			<code>mind_blocker()</code>
			<span>Log blocker + search</span>
		</div>
		<div class="tool">
			<code>mind_search()</code>
			<span>Search memories</span>
		</div>
		<div class="tool">
			<code>mind_edges()</code>
			<span>Check for gotchas</span>
		</div>
		<div class="tool">
			<code>mind_remind()</code>
			<span>Set reminders</span>
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
	.features, .how-it-works, .files, .tools {
		padding: var(--space-12) 0;
		border-top: 1px solid var(--border);
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

	/* Steps */
	.steps {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.step {
		display: flex;
		gap: var(--space-4);
		align-items: flex-start;
	}

	.step-num {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--green-dim);
		color: var(--bg-primary);
		font-weight: 600;
		flex-shrink: 0;
	}

	.step-content h3 {
		font-family: var(--font-mono);
		font-size: var(--text-base);
		margin-bottom: var(--space-1);
	}

	.step-content p {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	/* Files */
	.files pre {
		max-width: 400px;
		margin: 0 auto;
	}

	/* Tools */
	.tools-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-3);
	}

	.tool {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
	}

	.tool code {
		color: var(--green-dim);
		background: transparent;
		padding: 0;
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

	/* Mobile */
	@media (max-width: 600px) {
		.hero h1 {
			font-size: 2.5rem;
		}

		.feature-grid, .tools-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
