<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getAuditSchedule } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let entries: any[] = [];
	let searchQuery = '';
	let statusFilter = '';

	const sampleEntries = [
		{ id: '1', area: 'Bond Portfolio Valuation', description: 'Verify market values against third-party pricing sources (Bloomberg/Reuters) for all active bonds', assigned_to: 'S. Lim', due_date: '2026-09-20', status: 'IN_PROGRESS', priority: 'HIGH', findings: '', source_ref: 'IFRS 13 Fair Value', completion_pct: 60 },
		{ id: '2', area: 'Coupon Accrual Accuracy', description: 'Recalculate accrued interest for each bond using actual/365 day count convention and compare with system values', assigned_to: 'A. Tan', due_date: '2026-09-22', status: 'NOT_STARTED', priority: 'HIGH', findings: '', source_ref: 'IFRS 9 / MAS Notice 610', completion_pct: 0 },
		{ id: '3', area: 'New Purchases Verification', description: 'Trace new bond purchases to UBS trade confirmations and verify settlement amounts', assigned_to: 'S. Lim', due_date: '2026-09-18', status: 'COMPLETED', priority: 'MEDIUM', findings: '4 new purchases verified. All match UBS confirmations within SGD 50 tolerance.', source_ref: 'Trade Confirmations', completion_pct: 100 },
		{ id: '4', area: 'Maturity / Disposal', description: 'Confirm bonds reaching maturity have been properly derecognized and proceeds received', assigned_to: 'A. Tan', due_date: '2026-09-19', status: 'COMPLETED', priority: 'MEDIUM', findings: '2 maturities processed correctly. Face value SGD 1,000,000 received.', source_ref: 'Bank Statements', completion_pct: 100 },
		{ id: '5', area: 'IFRS 9 Classification', description: 'Review SPPI test results and business model assessment for all bond holdings', assigned_to: 'R. Ng', due_date: '2026-09-25', status: 'NOT_STARTED', priority: 'HIGH', findings: '', source_ref: 'IFRS 9.4.1', completion_pct: 0 },
		{ id: '6', area: 'Impairment Assessment (ECL)', description: 'Verify Expected Credit Loss calculations using PD, LGD, EAD inputs from rating agencies', assigned_to: 'R. Ng', due_date: '2026-09-28', status: 'NOT_STARTED', priority: 'HIGH', findings: '', source_ref: 'IFRS 9.5.5', completion_pct: 0 },
		{ id: '7', area: 'Journal Entry Review', description: 'Verify AI-generated journal entries for completeness, accuracy, and proper account mapping', assigned_to: 'A. Tan', due_date: '2026-09-22', status: 'IN_PROGRESS', priority: 'HIGH', findings: '', source_ref: 'Chart of Accounts', completion_pct: 35 },
		{ id: '8', area: 'Reconciliation Completeness', description: 'Confirm all bond line items are reconciled between UBS, LGI, and internal schedule', assigned_to: 'S. Lim', due_date: '2026-09-20', status: 'IN_PROGRESS', priority: 'MEDIUM', findings: '', source_ref: 'Three-way Reconciliation', completion_pct: 80 },
		{ id: '9', area: 'Custody Confirmation', description: 'Obtain and verify custodian confirmation letter matching bond holdings', assigned_to: 'S. Lim', due_date: '2026-09-30', status: 'NOT_STARTED', priority: 'LOW', findings: '', source_ref: 'Custody Agreement', completion_pct: 0 },
		{ id: '10', area: 'Related Party Transactions', description: 'Check for any related-party bond transactions and verify appropriate disclosures', assigned_to: 'R. Ng', due_date: '2026-09-28', status: 'NOT_STARTED', priority: 'LOW', findings: '', source_ref: 'IAS 24', completion_pct: 0 }
	];

	onMount(async () => {
		try {
			const data = await getAuditSchedule(localStorage.token);
			entries = Array.isArray(data) ? data : sampleEntries;
		} catch {
			entries = sampleEntries;
		}
		loading = false;
	});

	$: filtered = entries.filter(e => {
		if (statusFilter && e.status !== statusFilter) return false;
		if (searchQuery) {
			const q = searchQuery.toLowerCase();
			return e.area?.toLowerCase().includes(q) || e.description?.toLowerCase().includes(q) || e.assigned_to?.toLowerCase().includes(q);
		}
		return true;
	});

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			COMPLETED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
			IN_PROGRESS: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
			NOT_STARTED: 'bg-gray-100 text-gray-500 dark:bg-gray-700/30 dark:text-gray-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}

	function priorityBadge(p: string): string {
		const m: Record<string, string> = {
			HIGH: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			LOW: 'bg-gray-100 text-gray-500 dark:bg-gray-700/30 dark:text-gray-400'
		};
		return m[p] || 'bg-gray-100 text-gray-500';
	}

	$: completedCount = entries.filter(e => e.status === 'COMPLETED').length;
	$: overallProgress = entries.length ? Math.round(entries.reduce((s, e) => s + (e.completion_pct || 0), 0) / entries.length) : 0;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Audit Schedule</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Audit Schedule</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Month-end audit procedures, assignments, and completion tracking</p>
			</div>
			<button class="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
				Export Schedule
			</button>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-8 py-6 space-y-4">
				<!-- Summary Row -->
				<div class="grid grid-cols-4 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Items</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{entries.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Completed</div>
						<div class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{completedCount}/{entries.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Overall Progress</div>
						<div class="flex items-center gap-2">
							<div class="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-2.5">
								<div class="bg-indigo-600 h-2.5 rounded-full transition-all" style="width: {overallProgress}%"></div>
							</div>
							<span class="text-sm font-mono text-gray-600 dark:text-gray-400">{overallProgress}%</span>
						</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">High Priority Open</div>
						<div class="text-2xl font-semibold text-red-600 dark:text-red-400 font-mono">{entries.filter(e => e.priority === 'HIGH' && e.status !== 'COMPLETED').length}</div>
					</div>
				</div>

				<!-- Filters -->
				<div class="flex items-center gap-3">
					<div class="relative flex-1 max-w-sm">
						<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
						<input type="text" bind:value={searchQuery} placeholder="Search audit items..." class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400" />
					</div>
					<div class="flex items-center gap-1.5">
						{#each ['', 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED'] as s}
							<button
								class="px-3 py-1.5 text-xs rounded-lg border transition-colors {statusFilter === s ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
								on:click={() => (statusFilter = s)}
							>
								{s ? s.replace(/_/g, ' ') : 'All'}
							</button>
						{/each}
					</div>
				</div>

				<!-- Table -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b border-gray-100 dark:border-gray-800">
								{#each ['Audit Area', 'Description', 'Assigned To', 'Due Date', 'Priority', 'Status', 'Progress', 'Reference'] as h}
									<th class="text-left px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">{h}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each filtered as entry, idx}
								<tr class="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors {idx % 2 ? 'bg-gray-50/30 dark:bg-gray-800/10' : ''}">
									<td class="px-4 py-3 font-medium text-gray-900 dark:text-white max-w-[160px]">{entry.area}</td>
									<td class="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-[260px] text-xs">{entry.description}</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">{entry.assigned_to}</td>
									<td class="px-4 py-3 text-xs text-gray-500">{entry.due_date}</td>
									<td class="px-4 py-3">
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {priorityBadge(entry.priority)}">{entry.priority}</span>
									</td>
									<td class="px-4 py-3">
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(entry.status)}">{entry.status.replace(/_/g, ' ')}</span>
									</td>
									<td class="px-4 py-3">
										<div class="flex items-center gap-2 min-w-[80px]">
											<div class="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-1.5">
												<div class="{entry.completion_pct === 100 ? 'bg-emerald-500' : 'bg-indigo-500'} h-1.5 rounded-full" style="width: {entry.completion_pct}%"></div>
											</div>
											<span class="text-[10px] font-mono text-gray-500">{entry.completion_pct}%</span>
										</div>
									</td>
									<td class="px-4 py-3 text-[10px] text-gray-400">{entry.source_ref}</td>
								</tr>
								{#if entry.findings}
									<tr class="bg-emerald-50/50 dark:bg-emerald-500/5">
										<td colspan="8" class="px-4 py-2 text-xs text-emerald-700 dark:text-emerald-400">
											<span class="font-medium">Findings:</span> {entry.findings}
										</td>
									</tr>
								{/if}
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	{/if}
</div>
