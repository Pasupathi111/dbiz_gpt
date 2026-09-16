<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getFinanceDashboard, getReportingPeriods } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let periods: any[] = [];
	let selectedPeriodId = '';
	let dashboard: any = null;

	const defaultDashboard = {
		reporting_period: 'September 2026',
		bond_line_items: 82,
		reconciliation_rate: 98.7,
		exceptions: 3,
		draft_journals: 12,
		review_status: 'Pending',
		processing_time: '4m 32s',
		total_market_value: 45_200_000,
		total_face_value: 42_800_000,
		currency: 'SGD',
		steps: [
			{ name: 'Documents', status: 'complete', count: 4 },
			{ name: 'Extraction', status: 'complete', count: 82 },
			{ name: 'Validation', status: 'complete', count: 82 },
			{ name: 'Reconciliation', status: 'warning', count: 3 },
			{ name: 'Movements', status: 'complete', count: 15 },
			{ name: 'Schedule', status: 'complete', count: 82 },
			{ name: 'Journals', status: 'draft', count: 12 },
			{ name: 'Audit Schedule', status: 'complete', count: 82 },
			{ name: 'Finance Review', status: 'pending', count: 0 },
			{ name: 'Finalization', status: 'pending', count: 0 }
		],
		work_distribution: [
			{ name: 'Bond reconciliation', runs: 1816, pct: 57 },
			{ name: 'Movement analysis', runs: 890, pct: 28 },
			{ name: 'Schedule generation', runs: 318, pct: 10 },
			{ name: 'Journal preparation', runs: 160, pct: 5 }
		],
		recent_activity: [
			{ action: 'UBS Excel report uploaded', user: 'S. Lim', time: '2 hours ago', type: 'upload' },
			{ action: 'Reconciliation completed', user: 'System', time: '1 hour ago', type: 'process' },
			{ action: '3 exceptions flagged', user: 'System', time: '1 hour ago', type: 'warning' },
			{ action: 'Draft journals generated', user: 'System', time: '45 min ago', type: 'process' },
			{ action: 'Pending Finance review', user: 'System', time: '30 min ago', type: 'review' }
		]
	};

	onMount(async () => {
		try {
			periods = await getReportingPeriods(localStorage.token).catch(() => []);
			const data = await getFinanceDashboard(localStorage.token, selectedPeriodId).catch(() => null);
			dashboard = data?.bond_line_items !== undefined ? data : defaultDashboard;
		} catch {
			dashboard = defaultDashboard;
		}
		loading = false;
	});

	$: data = dashboard || defaultDashboard;

	function getStatusColor(status: string): string {
		switch (status) {
			case 'complete': return 'bg-emerald-500';
			case 'warning': return 'bg-amber-500';
			case 'draft': return 'bg-blue-500';
			case 'pending': return 'bg-gray-300 dark:bg-gray-600';
			default: return 'bg-gray-300 dark:bg-gray-600';
		}
	}

	function getStatusIcon(status: string): string {
		switch (status) {
			case 'complete': return '✓';
			case 'warning': return '⚠';
			case 'draft': return '◐';
			case 'pending': return '○';
			default: return '○';
		}
	}

	function formatCurrency(value: number): string {
		if (value >= 1_000_000) return `S$${(value / 1_000_000).toFixed(1)}M`;
		if (value >= 1_000) return `S$${(value / 1_000).toFixed(0)}K`;
		return `S$${value}`;
	}
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span>
			<span>/</span>
			<span>Dashboard</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Finance Operations Dashboard</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Bond reconciliation, movement analysis and monthly reporting
				</p>
			</div>
			<div class="flex items-center gap-3">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
				>
					<option value="">September 2026</option>
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
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-8 py-6 space-y-6">
				<!-- KPI Cards Row -->
				<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
					<!-- Bond Line Items -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Bond Line Items</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{data.bond_line_items}</span>
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
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{data.reconciliation_rate}%</span>
							<span class="text-xs text-emerald-500 font-medium mb-1">+0.6pt</span>
						</div>
						<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mt-3">
							<div class="bg-emerald-500 h-1.5 rounded-full transition-all" style="width: {data.reconciliation_rate}%"></div>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">{Math.round(data.bond_line_items * data.reconciliation_rate / 100)} of {data.bond_line_items} matched</div>
					</div>

					<!-- Exceptions -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Exceptions</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-amber-600 dark:text-amber-400 font-mono">{data.exceptions}</span>
						</div>
						<div class="flex items-center gap-1.5 mt-3">
							<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400">
								2 variance
							</span>
							<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-400">
								1 missing
							</span>
						</div>
					</div>

					<!-- Review Status -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Finance Review</div>
						<div class="flex items-end gap-2">
							<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400">
								{data.review_status}
							</span>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-3">{data.draft_journals} draft journals awaiting review</div>
					</div>
				</div>

				<!-- Second Row: Portfolio Value + Processing Timeline -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
					<!-- Portfolio Summary Card -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Portfolio Value</div>
						<div class="flex items-end gap-2">
							<span class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{formatCurrency(data.total_market_value)}</span>
						</div>
						<div class="flex items-center gap-4 mt-3">
							<div class="flex gap-0.5">
								{#each Array(7) as _, i}
									<div class="w-4 h-8 rounded-sm {['bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-300 dark:bg-amber-600', 'bg-amber-400 dark:bg-amber-500', 'bg-amber-500 dark:bg-amber-400'][i]}"></div>
								{/each}
							</div>
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">Face value: {formatCurrency(data.total_face_value)}</div>
					</div>

					<!-- Processing Timeline -->
					<div class="lg:col-span-2 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-4">Processing Pipeline</div>
						<div class="flex items-start gap-0 overflow-x-auto pb-2">
							{#each data.steps as step, i}
								<div class="flex items-start flex-shrink-0 min-w-0">
									<div class="flex flex-col items-center w-16">
										<div class="w-7 h-7 rounded-full {getStatusColor(step.status)} flex items-center justify-center text-white text-xs font-bold shadow-sm">
											{getStatusIcon(step.status)}
										</div>
										<div class="text-[9px] text-center text-gray-500 dark:text-gray-400 mt-1.5 leading-tight px-0.5">{step.name}</div>
									</div>
									{#if i < data.steps.length - 1}
										<div class="w-4 h-0.5 mt-3.5 flex-shrink-0 {step.status === 'complete' ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-gray-200 dark:bg-gray-700'}"></div>
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
							{#each data.work_distribution as item, i}
								{@const colors = ['bg-indigo-500', 'bg-blue-500', 'bg-purple-500', 'bg-violet-400']}
								<div>
									<div class="flex items-center justify-between mb-1.5">
										<span class="text-sm text-gray-700 dark:text-gray-300">{item.name}</span>
										<div class="flex items-center gap-3">
											<span class="text-sm font-semibold text-gray-900 dark:text-white font-mono">{item.runs.toLocaleString()}</span>
											<span class="text-xs text-gray-400 dark:text-gray-500 w-8 text-right">{item.pct}%</span>
										</div>
									</div>
									<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
										<div class="{colors[i]} h-2 rounded-full transition-all" style="width: {item.pct}%"></div>
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
							{#each data.recent_activity as activity}
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
										<div class="text-sm text-gray-700 dark:text-gray-300">{activity.action}</div>
										<div class="text-[10px] text-gray-400 dark:text-gray-500">{activity.user} · {activity.time}</div>
									</div>
								</div>
							{/each}
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
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">What changed in adoption, cost and quality</div>
							</div>
						</button>
						<button class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5 transition-colors text-left group">
							<span class="text-indigo-500 dark:text-indigo-400 mt-0.5">→</span>
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">Review exceptions</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Analyze {data.exceptions} unresolved variances</div>
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
