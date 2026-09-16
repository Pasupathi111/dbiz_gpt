<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getPendingReviews, approveOutput, rejectOutput } from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let items: any[] = [];
	let filterType = '';
	let selectedItem: any = null;
	let showDrawer = false;
	let reviewComment = '';
	let submitting = false;

	async function loadReviews() {
		try {
			const data = await getPendingReviews(localStorage.token);
			items = Array.isArray(data) ? data : [];
		} catch (e: any) {
			items = [];
			toast.error(e?.message || 'Failed to load review queue');
		}
	}

	onMount(async () => {
		await loadReviews();
		loading = false;
	});

	$: filtered = items.filter((i) => !filterType || i.output_type?.toUpperCase() === filterType);

	function typeBadge(t: string): string {
		const m: Record<string, string> = {
			JOURNAL: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400',
			MOVEMENT: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400',
			EXCEPTION: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			COMMENTARY: 'bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400'
		};
		return m[(t || '').toUpperCase()] || 'bg-gray-100 text-gray-500';
	}

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			APPROVED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
			REJECTED: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			CHANGES_REQUESTED: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400'
		};
		return m[(s || '').toUpperCase()] || 'bg-gray-100 text-gray-500';
	}

	function openDrawer(item: any) {
		selectedItem = item;
		reviewComment = '';
		showDrawer = true;
	}

	async function handleApprove() {
		if (!selectedItem) return;
		submitting = true;
		try {
			await approveOutput(localStorage.token, selectedItem.review_id || selectedItem.id, reviewComment || undefined);
			toast.success('Approved');
			showDrawer = false;
			await loadReviews();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to approve');
		}
		submitting = false;
	}

	async function handleReject() {
		if (!selectedItem) return;
		if (!reviewComment) {
			toast.error('A reason is required to reject');
			return;
		}
		submitting = true;
		try {
			await rejectOutput(localStorage.token, selectedItem.review_id || selectedItem.id, reviewComment);
			toast.info('Rejected');
			showDrawer = false;
			await loadReviews();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to reject');
		}
		submitting = false;
	}

	$: pendingCount = items.filter((i) => (i.status || '').toLowerCase() === 'pending').length;
	$: approvedCount = items.filter((i) => (i.status || '').toLowerCase() === 'approved').length;
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
							on:click={() => openDrawer(item)}
						>
							<div class="px-5 py-4 flex items-start gap-4">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(item.output_type)}">{(item.output_type || '').toUpperCase()}</span>
										<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(item.status)}">{(item.status || '').toUpperCase()}</span>
									</div>
									<h3 class="text-sm font-medium text-gray-900 dark:text-white">{item.title || `${item.output_type} ${item.output_id}`}</h3>
									<div class="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
										<span>Submitted by {item.submitted_by}</span>
										{#if item.submitted_at}<span>{new Date(item.submitted_at).toLocaleString('en-SG')}</span>{/if}
									</div>
								</div>
							</div>
						</div>
					{/each}
					{#if filtered.length === 0}
						<div class="text-center py-12 text-sm text-gray-400 dark:text-gray-500">
							No items match this filter.
						</div>
					{/if}
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
						<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(selectedItem.output_type)}">{(selectedItem.output_type || '').toUpperCase()}</span>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Review</h2>
					</div>
					<button on:click={() => (showDrawer = false)} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
					</button>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<h3 class="text-base font-medium text-gray-900 dark:text-white">{selectedItem.title || `${selectedItem.output_type} ${selectedItem.output_id}`}</h3>
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Output ID: <span class="font-mono">{selectedItem.output_id}</span></p>
					</div>

					{#if (selectedItem.status || '').toLowerCase() === 'pending'}
						<div class="border-t border-gray-100 dark:border-gray-800 pt-4">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Review Comments</label>
							<textarea bind:value={reviewComment} placeholder="Add your review comments (required to reject)..." class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 resize-none h-24"></textarea>
							<div class="flex items-center gap-2 mt-3">
								<button disabled={submitting} on:click={handleApprove} class="flex-1 px-4 py-2.5 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors">
									Approve
								</button>
								<button disabled={submitting} on:click={handleReject} class="flex-1 px-4 py-2.5 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors">
									Reject
								</button>
							</div>
						</div>
					{:else}
						<div class="border-t border-gray-100 dark:border-gray-800 pt-4">
							<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(selectedItem.status)}">{(selectedItem.status || '').toUpperCase()}</span>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
