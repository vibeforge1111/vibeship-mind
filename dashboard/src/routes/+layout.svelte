<script lang="ts">
	let { children } = $props();

	let theme = $state('dark');

	function toggleTheme() {
		theme = theme === 'dark' ? 'light' : 'dark';
		document.documentElement.setAttribute('data-theme', theme);
	}
</script>

<svelte:head>
	<title>Mind</title>
	<meta name="description" content="Context engine for AI-assisted development" />
</svelte:head>

<div class="app" data-theme={theme}>
	<nav class="nav">
		<a href="/" class="nav-logo">
			<span class="logo-icon">◉</span>
			<span class="logo-text">mind</span>
		</a>
		<div class="nav-actions">
			<button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
				{#if theme === 'dark'}
					<span>☀</span>
				{:else}
					<span>☾</span>
				{/if}
			</button>
		</div>
	</nav>

	<main class="main">
		{@render children()}
	</main>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.nav {
		position: sticky;
		top: 0;
		z-index: var(--z-nav);
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-4) var(--space-6);
		background: var(--bg-primary);
		border-bottom: 1px solid var(--border-subtle);
	}

	.nav-logo {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--text-lg);
		font-weight: 500;
		color: var(--text-primary);
		text-decoration: none;
	}

	.logo-icon {
		color: var(--color-decisions);
	}

	.logo-text {
		font-family: var(--font-serif);
		font-style: italic;
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.theme-toggle {
		padding: var(--space-2);
		font-size: var(--text-lg);
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		transition: color var(--transition-fast);
	}

	.theme-toggle:hover {
		color: var(--text-primary);
	}

	.main {
		flex: 1;
		width: 100%;
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--space-8) var(--space-6);
	}
</style>
