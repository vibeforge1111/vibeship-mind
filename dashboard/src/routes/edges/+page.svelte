<script lang="ts">
	import { onMount } from 'svelte';
	import { getEdges, formatRelativeTime, type SharpEdge } from '$lib/api';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let edges = $state<SharpEdge[]>([]);
	let expandedItem = $state<string | null>(null);

	function toggleItem(id: string) {
		expandedItem = expandedItem === id ? null : id;
	}

	onMount(async () => {
		try {
			const res = await getEdges(undefined, true);
			edges = res.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load edges';
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="loading">
		<div class="loading-dots">
			<div class="loading-dot"></div>
			<div class="loading-dot"></div>
			<div class="loading-dot"></div>
		</div>
		<div class="loading-text">Loading edges...</div>
	</div>
{:else if error}
	<div class="error-state">
		<p class="error-message">Failed to load edges</p>
		<p class="error-detail">{error}</p>
		<a href="/" class="btn btn-primary">Back to Home</a>
	</div>
{:else}
	<header class="page-header">
		<div class="header-top">
			<a href="/" class="back-link">← Back to Home</a>
		</div>
		<h1 class="page-title">Global Sharp Edges</h1>
		<p class="page-subtitle">Gotchas and workarounds that apply across all projects</p>
	</header>

	{#if edges.length === 0}
		<div class="empty-state">
			<p class="empty-state-title">No global edges recorded.</p>
			<p class="empty-state-description">Sharp edges that aren't specific to any project will appear here.</p>
		</div>
	{:else}
		<div class="items-list">
			{#each edges as edge}
				<div class="item card edge-item" class:expanded={expandedItem === edge.id}>
					<button class="item-header" onclick={() => toggleItem(edge.id)}>
						<span class="item-toggle">{expandedItem === edge.id ? '▼' : '▶'}</span>
						<span class="edge-icon">⚠</span>
						<span class="item-title">{edge.title}</span>
						<span class="item-meta">{formatRelativeTime(edge.discovered_at)}</span>
					</button>

					{#if expandedItem === edge.id}
						<div class="item-body">
							<div class="item-section">
								<p class="section-content edge-description">{edge.description}</p>
							</div>

							{#if edge.symptoms.length > 0}
								<div class="item-section">
									<h4 class="section-label">Symptoms</h4>
									<ul class="symptoms-list">
										{#each edge.symptoms as symptom}
											<li>{symptom}</li>
										{/each}
									</ul>
								</div>
							{/if}

							{#if edge.root_cause}
								<div class="item-section">
									<h4 class="section-label">Root cause</h4>
									<p class="section-content">{edge.root_cause}</p>
								</div>
							{/if}

							<div class="item-section">
								<h4 class="section-label">Workaround</h4>
								<p class="section-content workaround">{edge.workaround}</p>
							</div>

							{#if edge.detection_patterns.length > 0}
								<div class="item-section">
									<h4 class="section-label">Detection patterns</h4>
									<div class="patterns-list">
										{#each edge.detection_patterns as pattern}
											<div class="pattern">
												<span class="pattern-type">{pattern.type}:</span>
												<code class="pattern-value">{pattern.pattern}</code>
											</div>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}

<style>
	.page-header {
		margin-bottom: var(--space-8);
	}

	.header-top {
		margin-bottom: var(--space-4);
	}

	.back-link {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
		text-decoration: none;
		transition: color var(--transition-fast);
	}

	.back-link:hover {
		color: var(--text-secondary);
	}

	.page-title {
		font-family: var(--font-serif);
		font-size: var(--text-2xl);
		font-style: italic;
		color: var(--text-primary);
		margin-bottom: var(--space-2);
	}

	.page-subtitle {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	/* Items List */
	.items-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.item {
		overflow: hidden;
	}

	.item-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-4);
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		border-left: 3px solid var(--color-edges);
	}

	.item-toggle {
		font-size: var(--text-xs);
		color: var(--text-tertiary);
		width: 12px;
		flex-shrink: 0;
	}

	.item-title {
		flex: 1;
		font-size: var(--text-base);
		color: var(--text-primary);
	}

	.item-meta {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	.item-body {
		padding: 0 var(--space-4) var(--space-4);
		padding-left: calc(var(--space-4) + 12px + var(--space-3));
		border-top: 1px solid var(--border-subtle);
	}

	.item-section {
		margin-top: var(--space-4);
	}

	.item-section:first-child {
		margin-top: 0;
		padding-top: var(--space-4);
	}

	.section-label {
		font-size: var(--text-xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--text-tertiary);
		margin-bottom: var(--space-2);
	}

	.section-content {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		line-height: 1.6;
	}

	/* Edge specific */
	.edge-icon {
		color: var(--color-edges);
		font-size: var(--text-lg);
	}

	.edge-description {
		color: var(--color-edges);
		font-weight: 500;
	}

	.workaround {
		background: color-mix(in srgb, var(--color-sessions) 10%, transparent);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		border-left: 2px solid var(--color-sessions);
	}

	.symptoms-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.symptoms-list li {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
		padding-left: var(--space-4);
		position: relative;
	}

	.symptoms-list li::before {
		content: '◦';
		position: absolute;
		left: 0;
		color: var(--text-tertiary);
	}

	.patterns-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.pattern {
		display: flex;
		gap: var(--space-2);
		font-size: var(--text-sm);
	}

	.pattern-type {
		color: var(--text-tertiary);
		text-transform: capitalize;
	}

	.pattern-value {
		font-family: var(--font-mono);
		background: var(--bg-tertiary);
		padding: 1px 4px;
		border-radius: var(--radius-sm);
	}
</style>
