<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getBonds } from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import LiveIndicator from '$lib/components/common/LiveIndicator.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let bonds: any[] = [];
	let searchQuery = '';
	let statusFilter = '';
	let sourceFilter = '';
	let selectedBond: any = null;
	let showDetail = false;
	let drawerConfidenceExpanded = false;

	$: registerAssistantContext({
		page: 'bonds',
		pageTitle: 'Bond Data',
		module: 'Bond Reporting',
		selectedBondIds: selectedBond ? [selectedBond.id] : [],
		availableActions: ['portfolio.summary', 'exceptions.list'],
		pageData: { bondCount: bonds.length }
	});

	onMount(async () => {
		try {
			const data = await getBonds(localStorage.token);
			bonds = Array.isArray(data) ? data : [];
		} catch (e: any) {
			bonds = [];
			toast.error(e?.message || 'Failed to load bonds');
		}
		loading = false;
	});

	$: filtered = bonds.filter(b => {
		if (statusFilter && b.status !== statusFilter) return false;
		if (sourceFilter && b.source_type !== sourceFilter) return false;
		if (searchQuery) {
			const q = searchQuery.toLowerCase();
			return b.bond_id?.toLowerCase().includes(q) || b.isin?.toLowerCase().includes(q) || b.issuer?.toLowerCase().includes(q) || b.description?.toLowerCase().includes(q);
		}
		return true;
	});

	function fmt(v: number | null): string {
		if (v === null || v === undefined || v === 0) return '-';
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(v);
	}

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			ACTIVE: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
			MATURED: 'bg-gray-200 text-gray-600 dark:bg-gray-600/20 dark:text-gray-400',
			SOLD: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			TRANSFERRED: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400'
		};
		return m[s] || 'bg-gray-100 text-gray-600';
	}

	function confidenceColor(c: number | null | undefined): string {
		if (c === null || c === undefined) return 'text-gray-400 dark:text-gray-500';
		if (c >= 0.95) return 'text-emerald-600 dark:text-emerald-400';
		if (c >= 0.80) return 'text-amber-600 dark:text-amber-400';
		return 'text-red-600 dark:text-red-400';
	}

	function confidencePct(c: number | null | undefined): string {
		return c === null || c === undefined ? '—' : `${(c * 100).toFixed(0)}%`;
	}

	// Bonds below this extraction confidence are flagged for review.
	const CONFIDENCE_THRESHOLD = 0.8;

	function isLowConfidence(bond: any): boolean {
		const c = bond?.extraction_confidence;
		return c !== null && c !== undefined && c < CONFIDENCE_THRESHOLD;
	}

	// TODO(api): replace this client-side heuristic with the backend's own
	// extraction-confidence reasoning once it exposes one (e.g.
	// `bond.confidence_reason`). This keeps the POC's UI honest about which
	// fields are likely affected without a real explanation feed yet.
	function getConfidenceExplanation(bond: any): { field: string; reason: string; action: string } {
		if (bond?.confidence_reason) {
			return bond.confidence_reason;
		}

		const sourceLabel =
			bond?.source_type === 'LGI' ? 'the LGI PDF statement' :
			bond?.source_type === 'UBS' ? 'the UBS Excel export' :
			'the source schedule';

		if (!bond?.isin) {
			return {
				field: 'ISIN',
				reason: `The ISIN could not be reliably parsed from ${sourceLabel} — the field was blank or partially obscured in the source layout.`,
				action: 'Cross-check the ISIN against the original document and update it manually if needed.'
			};
		}
		if (bond?.source_type === 'LGI') {
			return {
				field: 'Face Value / Market Value',
				reason: `OCR text extraction from ${sourceLabel} produced a lower-confidence match for one or more numeric fields, likely due to formatting or a scanned page.`,
				action: 'Compare the extracted values against the source PDF page before relying on this record.'
			};
		}
		return {
			field: 'Extracted Values',
			reason: `The automated extraction from ${sourceLabel} flagged this record as a lower-confidence match, possibly due to an unusual row format or merged cells.`,
			action: 'Review the highlighted fields against the source document before validating this bond.'
		};
	}

	let expandedConfidenceId: string | null = null;

	function toggleConfidenceExplanation(bondId: string, e: Event) {
		e.stopPropagation();
		expandedConfidenceId = expandedConfidenceId === bondId ? null : bondId;
	}

	$: totalMarket = filtered.reduce((s, b) => s + (b.market_value || 0), 0);
	$: totalFace = filtered.reduce((s, b) => s + (b.face_value || 0), 0);
	$: activeCount = filtered.filter(b => b.status === 'ACTIVE').length;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI SCS Copilot</span><span>/</span><span>Bond Data</span>
		</div>
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
			<div>
				<div class="flex items-center gap-2">
					<h1 class="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">Bond Data Explorer</h1>
					<LiveIndicator title="Bond data reflects the latest processed extraction" />
				</div>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Normalized bond records with source traceability and validation status</p>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-4">
				<!-- KPI Row -->
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Bonds</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{filtered.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Active</div>
						<div class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{activeCount}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Face Value</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{fmt(totalFace)}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Market Value</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{fmt(totalMarket)}</div>
					</div>
				</div>

				<!-- Filters -->
				<div class="flex items-center gap-3 flex-wrap">
					<div class="relative flex-1 max-w-sm">
						<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
						<input type="text" bind:value={searchQuery} placeholder="Search bonds..." class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400" />
					</div>
					<div class="flex items-center gap-1.5 flex-wrap">
						{#each ['', 'ACTIVE', 'MATURED', 'SOLD'] as s}
							<button
								class="px-3 py-1.5 text-xs rounded-lg border transition-colors {statusFilter === s ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
								on:click={() => (statusFilter = s)}
							>
								{s || 'All'}
							</button>
						{/each}
					</div>
					<select bind:value={sourceFilter} class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300">
						<option value="">All Sources</option>
						<option value="UBS">UBS</option>
						<option value="LGI">LGI</option>
						<option value="SCHEDULE">Schedule</option>
					</select>
				</div>

				<!-- Table -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-gray-100 dark:border-gray-800">
									{#each ['Bond ID', 'ISIN', 'Issuer', 'CCY', 'Face Value', 'Market Value', 'Coupon', 'Maturity', 'Status', 'Source', 'Confidence', 'Validated'] as h, i}
										<th class="{i >= 4 && i <= 5 ? 'text-right' : i >= 6 ? 'text-center' : 'text-left'} px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">{h}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each filtered as bond, idx}
									<tr
										class="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors cursor-pointer {idx % 2 ? 'bg-gray-50/30 dark:bg-gray-800/10' : ''}"
										on:click={() => { selectedBond = bond; showDetail = true; drawerConfidenceExpanded = false; }}
									>
										<td class="px-4 py-3 font-mono text-xs font-medium text-gray-900 dark:text-white">{bond.bond_id}</td>
										<td class="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{bond.isin}</td>
										<td class="px-4 py-3 text-gray-700 dark:text-gray-300 max-w-[180px] truncate">{bond.issuer}</td>
										<td class="px-4 py-3 text-gray-500">{bond.currency}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300">{fmt(bond.face_value)}</td>
										<td class="px-4 py-3 text-right font-mono text-xs text-gray-700 dark:text-gray-300">{fmt(bond.market_value)}</td>
										<td class="px-4 py-3 text-center text-gray-600 dark:text-gray-400">{bond.coupon_rate}%</td>
										<td class="px-4 py-3 text-center text-xs text-gray-600 dark:text-gray-400">{bond.maturity_date}</td>
										<td class="px-4 py-3 text-center">
											<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(bond.status)}">{bond.status}</span>
										</td>
										<td class="px-4 py-3 text-center text-xs text-gray-500">{bond.source_type}</td>
										<td class="px-4 py-3 text-center text-xs font-mono {confidenceColor(bond.extraction_confidence)}">
											<div class="flex items-center justify-center gap-1.5">
												<span>{confidencePct(bond.extraction_confidence)}</span>
												{#if isLowConfidence(bond)}
													<button
														class="text-[10px] font-sans font-medium text-amber-600 dark:text-amber-400 underline decoration-dotted underline-offset-2 hover:text-amber-700 dark:hover:text-amber-300"
														on:click={(e) => toggleConfidenceExplanation(bond.id, e)}
														title="Why is this confidence low?"
													>
														Why low?
													</button>
												{/if}
											</div>
										</td>
										<td class="px-4 py-3 text-center">
											{#if bond.is_validated}
												<span class="text-emerald-500">✓</span>
											{:else}
												<span class="text-gray-300 dark:text-gray-600">○</span>
											{/if}
										</td>
									</tr>
									{#if expandedConfidenceId === bond.id}
										{@const explanation = getConfidenceExplanation(bond)}
										<tr class="bg-amber-50/60 dark:bg-amber-500/5 border-b border-amber-100 dark:border-amber-900/30">
											<td colspan="12" class="px-4 py-3">
												<div class="flex items-start gap-3 text-xs max-w-3xl">
													<svg class="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
														<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
													</svg>
													<div class="space-y-1">
														<p class="text-gray-700 dark:text-gray-300">
															<span class="font-medium text-gray-900 dark:text-white">Low confidence on:</span> {explanation.field}
														</p>
														<p class="text-gray-600 dark:text-gray-400">{explanation.reason}</p>
														<p class="text-gray-500 dark:text-gray-500"><span class="font-medium">Review:</span> {explanation.action}</p>
													</div>
												</div>
											</td>
										</tr>
									{/if}
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Bond Detail Drawer -->
	{#if showDetail && selectedBond}
		<div class="fixed inset-0 z-50 flex justify-end">
			<div class="absolute inset-0 bg-black/20 dark:bg-black/40" on:click={() => (showDetail = false)}></div>
			<div class="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-xl overflow-y-auto border-l border-gray-200 dark:border-gray-700">
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-900 z-10">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">{selectedBond.bond_id}</h2>
					<button on:click={() => (showDetail = false)} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
					</button>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						{#each [
							['ISIN', selectedBond.isin],
							['Issuer', selectedBond.issuer],
							['Currency', selectedBond.currency],
							['Coupon Rate', selectedBond.coupon_rate + '%'],
							['Maturity Date', selectedBond.maturity_date],
							['Purchase Date', selectedBond.purchase_date],
							['Status', selectedBond.status],
							['Source', selectedBond.source_type]
						] as [label, value]}
							<div>
								<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">{label}</div>
								<div class="text-sm text-gray-900 dark:text-white">{value}</div>
							</div>
						{/each}
					</div>
					<div class="border-t border-gray-100 dark:border-gray-800 pt-4 space-y-3">
						{#each [
							['Face Value', selectedBond.face_value],
							['Book Value', selectedBond.book_value],
							['Market Value', selectedBond.market_value],
							['Accrued Interest', selectedBond.accrued_interest]
						] as [label, value]}
							<div class="flex items-center justify-between">
								<span class="text-sm text-gray-500 dark:text-gray-400">{label}</span>
								<span class="text-sm font-mono font-medium text-gray-900 dark:text-white">{fmt(value)}</span>
							</div>
						{/each}
					</div>
					<div class="border-t border-gray-100 dark:border-gray-800 pt-4">
						<div class="flex items-center justify-between mb-2">
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400">Extraction Confidence</div>
							{#if isLowConfidence(selectedBond)}
								<button
									class="text-[10px] font-medium text-amber-600 dark:text-amber-400 underline decoration-dotted underline-offset-2 hover:text-amber-700 dark:hover:text-amber-300"
									on:click={() => (drawerConfidenceExpanded = !drawerConfidenceExpanded)}
								>
									Why low?
								</button>
							{/if}
						</div>
						<div class="flex items-center gap-2">
							<div class="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-2">
								<div
									class="h-2 rounded-full {isLowConfidence(selectedBond) ? 'bg-red-500' : (selectedBond.extraction_confidence ?? 0) >= 0.95 ? 'bg-emerald-500' : 'bg-amber-500'}"
									style="width: {(selectedBond.extraction_confidence ?? 0) * 100}%"
								></div>
							</div>
							<span class="text-sm font-mono {confidenceColor(selectedBond.extraction_confidence)}">{confidencePct(selectedBond.extraction_confidence)}</span>
						</div>
						{#if isLowConfidence(selectedBond) && drawerConfidenceExpanded}
							{@const explanation = getConfidenceExplanation(selectedBond)}
							<div class="mt-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-500/5 border border-amber-100 dark:border-amber-900/30 text-xs space-y-1">
								<p class="text-gray-700 dark:text-gray-300">
									<span class="font-medium text-gray-900 dark:text-white">Low confidence on:</span> {explanation.field}
								</p>
								<p class="text-gray-600 dark:text-gray-400">{explanation.reason}</p>
								<p class="text-gray-500 dark:text-gray-500"><span class="font-medium">Review:</span> {explanation.action}</p>
							</div>
						{/if}
					</div>
					<div class="flex items-center gap-2 pt-2">
						<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium {selectedBond.is_validated ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'}">
							{selectedBond.is_validated ? '✓ Validated' : '○ Pending Validation'}
						</span>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
