<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getFinanceDashboard, getReportingPeriods } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import LiveIndicator from '$lib/components/common/LiveIndicator.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let periods: any[] = [];
	let selectedPeriodId = '';
	let dashboard: any = null;
	let error: string | null = null;

	onMount(async () => {
		loading = true;
		error = null;
		try {
			periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
			const data = await getFinanceDashboard(localStorage.token, selectedPeriodId);
			dashboard = data && typeof data === 'object' ? data : null;
		} catch (e: any) {
			error = e?.detail || e?.message || String(e);
			dashboard = null;
		} finally {
			loading = false;
		}
	});

	function formatCurrency(value: number): string {
		if (value >= 1_000_000) return `S$${(value / 1_000_000).toFixed(1)}M`;
		if (value >= 1_000) return `S$${(value / 1_000).toFixed(0)}K`;
		return `S$${value ?? 0}`;
	}

	$: registerAssistantContext({
		page: 'dashboard',
		pageTitle: 'Dashboard',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['portfolio.summary', 'movements.analyze', 'reconciliation.summary', 'commentary.generate_with_movements'],
		pageData: {
			totalBonds: dashboard?.kpis?.total_bonds ?? 0,
			openExceptions: dashboard?.kpis?.exceptions_open ?? 0
		}
	});
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span>
			<span>/</span>
			<span>Dashboard</span>
		</div>
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
			<div>
				<div class="flex items-center gap-2">
					<h1 class="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">Finance Operations Dashboard</h1>
					<LiveIndicator title="Dashboard reflects live pipeline data" />
				</div>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Bond reconciliation, movement analysis and monthly reporting
				</p>
			</div>
			<div class="flex items-center gap-3">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={async () => {
						loading = true;
						error = null;
						try {
							const data = await getFinanceDashboard(localStorage.token, selectedPeriodId);
							dashboard = data && typeof data === 'object' ? data : null;
						} catch (e: any) {
							error = e?.detail || e?.message || String(e);
							dashboard = null;
						} finally {
							loading = false;
						}
					}}
				>
					<option value="">{periods?.[0]?.name || 'Current period'}</option>
					{#each periods as period}
						<option value={period.id}>{period.name}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<Spinner />
		</div>
	{:else if error}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-10">
				<div class="max-w-xl mx-auto rounded-xl border border-red-200 dark:border-red-800/60 bg-red-50 dark:bg-red-900/10 p-6">
					<div class="flex items-start gap-4">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-500/20 flex items-center justify-center">
							<svg class="w-5 h-5 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
							</svg>
						</div>
						<div class="flex-1 min-w-0">
							<h2 class="text-base font-semibold text-red-800 dark:text-red-200 mb-1">Unable to load dashboard</h2>
							<p class="text-sm text-red-700 dark:text-red-300 break-all">{error}</p>
							<button
								on:click={async () => {
									loading = true;
									error = null;
									try {
										const data = await getFinanceDashboard(localStorage.token, selectedPeriodId);
										dashboard = data && typeof data === 'object' ? data : null;
									} catch (e2: any) {
										error = e2?.detail || e2?.message || String(e2);
										dashboard = null;
									} finally {
										loading = false;
									}
								}}
								class="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-medium transition-colors"
							>
								Retry
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	{:else if !dashboard || (dashboard.bond_line_items === 0 && dashboard.total_market_value === 0)}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-10">
				<div class="max-w-xl mx-auto rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-8 text-center">
					<div class="w-14 h-14 mx-auto rounded-2xl bg-indigo-100 dark:bg-indigo-500/10 flex items-center justify-center mb-4">
						<svg class="w-7 h-7 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
						</svg>
					</div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">No finance data yet</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
						Upload bond source documents to start the pipeline. Once documents are uploaded, extraction, reconciliation and journal generation will populate this dashboard automatically.
					</p>
					<a
						href="/finance/documents"
						class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
					>
						Go to Documents
					</a>
				</div>
			</div>
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
				<!-- KPI Cards Row -->
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
					<!-- Bond Line Items -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Bond Line Items</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{dashboard.bond_line_items}</span>
						</div>
						<div class="flex items-center gap-4 mt-3">
							<div class="flex gap-0.5">
								{#each Array(7) as _, i}
									<div class="w-4 h-6 rounded-sm {i < 5 ? 'bg-indigo-400 dark:bg-indigo-500' : 'bg-indigo-200 dark:bg-indigo-800'}"></div>
								{/each}
							</div>
						</div>
					</div>

					<!-- Reconciliation -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Reconciliation</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{dashboard.reconciliation_rate}%</span>
						</div>
						<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mt-3">
							<div class="bg-emerald-500 h-1.5 rounded-full transition-all" style="width: {Math.max(0, Math.min(100, dashboard.reconciliation_rate || 0))}%"></div>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">{Math.round((dashboard.bond_line_items || 0) * (dashboard.reconciliation_rate || 0) / 100)} of {dashboard.bond_line_items || 0} matched</div>
					</div>

					<!-- Exceptions -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Exceptions</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-amber-600 dark:text-amber-400 font-mono">{dashboard.exceptions}</span>
						</div>
						<div class="flex items-center gap-1.5 mt-3">
							<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400">
								Variances
							</span>
							<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-400">
								Open
							</span>
						</div>
					</div>

					<!-- Review Status -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Finance Review</div>
						<div class="flex items-end gap-2">
							<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400">
								{dashboard.review_status}
							</span>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-3">{dashboard.draft_journals} draft journals awaiting review</div>
					</div>
				</div>

				<!-- Second Row: Portfolio Value + Processing Timeline -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
					<!-- Portfolio Summary Card -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Portfolio Value</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{formatCurrency(dashboard.total_market_value)}</span>
						</div>
						<div class="flex items-center gap-4 mt-3">
							<div class="flex gap-0.5">
								{#each Array(7) as _, i}
									<div class="w-4 h-8 rounded-sm {['bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-500 dark:bg-amber-400'][i]}"></div>
								{/each}
							</div>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">Face value: {formatCurrency(dashboard.total_face_value)}</div>
					</div>

					<!-- Processing Timeline -->
					<div class="lg:col-span-2 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-4">Processing Pipeline</div>
						<div class="flex items-start gap-0 overflow-x-auto pb-2">
							{#each dashboard.steps as step, i}
								{@const stepStatus = step.status ?? 'pending'}
								{@const statusColor = stepStatus === 'complete' ? 'bg-emerald-500' : stepStatus === 'warning' ? 'bg-amber-500' : stepStatus === 'draft' ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}
								{@const statusIcon = stepStatus === 'complete' ? '✓' : stepStatus === 'warning' ? '⚠' : stepStatus === 'draft' ? '◐' : '○'}
								<div class="flex items-start flex-shrink-0 min-w-0">
									<div class="flex flex-col items-center w-16">
										<div class="w-7 h-7 rounded-full {statusColor} flex items-center justify-center text-white text-xs font-bold shadow-sm">
											{statusIcon}
										</div>
										<div class="text-[9px] text-center text-gray-500 dark:text-gray-400 mt-1.5 leading-tight px-0.5">{step.name}</div>
									</div>
									{#if i < dashboard.steps.length - 1}
										<div class="w-4 h-0.5 mt-3.5 flex-shrink-0 {stepStatus === 'complete' ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-gray-200 dark:bg-gray-700'}"></div>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				</div>

				<!-- Third Row: Work Distribution + Recent Activity -->
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
					<!-- Work Distribution -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-4">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Where the work is going</div>
							<div class="text-[10px] text-gray-400 dark:text-gray-500">Processing steps, current period</div>
						</div>
						<div class="space-y-4">
							{#each dashboard.work_distribution as item, i}
								{@const colors = ['bg-indigo-500', 'bg-blue-500', 'bg-purple-500', 'bg-violet-400']}
								<div>
									<div class="flex items-center justify-between mb-1.5">
										<span class="text-sm text-gray-700 dark:text-gray-300">{item.name}</span>
										<div class="flex items-center gap-3">
											<span class="text-sm font-semibold text-gray-900 dark:text-white font-mono">{Number(item.runs).toLocaleString()}</span>
											<span class="text-xs text-gray-400 dark:text-gray-500 w-8 text-right">{item.pct}%</span>
										</div>
									</div>
									<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
										<div class="{colors[i % colors.length]} h-2 rounded-full transition-all" style="width: {Math.max(0, Math.min(100, item.pct || 0))}%"></div>
									</div>
								</div>
							{/each}
						</div>
					</div>

					<!-- Recent Activity -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-4">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Recent Activity</div>
							<button class="text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline">View all</button>
						</div>
						<div class="space-y-3">
							{#if dashboard.recent_activity && dashboard.recent_activity.length}
								{#each dashboard.recent_activity as activity}
									<div class="flex items-start gap-3">
										<div class="mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0
											{activity.type === 'upload' ? 'bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400' :
											 activity.type === 'process' ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
											 activity.type === 'warning' ? 'bg-amber-100 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400' :
											 'bg-indigo-100 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'}">
											{#if activity.type === 'upload'}
												<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
											{:else if activity.type === 'process'}
												<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
											{:else if activity.type === 'warning'}
												<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
											{:else}
												<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
											{/if}
										</div>
										<div class="min-w-0 flex-1">
											<div class="text-sm text-gray-700 dark:text-gray-300 truncate">{activity.action}</div>
											<div class="text-[10px] text-gray-400 dark:text-gray-500 truncate">{activity.user} · {activity.time}</div>
										</div>
									</div>
								{/each}
							{:else}
								<div class="text-xs text-gray-400 dark:text-gray-500 italic py-3 text-center">No recent activity</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- DO THIS FOR ME Panel (AI Suggestions) -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
					<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">AI Copilot Suggestions</div>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
						<button class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5 transition-colors text-left group">
							<span class="text-indigo-500 dark:text-indigo-400 mt-0.5">→</span>
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">Explain this period</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Portfolio movements, reconciliation and commentary</div>
							</div>
						</button>
						<button class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5 transition-colors text-left group">
							<span class="text-indigo-500 dark:text-indigo-400 mt-0.5">→</span>
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">Review exceptions</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Analyze {dashboard.exceptions} unresolved variances</div>
							</div>
						</button>
						<button class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5 transition-colors text-left group">
							<span class="text-indigo-500 dark:text-indigo-400 mt-0.5">→</span>
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">Generate commentary</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Draft month-end narrative for this period</div>
							</div>
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
