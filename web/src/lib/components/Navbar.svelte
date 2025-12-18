<script lang="ts">
	interface Props {
		theme: string;
		toggleTheme: () => void;
	}

	let { theme, toggleTheme }: Props = $props();
</script>

<nav class="navbar">
	<div class="navbar-content">
		<a href="/" class="navbar-logo-link">
			<img src="/logo.png" alt="vibeship" class="navbar-logo-img" />
			<span class="navbar-logo-text">vibeship</span>
			<span class="navbar-logo-product">mind</span>
		</a>

		<div class="navbar-right">
			<a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank" class="navbar-github-btn with-text">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
					<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
				</svg>
				<span>Get the Code</span>
			</a>
			<button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
				{#if theme === 'dark'}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="5"/>
						<line x1="12" y1="1" x2="12" y2="3"/>
						<line x1="12" y1="21" x2="12" y2="23"/>
						<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
						<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
						<line x1="1" y1="12" x2="3" y2="12"/>
						<line x1="21" y1="12" x2="23" y2="12"/>
						<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
						<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
					</svg>
				{:else}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
					</svg>
				{/if}
			</button>
		</div>
	</div>
</nav>

<style>
	.navbar {
		position: sticky;
		top: 0;
		height: 52px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-primary);
		z-index: 100;
	}

	.navbar-content {
		height: 100%;
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.625rem;
	}

	.navbar-logo-link {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		text-decoration: none;
	}

	.navbar-logo-img {
		width: 24px;
		height: 24px;
		position: relative;
		left: -1px;
	}

	/* Logo is white - invert to black in light mode, keep white in dark mode */
	:global([data-theme="light"]) .navbar-logo-img {
		filter: invert(1);
	}

	:global([data-theme="dark"]) .navbar-logo-img {
		filter: none;
	}

	.navbar-logo-text {
		font-family: 'Instrument Serif', Georgia, serif;
		font-size: 1.36rem;
		color: var(--text-primary);
		position: relative;
		top: 1px;
		left: -1px;
	}

	.navbar-logo-product {
		font-family: 'Instrument Serif', Georgia, serif;
		font-size: 1.36rem;
		color: var(--green-dim);
		position: relative;
		top: 1px;
	}

	.navbar-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.navbar-github-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.navbar-github-btn.with-text {
		width: auto;
		gap: 0.5rem;
		padding: 0 0.75rem;
		font-size: 0.8rem;
	}

	.navbar-github-btn:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}

	.navbar-github-btn svg {
		fill: currentColor;
	}

	.theme-toggle {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.theme-toggle:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}
</style>
