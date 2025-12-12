<script lang="ts">
	import { onMount } from 'svelte';
	import {
		getStatus,
		getUser,
		getProjects,
		getEdges,
		formatRecencyText,
		getCtaText,
		type Project,
		type User,
		type Stats,
		type SharpEdge
	} from '$lib/api';
	import LivingMind from '$lib/components/LivingMind.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);

	let user = $state<User | null>(null);
	let stats = $state<Stats | null>(null);
	let projects = $state<Project[]>([]);
	let globalEdges = $state<SharpEdge[]>([]);

	// Computed values
	let recencyText = $derived(formatRecencyText(user?.last_session ?? null));
	let ctaText = $derived(getCtaText(user, false)); // TODO: check for active session
	let depthText = $derived(getDepthText(user, stats));

	function getDepthText(user: User | null, stats: Stats | null): string {
		if (!user || !stats || user.total_sessions === 0) {
			return 'Ready to start building context.';
		}

		const parts: string[] = [];

		if (user.total_sessions > 0) {
			parts.push(`${user.total_sessions} sessions`);
		}

		if (stats.decisions > 0) {
			parts.push(`${stats.decisions} decisions`);
		}

		if (user.first_session) {
			const firstDate = new Date(user.first_session);
			const now = new Date();
			const months = Math.floor((now.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24 * 30));

			if (months >= 1) {
				const monthName = firstDate.toLocaleDateString('en-US', { month: 'long' });
				parts.push(`since ${monthName}`);
			}
		}

		return parts.join(' · ');
	}

	onMount(async () => {
		try {
			const [statusRes, userRes, projectsRes, edgesRes] = await Promise.all([
				getStatus(),
				getUser(),
				getProjects(),
				getEdges(undefined, true)
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

	function formatProjectRecency(project: Project): string {
		if (!project.last_session_date) return '';
		const date = new Date(project.last_session_date);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return 'today';
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		return `${Math.floor(diffDays / 7)} weeks ago`;
	}
</script>

{#if loading}
	<div class="loading">
		<div class="loading-dots">
			<div class="loading-dot"></div>
			<div class="loading-dot"></div>
			<div class="loading-dot"></div>
		</div>
		<div class="loading-text">Loading mind...</div>
	</div>
{:else if error}
	<div class="error-state">
		<p class="error-message">Failed to connect to Mind API</p>
		<p class="error-detail">{error}</p>
		<p class="error-hint">Make sure the Mind server is running: <code>uv run mind serve</code></p>
	</div>
{:else}
	<!-- Hero Section -->
	<section class="hero">
		<div class="hero-glow"></div>

		<div class="hero-viz">
			<LivingMind {projects} {stats} />
		</div>

		<div class="hero-content">
			<h1 class="hero-primary">{recencyText}</h1>
			<p class="hero-secondary">{depthText}</p>

			{#if user && user.total_sessions > 0 && projects.length > 0}
				{@const lastProject = projects.find((p) => p.last_session_date)}
				{#if lastProject?.last_session_summary}
					<div class="hero-readiness">
						<div class="readiness-item">
							<span class="readiness-label">Last time:</span>
							<span class="readiness-value">{lastProject.last_session_summary}</span>
						</div>
						{#if lastProject.last_session_next_step}
							<div class="readiness-item">
								<span class="readiness-label">Next step:</span>
								<span class="readiness-value accent"
									>"{lastProject.last_session_next_step}"</span
								>
							</div>
						{/if}
					</div>
				{/if}
			{/if}

			<button class="btn btn-primary btn-lg hero-cta">
				{ctaText}
			</button>
		</div>
	</section>

	<!-- Projects Section -->
	<section class="projects-section">
		<h2 class="section-title">Your Projects</h2>

		{#if projects.length === 0}
			<div class="empty-state">
				<p class="empty-state-title">No projects yet.</p>
				<p class="empty-state-description">Mind learns as you work.</p>
				<button class="btn btn-primary">Start First Project</button>
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

						<div class="project-stats">
							<!-- Stats would come from separate API call per project, simplified for now -->
							<span class="stat-item">
								<span class="stat-dot stat-dot-decision"></span>
								decisions
							</span>
							<span class="stat-item">
								<span class="stat-dot stat-dot-issue"></span>
								issues
							</span>
							<span class="stat-item">
								<span class="stat-dot stat-dot-edge"></span>
								edges
							</span>
						</div>

						{#if project.last_session_summary}
							<div class="project-context">
								<div class="context-row">
									<span class="context-label">Last:</span>
									<span class="context-value truncate"
										>"{project.last_session_summary}"</span
									>
								</div>
								{#if project.last_session_next_step}
									<div class="context-row">
										<span class="context-label">Next:</span>
										<span class="context-value accent truncate"
											>"{project.last_session_next_step}"</span
										>
									</div>
								{/if}
							</div>
						{/if}
					</a>
				{/each}

				<button class="project-card card new-project">
					<span class="new-project-icon">+</span>
					<span class="new-project-text">New Project</span>
				</button>
			</div>
		{/if}
	</section>

	<!-- Utility Row -->
	<section class="utility-row">
		<a href="/edges" class="utility-item">
			<span class="utility-dot" style="background: var(--color-edges)"></span>
			Global Edges ({globalEdges.length})
		</a>
		<button class="utility-item">
			<span class="utility-icon">🔍</span>
			Search All
		</button>
		<button class="utility-item">
			<span class="utility-icon">📤</span>
			Export
		</button>
	</section>
{/if}

<style>
	/* Hero Section */
	.hero {
		position: relative;
		text-align: center;
		padding: var(--space-8) 0 var(--space-12);
	}

	.hero-glow {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 400px;
		height: 400px;
		background: var(--glow-center);
		pointer-events: none;
		animation: breathe 6s ease-in-out infinite;
	}

	.hero-viz {
		position: relative;
		height: 280px;
		margin-bottom: var(--space-6);
	}

	.hero-content {
		position: relative;
		z-index: 1;
	}

	.hero-primary {
		font-family: var(--font-serif);
		font-size: var(--text-2xl);
		font-style: italic;
		font-weight: 400;
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.hero-secondary {
		font-size: var(--text-base);
		color: var(--text-secondary);
		margin-bottom: var(--space-6);
	}

	.hero-readiness {
		max-width: 400px;
		margin: 0 auto var(--space-6);
		padding: var(--space-4);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		text-align: left;
	}

	.readiness-item {
		display: flex;
		gap: var(--space-2);
		font-size: var(--text-sm);
		margin-bottom: var(--space-2);
	}

	.readiness-item:last-child {
		margin-bottom: 0;
	}

	.readiness-label {
		color: var(--text-tertiary);
		flex-shrink: 0;
	}

	.readiness-value {
		color: var(--text-secondary);
	}

	.readiness-value.accent {
		color: var(--text-accent);
	}

	.hero-cta {
		margin-top: var(--space-4);
	}

	/* Projects Section */
	.projects-section {
		margin-top: var(--space-12);
	}

	.section-title {
		font-size: var(--text-xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--text-tertiary);
		margin-bottom: var(--space-4);
	}

	.projects-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.project-card {
		text-decoration: none;
		color: inherit;
	}

	.project-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-3);
	}

	.project-name {
		font-size: var(--text-lg);
		font-weight: 500;
		color: var(--text-primary);
	}

	.project-recency {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	.project-stats {
		display: flex;
		gap: var(--space-4);
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-3);
	}

	.stat-item {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.stat-dot {
		width: 6px;
		height: 6px;
		border-radius: var(--radius-full);
	}

	.stat-dot-decision {
		background: var(--color-decisions);
	}
	.stat-dot-issue {
		background: var(--color-issues);
	}
	.stat-dot-edge {
		background: var(--color-edges);
	}

	.project-context {
		padding-top: var(--space-3);
		border-top: 1px solid var(--border-subtle);
	}

	.context-row {
		display: flex;
		gap: var(--space-2);
		font-size: var(--text-sm);
		margin-bottom: var(--space-1);
	}

	.context-row:last-child {
		margin-bottom: 0;
	}

	.context-label {
		color: var(--text-tertiary);
		flex-shrink: 0;
	}

	.context-value {
		color: var(--text-secondary);
	}

	.context-value.accent {
		color: var(--text-accent);
	}

	.new-project {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-6);
		border: 1px dashed var(--border);
		background: transparent;
		cursor: pointer;
		color: var(--text-tertiary);
		transition: all var(--transition-fast);
	}

	.new-project:hover {
		border-color: var(--border-strong);
		color: var(--text-secondary);
	}

	.new-project-icon {
		font-size: var(--text-xl);
	}

	.new-project-text {
		font-size: var(--text-sm);
	}

	/* Utility Row */
	.utility-row {
		display: flex;
		justify-content: center;
		gap: var(--space-6);
		margin-top: var(--space-12);
		padding-top: var(--space-6);
		border-top: 1px solid var(--border-subtle);
	}

	.utility-item {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		background: none;
		border: none;
		cursor: pointer;
		transition: color var(--transition-fast);
		text-decoration: none;
	}

	.utility-item:hover {
		color: var(--text-secondary);
	}

	.utility-dot {
		width: 8px;
		height: 8px;
		border-radius: var(--radius-full);
	}

	.utility-icon {
		font-size: var(--text-base);
	}

	/* Error State */
	.error-state {
		text-align: center;
		padding: var(--space-12);
	}

	.error-message {
		font-size: var(--text-lg);
		color: var(--color-error);
		margin-bottom: var(--space-2);
	}

	.error-detail {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		margin-bottom: var(--space-4);
	}

	.error-hint {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	.error-hint code {
		background: var(--bg-tertiary);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}
</style>
