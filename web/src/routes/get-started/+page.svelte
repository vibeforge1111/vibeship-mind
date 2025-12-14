<script lang="ts">
	let copied = $state<string | null>(null);

	function copyToClipboard(text: string, id: string) {
		navigator.clipboard.writeText(text);
		copied = id;
		setTimeout(() => copied = null, 2000);
	}
</script>

<div class="get-started">
	<h1>Get Started</h1>
	<p class="intro">Up and running in 2 minutes. Just terminal commands.</p>

	<!-- Step 1: Install -->
	<section class="step">
		<div class="step-header">
			<span class="step-number">1</span>
			<h2>Clone & Install</h2>
		</div>
		<div class="terminal">
			<div class="terminal-header">
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-title">terminal</span>
			</div>
			<div class="terminal-body">
				<div class="command-block">
					<button
						class="copy-btn"
						onclick={() => copyToClipboard('git clone https://github.com/vibeforge1111/vibeship-mind.git\ncd vibeship-mind\nuv sync', 'install')}
					>
						{copied === 'install' ? 'copied!' : 'copy'}
					</button>
					<div class="line comment"># Clone the repo</div>
					<div class="line command">$ git clone https://github.com/vibeforge1111/vibeship-mind.git</div>
					<div class="line output">Cloning into 'vibeship-mind'...</div>
					<div class="line output">done.</div>
					<div class="line blank"></div>
					<div class="line comment"># Install dependencies</div>
					<div class="line command">$ cd vibeship-mind</div>
					<div class="line command">$ uv sync</div>
					<div class="line output">Resolved 12 packages in 1.2s</div>
					<div class="line output success">Installed 12 packages</div>
				</div>
			</div>
		</div>
		<details class="uv-help">
			<summary>If <code>uv sync</code> fails, install uv first</summary>
			<div class="terminal small">
				<div class="terminal-body">
					<div class="line comment"># macOS/Linux</div>
					<div class="line command">$ curl -LsSf https://astral.sh/uv/install.sh | sh</div>
					<div class="line blank"></div>
					<div class="line comment"># Windows (PowerShell)</div>
					<div class="line command">$ powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"</div>
				</div>
			</div>
		</details>
	</section>

	<!-- Step 2: Add MCP Server -->
	<section class="step">
		<div class="step-header">
			<span class="step-number">2</span>
			<h2>Connect to Claude Code</h2>
		</div>

		<div class="option-tabs">
			<p class="option-label">Choose your method:</p>
		</div>

		<div class="option">
			<h3>Option A: Just tell Claude</h3>
			<div class="terminal small">
				<div class="terminal-body">
					<div class="line prompt">> Add Mind MCP server from github.com/vibeforge1111/vibeship-mind to my config</div>
				</div>
			</div>
			<p class="step-note">Claude will add it to your MCP config automatically.</p>
		</div>

		<div class="option">
			<h3>Option B: Manual config</h3>
			<p class="config-path">
				<strong>Mac/Linux:</strong> <code>~/.config/claude/mcp.json</code><br>
				<strong>Windows:</strong> <code>%APPDATA%\Claude\claude_desktop_config.json</code>
			</p>
			<div class="terminal">
				<div class="terminal-header">
					<span class="terminal-dot"></span>
					<span class="terminal-dot"></span>
					<span class="terminal-dot"></span>
					<span class="terminal-title">mcp.json</span>
				</div>
				<div class="terminal-body">
					<button
						class="copy-btn"
						onclick={() => copyToClipboard('{\n  "mcpServers": {\n    "mind": {\n      "command": "uv",\n      "args": ["--directory", "/path/to/vibeship-mind", "run", "mind", "mcp"]\n    }\n  }\n}', 'config')}
					>
						{copied === 'config' ? 'copied!' : 'copy'}
					</button>
					<div class="line json">{"{"}</div>
					<div class="line json">  "mcpServers": {"{"}</div>
					<div class="line json">    "mind": {"{"}</div>
					<div class="line json">      "command": "uv",</div>
					<div class="line json">      "args": ["--directory", "<span class="highlight">/path/to/vibeship-mind</span>", "run", "mind", "mcp"]</div>
					<div class="line json">    {"}"}</div>
					<div class="line json">  {"}"}</div>
					<div class="line json">{"}"}</div>
				</div>
			</div>
			<p class="step-note">Replace <code>/path/to/vibeship-mind</code> with your actual path. Restart Claude Code after.</p>
		</div>
	</section>

	<!-- Step 3: Initialize -->
	<section class="step">
		<div class="step-header">
			<span class="step-number">3</span>
			<h2>Initialize in Your Project</h2>
		</div>
		<div class="terminal">
			<div class="terminal-header">
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-title">terminal</span>
			</div>
			<div class="terminal-body">
				<button
					class="copy-btn"
					onclick={() => copyToClipboard('cd /your/project\nuv --directory ~/vibeship-mind run mind init', 'init')}
				>
					{copied === 'init' ? 'copied!' : 'copy'}
				</button>
				<div class="line command">$ cd /your/project</div>
				<div class="line command">$ uv --directory ~/vibeship-mind run mind init</div>
				<div class="line blank"></div>
				<div class="line output success">[+] Created .mind/MEMORY.md</div>
				<div class="line output success">[+] Created .mind/SESSION.md</div>
				<div class="line output success">[+] Updated CLAUDE.md with MIND:CONTEXT</div>
				<div class="line output">[+] Detected stack: typescript, react</div>
				<div class="line output">[+] Registered project with Mind</div>
				<div class="line blank"></div>
				<div class="line output">Mind initialized! Start working.</div>
			</div>
		</div>
	</section>

	<!-- Step 4: Verify -->
	<section class="step">
		<div class="step-header">
			<span class="step-number">4</span>
			<h2>Verify It Works</h2>
		</div>
		<div class="terminal">
			<div class="terminal-header">
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-dot"></span>
				<span class="terminal-title">claude code</span>
			</div>
			<div class="terminal-body">
				<div class="line prompt">> Check if Mind is working</div>
				<div class="line blank"></div>
				<div class="line output dim">Claude calls mind_recall()...</div>
				<div class="line blank"></div>
				<div class="line heading">## Memory: Active</div>
				<div class="line output">Last captured: just now</div>
				<div class="line blank"></div>
				<div class="line heading">## Project State</div>
				<div class="line output">- Stack: typescript, react</div>
				<div class="line output">- Blocked: None</div>
				<div class="line blank"></div>
				<div class="line output success">Mind is ready!</div>
			</div>
		</div>
	</section>

	<!-- Usage Examples -->
	<section class="usage">
		<h2>How to Use</h2>
		<p class="intro">Mind works automatically. But here are the key tools:</p>

		<div class="usage-grid">
			<div class="usage-example">
				<h3>Log a decision</h3>
				<div class="terminal small">
					<div class="terminal-body">
						<div class="line prompt">> We decided to use Zustand for state</div>
						<div class="line output dim">mind_log("use Zustand for state - simpler than Redux", type="decision")</div>
						<div class="line output success">Logged to MEMORY.md</div>
					</div>
				</div>
			</div>

			<div class="usage-example">
				<h3>Set a reminder</h3>
				<div class="terminal small">
					<div class="terminal-body">
						<div class="line prompt">> Remind me to add tests when we work on auth</div>
						<div class="line output dim">mind_remind("add tests", when="when I mention auth")</div>
						<div class="line output success">Reminder set (context trigger)</div>
					</div>
				</div>
			</div>

			<div class="usage-example">
				<h3>Log a blocker</h3>
				<div class="terminal small">
					<div class="terminal-body">
						<div class="line prompt">> I'm stuck on the CORS issue</div>
						<div class="line output dim">mind_blocker("CORS issue")</div>
						<div class="line output">Searching memory for related solutions...</div>
						<div class="line output success">Found: "Fixed CORS by adding proxy config"</div>
					</div>
				</div>
			</div>

			<div class="usage-example">
				<h3>Check health</h3>
				<div class="terminal small">
					<div class="terminal-body">
						<div class="line command">$ uv --directory ~/vibeship-mind run mind doctor</div>
						<div class="line output success">[+] Config directory exists</div>
						<div class="line output success">[+] Projects registered: 2</div>
						<div class="line output success">[+] MEMORY.md accessible (4KB)</div>
						<div class="line output">Overall: Healthy</div>
					</div>
				</div>
			</div>
		</div>
	</section>

	<div class="back-link">
		<a href="/">&larr; Back to home</a>
	</div>
</div>

<style>
	.get-started {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		text-align: center;
		margin-bottom: var(--space-2);
	}

	.intro {
		text-align: center;
		color: var(--text-secondary);
		margin-bottom: var(--space-8);
	}

	/* Steps */
	.step {
		margin-bottom: var(--space-10);
	}

	.step-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}

	.step-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: 2px solid var(--green-dim);
		color: var(--green-dim);
		font-family: var(--font-mono);
		font-weight: bold;
	}

	.step-header h2 {
		margin: 0;
		font-size: var(--text-xl);
	}

	.step-note {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin-top: var(--space-2);
	}

	.step-note code {
		background: var(--bg-secondary);
		padding: 2px 6px;
	}

	.step-note a {
		color: var(--green-dim);
	}

	.uv-help {
		margin-top: var(--space-3);
		font-size: var(--text-sm);
	}

	.uv-help summary {
		color: var(--text-secondary);
		cursor: pointer;
	}

	.uv-help summary:hover {
		color: var(--text-primary);
	}

	.uv-help summary code {
		background: transparent;
		padding: 0;
		color: inherit;
	}

	/* Terminal */
	.terminal {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		margin-bottom: var(--space-2);
	}

	.terminal.small .terminal-body {
		padding: var(--space-3);
		min-height: auto;
	}

	.terminal-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
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
		position: relative;
	}

	.command-block {
		position: relative;
	}

	.copy-btn {
		position: absolute;
		top: 0;
		right: 0;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		color: var(--text-tertiary);
		padding: var(--space-1) var(--space-2);
		font-size: var(--text-xs);
		cursor: pointer;
		font-family: var(--font-mono);
	}

	.copy-btn:hover {
		color: var(--green-dim);
		border-color: var(--green-dim);
	}

	.line {
		line-height: 1.6;
		font-family: var(--font-mono);
	}

	.line.blank {
		height: 1em;
	}

	.line.comment {
		color: var(--text-tertiary);
	}

	.line.command {
		color: var(--text-primary);
	}

	.line.command::before {
		content: '';
	}

	.line.output {
		color: var(--text-secondary);
	}

	.line.output.success {
		color: var(--green-dim);
	}

	.line.output.dim {
		color: var(--text-tertiary);
		font-style: italic;
	}

	.line.prompt {
		color: var(--text-primary);
	}

	.line.prompt::before {
		content: '> ';
		color: var(--green-dim);
	}

	.line.heading {
		color: var(--text-primary);
		font-weight: 600;
	}

	.line.json {
		color: var(--text-secondary);
	}

	.line.json .highlight {
		color: var(--green-dim);
	}

	/* Options */
	.option {
		margin-bottom: var(--space-6);
		padding-left: var(--space-4);
		border-left: 2px solid var(--border);
	}

	.option h3 {
		font-size: var(--text-base);
		margin-bottom: var(--space-3);
		color: var(--text-secondary);
	}

	.option-label {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin-bottom: var(--space-4);
	}

	.config-path {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-3);
	}

	.config-path code {
		background: var(--bg-secondary);
		padding: 2px 6px;
		font-size: var(--text-xs);
	}

	/* Usage */
	.usage {
		margin-top: var(--space-12);
		padding-top: var(--space-8);
		border-top: 1px solid var(--border);
	}

	.usage h2 {
		text-align: center;
		margin-bottom: var(--space-2);
	}

	.usage > .intro {
		margin-bottom: var(--space-6);
	}

	.usage-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-4);
	}

	.usage-example h3 {
		font-size: var(--text-sm);
		color: var(--green-dim);
		margin-bottom: var(--space-2);
		font-family: var(--font-mono);
	}

	/* Back link */
	.back-link {
		margin-top: var(--space-10);
		text-align: center;
	}

	.back-link a {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
	}

	.back-link a:hover {
		color: var(--green-dim);
	}

	/* Mobile */
	@media (max-width: 600px) {
		.usage-grid {
			grid-template-columns: 1fr;
		}

		.option {
			padding-left: var(--space-3);
		}
	}
</style>
