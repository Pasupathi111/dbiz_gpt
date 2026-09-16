<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import {
		getReconciliation,
		getReconciliationSummary,
		runReconciliation,
		updateException
	} from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	// --- Types ---
	interface ReconciliationItem {
		id: string;
		bond_id: string;
		isin: string;
		bond_name: string;
		ubs_value: number | null;
		lgi_value: number | null;
		schedule_value: number | null;
		variance: number;
		variance_pct: number;
		status: 'MATCHED' | 'VARIANCE' | 'MISSING' | 'DUPLICATE' | 'REVIEW_REQUIRED';
		source_a_label: string;
		source_b_label: string;
		ai_explanation: string;
		source_references: string[];
		recommended_action: string;
		last_updated: string;
	}

	interface ReconciliationSummary {
		matched: number;
		variances: number;
		missing: number;
		duplicates: number;
		total: number;
		match_rate: number;
	}

	// --- State ---
	let loading = true;
	let running = false;
	let items: ReconciliationItem[] = [];
	let summary: ReconciliationSummary | null = null;
	let searchQuery = '';
	let statusFilter: string = 'ALL';
	let sortColumn: string = 'bond_id';
	let sortDirection: 'asc' | 'desc' = 'asc';
	let selectedPeriod = 'sep-2026';
	let drawerOpen = false;
	let selectedItem: ReconciliationItem | null = null;

	// --- Sample data ---
	const defaultItems: ReconciliationItem[] = [
		{
			id: 'rec-001', bond_id: 'BOND-001', isin: 'SG7Q99939698', bond_name: 'Singapore Govt 3.375% 2033',
			ubs_value: 4_250_000.00, lgi_value: 4_250_000.00, schedule_value: 4_250_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'All three sources agree on the market value for this Singapore Government bond. No discrepancies detected.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 12', 'LGI GL Account 30410 Entry 0091'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-002', bond_id: 'BOND-002', isin: 'SG3260985842', bond_name: 'HDB 2.750% 2029',
			ubs_value: 3_180_000.00, lgi_value: 3_180_000.00, schedule_value: 3_180_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Market values match across UBS custody statement, LGI general ledger and prior-period schedule.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 14', 'LGI GL Account 30410 Entry 0093'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-003', bond_id: 'BOND-003', isin: 'XS2530501857', bond_name: 'Temasek 4.125% 2034',
			ubs_value: 5_420_000.00, lgi_value: 5_420_000.00, schedule_value: 5_420_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Temasek bond fully reconciled across all data sources with zero variance.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 3', 'LGI GL Account 30420 Entry 0034'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-004', bond_id: 'BOND-004', isin: 'SG7S83939893', bond_name: 'Singapore Govt 2.875% 2030',
			ubs_value: 6_750_000.00, lgi_value: 6_750_000.00, schedule_value: 6_750_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Perfect three-way match. Bond settlement and accrued interest align.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 5', 'LGI GL Account 30410 Entry 0056'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-005', bond_id: 'BOND-005', isin: 'SG31A7000007', bond_name: 'LTA 3.040% 2031',
			ubs_value: 2_890_000.00, lgi_value: 2_890_000.00, schedule_value: 2_890_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Land Transport Authority bond matched across all sources without exception.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 8', 'LGI GL Account 30430 Entry 0012'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-006', bond_id: 'BOND-006', isin: 'XS2388598867', bond_name: 'DBS 3.500% 2028',
			ubs_value: 4_100_000.00, lgi_value: 4_100_000.00, schedule_value: 4_100_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'DBS corporate bond fully reconciled with zero variance across custody and ledger.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 17', 'LGI GL Account 30440 Entry 0045'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-007', bond_id: 'BOND-007', isin: 'SG7V18000009', bond_name: 'Singapore Govt 3.000% 2032',
			ubs_value: 3_560_000.00, lgi_value: 3_560_000.00, schedule_value: 3_560_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Government bond reconciled with zero variance. All sources in agreement.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 21', 'LGI GL Account 30410 Entry 0078'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-008', bond_id: 'BOND-008', isin: 'SG3265998534', bond_name: 'HDB 2.500% 2027',
			ubs_value: 1_980_000.00, lgi_value: 1_980_000.00, schedule_value: 1_980_000.00,
			variance: 0, variance_pct: 0, status: 'MATCHED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'HDB statutory board bond matched. Market value consistent across all data sources.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 25', 'LGI GL Account 30410 Entry 0082'],
			recommended_action: 'No action required.', last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-009', bond_id: 'BOND-009', isin: 'XS2591847523', bond_name: 'Mapletree 4.250% 2035',
			ubs_value: 7_150_000.00, lgi_value: 7_123_500.00, schedule_value: 7_150_000.00,
			variance: -26_500.00, variance_pct: -0.37, status: 'VARIANCE',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'LGI general ledger shows S$26,500 less than UBS custody statement. The difference likely stems from an unreflected accrued interest adjustment in the LGI posting for this period. The prior-period schedule agrees with UBS.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 28', 'LGI GL Account 30440 Entry 0098', 'Prior Schedule Row 28'],
			recommended_action: 'Post accrued interest adjustment journal of S$26,500 to LGI GL Account 30440.',
			last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-010', bond_id: 'BOND-010', isin: 'SG7Q50929404', bond_name: 'Singapore Govt 2.625% 2028',
			ubs_value: 5_800_000.00, lgi_value: 5_812_400.00, schedule_value: 5_800_000.00,
			variance: 12_400.00, variance_pct: 0.21, status: 'VARIANCE',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'LGI GL exceeds UBS custody by S$12,400. This appears to be a duplicate interest accrual entry posted in the current period. The schedule value aligns with UBS.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 31', 'LGI GL Account 30410 Entry 0105', 'LGI GL Account 30410 Entry 0106 (duplicate)'],
			recommended_action: 'Reverse duplicate accrual entry 0106 for S$12,400 in LGI GL Account 30410.',
			last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-011', bond_id: 'BOND-011', isin: 'XS2715934821', bond_name: 'CapitaLand 3.875% 2031',
			ubs_value: 3_200_000.00, lgi_value: null, schedule_value: 3_200_000.00,
			variance: 0, variance_pct: 0, status: 'MISSING',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'This bond appears in UBS custody statement and the prior-period schedule but has no corresponding entry in the LGI general ledger. It may have been omitted during the monthly posting cycle.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 35', 'Prior Schedule Row 35'],
			recommended_action: 'Create LGI GL posting for CapitaLand bond BOND-011, market value S$3,200,000.',
			last_updated: '2026-09-15T10:30:00Z'
		},
		{
			id: 'rec-012', bond_id: 'BOND-012', isin: 'SG7T44939609', bond_name: 'Singapore Govt 3.125% 2034',
			ubs_value: 8_450_000.00, lgi_value: 8_450_000.00, schedule_value: 8_450_000.00,
			variance: 0, variance_pct: 0, status: 'REVIEW_REQUIRED',
			source_a_label: 'UBS Custody', source_b_label: 'LGI GL',
			ai_explanation: 'Values match across all sources, but this bond was recently restructured. The coupon rate changed from 2.875% to 3.125% effective August 2026. The schedule needs manual verification to confirm the updated amortisation parameters are applied correctly.',
			source_references: ['UBS Monthly Statement Sep-2026 Row 38', 'LGI GL Account 30410 Entry 0112', 'Restructure Notice Aug-2026'],
			recommended_action: 'Manually verify amortisation schedule parameters reflect the coupon rate change to 3.125%. Approve once confirmed.',
			last_updated: '2026-09-15T10:30:00Z'
		}
	];

	const defaultSummary: ReconciliationSummary = {
		matched: 8,
		variances: 2,
		missing: 1,
		duplicates: 0,
		total: 12,
		match_rate: 95.1
	};

	// --- Lifecycle ---
	onMount(async () => {
		try {
			const [fetchedItems, fetchedSummary] = await Promise.all([
				getReconciliation(localStorage.token).catch(() => null),
				getReconciliationSummary(localStorage.token, selectedPeriod).catch(() => null)
			]);
			items = Array.isArray(fetchedItems) && fetchedItems.length ? fetchedItems : defaultItems;
			summary = fetchedSummary?.total_items ? fetchedSummary : defaultSummary;
		} catch {
			items = defaultItems;
			summary = defaultSummary;
		}
		loading = false;
	});

	// --- Computed ---
	$: data = summary || defaultSummary;

	$: filteredItems = items
		.filter((item) => {
			if (statusFilter !== 'ALL' && item.status !== statusFilter) return false;
			if (searchQuery) {
				const q = searchQuery.toLowerCase();
				return (
					item.bond_id.toLowerCase().includes(q) ||
					item.isin.toLowerCase().includes(q) ||
					item.bond_name.toLowerCase().includes(q)
				);
			}
			return true;
		})
		.sort((a, b) => {
			let aVal: any = a[sortColumn as keyof ReconciliationItem];
			let bVal: any = b[sortColumn as keyof ReconciliationItem];
			if (aVal == null) aVal = '';
			if (bVal == null) bVal = '';
			if (typeof aVal === 'number' && typeof bVal === 'number') {
				return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
			}
			const cmp = String(aVal).localeCompare(String(bVal));
			return sortDirection === 'asc' ? cmp : -cmp;
		});

	// --- Helpers ---
	function formatCurrency(value: number | null): string {
		if (value == null) return '--';
		return `S$ ${value.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
	}

	function getStatusBadge(status: string): { label: string; classes: string } {
		switch (status) {
			case 'MATCHED':
				return { label: 'Matched', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' };
			case 'VARIANCE':
				return { label: 'Variance', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400' };
			case 'MISSING':
				return { label: 'Missing', classes: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400' };
			case 'DUPLICATE':
				return { label: 'Duplicate', classes: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400' };
			case 'REVIEW_REQUIRED':
				return { label: 'Review Required', classes: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400' };
			default:
				return { label: status, classes: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
		}
	}

	function getVarianceColor(value: number): string {
		if (value === 0) return 'text-emerald-600 dark:text-emerald-400';
		if (value < 0) return 'text-red-600 dark:text-red-400';
		return 'text-amber-600 dark:text-amber-400';
	}

	function toggleSort(column: string) {
		if (sortColumn === column) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortColumn = column;
			sortDirection = 'asc';
		}
	}

	function openDetail(item: ReconciliationItem) {
		selectedItem = item;
		drawerOpen = true;
	}

	function closeDrawer() {
		drawerOpen = false;
		setTimeout(() => { selectedItem = null; }, 200);
	}

	async function handleRunReconciliation() {
		running = true;
		try {
			await runReconciliation(localStorage.token, selectedPeriod);
			toast.success('Reconciliation completed successfully');
			const [fetchedItems, fetchedSummary] = await Promise.all([
				getReconciliation(localStorage.token).catch(() => null),
				getReconciliationSummary(localStorage.token, selectedPeriod).catch(() => null)
			]);
			if (fetchedItems) items = fetchedItems;
			if (fetchedSummary) summary = fetchedSummary;
		} catch {
			toast.error('Reconciliation failed. Using sample data.');
		}
		running = false;
	}

	async function handleResolve() {
		if (!selectedItem) return;
		try {
			await updateException(localStorage.token, selectedItem.id, { status: 'RESOLVED', action: 'resolve' });
			toast.success(`Exception ${selectedItem.bond_id} resolved`);
			closeDrawer();
		} catch {
			toast.error('Failed to resolve exception');
		}
	}

	async function handleWaive() {
		if (!selectedItem) return;
		try {
			await updateException(localStorage.token, selectedItem.id, { status: 'WAIVED', action: 'waive' });
			toast.success(`Exception ${selectedItem.bond_id} waived`);
			closeDrawer();
		} catch {
			toast.error('Failed to waive exception');
		}
	}

	const statusFilters = [
		{ id: 'ALL', label: 'All' },
		{ id: 'MATCHED', label: 'Matched' },
		{ id: 'VARIANCE', label: 'Variance' },
		{ id: 'MISSING', label: 'Missing' }
	];

	const sortIcon = (col: string): string => {
		if (sortColumn !== col) return '';
		return sortDirection === 'asc' ? '↑' : '↓';
	};
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span>
			<span>/</span>
			<span>Reconciliation</span>
		</div>
		<div class="flex items-center justify-between flex-wrap gap-4">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Reconciliation Dashboard</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Cross-source validation across UBS, LGI and prior-period schedules
				</p>
			</div>
			<div class="flex items-center gap-3">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
					bind:value={selectedPeriod}
				>
					<option value="sep-2026">September 2026</option>
					<option value="aug-2026">August 2026</option>
					<option value="jul-2026">July 2026</option>
				</select>
				<button
					class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={handleRunReconciliation}
					disabled={running}
				>
					{#if running}
						<svg class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Running...
					{:else}
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
						Run Reconciliation
					{/if}
				</button>
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
				<!-- Summary Cards -->
				<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
					<!-- Matched -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-2">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Matched</div>
							<div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center">
								<svg class="w-4.5 h-4.5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
								</svg>
							</div>
						</div>
						<div class="text-3xl font-semibold text-gray-900 dark:text-white font-mono">{data.matched}</div>
						<div class="flex items-center gap-2 mt-2">
							<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
								{data.match_rate}% match rate
							</span>
						</div>
					</div>

					<!-- Variances -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-2">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Variances</div>
							<div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-500/10 flex items-center justify-center">
								<svg class="w-4.5 h-4.5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
								</svg>
							</div>
						</div>
						<div class="text-3xl font-semibold text-amber-600 dark:text-amber-400 font-mono">{data.variances}</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-2">Requires investigation</div>
					</div>

					<!-- Missing -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-2">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Missing</div>
							<div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-500/10 flex items-center justify-center">
								<svg class="w-4.5 h-4.5 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</div>
						</div>
						<div class="text-3xl font-semibold text-red-600 dark:text-red-400 font-mono">{data.missing}</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-2">Not found in one source</div>
					</div>

					<!-- Duplicates -->
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
						<div class="flex items-center justify-between mb-2">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Duplicates</div>
							<div class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
								<svg class="w-4.5 h-4.5 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
								</svg>
							</div>
						</div>
						<div class="text-3xl font-semibold text-gray-500 dark:text-gray-400 font-mono">{data.duplicates}</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-2">No duplicates detected</div>
					</div>
				</div>

				<!-- Match Rate Progress Bar -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
					<div class="flex items-center justify-between mb-3">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Overall Match Rate</div>
						<span class="text-lg font-semibold text-gray-900 dark:text-white font-mono">{data.match_rate}%</span>
					</div>
					<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-3">
						<div
							class="h-3 rounded-full transition-all duration-500 {data.match_rate >= 95 ? 'bg-emerald-500' : data.match_rate >= 80 ? 'bg-amber-500' : 'bg-red-500'}"
							style="width: {data.match_rate}%"
						></div>
					</div>
					<div class="flex items-center justify-between mt-2 text-[10px] text-gray-400 dark:text-gray-500">
						<span>{data.matched} of {data.total} items matched</span>
						<span>{data.total - data.matched} items require attention</span>
					</div>
				</div>

				<!-- Table Controls -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<div class="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
						<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
							<!-- Search -->
							<div class="relative w-full sm:w-80">
								<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
								</svg>
								<input
									type="text"
									placeholder="Search by Bond ID, ISIN or name..."
									class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
									bind:value={searchQuery}
								/>
							</div>

							<!-- Status Filter Chips -->
							<div class="flex items-center gap-2 flex-wrap">
								{#each statusFilters as filter}
									<button
										class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
											{statusFilter === filter.id
												? 'bg-indigo-600 text-white shadow-sm'
												: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
										on:click={() => (statusFilter = filter.id)}
									>
										{filter.label}
									</button>
								{/each}
							</div>
						</div>
					</div>

					<!-- Data Table -->
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="bg-gray-50 dark:bg-gray-800/50 sticky top-0 z-10">
									<th
										class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
										on:click={() => toggleSort('bond_id')}
									>
										Bond ID {sortIcon('bond_id')}
									</th>
									<th
										class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
										on:click={() => toggleSort('isin')}
									>
										ISIN {sortIcon('isin')}
									</th>
									<th
										class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none whitespace-nowrap"
										on:click={() => toggleSort('ubs_value')}
									>
										UBS Value {sortIcon('ubs_value')}
									</th>
									<th
										class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none whitespace-nowrap"
										on:click={() => toggleSort('lgi_value')}
									>
										LGI Value {sortIcon('lgi_value')}
									</th>
									<th
										class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none whitespace-nowrap"
										on:click={() => toggleSort('schedule_value')}
									>
										Schedule Value {sortIcon('schedule_value')}
									</th>
									<th
										class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
										on:click={() => toggleSort('variance')}
									>
										Variance {sortIcon('variance')}
									</th>
									<th
										class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
										on:click={() => toggleSort('variance_pct')}
									>
										Var % {sortIcon('variance_pct')}
									</th>
									<th
										class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
										on:click={() => toggleSort('status')}
									>
										Status {sortIcon('status')}
									</th>
									<th class="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
										Action
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-100 dark:divide-gray-800">
								{#each filteredItems as item, idx}
									{@const badge = getStatusBadge(item.status)}
									<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors {idx % 2 === 1 ? 'bg-gray-50/50 dark:bg-gray-800/20' : ''}">
										<td class="px-4 py-3 font-medium text-gray-900 dark:text-white whitespace-nowrap font-mono text-xs">
											{item.bond_id}
										</td>
										<td class="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap font-mono text-xs">
											{item.isin}
										</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
											{formatCurrency(item.ubs_value)}
										</td>
										<td class="px-4 py-3 text-right font-mono text-xs whitespace-nowrap {item.lgi_value == null ? 'text-red-500 dark:text-red-400 italic' : 'text-gray-700 dark:text-gray-300'}">
											{formatCurrency(item.lgi_value)}
										</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
											{formatCurrency(item.schedule_value)}
										</td>
										<td class="px-4 py-3 text-right font-mono text-xs whitespace-nowrap {getVarianceColor(item.variance)}">
											{#if item.variance === 0}
												--
											{:else}
												{item.variance > 0 ? '+' : ''}{formatCurrency(item.variance)}
											{/if}
										</td>
										<td class="px-4 py-3 text-right font-mono text-xs whitespace-nowrap {getVarianceColor(item.variance_pct)}">
											{#if item.variance_pct === 0}
												--
											{:else}
												{item.variance_pct > 0 ? '+' : ''}{item.variance_pct.toFixed(2)}%
											{/if}
										</td>
										<td class="px-4 py-3 whitespace-nowrap">
											<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold {badge.classes}">
												{badge.label}
											</span>
										</td>
										<td class="px-4 py-3 text-center whitespace-nowrap">
											<button
												class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 transition-colors"
												on:click={() => openDetail(item)}
											>
												View Details
											</button>
										</td>
									</tr>
								{/each}

								{#if filteredItems.length === 0}
									<tr>
										<td colspan="9" class="px-4 py-12 text-center text-sm text-gray-400 dark:text-gray-500">
											No reconciliation items match the current filter.
										</td>
									</tr>
								{/if}
							</tbody>
						</table>
					</div>

					<!-- Table Footer -->
					<div class="px-5 py-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-400 dark:text-gray-500 flex items-center justify-between">
						<span>Showing {filteredItems.length} of {items.length} items</span>
						<span>Last reconciliation: 15 Sep 2026, 10:30 AM</span>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- Detail Drawer Overlay -->
{#if drawerOpen}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed inset-0 z-50 flex justify-end"
		on:click|self={closeDrawer}
	>
		<!-- Backdrop -->
		<div class="absolute inset-0 bg-black/30 dark:bg-black/50 transition-opacity" on:click={closeDrawer}></div>

		<!-- Drawer Panel -->
		<div class="relative w-full max-w-lg bg-white dark:bg-gray-900 shadow-2xl border-l border-gray-200 dark:border-gray-700 flex flex-col h-full overflow-hidden animate-slide-in">
			{#if selectedItem}
				<!-- Drawer Header -->
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between flex-shrink-0">
					<div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white">{selectedItem.bond_id}</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400">{selectedItem.bond_name}</p>
					</div>
					<button
						class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
						on:click={closeDrawer}
					>
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>

				<!-- Drawer Content -->
				<div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
					<!-- Bond Identifier -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Bond Identifier</h3>
						<div class="grid grid-cols-2 gap-3">
							<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
								<div class="text-[10px] text-gray-400 dark:text-gray-500 mb-1">Bond ID</div>
								<div class="text-sm font-mono font-medium text-gray-900 dark:text-white">{selectedItem.bond_id}</div>
							</div>
							<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
								<div class="text-[10px] text-gray-400 dark:text-gray-500 mb-1">ISIN</div>
								<div class="text-sm font-mono font-medium text-gray-900 dark:text-white">{selectedItem.isin}</div>
							</div>
						</div>
					</div>

					<!-- Status -->
					<div>
						<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold {getStatusBadge(selectedItem.status).classes}">
							{getStatusBadge(selectedItem.status).label}
						</span>
					</div>

					<!-- Source Comparison -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Source Comparison</h3>
						<div class="space-y-2">
							<div class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
								<span class="text-xs text-gray-500 dark:text-gray-400">{selectedItem.source_a_label}</span>
								<span class="text-sm font-mono font-medium text-gray-900 dark:text-white">{formatCurrency(selectedItem.ubs_value)}</span>
							</div>
							<div class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
								<span class="text-xs text-gray-500 dark:text-gray-400">{selectedItem.source_b_label}</span>
								<span class="text-sm font-mono font-medium {selectedItem.lgi_value == null ? 'text-red-500 dark:text-red-400 italic' : 'text-gray-900 dark:text-white'}">{formatCurrency(selectedItem.lgi_value)}</span>
							</div>
							<div class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
								<span class="text-xs text-gray-500 dark:text-gray-400">Prior Schedule</span>
								<span class="text-sm font-mono font-medium text-gray-900 dark:text-white">{formatCurrency(selectedItem.schedule_value)}</span>
							</div>
						</div>
					</div>

					<!-- Difference Calculation -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Difference Calculation</h3>
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
							<div class="grid grid-cols-2 gap-4">
								<div>
									<div class="text-[10px] text-gray-400 dark:text-gray-500 mb-1">Variance Amount</div>
									<div class="text-lg font-mono font-semibold {getVarianceColor(selectedItem.variance)}">
										{#if selectedItem.variance === 0}
											S$ 0.00
										{:else}
											{selectedItem.variance > 0 ? '+' : ''}{formatCurrency(selectedItem.variance)}
										{/if}
									</div>
								</div>
								<div>
									<div class="text-[10px] text-gray-400 dark:text-gray-500 mb-1">Variance %</div>
									<div class="text-lg font-mono font-semibold {getVarianceColor(selectedItem.variance_pct)}">
										{#if selectedItem.variance_pct === 0}
											0.00%
										{:else}
											{selectedItem.variance_pct > 0 ? '+' : ''}{selectedItem.variance_pct.toFixed(2)}%
										{/if}
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- AI Explanation -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">AI Explanation</h3>
						<div class="bg-indigo-50 dark:bg-indigo-500/5 border border-indigo-100 dark:border-indigo-500/10 rounded-lg p-4">
							<div class="flex gap-3">
								<div class="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center mt-0.5">
									<svg class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
									</svg>
								</div>
								<p class="text-sm text-indigo-900 dark:text-indigo-200 leading-relaxed">{selectedItem.ai_explanation}</p>
							</div>
						</div>
					</div>

					<!-- Source References -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Source References</h3>
						<ul class="space-y-1.5">
							{#each selectedItem.source_references as ref}
								<li class="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
									<svg class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
									</svg>
									<span class="font-mono text-xs">{ref}</span>
								</li>
							{/each}
						</ul>
					</div>

					<!-- Recommended Action -->
					<div class="space-y-3">
						<h3 class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Recommended Action</h3>
						<div class="bg-amber-50 dark:bg-amber-500/5 border border-amber-100 dark:border-amber-500/10 rounded-lg p-4">
							<p class="text-sm text-amber-900 dark:text-amber-200 leading-relaxed">{selectedItem.recommended_action}</p>
						</div>
					</div>
				</div>

				<!-- Drawer Footer -->
				{#if selectedItem.status !== 'MATCHED'}
					<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex items-center gap-3 flex-shrink-0">
						<button
							class="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 transition-colors"
							on:click={handleResolve}
						>
							Resolve
						</button>
						<button
							class="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:focus:ring-offset-gray-900 transition-colors"
							on:click={handleWaive}
						>
							Waive
						</button>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}

<style>
	@keyframes slideIn {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	.animate-slide-in {
		animation: slideIn 0.2s ease-out;
	}

	table {
		border-collapse: collapse;
	}

	thead th {
		position: sticky;
		top: 0;
		z-index: 10;
	}
</style>
