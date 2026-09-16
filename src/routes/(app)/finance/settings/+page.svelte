<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let materialityThreshold = '1000';
	let confidenceThreshold = '95';
	let autoReconcile = true;
	let autoJournal = true;
	let autoCommentary = true;
	let aiModel = 'claude-sonnet-5';
	let baseCurrency = 'SGD';
	let dayCountConvention = 'ACT/365';
	let notifyOnException = true;
	let notifyOnApproval = true;
	let saved = false;

	function handleSave() {
		saved = true;
		setTimeout(() => (saved = false), 2000);
	}
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Settings</span>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Settings</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Configure finance module parameters, thresholds, and AI behavior</p>
	</div>

	<div class="flex-1 overflow-y-auto">
		<div class="px-8 py-6 space-y-6 max-w-3xl">
			<!-- Thresholds -->
			<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">Thresholds & Tolerances</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Control exception detection sensitivity</p>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Materiality Threshold (SGD)</label>
						<input type="number" bind:value={materialityThreshold} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white" />
						<p class="text-[10px] text-gray-400 mt-1">Variances below this amount are flagged as immaterial</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">AI Confidence Auto-Accept (%)</label>
						<input type="number" bind:value={confidenceThreshold} min="80" max="100" class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white" />
						<p class="text-[10px] text-gray-400 mt-1">Extracted data above this confidence level is auto-accepted</p>
					</div>
				</div>
			</div>

			<!-- Automation -->
			<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">Automation</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Enable or disable AI-driven processing steps</p>
				</div>
				<div class="px-6 py-4 space-y-3">
					{#each [
						[() => autoReconcile, (v) => (autoReconcile = v), 'Auto-Reconciliation', 'Automatically run three-way reconciliation after document upload'],
						[() => autoJournal, (v) => (autoJournal = v), 'Auto-Generate Journals', 'AI generates draft journal entries after reconciliation'],
						[() => autoCommentary, (v) => (autoCommentary = v), 'Auto-Generate Commentary', 'AI generates month-end commentary after all processing']
					] as [getter, setter, label, desc]}
						<div class="flex items-center justify-between py-2">
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white">{label}</div>
								<div class="text-[10px] text-gray-500 dark:text-gray-400">{desc}</div>
							</div>
							<button
								class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {getter() ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700'}"
								on:click={() => setter(!getter())}
							>
								<span class="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform {getter() ? 'translate-x-6' : 'translate-x-1'}"></span>
							</button>
						</div>
					{/each}
				</div>
			</div>

			<!-- AI Configuration -->
			<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">AI Configuration</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Select AI model and processing parameters</p>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">AI Model</label>
						<select bind:value={aiModel} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
							<option value="claude-sonnet-5">Claude Sonnet 5 (Recommended)</option>
							<option value="claude-opus-5">Claude Opus 5</option>
							<option value="claude-haiku-4-5">Claude Haiku 4.5</option>
						</select>
					</div>
				</div>
			</div>

			<!-- Accounting Standards -->
			<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">Accounting Standards</h3>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Base Currency</label>
						<select bind:value={baseCurrency} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
							<option value="SGD">SGD — Singapore Dollar</option>
							<option value="USD">USD — US Dollar</option>
							<option value="EUR">EUR — Euro</option>
						</select>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Day Count Convention</label>
						<select bind:value={dayCountConvention} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
							<option value="ACT/365">ACT/365</option>
							<option value="ACT/360">ACT/360</option>
							<option value="30/360">30/360</option>
						</select>
					</div>
				</div>
			</div>

			<!-- Notifications -->
			<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">Notifications</h3>
				</div>
				<div class="px-6 py-4 space-y-3">
					{#each [
						[() => notifyOnException, (v) => (notifyOnException = v), 'Exception Alerts', 'Notify when new exceptions are detected'],
						[() => notifyOnApproval, (v) => (notifyOnApproval = v), 'Approval Requests', 'Notify when items require your approval']
					] as [getter, setter, label, desc]}
						<div class="flex items-center justify-between py-2">
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white">{label}</div>
								<div class="text-[10px] text-gray-500 dark:text-gray-400">{desc}</div>
							</div>
							<button
								class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {getter() ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700'}"
								on:click={() => setter(!getter())}
							>
								<span class="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform {getter() ? 'translate-x-6' : 'translate-x-1'}"></span>
							</button>
						</div>
					{/each}
				</div>
			</div>

			<!-- Save -->
			<div class="flex items-center gap-3">
				<button
					on:click={handleSave}
					class="px-6 py-2.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
				>
					Save Settings
				</button>
				{#if saved}
					<span class="text-sm text-emerald-600 dark:text-emerald-400">Settings saved successfully</span>
				{/if}
			</div>
		</div>
	</div>
</div>
