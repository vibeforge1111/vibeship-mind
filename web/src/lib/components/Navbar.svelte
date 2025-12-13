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
			<a href="/get-started" class="nav-link">
				Get Started
			</a>
			<a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank" class="nav-link">
				GitHub
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

	.nav-link {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.nav-link:hover {
		color: var(--green-dim);
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
