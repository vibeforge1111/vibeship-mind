<script lang="ts">
	import '$lib/styles/theme.css';
	import Navbar from '$lib/components/Navbar.svelte';

	let { children } = $props();

	// Theme state
	let theme = $state('dark');

	function toggleTheme() {
		theme = theme === 'dark' ? 'light' : 'dark';
		if (typeof document !== 'undefined') {
			document.documentElement.setAttribute('data-theme', theme);
		}
	}

	// Set initial theme on mount
	$effect(() => {
		if (typeof document !== 'undefined') {
			document.documentElement.setAttribute('data-theme', theme);
		}
	});
</script>

<svelte:head>
	<title>Mind - Memory for Claude</title>
	<meta name="description" content="Give Claude a mind. File-based memory that persists across sessions." />
</svelte:head>

<Navbar {theme} {toggleTheme} />

<main>
	{@render children()}
</main>

<footer class="site-footer">
	<div class="site-footer-inner">
		<div class="footer-top">
			<div class="footer-nav">
				<a href="https://vibeship.co" target="_blank">Ecosystem</a>
				<a href="https://mind.vibeship.co" target="_blank">Mind</a>
				<a href="https://scanner.vibeship.co" target="_blank">Scanner</a>
				<a href="https://vibeship.co/kb" target="_blank">Knowledge Base</a>
			</div>
			<div class="footer-social">
				<a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank" rel="noopener noreferrer" class="footer-icon-btn">
					<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
					</svg>
					GitHub
				</a>
				<a href="https://x.com/vibeshipco" target="_blank" rel="noopener noreferrer" class="footer-icon-btn footer-icon-only" aria-label="X">
					<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
						<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
					</svg>
				</a>
			</div>
		</div>
		<div class="footer-bottom">
			<a href="https://vibeship.co" class="footer-logo">
				<img src="/logo.png" alt="vibeship" class="footer-logo-icon">
				<span>vibeship</span>
			</a>
			<div class="footer-bottom-right">
				<a href="/terms">Terms</a>
				<span class="footer-dot">.</span>
				<a href="/privacy">Privacy</a>
				<span class="footer-dot">.</span>
				<span class="footer-tagline">Vibe coded. For vibe coders.</span>
			</div>
		</div>
	</div>
</footer>

<style>
	main {
		min-height: calc(100vh - 60px);
		padding: var(--space-8) var(--space-4);
		max-width: 900px;
		margin: 0 auto;
	}

	/* Footer */
	.site-footer {
		padding: 1rem 0 0;
	}

	.site-footer-inner {
		max-width: 100%;
		margin: 0;
		padding: 0;
	}

	.footer-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0 5rem 0.75rem;
	}

	.footer-nav {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.footer-nav a {
		font-size: 0.75rem;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}

	.footer-nav a:hover {
		color: var(--text-primary);
	}

	.footer-social {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.footer-icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		height: 28px;
		padding: 0 0.6rem;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		text-decoration: none;
		font-size: 0.75rem;
		transition: all 0.15s;
	}

	.footer-icon-btn:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}

	.footer-icon-only {
		width: 28px;
		padding: 0;
	}

	.footer-bottom {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 0 0.5rem;
		margin: 0 5rem;
		border-top: 1px solid var(--border);
	}

	.footer-logo {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		text-decoration: none;
	}

	.footer-logo-icon {
		width: 18px;
		height: 18px;
	}

	:global([data-theme="light"]) .footer-logo-icon {
		filter: invert(1);
	}

	:global([data-theme="dark"]) .footer-logo-icon {
		filter: none;
	}

	.footer-logo span {
		font-family: var(--font-serif);
		font-size: 1rem;
		color: var(--text-primary);
	}

	.footer-bottom-right {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.75rem;
	}

	.footer-bottom-right a {
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}

	.footer-bottom-right a:hover {
		color: var(--text-primary);
	}

	.footer-dot {
		color: var(--text-tertiary);
	}

	.footer-tagline {
		color: var(--text-tertiary);
	}

	@media (max-width: 768px) {
		.footer-top {
			flex-direction: column;
			gap: 1rem;
		}

		.footer-nav {
			flex-wrap: wrap;
			justify-content: center;
			gap: 1rem;
		}

		.footer-bottom {
			flex-direction: column;
			gap: 1rem;
			text-align: center;
		}

		.footer-bottom-right {
			flex-wrap: wrap;
			justify-content: center;
		}
	}
</style>
