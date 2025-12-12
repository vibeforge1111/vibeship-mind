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
		return parts.join(' · ') || 'Ready to start building context.';
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
		<div class="mind-glow"></div>
		<div class="hero-content">
			<h1 class="hero-primary">{recencyText}</h1>
			<p class="hero-secondary">{depthText}</p>
			<button class="btn btn-primary btn-lg hero-cta">{ctaText}</button>
		</div>
	</section>

	<section class="projects-section">
		<h2 class="section-title">Your Projects</h2>

		{#if projects.length === 0}
			<div class="empty-state">
				<p>No projects yet. Mind learns as you work.</p>
			</div>
		{:else}
			<div class="projects-list">
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

	<section class="utility-row">
		<a href="/edges" class="utility-item">
			Global Edges ({globalEdges.length})
		</a>
	</section>
{/if}

<style>
	.loading, .error-state {
		text-align: center;
		padding: 4rem 2rem;
	}

	.loading-text {
		color: var(--text-secondary, #888);
	}

	.error-message {
		color: var(--color-error, #e53935);
		font-size: 1.25rem;
		margin-bottom: 0.5rem;
	}

	.error-detail {
		color: var(--text-tertiary, #666);
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.error-hint code {
		background: var(--bg-tertiary, #f5f5f5);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.hero {
		text-align: center;
		padding: 3rem 0;
		position: relative;
	}

	.mind-glow {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 200px;
		height: 200px;
		border-radius: 50%;
		background: radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%);
		animation: breathe 4s ease-in-out infinite;
		pointer-events: none;
		z-index: 0;
	}

	@keyframes breathe {
		0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
		50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.8; }
	}

	.hero-content {
		position: relative;
		z-index: 1;
	}

	.hero-primary {
		font-size: 1.75rem;
		font-style: italic;
		margin-bottom: 0.5rem;
	}

	.hero-secondary {
		color: var(--text-secondary, #888);
		margin-bottom: 1.5rem;
	}

	.hero-cta {
		padding: 0.75rem 2rem;
		background: var(--color-primary, #6366f1);
		color: white;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		font-size: 1rem;
	}

	.projects-section {
		margin-top: 2rem;
	}

	.section-title {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-tertiary, #666);
		margin-bottom: 1rem;
	}

	.projects-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.project-card {
		display: block;
		padding: 1rem;
		background: var(--bg-secondary, #1a1a1a);
		border: 1px solid var(--border, #333);
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.2s;
	}

	.project-card:hover {
		border-color: var(--border-strong, #555);
	}

	.project-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.project-name {
		font-size: 1.125rem;
		font-weight: 500;
	}

	.project-recency {
		font-size: 0.875rem;
		color: var(--text-tertiary, #666);
	}

	.project-summary {
		font-size: 0.875rem;
		color: var(--text-secondary, #888);
		font-style: italic;
	}

	.badge-active {
		background: var(--color-sessions, #10b981);
		color: white;
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		color: var(--text-tertiary, #666);
	}

	.utility-row {
		display: flex;
		justify-content: center;
		gap: 1.5rem;
		margin-top: 3rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--border-subtle, #222);
	}

	.utility-item {
		font-size: 0.875rem;
		color: var(--text-tertiary, #666);
		text-decoration: none;
	}

	.utility-item:hover {
		color: var(--text-secondary, #888);
	}
</style>
