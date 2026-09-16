<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getPendingReviews } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let items: any[] = [];
	let filterType = '';
	let selectedItem: any = null;
	let showDrawer = false;
	let reviewComment = '';

	const sampleItems = [
		{ id: '1', type: 'JOURNAL', title: 'Bond Purchase Journal JV-2026-09-001', description: 'AI-generated journal for 4 new bond purchases totalling SGD 3,550,000', submitted_by: 'System', submitted_at: '2026-09-16T14:55:00', status: 'PENDING', priority: 'HIGH', amount: 3550000, details: { entries: 4, debit_total: 3550000, credit_total: 3550000, balanced: true } },
		{ id: '2', type: 'JOURNAL', title: 'Bond Maturity Journal JV-2026-09-002', description: 'AI-generated journal for 3 bond maturities with face value SGD 1,600,000', submitted_by: 'System', submitted_at: '2026-09-16T14:55:30', status: 'APPROVED', priority: 'HIGH', amount: 1600000, approved_by: 'A. Tan', approved_at: '2026-09-16T15:00:00', details: { entries: 3, debit_total: 1600000, credit_total: 1600000, balanced: true } },
		{ id: '3', type: 'JOURNAL', title: 'Accrued Interest Journal JV-2026-09-003', description: 'Monthly accrued interest calculation for 82 active bonds', submitted_by: 'System', submitted_at: '2026-09-16T14:56:00', status: 'PENDING', priority: 'MEDIUM', amount: 84024, details: { entries: 82, debit_total: 84024, credit_total: 84024, balanced: true } },
		{ id: '4', type: 'JOURNAL', title: 'Fair Value Adjustment JV-2026-09-004', description: 'FVOCI fair value adjustment through OCI reserve', submitted_by: 'System', submitted_at: '2026-09-16T14:56:30', status: 'PENDING', priority: 'MEDIUM', amount: 112000, details: { entries: 1, debit_total: 112000, credit_total: 112000, balanced: true } },
		{ id: '5', type: 'MOVEMENT', title: 'Bond Sold — HDB 2.50% 2027', description: 'BOND-010 sold at market. Gain/loss calculation requires review.', submitted_by: 'System', submitted_at: '2026-09-16T14:45:30', status: 'PENDING', priority: 'HIGH', amount: 400000, details: { bond_id: 'BOND-010', face_value: 400000, book_value: 398000, sale_proceeds: 402500, gain_loss: 4500 } },
		{ id: '6', type: 'EXCEPTION', title: 'Market Value Variance — Mapletree', description: 'BOND-006 market value differs SGD 5,200 between UBS and LGI', submitted_by: 'System', submitted_at: '2026-09-16T14:41:00', status: 'PENDING', priority: 'HIGH', amount: 5200, details: { bond_id: 'BOND-006', ubs_value: 795000, lgi_value: 800200, variance: 5200, variance_pct: 0.65 } },
		{ id: '7', type: 'COMMENTARY', title: 'September 2026 Month-End Commentary', description: 'AI-generated commentary covering portfolio movements, reconciliation, and observations', submitted_by: 'System', submitted_at: '2026-09-16T15:10:00', status: 'PENDING', priority: 'MEDIUM', amount: null, details: { sections: 6, word_count: 520 } },
		{ id: '8', type: 'MOVEMENT', title: 'Inter-Portfolio Transfer — CapitaLand', description: 'BOND-005 transferred from trading to held-to-maturity classification', submitted_by: 'S. Lim', submitted_at: '2026-09-16T14:46:00', status: 'APPROVED', priority: 'MEDIUM', amount: 750000, approved_by: 'A. Tan', approved_at: '2026-09-16T15:02:00', details: { bond_id: 'BOND-005', from_class: 'FVTPL', to_class: 'HTM' } }
	];

	onMount(async () => {
		try {
			const data = await getPendingReviews(localStorage.token);
			items = data?.items?.length ? data.items : sampleItems;
		} catch {
			items = sampleItems;
		}
		loading = false;
	});

	$: filtered = items.filter(i => !filterType || i.type === filterType);

	function typeBadge(t: string): string {
		const m: Record<string, string> = {
			JOURNAL: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400',
			MOVEMENT: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400',
			EXCEPTION: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			COMMENTARY: 'bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400'
		};
		return m[t] || 'bg-gray-100 text-gray-500';
	}

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			APPROVED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
			REJECTED: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}

	function fmt(v: number | null): string {
		if (v === null || v === undefined) return '-';
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(v);
	}

	$: pendingCount = items.filter(i => i.status === 'PENDING').length;
	$: approvedCount = items.filter(i => i.status === 'APPROVED').length;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Review & Approval</span>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Review & Approval Queue</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Human-in-the-loop review for AI-generated outputs and detected changes</p>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-8 py-6 space-y-4">
				<!-- Summary -->
				<div class="grid grid-cols-3 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Pending Review</div>
						<div class="text-2xl font-semibold text-amber-600 dark:text-amber-400 font-mono">{pendingCount}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Approved</div>
						<div class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{approvedCount}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total Items</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{items.length}</div>
					</div>
				</div>

				<!-- Type Filter -->
				<div class="flex items-center gap-1.5">
					{#each ['', 'JOURNAL', 'MOVEMENT', 'EXCEPTION', 'COMMENTARY'] as t}
						<button
							class="px-3 py-1.5 text-xs rounded-lg border transition-colors {filterType === t ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
							on:click={() => (filterType = t)}
						>
							{t || 'All'}
						</button>
					{/each}
				</div>

				<!-- Queue Items -->
				<div class="space-y-3">
					{#each filtered as item}
						<div
							class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer"
							on:click={() => { selectedItem = item; showDrawer = true; }}
						>
							<div class="px-5 py-4 flex items-start gap-4">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(item.type)}">{item.type}</span>
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(item.status)}">{item.status}</span>
										{#if item.priority === 'HIGH'}
											<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400">HIGH</span>
										{/if}
									</div>
									<h3 class="text-sm font-medium text-gray-900 dark:text-white">{item.title}</h3>
									<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{item.description}</p>
									<div class="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
										<span>Submitted by {item.submitted_by}</span>
										<span>{new Date(item.submitted_at).toLocaleString('en-SG')}</span>
										{#if item.approved_by}
											<span class="text-emerald-500">Approved by {item.approved_by}</span>
										{/if}
									</div>
								</div>
								{#if item.amount !== null}
									<div class="text-right flex-shrink-0">
										<div class="text-sm font-mono font-medium text-gray-900 dark:text-white">{fmt(item.amount)}</div>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Review Drawer -->
	{#if showDrawer && selectedItem}
		<div class="fixed inset-0 z-50 flex justify-end">
			<div class="absolute inset-0 bg-black/20 dark:bg-black/40" on:click={() => (showDrawer = false)}></div>
			<div class="relative w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl overflow-y-auto border-l border-gray-200 dark:border-gray-700">
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-900 z-10">
					<div class="flex items-center gap-2">
						<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(selectedItem.type)}">{selectedItem.type}</span>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Review</h2>
					</div>
					<button on:click={() => (showDrawer = false)} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
					</button>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<h3 class="text-base font-medium text-gray-900 dark:text-white">{selectedItem.title}</h3>
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{selectedItem.description}</p>
					</div>

					{#if selectedItem.details}
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-2">Details</div>
							{#each Object.entries(selectedItem.details) as [key, val]}
								<div class="flex items-center justify-between text-sm">
									<span class="text-gray-500 dark:text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
									<span class="font-mono text-gray-900 dark:text-white">{typeof val === 'number' && val > 1000 ? fmt(val) : val}</span>
								</div>
							{/each}
						</div>
					{/if}

					{#if selectedItem.status === 'PENDING'}
						<div class="border-t border-gray-100 dark:border-gray-800 pt-4">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Review Comments</label>
							<textarea bind:value={reviewComment} placeholder="Add your review comments..." class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 resize-none h-24"></textarea>
							<div class="flex items-center gap-2 mt-3">
								<button class="flex-1 px-4 py-2.5 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
									Approve
								</button>
								<button class="flex-1 px-4 py-2.5 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
									Reject
								</button>
							</div>
						</div>
					{:else}
						<div class="border-t border-gray-100 dark:border-gray-800 pt-4">
							<div class="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
								<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
								<span>Approved by {selectedItem.approved_by} on {new Date(selectedItem.approved_at).toLocaleString('en-SG')}</span>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
