<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getAuditSchedule, generateAuditSchedule, exportAuditSchedule, getReportingPeriods } from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let generating = false;
	let entries: any[] = [];
	let searchQuery = '';
	let statusFilter = '';
	let periods: any[] = [];
	let selectedPeriodId = '';

	$: registerAssistantContext({
		page: 'audit-schedule',
		pageTitle: 'Audit Schedule',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['audit_schedule.generate', 'audit_trail.list'],
		pageData: { entryCount: entries.length }
	});

	async function loadEntries() {
		try {
			const data = await getAuditSchedule(
				localStorage.token,
				selectedPeriodId ? { period_id: selectedPeriodId } : undefined
			);
			entries = Array.isArray(data) ? data : [];
		} catch (e: any) {
			entries = [];
			toast.error(e?.message || 'Failed to load audit schedule');
		}
	}

	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		await loadEntries();
		loading = false;
	});

	async function handleGenerate() {
		if (!selectedPeriodId) {
			toast.error('Select a reporting period first');
			return;
		}
		generating = true;
		try {
			await generateAuditSchedule(localStorage.token, selectedPeriodId);
			toast.success('Audit schedule generated');
			await loadEntries();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to generate audit schedule');
		}
		generating = false;
	}

	function handleExport() {
		if (!selectedPeriodId) {
			toast.error('Select a reporting period first');
			return;
		}
		window.open(exportAuditSchedule(localStorage.token, selectedPeriodId), '_blank');
	}

	$: filtered = entries.filter((e) => {
		if (statusFilter && e.reconciliation_status !== statusFilter) return false;
		if (searchQuery) {
			const q = searchQuery.toLowerCase();
			return e.bond_id?.toLowerCase().includes(q);
		}
		return true;
	});

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			VALID: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
			WARNING: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			ERROR: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			UNKNOWN: 'bg-gray-100 text-gray-500 dark:bg-gray-700/30 dark:text-gray-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}

	function fmt(v: number | null | undefined): string {
		if (v === null || v === undefined) return '-';
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(v);
	}

	$: totalOpening = filtered.reduce((s, e) => s + (e.opening_balance || 0), 0);
	$: totalClosing = filtered.reduce((s, e) => s + (e.closing_balance || 0), 0);
	$: validCount = entries.filter((e) => e.reconciliation_status === 'VALID').length;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI SCS Copilot</span><span>/</span><span>Audit Schedule</span>
		</div>
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Audit Schedule</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Per-bond roll-forward for month-end audit support</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={loadEntries}
				>
					{#if periods.length === 0}
						<option value="">No periods</option>
					{/if}
					{#each periods as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
				<button on:click={handleExport} class="px-4 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
					Export Schedule
				</button>
				<button on:click={handleGenerate} disabled={generating} class="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2">
					{#if generating}<Spinner className="size-3.5" />{/if}
					Generate Audit Schedule
				</button>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-4">
				<!-- Summary Row -->
				<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Bonds</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{entries.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Reconciled</div>
						<div class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{validCount}/{entries.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Opening Balance</div>
						<div class="text-xl font-semibold text-gray-900 dark:text-white font-mono">{fmt(totalOpening)}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Closing Balance</div>
						<div class="text-xl font-semibold text-gray-900 dark:text-white font-mono">{fmt(totalClosing)}</div>
					</div>
				</div>

				<!-- Filters -->
				<div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
					<div class="relative flex-1 max-w-sm">
						<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
						<input type="text" bind:value={searchQuery} placeholder="Search by Bond ID..." class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400" />
					</div>
					<div class="flex flex-wrap items-center gap-1.5">
						{#each ['', 'VALID', 'WARNING', 'ERROR'] as s}
							<button
								class="px-3 py-1.5 text-xs rounded-lg border transition-colors {statusFilter === s ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
								on:click={() => (statusFilter = s)}
							>
								{s || 'All'}
							</button>
						{/each}
					</div>
				</div>

				<!-- Table -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-gray-100 dark:border-gray-800">
									{#each ['Bond ID', 'Opening', 'Purchases', 'Sales', 'Maturities', 'Transfers', 'Interest', 'FV Changes', 'Closing', 'Status'] as h}
										<th class="text-right first:text-left px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">{h}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each filtered as entry, idx}
									<tr class="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors {idx % 2 ? 'bg-gray-50/30 dark:bg-gray-800/10' : ''}">
										<td class="px-4 py-3 font-mono text-xs font-medium text-gray-900 dark:text-white whitespace-nowrap">{entry.bond_id}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.opening_balance)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.purchases)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.sales)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.maturities)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.transfers)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.interest)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmt(entry.fair_value_changes)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs font-semibold text-gray-900 dark:text-white whitespace-nowrap">{fmt(entry.closing_balance)}</td>
										<td class="px-4 py-3 text-right whitespace-nowrap">
											<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(entry.reconciliation_status)}">{entry.reconciliation_status || 'UNKNOWN'}</span>
										</td>
									</tr>
								{/each}
								{#if filtered.length === 0}
									<tr>
										<td colspan="10" class="px-4 py-12 text-center text-sm text-gray-400 dark:text-gray-500">
											No audit schedule entries yet. Generate one for the selected period.
										</td>
									</tr>
								{/if}
							</tbody>
							<tfoot>
								<tr class="border-t-2 border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
									<td class="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Total ({filtered.length})</td>
									<td class="px-4 py-3 text-right font-mono text-xs font-semibold text-gray-900 dark:text-white whitespace-nowrap">{fmt(totalOpening)}</td>
									<td colspan="6"></td>
									<td class="px-4 py-3 text-right font-mono text-xs font-semibold text-gray-900 dark:text-white whitespace-nowrap">{fmt(totalClosing)}</td>
									<td></td>
								</tr>
							</tfoot>
						</table>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
