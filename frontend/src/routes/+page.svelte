<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';

	let prompt = $state('');
	let mode = $state('detailed');
	let loading = $state(false);
	let result = $state<{
		refined_prompt: string;
		intent: string;
		original_score: number;
		refined_score: number;
		improvements: string[];
	} | null>(null);
	let error = $state('');
	let showCopied = $state(false);

	const modes = [
		{ value: 'detailed', label: 'DETAILED' },
		{ value: 'concise', label: 'CONCISE' },
		{ value: 'structured', label: 'STRUCTURED' },
		{ value: 'multi_step', label: 'MULTI_STEP' }
	];

	const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	async function refine() {
		if (!prompt.trim()) return;

		loading = true;
		error = '';
		result = null;

		try {
			const response = await fetch(`${API_URL}/refine`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prompt, mode })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Something went wrong');
			}

			result = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to refine prompt';
		} finally {
			loading = false;
		}
	}

	async function copyToClipboard() {
		if (result?.refined_prompt) {
			await navigator.clipboard.writeText(result.refined_prompt);
			showCopied = true;
			setTimeout(() => showCopied = false, 2000);
		}
	}
</script>

<svelte:head>
	<title>Prompt Refinery</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
	<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
</svelte:head>

<main>
	<div class="container">
		<header>
			<div class="logo">
				<span class="logo-bracket">[</span>
				<span class="logo-text">PROMPT REFINERY</span>
				<span class="logo-bracket">]</span>
			</div>
			<span class="version">v1.0.0</span>
		</header>

		<div class="terminal">
			<div class="input-section">
				<label class="input-label">
					<span class="prompt-char">$</span>
					<span>Enter your prompt</span>
					<span class="cursor">_</span>
				</label>

				<div class="input-wrapper" class:focused={!loading}>
					<textarea
						bind:value={prompt}
						placeholder="write a python function to calculate fibonacci..."
						class="prompt-input"
						rows="4"
						disabled={loading}
						onfocus={() => {}}
					></textarea>
					<div class="input-glow"></div>
				</div>

				<div class="mode-section">
					<span class="mode-label">Refinement Mode:</span>
					<div class="mode-selector">
						{#each modes as m}
							<button
								class="mode-btn"
								class:active={mode === m.value}
								onclick={() => mode = m.value}
								disabled={loading}
							>
								{m.label}
							</button>
						{/each}
					</div>
				</div>

				<button
					class="refine-btn"
					onclick={refine}
					disabled={loading || !prompt.trim()}
				>
					{#if loading}
						<span class="spinner"></span>
						<span>PROCESSING</span>
						<span class="loading-dots">...</span>
					{:else}
						<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 2L2 7l10 5 10-5-10-5z"/>
							<path d="M2 17l10 5 10-5"/>
							<path d="M2 12l10 5 10-5"/>
						</svg>
						<span>REFINE PROMPT</span>
					{/if}
				</button>
			</div>

			{#if error}
				<div class="error-msg" transition:fade={{ duration: 200 }}>
					<svg class="error-icon" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
					</svg>
					<span>{error}</span>
				</div>
			{/if}

			{#if result}
				<div class="output-section" transition:fly={{ y: 30, duration: 400, easing: cubicOut }}>
					<div class="output-divider">
						<span class="divider-line"></span>
						<span class="divider-text">OUTPUT</span>
						<span class="divider-line"></span>
					</div>

					<div class="result-box">
						<div class="result-header">
							<span class="result-label">REFINED PROMPT</span>
							<span class="intent-badge">{result.intent}</span>
						</div>

						<div class="result-content">
							{result.refined_prompt}
						</div>

						<div class="result-actions">
							<button class="copy-btn" class:copied={showCopied} onclick={copyToClipboard}>
								{#if showCopied}
									<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<polyline points="20 6 9 17 4 12"></polyline>
									</svg>
									<span>COPIED!</span>
								{:else}
									<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
										<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
									</svg>
									<span>COPY</span>
								{/if}
							</button>
						</div>
					</div>

					<div class="score-section">
						<div class="score-card original">
							<div class="score-header">
								<span class="score-title">ORIGINAL</span>
								<span class="score-value">{result.original_score}/10</span>
							</div>
							<div class="score-bar">
								<div
									class="score-fill"
									style="width: {result.original_score * 10}%"
								></div>
							</div>
						</div>

						<div class="score-arrow">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M5 12h14M12 5l7 7-7 7"/>
							</svg>
						</div>

						<div class="score-card refined">
							<div class="score-header">
								<span class="score-title">REFINED</span>
								<span class="score-value">{result.refined_score}/10</span>
							</div>
							<div class="score-bar">
								<div
									class="score-fill"
									style="width: {result.refined_score * 10}%"
								></div>
							</div>
						</div>
					</div>

					<details class="improvements">
						<summary>
							<span>Improvements Applied</span>
							<span class="improvement-count">{result.improvements.length}</span>
						</summary>
						<ul>
							{#each result.improvements as improvement}
								<li transition:fly={{ x: -10, duration: 200 }}>
									<span class="check">+</span>
									<span>{improvement}</span>
								</li>
							{/each}
						</ul>
					</details>
				</div>
			{/if}
		</div>

		<footer></footer>
	</div>
</main>

<style>
	main {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 40px 20px;
	}

	.container {
		width: 100%;
		max-width: 700px;
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 32px;
	}

	.logo {
		font-size: 18px;
		font-weight: 700;
		letter-spacing: 2px;
	}

	.logo-bracket {
		color: var(--accent);
	}

	.logo-text {
		color: var(--text-primary);
		text-shadow: 0 0 20px var(--accent-glow);
	}

	.version {
		color: var(--text-muted);
		font-size: 12px;
	}

	.terminal {
		background: var(--bg-secondary);
		border: 1px solid var(--border-color);
		border-radius: 16px;
		padding: 32px;
		box-shadow:
			0 0 0 1px var(--border-color),
			0 25px 50px -12px rgba(0, 0, 0, 0.5);
	}

	.input-section {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.input-label {
		display: flex;
		align-items: center;
		gap: 12px;
		color: var(--text-secondary);
		font-size: 14px;
	}

	.prompt-char {
		color: var(--accent);
		font-weight: 700;
	}

	.cursor {
		animation: blink 1s step-end infinite;
		color: var(--accent);
	}

	@keyframes blink {
		0%, 100% { opacity: 1; }
		50% { opacity: 0; }
	}

	.input-wrapper {
		position: relative;
		transition: transform 0.2s ease;
	}

	.input-wrapper:focus-within .input-glow {
		opacity: 1;
	}

	.input-glow {
		position: absolute;
		inset: -2px;
		background: linear-gradient(135deg, var(--accent), transparent);
		border-radius: 14px;
		opacity: 0;
		transition: opacity 0.3s ease;
		z-index: -1;
		filter: blur(8px);
	}

	.prompt-input {
		width: 100%;
		background: var(--bg-primary);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 20px;
		color: var(--text-primary);
		font-family: var(--font-mono);
		font-size: 14px;
		line-height: 1.6;
		resize: vertical;
		transition: all 0.3s ease;
	}

	.prompt-input:focus {
		outline: none;
		border-color: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-dim);
	}

	.prompt-input::placeholder {
		color: var(--text-muted);
	}

	.prompt-input:disabled {
		opacity: 0.5;
	}

	.mode-section {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.mode-label {
		color: var(--text-muted);
		font-size: 12px;
		letter-spacing: 1px;
		text-transform: uppercase;
	}

	.mode-selector {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	.mode-btn {
		background: transparent;
		border: 1px solid var(--border-color);
		color: var(--text-secondary);
		padding: 10px 16px;
		border-radius: 8px;
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 1px;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.mode-btn:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--accent);
	}

	.mode-btn.active {
		background: var(--accent);
		color: var(--bg-primary);
		border-color: var(--accent);
		box-shadow: 0 0 20px var(--accent-glow);
	}

	.mode-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.refine-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		background: linear-gradient(135deg, var(--accent), #00cc6a);
		border: none;
		color: var(--bg-primary);
		padding: 18px 32px;
		border-radius: 12px;
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 700;
		letter-spacing: 1px;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
	}

	.refine-btn::before {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(135deg, transparent, rgba(255,255,255,0.2));
		opacity: 0;
		transition: opacity 0.3s ease;
	}

	.refine-btn:hover:not(:disabled)::before {
		opacity: 1;
	}

	.refine-btn:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: 0 10px 30px var(--accent-glow);
	}

	.refine-btn:active:not(:disabled) {
		transform: translateY(0);
	}

	.refine-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
		transform: none;
	}

	.btn-icon {
		width: 18px;
		height: 18px;
	}

	.spinner {
		width: 18px;
		height: 18px;
		border: 2px solid transparent;
		border-top-color: var(--bg-primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.loading-dots {
		animation: dots 1.5s infinite;
	}

	@keyframes dots {
		0%, 20% { content: '.'; }
		40% { content: '..'; }
		60%, 100% { content: '...'; }
	}

	.error-msg {
		display: flex;
		align-items: center;
		gap: 12px;
		background: var(--error-dim);
		border: 1px solid var(--error);
		color: var(--error);
		padding: 16px 20px;
		border-radius: 12px;
		margin-top: 24px;
		font-size: 13px;
	}

	.error-icon {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
	}

	.output-section {
		margin-top: 32px;
	}

	.output-divider {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 24px;
	}

	.divider-line {
		flex: 1;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--border-color), transparent);
	}

	.divider-text {
		color: var(--text-muted);
		font-size: 11px;
		letter-spacing: 3px;
		text-transform: uppercase;
	}

	.result-box {
		background: var(--bg-primary);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 24px;
		transition: border-color 0.3s ease;
	}

	.result-box:hover {
		border-color: var(--accent);
	}

	.result-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;
	}

	.result-label {
		color: var(--accent);
		font-size: 11px;
		letter-spacing: 2px;
		font-weight: 700;
	}

	.intent-badge {
		background: var(--bg-tertiary);
		color: var(--text-secondary);
		padding: 6px 12px;
		border-radius: 20px;
		font-size: 11px;
	}

	.result-content {
		color: var(--text-primary);
		font-size: 14px;
		line-height: 1.7;
	}

	.result-actions {
		margin-top: 20px;
		padding-top: 16px;
		border-top: 1px solid var(--border-color);
		display: flex;
		justify-content: flex-end;
	}

	.copy-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		background: transparent;
		border: 1px solid var(--accent);
		color: var(--accent);
		padding: 10px 20px;
		border-radius: 8px;
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 500;
		letter-spacing: 1px;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.copy-btn:hover {
		background: var(--accent);
		color: var(--bg-primary);
	}

	.copy-btn.copied {
		background: var(--accent);
		color: var(--bg-primary);
	}

	.score-section {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-top: 24px;
	}

	.score-card {
		flex: 1;
		background: var(--bg-primary);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 16px;
	}

	.score-card.original .score-fill {
		background: #ff6b6b;
	}

	.score-card.refined .score-fill {
		background: var(--accent);
		box-shadow: 0 0 10px var(--accent-glow);
	}

	.score-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.score-title {
		color: var(--text-muted);
		font-size: 10px;
		letter-spacing: 2px;
	}

	.score-value {
		color: var(--text-primary);
		font-size: 18px;
		font-weight: 700;
	}

	.score-bar {
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.score-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.score-arrow {
		color: var(--accent);
		flex-shrink: 0;
	}

	.score-arrow svg {
		width: 24px;
		height: 24px;
	}

	.improvements {
		margin-top: 20px;
		background: var(--bg-primary);
		border: 1px solid var(--border-color);
		border-radius: 12px;
	}

	.improvements summary {
		padding: 16px 20px;
		cursor: pointer;
		display: flex;
		justify-content: space-between;
		align-items: center;
		color: var(--text-secondary);
		font-size: 13px;
		transition: color 0.2s ease;
		list-style: none;
	}

	.improvements summary::-webkit-details-marker {
		display: none;
	}

	.improvements summary:hover {
		color: var(--text-primary);
	}

	.improvement-count {
		background: var(--accent);
		color: var(--bg-primary);
		padding: 4px 10px;
		border-radius: 12px;
		font-size: 11px;
		font-weight: 700;
	}

	.improvements ul {
		padding: 0 20px 16px;
		list-style: none;
	}

	.improvements li {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		color: var(--text-secondary);
		font-size: 13px;
		line-height: 1.5;
		padding: 8px 0;
		border-bottom: 1px solid var(--border-color);
	}

	.improvements li:last-child {
		border-bottom: none;
	}

	.check {
		color: var(--accent);
		font-weight: 700;
	}

	footer {
		text-align: center;
		margin-top: 32px;
		color: var(--text-muted);
		font-size: 12px;
	}

	@media (max-width: 600px) {
		main {
			padding: 20px 16px;
		}

		.terminal {
			padding: 24px 20px;
		}

		header {
			flex-direction: column;
			gap: 8px;
			text-align: center;
		}

		.logo {
			font-size: 16px;
		}

		.score-section {
			flex-direction: column;
		}

		.score-arrow {
			transform: rotate(90deg);
		}
	}
</style>