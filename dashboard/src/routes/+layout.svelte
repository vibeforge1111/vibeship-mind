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
	<nav class="navbar">
		<a href="/" class="navbar-logo-link">
			<img src="/assets/images/logo.png" alt="vibeship" class="navbar-logo-img" />
			<span class="navbar-logo-text">vibeship</span>
			<span class="navbar-logo-text" style="color: var(--green-dim); margin-left: 0.25rem;">mind</span>
		</a>
		<div class="nav-links">
			<a href="/edges">Edges</a>
			<button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
				{#if theme === 'dark'}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="5"/>
						<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
					</svg>
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
					</svg>
				{/if}
			</button>
		</div>
	</nav>

	<main class="main">
		{@render children()}
	</main>

	<footer class="footer">
		<div class="footer-left">Mind v0.1</div>
		<div class="footer-links">
			<a href="https://github.com/vibeforge1111/vibeship-mind">GitHub</a>
		</div>
	</footer>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.navbar {
		position: sticky;
		top: 0;
		z-index: var(--z-nav);
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.5rem 3rem;
		background: var(--bg-primary);
		border-bottom: 1px solid var(--border);
	}

	.navbar-logo-link {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		text-decoration: none;
	}

	.navbar-logo-img {
		height: 28px;
		width: auto;
	}

	.navbar-logo-text {
		position: relative;
		top: 1px;
		font-family: var(--font-serif);
		font-size: 1.35rem;
		font-weight: 400;
		color: var(--text-primary);
		line-height: 1;
		letter-spacing: -0.02em;
	}

	.nav-links {
		display: flex;
		gap: 2rem;
		align-items: center;
	}

	.nav-links a:not(.theme-toggle) {
		font-size: var(--text-sm);
		text-decoration: none;
		color: var(--text-secondary);
		transition: color var(--transition-fast);
	}

	.nav-links a:not(.theme-toggle):hover {
		color: var(--text-primary);
	}

	.theme-toggle {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-primary);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.theme-toggle:hover {
		border-color: var(--text-primary);
	}

	.main {
		flex: 1;
		width: 100%;
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--space-8) 3rem;
	}

	.footer {
		padding: 2rem 3rem;
		border-top: 1px solid var(--border);
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.footer-left {
		font-size: var(--text-xs);
		color: var(--text-secondary);
	}

	.footer-links {
		display: flex;
		gap: 2rem;
	}

	.footer-links a {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		text-decoration: none;
		transition: color var(--transition-fast);
	}

	.footer-links a:hover {
		color: var(--text-primary);
	}
</style>
