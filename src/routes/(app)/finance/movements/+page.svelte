<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	import { getMovements, analyzeMovements, updateMovement, getReportingPeriods } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	// --- Types ---
	type MovementType = 'NEW' | 'SOLD' | 'MATURED' | 'TRANSFERRED' | 'VALUE_CHANGE' | 'COUPON_CHANGE' | 'UNCHANGED' | 'OTHER';

	interface Movement {
		id: string;
		bond_id: string;
		isin: string;
		movement_type: MovementType;
		previous_value: number | null;
		current_value: number | null;
		variance: number | null;
		variance_pct: number | null;
		ai_explanation: string;
		source_documents: string[];
		confidence: number;
		approved: boolean;
		status: string;
		currency: string;
	}

	// --- State ---
	let loading = true;
	let analyzing = false;
	let movements: Movement[] = [];
	let expandedRow: string | null = null;
	let searchQuery = '';
	let activeTypeFilter: MovementType | 'ALL' = 'ALL';
	let showOnlyUnapproved = false;
	let periods: any[] = [];
	let selectedPeriodId = '';

	$: registerAssistantContext({
		page: 'movements',
		pageTitle: 'Movements',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['movements.analyze', 'movements.list', 'commentary.generate_with_movements'],
		pageData: { movementCount: movements.length }
	});

	// Backend rows use is_approved/current_status/explanation_confidence (0-1)
	// and don't carry source_documents/currency/variance_pct — reshape them.
	// Backend uses accounting-style movement types (PURCHASE/SALE/MATURITY/
	// TRANSFER/ACCRUAL); map them onto this page's display vocabulary.
	const BACKEND_TYPE_MAP: Record<string, MovementType> = {
		PURCHASE: 'NEW',
		SALE: 'SOLD',
		MATURITY: 'MATURED',
		TRANSFER: 'TRANSFERRED',
		ACCRUAL: 'VALUE_CHANGE',
		NEW: 'NEW',
		SOLD: 'SOLD',
		MATURED: 'MATURED',
		TRANSFERRED: 'TRANSFERRED',
		VALUE_CHANGE: 'VALUE_CHANGE',
		UNCHANGED: 'UNCHANGED'
	};

	function toMovement(row: any): Movement {
		const prev = row.previous_value ?? null;
		const curr = row.current_value ?? null;
		const variance = row.variance ?? (prev != null && curr != null ? curr - prev : null);
		return {
			id: row.id,
			bond_id: row.bond_id,
			isin: row.isin,
			movement_type: BACKEND_TYPE_MAP[row.movement_type] || 'OTHER',
			previous_value: prev,
			current_value: curr,
			variance,
			variance_pct: prev ? Math.round(((variance ?? 0) / prev) * 1000) / 10 : null,
			ai_explanation: row.ai_explanation || 'No explanation available.',
			source_documents: [],
			confidence: Math.round((row.explanation_confidence ?? 0) * 100),
			approved: !!row.is_approved,
			status: row.current_status || (row.is_approved ? 'approved' : 'pending'),
			currency: row.currency || 'SGD'
		};
	}

	// --- Summary counts ---
	$: summary = computeSummary(movements);

	function computeSummary(data: Movement[]) {
		const counts: Record<string, number> = {
			NEW: 0, SOLD: 0, MATURED: 0, TRANSFERRED: 0,
			VALUE_CHANGE: 0, UNCHANGED: 0
		};
		for (const m of data) {
			if (counts[m.movement_type] !== undefined) {
				counts[m.movement_type]++;
			}
		}
		return counts;
	}

	// --- Filtering ---
	$: filteredMovements = filterMovements(movements, activeTypeFilter, searchQuery, showOnlyUnapproved);

	function filterMovements(data: Movement[], typeFilter: MovementType | 'ALL', search: string, unapprovedOnly: boolean): Movement[] {
		let result = data;
		if (typeFilter !== 'ALL') {
			result = result.filter(m => m.movement_type === typeFilter);
		}
		if (search.trim()) {
			const q = search.toLowerCase().trim();
			result = result.filter(m =>
				m.bond_id.toLowerCase().includes(q) || m.isin.toLowerCase().includes(q)
			);
		}
		if (unapprovedOnly) {
			result = result.filter(m => !m.approved);
		}
		return result;
	}

	// --- Formatting ---
	function formatCurrency(value: number | null): string {
		if (value === null || value === undefined) return '—';
		return `S$ ${value.toLocaleString('en-SG', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
	}

	function formatVariance(value: number | null, pct: number | null): string {
		if (value === null || value === undefined) return '—';
		const sign = value > 0 ? '+' : '';
		const formatted = `${sign}S$ ${Math.abs(value).toLocaleString('en-SG')}`;
		if (pct !== null && pct !== undefined) {
			return `${formatted} (${value > 0 ? '+' : ''}${pct.toFixed(1)}%)`;
		}
		return formatted;
	}

	// --- Badge config ---
	const typeBadgeClasses: Record<string, string> = {
		NEW: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
		SOLD: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
		MATURED: 'bg-gray-200 text-gray-700 dark:bg-gray-600/30 dark:text-gray-400',
		TRANSFERRED: 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400',
		VALUE_CHANGE: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
		COUPON_CHANGE: 'bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-400',
		UNCHANGED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
		OTHER: 'bg-gray-100 text-gray-600 dark:bg-gray-600/20 dark:text-gray-500'
	};

	const summaryCards = [
		{ key: 'NEW', label: 'New', color: 'text-blue-600 dark:text-blue-400', bgIcon: 'bg-blue-100 dark:bg-blue-500/15', icon: 'plus' },
		{ key: 'SOLD', label: 'Sold', color: 'text-red-600 dark:text-red-400', bgIcon: 'bg-red-100 dark:bg-red-500/15', icon: 'minus' },
		{ key: 'MATURED', label: 'Matured', color: 'text-gray-600 dark:text-gray-400', bgIcon: 'bg-gray-200 dark:bg-gray-600/30', icon: 'check' },
		{ key: 'TRANSFERRED', label: 'Transferred', color: 'text-purple-600 dark:text-purple-400', bgIcon: 'bg-purple-100 dark:bg-purple-500/15', icon: 'arrow' },
		{ key: 'VALUE_CHANGE', label: 'Value Change', color: 'text-amber-600 dark:text-amber-400', bgIcon: 'bg-amber-100 dark:bg-amber-500/15', icon: 'trending' },
		{ key: 'UNCHANGED', label: 'Unchanged', color: 'text-emerald-600 dark:text-emerald-400', bgIcon: 'bg-emerald-100 dark:bg-emerald-500/15', icon: 'stable' }
	];

	const filterChips: { key: MovementType | 'ALL'; label: string }[] = [
		{ key: 'ALL', label: 'All' },
		{ key: 'NEW', label: 'New' },
		{ key: 'SOLD', label: 'Sold' },
		{ key: 'MATURED', label: 'Matured' },
		{ key: 'TRANSFERRED', label: 'Transferred' },
		{ key: 'VALUE_CHANGE', label: 'Value Change' },
		{ key: 'UNCHANGED', label: 'Unchanged' }
	];

	// --- Confidence color ---
	function confidenceColor(pct: number): string {
		if (pct >= 90) return 'text-emerald-600 dark:text-emerald-400';
		if (pct >= 70) return 'text-amber-600 dark:text-amber-400';
		return 'text-red-600 dark:text-red-400';
	}

	function confidenceBarColor(pct: number): string {
		if (pct >= 90) return 'bg-emerald-500';
		if (pct >= 70) return 'bg-amber-500';
		return 'bg-red-500';
	}

	// --- Variance color ---
	function varianceColor(value: number | null): string {
		if (value === null || value === undefined) return 'text-gray-500 dark:text-gray-400';
		if (value > 0) return 'text-emerald-600 dark:text-emerald-400';
		if (value < 0) return 'text-red-600 dark:text-red-400';
		return 'text-gray-500 dark:text-gray-400';
	}

	// --- Actions ---
	function toggleExpand(id: string) {
		expandedRow = expandedRow === id ? null : id;
	}

	async function loadMovements() {
		try {
			const result = await getMovements(
				localStorage.token,
				selectedPeriodId ? { period_id: selectedPeriodId } : undefined
			);
			movements = Array.isArray(result) ? result.map(toMovement) : [];
		} catch (e: any) {
			movements = [];
			toast.error(e?.message || 'Failed to load movements');
		}
	}

	async function handleAnalyze() {
		if (!selectedPeriodId) {
			toast.error('Select a reporting period first');
			return;
		}
		analyzing = true;
		try {
			await analyzeMovements(localStorage.token, selectedPeriodId);
			await loadMovements();
			toast.success('Movement analysis completed');
		} catch (e: any) {
			toast.error(e?.message || 'Movement analysis failed');
		}
		analyzing = false;
	}

	async function handleApprove(movement: Movement) {
		try {
			await updateMovement(localStorage.token, movement.id, { approved: true, status: 'approved' });
			toast.success(`Movement ${movement.id} approved`);
			await loadMovements();
		} catch (e: any) {
			toast.error(e?.message || `Failed to approve movement ${movement.id}`);
		}
	}

	async function handleReject(movement: Movement) {
		try {
			await updateMovement(localStorage.token, movement.id, { approved: false, status: 'rejected' });
			toast.info(`Movement ${movement.id} rejected`);
			await loadMovements();
		} catch (e: any) {
			toast.error(e?.message || `Failed to reject movement ${movement.id}`);
		}
	}

	// --- Mount ---
	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		await loadMovements();
		loading = false;
	});
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span>
			<span>/</span>
			<span>Movements</span>
		</div>
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
			<div>
				<h1 class="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">Bond Movement Analysis</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Identify new, sold, matured, and transferred bonds with AI-powered explanations
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-3">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={loadMovements}
				>
					{#if periods.length === 0}
						<option value="">No periods</option>
					{/if}
					{#each periods as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
				<button
					class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={handleAnalyze}
					disabled={analyzing}
				>
					{#if analyzing}
						<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Analyzing...
					{:else}
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
						</svg>
						Analyze Movements
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
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
				<!-- Summary Cards -->
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
					{#each summaryCards as card}
						<button
							class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm text-left transition-all hover:shadow-md
								{activeTypeFilter === card.key ? 'ring-2 ring-indigo-500 border-indigo-300 dark:border-indigo-600' : ''}"
							on:click={() => activeTypeFilter = activeTypeFilter === card.key ? 'ALL' : card.key}
						>
							<div class="flex items-center justify-between mb-2">
								<div class="w-7 h-7 rounded-lg {card.bgIcon} flex items-center justify-center">
									{#if card.icon === 'plus'}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
									{:else if card.icon === 'minus'}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4" /></svg>
									{:else if card.icon === 'check'}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
									{:else if card.icon === 'arrow'}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
									{:else if card.icon === 'trending'}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
									{:else}
										<svg class="w-3.5 h-3.5 {card.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" /></svg>
									{/if}
								</div>
								<span class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">{card.label}</span>
							</div>
							<div class="text-2xl font-semibold font-mono {card.color}">{summary[card.key] || 0}</div>
						</button>
					{/each}
				</div>

				<!-- Filter Bar -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
					<div class="flex flex-wrap items-center gap-4">
						<!-- Type Chips -->
						<div class="flex flex-wrap items-center gap-1.5">
							{#each filterChips as chip}
								<button
									class="px-3 py-1.5 rounded-full text-xs font-medium transition-colors
										{activeTypeFilter === chip.key
											? 'bg-indigo-600 text-white'
											: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
									on:click={() => activeTypeFilter = chip.key}
								>
									{chip.label}
								</button>
							{/each}
						</div>

						<!-- Divider -->
						<div class="w-px h-6 bg-gray-200 dark:bg-gray-700 hidden sm:block"></div>

						<!-- Search -->
						<div class="relative flex-1 min-w-[200px]">
							<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
							</svg>
							<input
								type="text"
								placeholder="Search by Bond ID or ISIN..."
								class="w-full pl-10 pr-4 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
								bind:value={searchQuery}
							/>
						</div>

						<!-- Unapproved toggle -->
						<label class="flex items-center gap-2 cursor-pointer select-none whitespace-nowrap">
							<span class="text-xs text-gray-500 dark:text-gray-400">Unapproved only</span>
							<button
								class="relative w-9 h-5 rounded-full transition-colors {showOnlyUnapproved ? 'bg-indigo-600' : 'bg-gray-300 dark:bg-gray-600'}"
								on:click={() => showOnlyUnapproved = !showOnlyUnapproved}
								role="switch"
								aria-checked={showOnlyUnapproved}
							>
								<span class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform {showOnlyUnapproved ? 'translate-x-4' : 'translate-x-0'}"></span>
							</button>
						</label>
					</div>
				</div>

				<!-- Movement Table -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<!-- Table Header -->
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-gray-100 dark:border-gray-800">
									<th class="text-left px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Bond ID</th>
									<th class="text-left px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">ISIN</th>
									<th class="text-left px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Movement Type</th>
									<th class="text-right px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Previous Value</th>
									<th class="text-right px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Current Value</th>
									<th class="text-right px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Variance</th>
									<th class="text-left px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">AI Explanation</th>
									<th class="text-center px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Confidence</th>
									<th class="text-center px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Approved</th>
									<th class="text-center px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Actions</th>
								</tr>
							</thead>
							<tbody>
								{#if filteredMovements.length === 0}
									<tr>
										<td colspan="10" class="px-4 py-12 text-center text-gray-400 dark:text-gray-500">
											<div class="flex flex-col items-center gap-2">
												<svg class="w-8 h-8 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
													<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
												</svg>
												<span class="text-sm">No movements match the current filters</span>
											</div>
										</td>
									</tr>
								{/if}
								{#each filteredMovements as movement (movement.id)}
									<!-- Main Row -->
									<tr
										class="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors cursor-pointer"
										on:click={() => toggleExpand(movement.id)}
									>
										<td class="px-4 py-3">
											<span class="font-mono text-sm font-medium text-gray-900 dark:text-white">{movement.bond_id}</span>
										</td>
										<td class="px-4 py-3">
											<span class="font-mono text-xs text-gray-500 dark:text-gray-400">{movement.isin}</span>
										</td>
										<td class="px-4 py-3">
											<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium {typeBadgeClasses[movement.movement_type] || typeBadgeClasses.OTHER}">
												{movement.movement_type.replace('_', ' ')}
											</span>
										</td>
										<td class="px-4 py-3 text-right">
											<span class="font-mono text-sm text-gray-700 dark:text-gray-300">{formatCurrency(movement.previous_value)}</span>
										</td>
										<td class="px-4 py-3 text-right">
											<span class="font-mono text-sm text-gray-700 dark:text-gray-300">{formatCurrency(movement.current_value)}</span>
										</td>
										<td class="px-4 py-3 text-right">
											<span class="font-mono text-sm font-medium {varianceColor(movement.variance)}">{formatVariance(movement.variance, movement.variance_pct)}</span>
										</td>
										<td class="px-4 py-3 max-w-[200px]">
											<p class="text-xs text-gray-600 dark:text-gray-400 truncate">{movement.ai_explanation}</p>
										</td>
										<td class="px-4 py-3 text-center">
											<span class="font-mono text-sm font-medium {confidenceColor(movement.confidence)}">{movement.confidence}%</span>
										</td>
										<td class="px-4 py-3 text-center">
											{#if movement.approved}
												<span class="inline-flex items-center justify-center w-5 h-5 rounded bg-emerald-100 dark:bg-emerald-500/15">
													<svg class="w-3 h-3 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
												</span>
											{:else}
												<span class="inline-flex items-center justify-center w-5 h-5 rounded bg-gray-100 dark:bg-gray-700">
													<span class="w-2 h-2 rounded-sm bg-gray-300 dark:bg-gray-500"></span>
												</span>
											{/if}
										</td>
										<td class="px-4 py-3 text-center">
											<div class="flex items-center justify-center gap-1" on:click|stopPropagation>
												{#if !movement.approved}
													<button
														class="px-2 py-1 text-[11px] font-medium rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-500/20 transition-colors"
														on:click={() => handleApprove(movement)}
													>
														Approve
													</button>
												{/if}
												<button
													class="px-2 py-1 text-[11px] font-medium rounded bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
													on:click={() => toggleExpand(movement.id)}
												>
													Edit
												</button>
												{#if !movement.approved}
													<button
														class="px-2 py-1 text-[11px] font-medium rounded bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors"
														on:click={() => handleReject(movement)}
													>
														Reject
													</button>
												{/if}
											</div>
										</td>
									</tr>

									<!-- Expanded AI Explanation Panel -->
									{#if expandedRow === movement.id}
										<tr class="bg-gray-50/50 dark:bg-gray-800/20">
											<td colspan="10" class="px-4 py-0">
												<div class="py-4 px-2 space-y-4">
													<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
														<!-- Full AI Explanation -->
														<div class="lg:col-span-2 space-y-3">
															<div>
																<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1.5">AI Explanation</div>
																<p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{movement.ai_explanation}</p>
															</div>

															<!-- Source Documents -->
															<div>
																<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1.5">Source Documents</div>
																<div class="flex flex-wrap gap-2">
																	{#each movement.source_documents as doc}
																		<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
																			<svg class="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
																			{doc}
																		</span>
																	{/each}
																</div>
															</div>
														</div>

														<!-- Confidence + Actions -->
														<div class="space-y-4">
															<!-- Confidence Score -->
															<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
																<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Confidence Score</div>
																<div class="flex items-end gap-2 mb-2">
																	<span class="text-3xl font-semibold font-mono {confidenceColor(movement.confidence)}">{movement.confidence}%</span>
																</div>
																<div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
																	<div class="{confidenceBarColor(movement.confidence)} h-2 rounded-full transition-all" style="width: {movement.confidence}%"></div>
																</div>
															</div>

															<!-- AI Label -->
															<div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20">
																<svg class="w-4 h-4 text-indigo-500 dark:text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
																	<path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
																</svg>
																<span class="text-[11px] text-indigo-700 dark:text-indigo-300 font-medium">This explanation was AI-generated</span>
															</div>

															<!-- Action Buttons -->
															<div class="flex gap-2">
																{#if !movement.approved}
																	<button
																		class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium transition-colors"
																		on:click={() => handleApprove(movement)}
																	>
																		<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
																		Approve
																	</button>
																{/if}
																<button
																	class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
																>
																	<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
																	Edit
																</button>
															</div>
														</div>
													</div>
												</div>
											</td>
										</tr>
									{/if}
								{/each}
							</tbody>
						</table>
					</div>

					<!-- Table Footer -->
					<div class="px-4 py-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
						<div class="text-xs text-gray-400 dark:text-gray-500">
							Showing <span class="font-medium text-gray-600 dark:text-gray-400">{filteredMovements.length}</span> of <span class="font-medium text-gray-600 dark:text-gray-400">{movements.length}</span> movements
						</div>
						<div class="flex items-center gap-2">
							<span class="inline-flex items-center gap-1 text-[10px] text-gray-400 dark:text-gray-500">
								<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
								Click a row to expand AI details
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
