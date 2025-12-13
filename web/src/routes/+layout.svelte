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

<style>
	main {
		min-height: calc(100vh - 60px);
		padding: var(--space-8) var(--space-4);
		max-width: 900px;
		margin: 0 auto;
	}
</style>
