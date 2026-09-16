<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getBonds } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let bonds: any[] = [];
	let searchQuery = '';
	let statusFilter = '';
	let sourceFilter = '';
	let selectedBond: any = null;
	let showDetail = false;

	const sampleBonds = [
		{ id: '1', bond_id: 'BOND-001', isin: 'SG7M18000001', description: '3.25% DBS 2028', issuer: 'DBS Group Holdings', currency: 'SGD', face_value: 1000000, book_value: 998500, market_value: 1012000, coupon_rate: 3.25, accrued_interest: 8125, maturity_date: '2028-03-15', purchase_date: '2024-03-15', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.98, is_validated: true },
		{ id: '2', bond_id: 'BOND-002', isin: 'SG7M18000002', description: '3.50% OCBC 2029', issuer: 'OCBC Bank', currency: 'SGD', face_value: 2000000, book_value: 1995000, market_value: 2035000, coupon_rate: 3.50, accrued_interest: 17500, maturity_date: '2029-06-20', purchase_date: '2024-06-20', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.99, is_validated: true },
		{ id: '3', bond_id: 'BOND-003', isin: 'XS1234567890', description: '2.75% Temasek 2027', issuer: 'Temasek Holdings', currency: 'SGD', face_value: 500000, book_value: 502000, market_value: 510000, coupon_rate: 2.75, accrued_interest: 3437, maturity_date: '2027-12-01', purchase_date: '2026-09-05', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.97, is_validated: true },
		{ id: '4', bond_id: 'BOND-004', isin: 'SG3258987654', description: '4.00% Singtel 2030', issuer: 'Singtel Group', currency: 'SGD', face_value: 1500000, book_value: 1498000, market_value: 1520000, coupon_rate: 4.00, accrued_interest: 15000, maturity_date: '2030-09-30', purchase_date: '2025-03-15', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.99, is_validated: true },
		{ id: '5', bond_id: 'BOND-005', isin: 'SG7M18000003', description: '3.10% CapitaLand 2028', issuer: 'CapitaLand Investment', currency: 'SGD', face_value: 750000, book_value: 748500, market_value: 755000, coupon_rate: 3.10, accrued_interest: 5812, maturity_date: '2028-07-15', purchase_date: '2026-09-10', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.96, is_validated: false },
		{ id: '6', bond_id: 'BOND-006', isin: 'SG1K24000006', description: '3.80% Mapletree 2029', issuer: 'Mapletree Logistics Trust', currency: 'SGD', face_value: 800000, book_value: 799000, market_value: 795000, coupon_rate: 3.80, accrued_interest: 7600, maturity_date: '2029-01-20', purchase_date: '2025-01-20', status: 'ACTIVE', source_type: 'LGI', extraction_confidence: 0.92, is_validated: false },
		{ id: '7', bond_id: 'BOND-007', isin: 'XS9876543210', description: '3.45% Keppel 2028', issuer: 'Keppel Corporation', currency: 'SGD', face_value: 1200000, book_value: 1198000, market_value: 1205000, coupon_rate: 3.45, accrued_interest: 10350, maturity_date: '2028-11-30', purchase_date: '2024-11-30', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.98, is_validated: true },
		{ id: '8', bond_id: 'BOND-008', isin: 'SG3L58000008', description: '2.90% SIA 2026', issuer: 'Singapore Airlines', currency: 'SGD', face_value: 600000, book_value: 598000, market_value: 0, coupon_rate: 2.90, accrued_interest: 0, maturity_date: '2026-08-31', purchase_date: '2023-08-31', status: 'MATURED', source_type: 'SCHEDULE', extraction_confidence: 1.0, is_validated: true },
		{ id: '9', bond_id: 'BOND-009', isin: 'SG4R92000009', description: '3.60% UOB 2030', issuer: 'United Overseas Bank', currency: 'SGD', face_value: 1800000, book_value: 1795000, market_value: 1830000, coupon_rate: 3.60, accrued_interest: 16200, maturity_date: '2030-04-15', purchase_date: '2025-04-15', status: 'ACTIVE', source_type: 'UBS', extraction_confidence: 0.99, is_validated: true },
		{ id: '10', bond_id: 'BOND-010', isin: 'SG5T71000010', description: '2.50% HDB 2027', issuer: 'Housing & Development Board', currency: 'SGD', face_value: 400000, book_value: 398000, market_value: 0, coupon_rate: 2.50, accrued_interest: 0, maturity_date: '2026-07-15', purchase_date: '2022-07-15', status: 'SOLD', source_type: 'SCHEDULE', extraction_confidence: 1.0, is_validated: true }
	];

	onMount(async () => {
		try {
			const data = await getBonds(localStorage.token);
			bonds = Array.isArray(data) ? data : sampleBonds;
		} catch {
			bonds = sampleBonds;
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

	function confidenceColor(c: number): string {
		if (c >= 0.95) return 'text-emerald-600 dark:text-emerald-400';
		if (c >= 0.80) return 'text-amber-600 dark:text-amber-400';
		return 'text-red-600 dark:text-red-400';
	}

	$: totalMarket = filtered.reduce((s, b) => s + (b.market_value || 0), 0);
	$: totalFace = filtered.reduce((s, b) => s + (b.face_value || 0), 0);
	$: activeCount = filtered.filter(b => b.status === 'ACTIVE').length;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Bond Data</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Bond Data Explorer</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Normalized bond records with source traceability and validation status</p>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-8 py-6 space-y-4">
				<!-- KPI Row -->
				<div class="grid grid-cols-4 gap-4">
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
					<div class="flex items-center gap-1.5">
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
										on:click={() => { selectedBond = bond; showDetail = true; }}
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
										<td class="px-4 py-3 text-center text-xs font-mono {confidenceColor(bond.extraction_confidence)}">{(bond.extraction_confidence * 100).toFixed(0)}%</td>
										<td class="px-4 py-3 text-center">
											{#if bond.is_validated}
												<span class="text-emerald-500">✓</span>
											{:else}
												<span class="text-gray-300 dark:text-gray-600">○</span>
											{/if}
										</td>
									</tr>
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
					<div class="grid grid-cols-2 gap-4">
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
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-2">Extraction Confidence</div>
						<div class="flex items-center gap-2">
							<div class="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-2">
								<div class="bg-emerald-500 h-2 rounded-full" style="width: {selectedBond.extraction_confidence * 100}%"></div>
							</div>
							<span class="text-sm font-mono {confidenceColor(selectedBond.extraction_confidence)}">{(selectedBond.extraction_confidence * 100).toFixed(1)}%</span>
						</div>
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
