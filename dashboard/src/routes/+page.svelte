<script lang="ts">
	import { onMount } from 'svelte';
	import type { Project, User, Stats, SharpEdge } from '$lib/api';
	import { formatRecencyText, getCtaText } from '$lib/api';

	// Svelte 5 runes for state
	let loading = $state(true);
	let error = $state<string | null>(null);
	let user = $state<User | null>(null);
	let stats = $state<Stats | null>(null);
	let projects = $state<Project[]>([]);
	let globalEdges = $state<SharpEdge[]>([]);

	// Derived values using Svelte 5 runes
	let recencyText = $derived(formatRecencyText(user?.last_session ?? null));
	let ctaText = $derived(getCtaText(user, false));
	let depthText = $derived(getDepthText());

	function getDepthText(): string {
		if (!user || !stats || user.total_sessions === 0) {
			return 'Ready to start building context.';
		}
		const parts: string[] = [];
		if (user.total_sessions > 0) parts.push(`${user.total_sessions} sessions`);
		if (stats.decisions > 0) parts.push(`${stats.decisions} decisions`);
		return parts.join(' / ') || 'Ready to start building context.';
	}

	function formatProjectRecency(project: Project): string {
		if (!project.last_session_date) return '';
		const diffDays = Math.floor((Date.now() - new Date(project.last_session_date).getTime()) / (1000 * 60 * 60 * 24));
		if (diffDays === 0) return 'today';
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		return `${Math.floor(diffDays / 7)} weeks ago`;
	}

	// Load data only after component mounts (client-side only)
	onMount(async () => {
		try {
			const API = 'http://127.0.0.1:8765';

			const [statusRes, userRes, projectsRes, edgesRes] = await Promise.all([
				fetch(`${API}/status`).then(r => r.json()),
				fetch(`${API}/user`).then(r => r.json()),
				fetch(`${API}/projects`).then(r => r.json()),
				fetch(`${API}/edges?global_only=true`).then(r => r.json())
			]);

			stats = statusRes.stats;
			user = userRes;
			projects = projectsRes.items;
			globalEdges = edgesRes.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load data';
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="loading">
		<div class="loading-text">Loading mind...</div>
	</div>
{:else if error}
	<div class="error-state">
		<p class="error-message">Failed to connect to Mind API</p>
		<p class="error-detail">{error}</p>
		<p class="error-hint">Make sure the Mind server is running: <code>uv run mind serve</code></p>
	</div>
{:else}
	<section class="hero">
		<div class="hero-content">
			<h1 class="hero-primary">{recencyText}</h1>
			<p class="hero-secondary">{depthText}</p>
			<button class="btn btn-primary btn-lg">{ctaText}</button>
		</div>
	</section>

	<section class="projects-section">
		<h2 class="section-title">Your Projects</h2>

		{#if projects.length === 0}
			<div class="empty-state">
				<p>No projects yet. Mind learns as you work.</p>
			</div>
		{:else}
			<div class="projects-grid">
				{#each projects as project}
					<a href="/projects/{project.id}" class="project-card card card-interactive">
						<div class="project-header">
							<h3 class="project-name">{project.name}</h3>
							{#if project.last_session_date}
								<span class="project-recency">{formatProjectRecency(project)}</span>
							{:else}
								<span class="badge badge-active">NEW</span>
							{/if}
						</div>
						{#if project.last_session_summary}
							<p class="project-summary">"{project.last_session_summary}"</p>
						{/if}
					</a>
				{/each}
			</div>
		{/if}
	</section>

	{#if globalEdges.length > 0}
		<section class="edges-section">
			<h2 class="section-title">Global Edges</h2>
			<div class="edges-list">
				{#each globalEdges.slice(0, 3) as edge}
					<div class="edge-item">
						<span class="edge-icon">!</span>
						<span class="edge-title">{edge.title}</span>
					</div>
				{/each}
				{#if globalEdges.length > 3}
					<a href="/edges" class="edges-more">View all {globalEdges.length} edges</a>
				{/if}
			</div>
		</section>
	{/if}
{/if}

<style>
	.loading, .error-state {
		text-align: center;
		padding: 4rem 2rem;
	}

	.error-message {
		color: var(--color-error);
		font-size: var(--text-xl);
		margin-bottom: 0.5rem;
	}

	.error-detail {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		margin-bottom: 1rem;
	}

	.error-hint code {
		background: var(--bg-tertiary);
		padding: 0.25rem 0.5rem;
	}

	.hero {
		text-align: center;
		padding: 4rem 0;
	}

	.hero-content {
		position: relative;
		z-index: 1;
	}

	.hero-primary {
		font-size: 2rem;
		font-weight: 400;
		margin-bottom: 0.75rem;
		color: var(--text-primary);
	}

	.hero-secondary {
		color: var(--text-secondary);
		margin-bottom: 2rem;
		font-size: var(--text-base);
	}

	.projects-section {
		margin-top: 2rem;
	}

	.projects-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.project-card {
		display: block;
		text-decoration: none;
		color: inherit;
	}

	.project-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.project-name {
		font-family: var(--font-serif);
		font-size: var(--text-lg);
		font-weight: 400;
	}

	.project-recency {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
	}

	.project-summary {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		font-style: italic;
	}

	.edges-section {
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 1px solid var(--border);
	}

	.edges-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.edge-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
	}

	.edge-icon {
		color: var(--color-edges);
		font-weight: 600;
	}

	.edge-title {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	.edges-more {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin-top: 0.5rem;
	}

	.edges-more:hover {
		color: var(--text-primary);
	}
</style>
