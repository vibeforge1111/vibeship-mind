<script lang="ts">
	interface Props {
		theme: string;
		toggleTheme: () => void;
	}

	let { theme, toggleTheme }: Props = $props();
</script>

<nav>
	<div class="nav-content">
		<a href="/" class="logo">
			<img src="/logo.png" alt="vibeship" class="logo-icon" />
			<span class="logo-text">vibeship</span>
			<span class="logo-text logo-product">mind</span>
		</a>

		<div class="nav-right">
			<a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank" class="github-cta">
				<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
					<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
				</svg>
				<span>Star on GitHub</span>
			</a>
			<button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
				{#if theme === 'dark'}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
					</svg>
				{/if}
			</button>
		</div>
	</div>
</nav>

<style>
	nav {
		height: 52px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-primary);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.nav-content {
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-6);
	}

	.logo {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.logo-icon {
		height: 22px;
		width: auto;
		/* Dark grey on light mode, white on dark mode */
		filter: brightness(0) saturate(100%) invert(20%) sepia(5%) saturate(500%) hue-rotate(180deg);
	}

	:global([data-theme="dark"]) .logo-icon {
		filter: none;
	}

	.logo-text {
		font-family: var(--font-serif);
		font-size: var(--text-xl);
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	.logo-product {
		margin-left: -0.15rem;
		color: var(--green-dim);
	}

	.nav-right {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.github-cta {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--text-sm);
		color: var(--text-primary);
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--border);
		transition: all var(--transition-fast);
	}

	.github-cta:hover {
		border-color: var(--green-dim);
		color: var(--green-dim);
	}

	.github-cta span {
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.theme-toggle {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		padding: var(--space-2);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all var(--transition-fast);
	}

	.theme-toggle:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}
</style>
