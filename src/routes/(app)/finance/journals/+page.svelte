<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getJournals, generateJournals, approveJournal, rejectJournal, getReportingPeriods } from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let generating = false;
	let journals: any[] = [];
	let selectedJournal: any = null;
	let showDetail = false;
	let approvalComment = '';
	let periods: any[] = [];
	let selectedPeriodId = '';

	$: registerAssistantContext({
		page: 'journals',
		pageTitle: 'Draft Journals',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		entityId: selectedJournal?.id,
		selectedRecords: selectedJournal ? [selectedJournal.id] : [],
		availableActions: ['journals.generate', 'journals.approve', 'journals.reject', 'review.pending'],
		pageData: { journalCount: journals.length }
	});

	async function loadJournals() {
		try {
			const data = await getJournals(localStorage.token, selectedPeriodId ? { period_id: selectedPeriodId } : undefined);
			journals = Array.isArray(data) ? data : [];
		} catch (e: any) {
			journals = [];
			toast.error(e?.message || 'Failed to load journals');
		}
	}

	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		await loadJournals();
		loading = false;
	});

	function formatCurrency(value: number): string {
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(value);
	}

	function getStatusBadge(status: string) {
		const map: Record<string, { class: string; label: string }> = {
			DRAFT: { class: 'bg-gray-100 text-gray-700 dark:bg-gray-600/20 dark:text-gray-400', label: 'Draft' },
			AI_GENERATED: { class: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400', label: 'AI Generated' },
			PENDING_REVIEW: { class: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400', label: 'Pending Review' },
			APPROVED: { class: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400', label: 'Approved' },
			REJECTED: { class: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400', label: 'Rejected' },
			POSTED_EXTERNALLY: { class: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400', label: 'Posted Externally' }
		};
		return map[status] || { class: 'bg-gray-100 text-gray-600', label: status };
	}

	function openDetail(journal: any) {
		selectedJournal = journal;
		showDetail = true;
	}

	async function handleApprove() {
		if (!selectedJournal) return;
		try {
			await approveJournal(localStorage.token, selectedJournal.id, approvalComment);
			toast.success('Journal approved');
			showDetail = false;
			approvalComment = '';
			await loadJournals();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to approve journal');
		}
	}

	async function handleReject() {
		if (!selectedJournal || !approvalComment) {
			toast.error('Comment is required for rejection');
			return;
		}
		try {
			await rejectJournal(localStorage.token, selectedJournal.id, approvalComment);
			toast.info('Journal rejected');
			showDetail = false;
			approvalComment = '';
			await loadJournals();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to reject journal');
		}
	}

	async function handleGenerate() {
		if (!selectedPeriodId) {
			toast.error('Select a reporting period first');
			return;
		}
		generating = true;
		try {
			await generateJournals(localStorage.token, selectedPeriodId);
			toast.success('Draft journals generated');
			await loadJournals();
		} catch (e: any) {
			toast.error(e?.message || 'Failed to generate journals');
		}
		generating = false;
	}

	$: totalDebit = journals.reduce((sum, j) => sum + j.total_debit, 0);
	$: totalCredit = journals.reduce((sum, j) => sum + j.total_credit, 0);
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Draft Journals</span>
		</div>
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
			<div>
				<h1 class="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white">Draft Accounting Journals</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-generated journal entries for finance review and approval</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={loadJournals}
				>
					{#if periods.length === 0}
						<option value="">No periods</option>
					{/if}
					{#each periods as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
				<button on:click={handleGenerate} disabled={generating} class="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2">
					{#if generating}<Spinner className="size-3.5" />{/if}
					Generate Journals
				</button>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-4">
				<!-- Summary -->
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Total Journals</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{journals.length}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Total Debits</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{formatCurrency(totalDebit)}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Balance Check</div>
						<div class="flex items-center gap-2">
							{#if totalDebit === totalCredit}
								<span class="text-emerald-600 dark:text-emerald-400 font-semibold">✓ Balanced</span>
							{:else}
								<span class="text-red-600 dark:text-red-400 font-semibold">✕ Unbalanced</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Journal Cards -->
				<div class="space-y-4">
					{#each journals as journal}
						{@const badge = getStatusBadge(journal.status)}
						<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
							<!-- Journal Header -->
							<div class="px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-gray-100 dark:border-gray-800">
								<div class="flex items-center gap-3 flex-wrap">
									<div class="text-sm font-mono font-semibold text-gray-900 dark:text-white">{journal.journal_number}</div>
									<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium {badge.class}">{badge.label}</span>
									{#if journal.is_balanced}
										<span class="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">✓ Balanced</span>
									{/if}
								</div>
								<button on:click={() => openDetail(journal)} class="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
									View Details
								</button>
							</div>

							<div class="px-5 py-3">
								<div class="text-sm text-gray-700 dark:text-gray-300 mb-3">{journal.description}</div>

								<!-- Journal Lines Table -->
								<div class="overflow-x-auto">
								<table class="w-full text-sm">
									<thead>
										<tr class="border-b border-gray-100 dark:border-gray-800">
											<th class="text-left py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">#</th>
											<th class="text-left py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Account</th>
											<th class="text-left py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Description</th>
											<th class="text-right py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Debit</th>
											<th class="text-right py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Credit</th>
											<th class="text-left py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Bond</th>
										</tr>
									</thead>
									<tbody>
										{#each journal.lines as line}
											<tr class="border-b border-gray-50 dark:border-gray-800/50">
												<td class="py-2 text-xs text-gray-400">{line.line_number}</td>
												<td class="py-2 font-mono text-xs text-gray-700 dark:text-gray-300">
													{line.account_code}
													<span class="text-gray-400 dark:text-gray-500 ml-1">{line.account_description}</span>
												</td>
												<td class="py-2 text-xs text-gray-600 dark:text-gray-400">{line.description}</td>
												<td class="py-2 text-right font-mono text-xs {line.debit > 0 ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-300 dark:text-gray-600'}">
													{line.debit > 0 ? formatCurrency(line.debit) : '-'}
												</td>
												<td class="py-2 text-right font-mono text-xs {line.credit > 0 ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-300 dark:text-gray-600'}">
													{line.credit > 0 ? formatCurrency(line.credit) : '-'}
												</td>
												<td class="py-2 text-xs text-gray-500 dark:text-gray-400 font-mono">{line.bond_id || '-'}</td>
											</tr>
										{/each}
									</tbody>
									<tfoot>
										<tr class="border-t-2 border-gray-200 dark:border-gray-700">
											<td colspan="3" class="py-2 text-xs font-medium text-gray-500 uppercase">Total</td>
											<td class="py-2 text-right font-mono text-xs font-semibold text-gray-900 dark:text-white">{formatCurrency(journal.total_debit)}</td>
											<td class="py-2 text-right font-mono text-xs font-semibold text-gray-900 dark:text-white">{formatCurrency(journal.total_credit)}</td>
											<td></td>
										</tr>
									</tfoot>
								</table>
								</div>
							</div>

							<!-- AI Rationale -->
							<div class="px-5 py-3 bg-indigo-50/50 dark:bg-indigo-500/5 border-t border-indigo-100 dark:border-indigo-500/10">
								<div class="flex items-start gap-2">
									<svg class="w-4 h-4 text-indigo-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
									<div>
										<div class="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-0.5">AI Rationale</div>
										<div class="text-xs text-indigo-800 dark:text-indigo-300/80">{journal.ai_rationale}</div>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Detail / Approval Drawer -->
	{#if showDetail && selectedJournal}
		<div class="fixed inset-0 z-50 flex justify-end" on:click|self={() => (showDetail = false)}>
			<div class="absolute inset-0 bg-black/20 dark:bg-black/40" on:click={() => (showDetail = false)}></div>
			<div class="relative w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl overflow-y-auto border-l border-gray-200 dark:border-gray-700">
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-900 z-10">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Journal Approval</h2>
					<button on:click={() => (showDetail = false)} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
					</button>
				</div>
				<div class="px-6 py-4 space-y-4">
					<div>
						<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Journal Number</div>
						<div class="text-sm font-mono font-medium text-gray-900 dark:text-white">{selectedJournal.journal_number}</div>
					</div>
					<div>
						<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Description</div>
						<div class="text-sm text-gray-700 dark:text-gray-300">{selectedJournal.description}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<div>
							<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Total Debit</div>
							<div class="text-lg font-mono font-semibold text-gray-900 dark:text-white">{formatCurrency(selectedJournal.total_debit)}</div>
						</div>
						<div>
							<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Total Credit</div>
							<div class="text-lg font-mono font-semibold text-gray-900 dark:text-white">{formatCurrency(selectedJournal.total_credit)}</div>
						</div>
					</div>
					<div class="p-3 rounded-lg {selectedJournal.is_balanced ? 'bg-emerald-50 dark:bg-emerald-500/5 border border-emerald-200 dark:border-emerald-500/20' : 'bg-red-50 dark:bg-red-500/5 border border-red-200 dark:border-red-500/20'}">
						<div class="text-sm font-medium {selectedJournal.is_balanced ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}">
							{selectedJournal.is_balanced ? '✓ Debit and Credit are balanced' : '✕ Debit and Credit are NOT balanced — approval blocked'}
						</div>
					</div>
					<div>
						<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">AI Rationale</div>
						<div class="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">{selectedJournal.ai_rationale}</div>
					</div>
					<div>
						<div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Review Comment</div>
						<textarea bind:value={approvalComment} rows="3" class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white" placeholder="Add a comment for this approval/rejection..."></textarea>
					</div>
					<div class="flex items-center gap-3 pt-2">
						<button on:click={handleApprove} disabled={!selectedJournal.is_balanced} class="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors">
							Approve
						</button>
						<button on:click={handleReject} class="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium transition-colors">
							Reject
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
