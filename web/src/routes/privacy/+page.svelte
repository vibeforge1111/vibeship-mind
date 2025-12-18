<script lang="ts">
</script>

<div class="legal-page">
	<h1>Privacy Policy</h1>
	<p class="last-updated">Last updated: December 2024</p>

	<section>
		<h2>1. Introduction</h2>
		<p>This Privacy Policy explains how Mind ("the Software") handles your information. We are committed to protecting your privacy and being transparent about our practices.</p>
	</section>

	<section>
		<h2>2. Data Collection - The Software</h2>
		<p><strong>Mind does not collect any personal data.</strong> The Software runs entirely on your local machine. All memories, decisions, learnings, and project data are stored locally in your project's <code>.mind/</code> directory. This data never leaves your machine and is never transmitted to us or any third party.</p>
	</section>

	<section>
		<h2>3. Local-First Architecture</h2>
		<p>Mind is designed with privacy at its core:</p>
		<ul>
			<li>All data is stored locally in plain markdown files</li>
			<li>No cloud storage or remote databases</li>
			<li>No accounts or authentication required</li>
			<li>No telemetry or usage tracking in the Software itself</li>
			<li>You have complete control over your data</li>
		</ul>
	</section>

	<section>
		<h2>4. Website Analytics</h2>
		<p>This website (mind.vibeship.co) uses Amplitude for basic analytics to help us understand how visitors use the site. This may collect:</p>
		<ul>
			<li>Page views and navigation patterns</li>
			<li>General geographic location (country/region level)</li>
			<li>Device type and browser information</li>
			<li>Referral sources</li>
		</ul>
		<p>We do not collect names, email addresses, or other personally identifiable information through website analytics.</p>
	</section>

	<section>
		<h2>5. Third-Party Integrations</h2>
		<p>Mind is designed to integrate with AI coding assistants (such as Claude Code) via the Model Context Protocol (MCP). When you use Mind with these services:</p>
		<ul>
			<li>Data is shared directly between your local Mind installation and the AI assistant</li>
			<li>This sharing happens locally on your machine</li>
			<li>The AI assistant's handling of this data is governed by their privacy policies</li>
			<li>We do not receive or process any data shared with AI assistants</li>
		</ul>
	</section>

	<section>
		<h2>6. Data You Control</h2>
		<p>Since all Mind data is stored locally, you have complete control:</p>
		<ul>
			<li><strong>Access:</strong> Your data is in readable markdown files in <code>.mind/</code></li>
			<li><strong>Portability:</strong> Copy or move your <code>.mind/</code> folder freely</li>
			<li><strong>Deletion:</strong> Delete the <code>.mind/</code> folder to remove all data</li>
			<li><strong>Backup:</strong> Include <code>.mind/</code> in your regular backups or version control</li>
		</ul>
	</section>

	<section>
		<h2>7. Open Source Transparency</h2>
		<p>Mind is open source software licensed under Apache 2.0. You can inspect exactly what the code does at any time by reviewing our <a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank">GitHub repository</a>. This transparency is fundamental to our privacy commitment.</p>
	</section>

	<section>
		<h2>8. Children's Privacy</h2>
		<p>Mind is not directed at children under 13. We do not knowingly collect any information from children.</p>
	</section>

	<section>
		<h2>9. Changes to This Policy</h2>
		<p>We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated revision date. We encourage you to review this policy periodically.</p>
	</section>

	<section>
		<h2>10. Contact Us</h2>
		<p>If you have questions about this Privacy Policy, please open an issue on our <a href="https://github.com/vibeforge1111/vibeship-mind" target="_blank">GitHub repository</a> or contact us at <a href="https://x.com/vibeshipco" target="_blank">@vibeshipco</a>.</p>
	</section>
</div>

<style>
	.legal-page {
		max-width: 700px;
		margin: 0 auto;
		padding: var(--space-8) var(--space-4);
	}

	h1 {
		font-size: var(--text-3xl);
		margin-bottom: var(--space-2);
	}

	.last-updated {
		color: var(--text-tertiary);
		font-size: var(--text-sm);
		margin-bottom: var(--space-8);
	}

	section {
		margin-bottom: var(--space-6);
	}

	h2 {
		font-size: var(--text-lg);
		margin-bottom: var(--space-2);
		color: var(--text-primary);
	}

	p {
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: var(--space-2);
	}

	ul {
		color: var(--text-secondary);
		line-height: 1.6;
		margin-top: var(--space-2);
		padding-left: var(--space-6);
	}

	li {
		margin-bottom: var(--space-1);
	}

	code {
		background: var(--bg-secondary);
		padding: 0.1em 0.3em;
		border-radius: 3px;
		font-size: 0.9em;
	}

	strong {
		color: var(--text-primary);
	}

	a {
		color: var(--green-dim);
	}

	a:hover {
		text-decoration: underline;
	}
</style>
