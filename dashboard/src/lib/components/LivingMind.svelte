<script lang="ts">
	import { onMount } from 'svelte';
	import type { Project, Stats } from '$lib/api';

	interface Props {
		projects: Project[];
		stats: Stats | null;
	}

	let { projects, stats }: Props = $props();

	interface Node {
		id: string;
		label: string;
		type: 'decision' | 'issue' | 'edge' | 'episode' | 'project';
		x: number;
		y: number;
		size: number;
		opacity: number;
		delay: number;
	}

	interface Connection {
		from: Node;
		to: Node;
		delay: number;
	}

	let nodes = $state<Node[]>([]);
	let connections = $state<Connection[]>([]);
	let containerWidth = $state(600);
	let containerHeight = $state(280);

	// Generate nodes based on real data
	function generateNodes(): Node[] {
		const result: Node[] = [];
		const centerX = containerWidth / 2;
		const centerY = containerHeight / 2;

		// Add project nodes (larger, more central)
		projects.forEach((project, i) => {
			const angle = (i / Math.max(projects.length, 1)) * Math.PI * 2 - Math.PI / 2;
			const radius = 60 + Math.random() * 20;

			result.push({
				id: project.id,
				label: project.name.slice(0, 12),
				type: 'project',
				x: centerX + Math.cos(angle) * radius,
				y: centerY + Math.sin(angle) * radius,
				size: 12,
				opacity: 0.9,
				delay: i * 0.3
			});
		});

		// Add ambient nodes representing decisions, issues, edges
		const nodeTypes: Array<'decision' | 'issue' | 'edge' | 'episode'> = [
			'decision',
			'issue',
			'edge',
			'episode'
		];

		// Create ambient nodes based on stats
		if (stats) {
			const counts = {
				decision: Math.min(stats.decisions, 8),
				issue: Math.min(stats.issues, 5),
				edge: Math.min(stats.edges, 4),
				episode: Math.min(stats.episodes, 6)
			};

			nodeTypes.forEach((type) => {
				for (let i = 0; i < counts[type]; i++) {
					const angle = Math.random() * Math.PI * 2;
					const radius = 80 + Math.random() * 80;

					result.push({
						id: `${type}-${i}`,
						label: '',
						type,
						x: centerX + Math.cos(angle) * radius,
						y: centerY + Math.sin(angle) * radius,
						size: 4 + Math.random() * 4,
						opacity: 0.2 + Math.random() * 0.4,
						delay: Math.random() * 3
					});
				}
			});
		}

		return result;
	}

	// Generate connections between nodes
	function generateConnections(nodeList: Node[]): Connection[] {
		const result: Connection[] = [];
		const projectNodes = nodeList.filter((n) => n.type === 'project');
		const otherNodes = nodeList.filter((n) => n.type !== 'project');

		// Connect some ambient nodes to projects
		otherNodes.forEach((node, i) => {
			if (projectNodes.length > 0 && Math.random() > 0.6) {
				const project = projectNodes[Math.floor(Math.random() * projectNodes.length)];
				result.push({
					from: node,
					to: project,
					delay: Math.random() * 2
				});
			}
		});

		// Some ambient-to-ambient connections
		for (let i = 0; i < Math.min(otherNodes.length / 3, 5); i++) {
			const a = otherNodes[Math.floor(Math.random() * otherNodes.length)];
			const b = otherNodes[Math.floor(Math.random() * otherNodes.length)];
			if (a && b && a.id !== b.id) {
				result.push({
					from: a,
					to: b,
					delay: Math.random() * 2
				});
			}
		}

		return result;
	}

	function getNodeColor(type: Node['type']): string {
		switch (type) {
			case 'decision':
				return 'var(--color-decisions)';
			case 'issue':
				return 'var(--color-issues)';
			case 'edge':
				return 'var(--color-edges)';
			case 'episode':
				return 'var(--color-episodes)';
			case 'project':
				return 'var(--color-sessions)';
			default:
				return 'var(--text-tertiary)';
		}
	}

	onMount(() => {
		nodes = generateNodes();
		connections = generateConnections(nodes);
	});

	// Regenerate when data changes
	$effect(() => {
		if (projects || stats) {
			nodes = generateNodes();
			connections = generateConnections(nodes);
		}
	});
</script>

<div class="living-mind" bind:clientWidth={containerWidth} bind:clientHeight={containerHeight}>
	<svg width="100%" height="100%" viewBox="0 0 {containerWidth} {containerHeight}">
		<!-- Connections -->
		<g class="connections">
			{#each connections as conn}
				<line
					x1={conn.from.x}
					y1={conn.from.y}
					x2={conn.to.x}
					y2={conn.to.y}
					stroke="var(--color-decisions)"
					stroke-opacity="0.1"
					stroke-width="1"
					class="connection"
					style="animation-delay: {conn.delay}s"
				/>
			{/each}
		</g>

		<!-- Nodes -->
		<g class="nodes">
			{#each nodes as node}
				<g
					class="node"
					style="animation-delay: {node.delay}s"
					transform="translate({node.x}, {node.y})"
				>
					<!-- Glow for larger nodes -->
					{#if node.size > 8}
						<circle
							r={node.size + 4}
							fill={getNodeColor(node.type)}
							opacity={node.opacity * 0.2}
							class="node-glow"
						/>
					{/if}

					<!-- Main circle -->
					<circle
						r={node.size}
						fill={getNodeColor(node.type)}
						opacity={node.opacity}
						class="node-circle"
					/>

					<!-- Label for larger nodes -->
					{#if node.label}
						<text
							y={node.size + 14}
							text-anchor="middle"
							class="node-label"
							fill="var(--text-secondary)"
							font-size="10"
						>
							{node.label}
						</text>
					{/if}
				</g>
			{/each}
		</g>
	</svg>
</div>

<style>
	.living-mind {
		width: 100%;
		height: 100%;
		position: relative;
	}

	svg {
		overflow: visible;
	}

	.node {
		animation: drift 10s ease-in-out infinite;
	}

	.node-glow {
		animation: breathe 4s ease-in-out infinite;
	}

	.node-circle {
		transition: opacity 0.3s ease;
	}

	.node:hover .node-circle {
		opacity: 1 !important;
	}

	.node-label {
		font-family: var(--font-mono);
		pointer-events: none;
		opacity: 0.8;
	}

	.connection {
		animation: pulse-connection 4s ease-in-out infinite;
	}

	/* Stagger animations */
	.node:nth-child(1) {
		animation-delay: 0s;
	}
	.node:nth-child(2) {
		animation-delay: 0.7s;
	}
	.node:nth-child(3) {
		animation-delay: 1.4s;
	}
	.node:nth-child(4) {
		animation-delay: 2.1s;
	}
	.node:nth-child(5) {
		animation-delay: 2.8s;
	}
	.node:nth-child(6) {
		animation-delay: 0.3s;
	}
	.node:nth-child(7) {
		animation-delay: 1s;
	}
	.node:nth-child(8) {
		animation-delay: 1.7s;
	}
	.node:nth-child(9) {
		animation-delay: 2.4s;
	}
	.node:nth-child(10) {
		animation-delay: 3.1s;
	}

	@keyframes drift {
		0%,
		100% {
			transform: translate(var(--x, 0), var(--y, 0));
		}
		33% {
			transform: translate(calc(var(--x, 0) + 3px), calc(var(--y, 0) - 2px));
		}
		66% {
			transform: translate(calc(var(--x, 0) - 2px), calc(var(--y, 0) + 3px));
		}
	}
</style>
