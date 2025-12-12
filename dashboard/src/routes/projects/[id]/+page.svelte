<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import {
		getProject,
		getDecisions,
		getIssues,
		getEdges,
		getEpisodes,
		getSessions,
		formatRelativeTime,
		formatDuration,
		type Project,
		type Decision,
		type Issue,
		type SharpEdge,
		type Episode,
		type Session
	} from '$lib/api';

	let loading = $state(true);
	let error = $state<string | null>(null);

	let project = $state<Project | null>(null);
	let decisions = $state<Decision[]>([]);
	let issues = $state<Issue[]>([]);
	let edges = $state<SharpEdge[]>([]);
	let episodes = $state<Episode[]>([]);
	let sessions = $state<Session[]>([]);

	let activeTab = $state<'decisions' | 'issues' | 'edges' | 'episodes' | 'sessions'>('decisions');
	let expandedItem = $state<string | null>(null);
	let issueFilter = $state<'all' | 'open' | 'resolved'>('all');

	// Derived stats
	let openIssueCount = $derived(issues.filter((i) => i.status === 'open' || i.status === 'investigating').length);
	let resolvedIssueCount = $derived(issues.filter((i) => i.status === 'resolved').length);

	let filteredIssues = $derived(() => {
		if (issueFilter === 'open') return issues.filter((i) => i.status === 'open' || i.status === 'investigating' || i.status === 'blocked');
		if (issueFilter === 'resolved') return issues.filter((i) => i.status === 'resolved' || i.status === 'wont_fix');
		return issues;
	});

	// Stats summary
	let statsText = $derived(() => {
		const parts: string[] = [];
		if (decisions.length > 0) parts.push(`${decisions.length} decisions`);
		if (openIssueCount > 0) parts.push(`${openIssueCount} open issues`);
		if (edges.length > 0) parts.push(`${edges.length} edges`);
		if (sessions.length > 0) parts.push(`${sessions.length} sessions`);
		return parts.join(' · ');
	});

	function toggleItem(id: string) {
		expandedItem = expandedItem === id ? null : id;
	}

	function formatConfidence(confidence: number): string {
		const filled = Math.round(confidence * 5);
		return '●'.repeat(filled) + '○'.repeat(5 - filled);
	}

	function getSeverityClass(severity: string): string {
		switch (severity) {
			case 'blocking':
				return 'severity-blocking';
			case 'major':
				return 'severity-major';
			default:
				return 'severity-minor';
		}
	}

	function getStatusClass(status: string): string {
		switch (status) {
			case 'open':
			case 'investigating':
			case 'blocked':
				return 'status-open';
			default:
				return 'status-resolved';
		}
	}

	onMount(async () => {
		const projectId = $page.params.id;

		if (!projectId) {
			error = 'No project ID provided';
			loading = false;
			return;
		}

		try {
			const [projectRes, decisionsRes, issuesRes, edgesRes, episodesRes, sessionsRes] =
				await Promise.all([
					getProject(projectId),
					getDecisions(projectId),
					getIssues(projectId),
					getEdges(projectId),
					getEpisodes(projectId),
					getSessions(projectId)
				]);

			project = projectRes;
			decisions = decisionsRes.items;
			issues = issuesRes.items;
			edges = edgesRes.items;
			episodes = episodesRes.items;
			sessions = sessionsRes.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load project';
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
		<div class="loading-text">Loading project...</div>
	</div>
{:else if error}
	<div class="error-state">
		<p class="error-message">Failed to load project</p>
		<p class="error-detail">{error}</p>
		<a href="/" class="btn btn-primary">Back to Home</a>
	</div>
{:else if project}
	<!-- Header -->
	<header class="project-header">
		<div class="header-top">
			<a href="/" class="back-link">← Back to Projects</a>
			<div class="header-right">
				<span class="project-name">{project.name}</span>
				{#if project.status === 'active'}
					<span class="badge badge-active">ACTIVE</span>
				{/if}
			</div>
		</div>

		<div class="header-meta">
			<span class="meta-stats">{statsText()}</span>
		</div>

		{#if project.last_session_summary}
			<div class="header-context">
				<span class="context-label">Last:</span>
				<span class="context-value">"{project.last_session_summary}"</span>
				{#if project.last_session_next_step}
					<span class="context-divider">·</span>
					<span class="context-label">Next:</span>
					<span class="context-value accent">"{project.last_session_next_step}"</span>
				{/if}
			</div>
		{/if}
	</header>

	<!-- Tabs -->
	<nav class="tabs">
		<button
			class="tab"
			class:active={activeTab === 'decisions'}
			onclick={() => (activeTab = 'decisions')}
		>
			Decisions
			{#if decisions.length > 0}
				<span class="tab-count">{decisions.length}</span>
			{/if}
		</button>
		<button
			class="tab"
			class:active={activeTab === 'issues'}
			onclick={() => (activeTab = 'issues')}
		>
			Issues
			{#if openIssueCount > 0}
				<span class="tab-count tab-count-issue">{openIssueCount}</span>
			{/if}
		</button>
		<button
			class="tab"
			class:active={activeTab === 'edges'}
			onclick={() => (activeTab = 'edges')}
		>
			Edges
			{#if edges.length > 0}
				<span class="tab-count tab-count-edge">{edges.length}</span>
			{/if}
		</button>
		<button
			class="tab"
			class:active={activeTab === 'episodes'}
			onclick={() => (activeTab = 'episodes')}
		>
			Episodes
			{#if episodes.length > 0}
				<span class="tab-count tab-count-episode">{episodes.length}</span>
			{/if}
		</button>
		<button
			class="tab"
			class:active={activeTab === 'sessions'}
			onclick={() => (activeTab = 'sessions')}
		>
			Sessions
			{#if sessions.length > 0}
				<span class="tab-count tab-count-session">{sessions.length}</span>
			{/if}
		</button>
	</nav>

	<!-- Tab Content -->
	<div class="tab-content">
		<!-- Decisions Tab -->
		{#if activeTab === 'decisions'}
			{#if decisions.length === 0}
				<div class="empty-state">
					<p class="empty-state-title">No decisions recorded yet.</p>
					<p class="empty-state-description">As you make choices, Mind remembers why.</p>
				</div>
			{:else}
				<div class="items-list">
					{#each decisions as decision}
						<div class="item card decision-item" class:expanded={expandedItem === decision.id}>
							<button class="item-header" onclick={() => toggleItem(decision.id)}>
								<span class="item-toggle">{expandedItem === decision.id ? '▼' : '▶'}</span>
								<span class="item-title">{decision.title}</span>
								<span class="item-meta">{formatRelativeTime(decision.created_at)}</span>
							</button>

							{#if expandedItem === decision.id}
								<div class="item-body">
									{#if decision.context}
										<div class="item-section">
											<h4 class="section-label">Context</h4>
											<p class="section-content">{decision.context}</p>
										</div>
									{/if}

									{#if decision.reasoning}
										<div class="item-section">
											<h4 class="section-label">Reasoning</h4>
											<p class="section-content">{decision.reasoning}</p>
										</div>
									{/if}

									{#if decision.alternatives.length > 0}
										<div class="item-section">
											<h4 class="section-label">Alternatives considered</h4>
											<ul class="alternatives-list">
												{#each decision.alternatives as alt}
													<li>
														<span class="alt-option">{alt.option}</span>
														<span class="alt-reason">→ {alt.rejected_because}</span>
													</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if decision.revisit_if}
										<div class="item-section">
											<h4 class="section-label">Revisit if</h4>
											<p class="section-content">{decision.revisit_if}</p>
										</div>
									{/if}

									{#if decision.related_issues.length > 0 || decision.related_edges.length > 0}
										<div class="item-section">
											<h4 class="section-label">Related</h4>
											<div class="related-items">
												{#each decision.related_issues as issueId}
													<span class="related-badge related-issue">Issue</span>
												{/each}
												{#each decision.related_edges as edgeId}
													<span class="related-badge related-edge">Edge</span>
												{/each}
											</div>
										</div>
									{/if}

									<div class="item-footer">
										<span class="confidence" title="Confidence: {Math.round(decision.confidence * 100)}%">
											{formatConfidence(decision.confidence)}
										</span>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- Issues Tab -->
		{#if activeTab === 'issues'}
			{#if issues.length === 0}
				<div class="empty-state">
					<p class="empty-state-title">No issues tracked.</p>
					<p class="empty-state-description">Problems you work through will appear here.</p>
				</div>
			{:else}
				<div class="filter-bar">
					<button
						class="filter-btn"
						class:active={issueFilter === 'all'}
						onclick={() => (issueFilter = 'all')}
					>
						All
					</button>
					<button
						class="filter-btn"
						class:active={issueFilter === 'open'}
						onclick={() => (issueFilter = 'open')}
					>
						Open
						{#if openIssueCount > 0}
							<span class="filter-count">{openIssueCount}</span>
						{/if}
					</button>
					<button
						class="filter-btn"
						class:active={issueFilter === 'resolved'}
						onclick={() => (issueFilter = 'resolved')}
					>
						Resolved
					</button>
				</div>

				<div class="items-list">
					{#each filteredIssues() as issue}
						<div class="item card issue-item" class:expanded={expandedItem === issue.id}>
							<button class="item-header" onclick={() => toggleItem(issue.id)}>
								<span class="item-toggle">{expandedItem === issue.id ? '▼' : '▶'}</span>
								<span class="item-title">{issue.title}</span>
								<span class="status-badge {getStatusClass(issue.status)}">{issue.status.toUpperCase()}</span>
								<span class="item-meta">{formatRelativeTime(issue.created_at)}</span>
							</button>

							{#if expandedItem === issue.id}
								<div class="item-body">
									{#if issue.symptoms.length > 0}
										<div class="item-section">
											<h4 class="section-label">Symptoms</h4>
											<ul class="symptoms-list">
												{#each issue.symptoms as symptom}
													<li>{symptom}</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if issue.current_theory}
										<div class="item-section">
											<h4 class="section-label">Current theory</h4>
											<p class="section-content">{issue.current_theory}</p>
										</div>
									{/if}

									{#if issue.attempts.length > 0}
										<div class="item-section">
											<h4 class="section-label">Attempts</h4>
											<div class="attempts-list">
												{#each issue.attempts as attempt, i}
													<div class="attempt">
														<span class="attempt-num">{i + 1}.</span>
														<span class="attempt-what">{attempt.what}</span>
														<span class="attempt-result">{attempt.result === 'success' ? '✓' : '✗'} {attempt.learned || attempt.result}</span>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									{#if issue.blocked_by}
										<div class="item-section">
											<h4 class="section-label">Blocked by</h4>
											<p class="section-content">{issue.blocked_by}</p>
										</div>
									{/if}

									{#if issue.resolution}
										<div class="item-section">
											<h4 class="section-label">Resolution</h4>
											<p class="section-content resolution">{issue.resolution}</p>
										</div>
									{/if}

									<div class="item-footer">
										<span class="severity-badge {getSeverityClass(issue.severity)}">{issue.severity.toUpperCase()}</span>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- Edges Tab -->
		{#if activeTab === 'edges'}
			{#if edges.length === 0}
				<div class="empty-state">
					<p class="empty-state-title">No sharp edges recorded.</p>
					<p class="empty-state-description">Gotchas and workarounds will appear here.</p>
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

		<!-- Episodes Tab -->
		{#if activeTab === 'episodes'}
			{#if episodes.length === 0}
				<div class="empty-state">
					<p class="empty-state-title">No episodes yet.</p>
					<p class="empty-state-description">Significant sessions become stories over time.</p>
				</div>
			{:else}
				<div class="tab-intro">
					<h3>Episodes</h3>
					<p class="intro-subtitle">"The significant moments"</p>
				</div>

				<div class="items-list">
					{#each episodes as episode}
						<div class="item card episode-item" class:expanded={expandedItem === episode.id}>
							<button class="item-header" onclick={() => toggleItem(episode.id)}>
								<span class="item-toggle">{expandedItem === episode.id ? '▼' : '▶'}</span>
								<span class="item-title">{episode.title}</span>
								<span class="item-meta">{formatRelativeTime(episode.created_at)}</span>
							</button>

							{#if expandedItem === episode.id}
								<div class="item-body">
									<div class="item-section">
										<p class="episode-quote">"{episode.summary}"</p>
									</div>

									{#if episode.the_journey}
										<div class="item-section">
											<h4 class="section-label">What happened</h4>
											<p class="section-content">{episode.the_journey}</p>
										</div>
									{/if}

									{#if episode.outcome}
										<div class="item-section">
											<h4 class="section-label">Outcome</h4>
											<p class="section-content">{episode.outcome}</p>
										</div>
									{/if}

									{#if episode.lessons_learned.length > 0}
										<div class="item-section">
											<h4 class="section-label">Lessons learned</h4>
											<ul class="lessons-list">
												{#each episode.lessons_learned as lesson}
													<li>{lesson}</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if episode.artifacts_created.length > 0}
										<div class="item-section">
											<h4 class="section-label">Artifacts created</h4>
											<div class="artifacts-list">
												{#each episode.artifacts_created as artifact}
													<span class="artifact-badge">{artifact}</span>
												{/each}
											</div>
										</div>
									{/if}

									{#if episode.mood}
										<div class="item-footer">
											<span class="mood">Mood: {episode.mood}</span>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- Sessions Tab -->
		{#if activeTab === 'sessions'}
			{#if sessions.length === 0}
				<div class="empty-state">
					<p class="empty-state-title">No sessions yet.</p>
					<p class="empty-state-description">Your work history will appear here.</p>
				</div>
			{:else}
				<div class="items-list">
					{#each sessions as session, i}
						{@const isActive = !session.ended_at}
						<div
							class="item card session-item"
							class:active-session={isActive}
							class:expanded={expandedItem === session.id}
						>
							<button class="item-header" onclick={() => toggleItem(session.id)}>
								<span class="item-toggle">{expandedItem === session.id ? '▼' : '▶'}</span>
								<span class="session-date">{new Date(session.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
								{#if session.summary}
									<span class="item-title">· "{session.summary}"</span>
								{/if}
								{#if isActive}
									<span class="badge badge-active">ACTIVE</span>
								{:else}
									<span class="item-meta">{formatDuration(session.started_at, session.ended_at)}</span>
								{/if}
							</button>

							{#if expandedItem === session.id}
								<div class="item-body">
									{#if session.progress.length > 0}
										<div class="item-section">
											<h4 class="section-label">Progress</h4>
											<ul class="progress-list">
												{#each session.progress as item}
													<li>{item}</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if session.decisions_made.length > 0 || session.issues_resolved.length > 0 || session.issues_encountered.length > 0}
										<div class="item-section">
											<h4 class="section-label">Artifacts</h4>
											<div class="session-artifacts">
												{#if session.decisions_made.length > 0}
													<span class="artifact-stat decision-stat">
														{session.decisions_made.length} decisions made
													</span>
												{/if}
												{#if session.issues_resolved.length > 0}
													<span class="artifact-stat resolved-stat">
														{session.issues_resolved.length} issues resolved
													</span>
												{/if}
												{#if session.issues_encountered.length > 0}
													<span class="artifact-stat encountered-stat">
														{session.issues_encountered.length} issues encountered
													</span>
												{/if}
											</div>
										</div>
									{/if}

									{#if session.next_steps.length > 0}
										<div class="item-section">
											<h4 class="section-label">Next steps</h4>
											<ul class="next-steps-list">
												{#each session.next_steps as step}
													<li class="next-step">"{step}"</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if session.still_open.length > 0}
										<div class="item-section">
											<h4 class="section-label">Still open</h4>
											<ul class="open-list">
												{#each session.still_open as item}
													<li>{item}</li>
												{/each}
											</ul>
										</div>
									{/if}

									{#if session.mood}
										<div class="item-footer">
											<span class="mood">Mood: {session.mood}</span>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
{/if}

<style>
	/* Header */
	.project-header {
		margin-bottom: var(--space-6);
		padding-bottom: var(--space-6);
		border-bottom: 1px solid var(--border-subtle);
	}

	.header-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-3);
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

	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.project-name {
		font-family: var(--font-serif);
		font-size: var(--text-xl);
		font-style: italic;
		color: var(--text-primary);
	}

	.header-meta {
		margin-bottom: var(--space-3);
	}

	.meta-stats {
		font-size: var(--text-sm);
		color: var(--text-secondary);
	}

	.header-context {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		font-size: var(--text-sm);
	}

	.context-label {
		color: var(--text-tertiary);
	}

	.context-value {
		color: var(--text-secondary);
	}

	.context-value.accent {
		color: var(--text-accent);
	}

	.context-divider {
		color: var(--text-tertiary);
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: var(--space-1);
		margin-bottom: var(--space-6);
		border-bottom: 1px solid var(--border-subtle);
		padding-bottom: var(--space-1);
	}

	.tab {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.tab:hover {
		color: var(--text-secondary);
	}

	.tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--color-decisions);
	}

	.tab-count {
		font-size: var(--text-xs);
		padding: 2px 6px;
		border-radius: var(--radius-full);
		background: var(--bg-tertiary);
		color: var(--text-secondary);
	}

	.tab-count-issue {
		background: color-mix(in srgb, var(--color-issues) 20%, transparent);
		color: var(--color-issues);
	}

	.tab-count-edge {
		background: color-mix(in srgb, var(--color-edges) 20%, transparent);
		color: var(--color-edges);
	}

	.tab-count-episode {
		background: color-mix(in srgb, var(--color-episodes) 20%, transparent);
		color: var(--color-episodes);
	}

	.tab-count-session {
		background: color-mix(in srgb, var(--color-sessions) 20%, transparent);
		color: var(--color-sessions);
	}

	/* Filter Bar */
	.filter-bar {
		display: flex;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
	}

	.filter-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-full);
		color: var(--text-tertiary);
		font-size: var(--text-xs);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.filter-btn:hover {
		border-color: var(--border-strong);
		color: var(--text-secondary);
	}

	.filter-btn.active {
		background: var(--bg-tertiary);
		border-color: var(--border-strong);
		color: var(--text-primary);
	}

	.filter-count {
		padding: 0 4px;
		background: var(--color-issues);
		color: var(--bg-primary);
		border-radius: var(--radius-sm);
		font-size: 10px;
	}

	/* Tab Content */
	.tab-content {
		min-height: 300px;
	}

	.tab-intro {
		margin-bottom: var(--space-4);
	}

	.tab-intro h3 {
		font-size: var(--text-xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--text-tertiary);
		margin-bottom: var(--space-1);
	}

	.intro-subtitle {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		font-style: italic;
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
		margin-bottom: var(--space-4);
	}

	.item-section:last-child {
		margin-bottom: 0;
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

	.item-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-top: var(--space-3);
		margin-top: var(--space-3);
		border-top: 1px solid var(--border-subtle);
	}

	/* Decision specific */
	.decision-item .item-header {
		border-left: 3px solid var(--color-decisions);
	}

	.alternatives-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.alternatives-list li {
		display: flex;
		gap: var(--space-2);
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-2);
	}

	.alternatives-list li:last-child {
		margin-bottom: 0;
	}

	.alt-option {
		color: var(--text-primary);
	}

	.alt-reason {
		color: var(--text-tertiary);
	}

	.confidence {
		font-size: var(--text-sm);
		color: var(--color-decisions);
		letter-spacing: 2px;
	}

	.related-items {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.related-badge {
		font-size: var(--text-xs);
		padding: 2px 8px;
		border-radius: var(--radius-sm);
	}

	.related-issue {
		background: color-mix(in srgb, var(--color-issues) 20%, transparent);
		color: var(--color-issues);
	}

	.related-edge {
		background: color-mix(in srgb, var(--color-edges) 20%, transparent);
		color: var(--color-edges);
	}

	/* Issue specific */
	.issue-item .item-header {
		border-left: 3px solid var(--color-issues);
	}

	.status-badge {
		font-size: var(--text-xs);
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		font-weight: 500;
	}

	.status-open {
		background: color-mix(in srgb, var(--color-issues) 20%, transparent);
		color: var(--color-issues);
	}

	.status-resolved {
		background: var(--bg-tertiary);
		color: var(--text-tertiary);
	}

	.severity-badge {
		font-size: var(--text-xs);
		padding: 2px 8px;
		border-radius: var(--radius-sm);
	}

	.severity-blocking {
		background: color-mix(in srgb, var(--color-error) 20%, transparent);
		color: var(--color-error);
	}

	.severity-major {
		background: color-mix(in srgb, var(--color-issues) 20%, transparent);
		color: var(--color-issues);
	}

	.severity-minor {
		background: var(--bg-tertiary);
		color: var(--text-tertiary);
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

	.attempts-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.attempt {
		display: flex;
		gap: var(--space-2);
		font-size: var(--text-sm);
		padding: var(--space-2);
		background: var(--bg-tertiary);
		border-radius: var(--radius-sm);
	}

	.attempt-num {
		color: var(--text-tertiary);
		flex-shrink: 0;
	}

	.attempt-what {
		color: var(--text-secondary);
		flex: 1;
	}

	.attempt-result {
		color: var(--text-tertiary);
		flex-shrink: 0;
	}

	.resolution {
		color: var(--color-sessions);
	}

	/* Edge specific */
	.edge-item .item-header {
		border-left: 3px solid var(--color-edges);
	}

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

	/* Episode specific */
	.episode-item .item-header {
		border-left: 3px solid var(--color-episodes);
	}

	.episode-quote {
		font-style: italic;
		color: var(--color-episodes);
		font-size: var(--text-base);
		padding: var(--space-3);
		background: color-mix(in srgb, var(--color-episodes) 10%, transparent);
		border-radius: var(--radius-sm);
		margin-bottom: var(--space-4);
	}

	.lessons-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.lessons-list li {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-2);
		padding-left: var(--space-4);
		position: relative;
	}

	.lessons-list li::before {
		content: '◦';
		position: absolute;
		left: 0;
		color: var(--color-episodes);
	}

	.artifacts-list {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.artifact-badge {
		font-size: var(--text-xs);
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
	}

	.mood {
		font-size: var(--text-sm);
		color: var(--text-tertiary);
	}

	/* Session specific */
	.session-item .item-header {
		border-left: 3px solid var(--color-sessions);
	}

	.session-item.active-session .item-header {
		border-left-width: 4px;
	}

	.session-date {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		font-weight: 500;
		flex-shrink: 0;
	}

	.progress-list,
	.next-steps-list,
	.open-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.progress-list li,
	.open-list li {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin-bottom: var(--space-1);
		padding-left: var(--space-4);
		position: relative;
	}

	.progress-list li::before {
		content: '◦';
		position: absolute;
		left: 0;
		color: var(--color-sessions);
	}

	.open-list li::before {
		content: '○';
		position: absolute;
		left: 0;
		color: var(--text-tertiary);
	}

	.next-step {
		font-size: var(--text-sm);
		color: var(--text-accent);
		font-style: italic;
		margin-bottom: var(--space-1);
	}

	.session-artifacts {
		display: flex;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.artifact-stat {
		font-size: var(--text-sm);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}

	.decision-stat {
		background: color-mix(in srgb, var(--color-decisions) 15%, transparent);
		color: var(--color-decisions);
	}

	.resolved-stat {
		background: color-mix(in srgb, var(--color-sessions) 15%, transparent);
		color: var(--color-sessions);
	}

	.encountered-stat {
		background: color-mix(in srgb, var(--color-issues) 15%, transparent);
		color: var(--color-issues);
	}
</style>
