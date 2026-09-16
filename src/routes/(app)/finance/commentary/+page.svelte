<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import {
		getCommentary,
		getReportingPeriods,
		generateCommentary,
		regenerateCommentary,
		updateCommentary,
		approveCommentary
	} from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let commentary: any = null;
	let editMode = false;
	let editedContent: Record<string, string> = {};
	let periods: any[] = [];
	let selectedPeriodId = '';

	$: registerAssistantContext({
		page: 'commentary',
		pageTitle: 'Commentary',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['commentary.generate', 'commentary.generate_with_movements'],
		pageData: { hasCommentary: !!commentary, sectionCount: commentary?.sections?.length ?? 0 }
	});
	let regenerating = false;
	let approving = false;
	let returning = false;
	let saving = false;
	let reviewComment = '';

	function titleCase(contentType: string): string {
		return (contentType || '')
			.split('_')
			.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
			.join(' ');
	}

	// Backend returns a flat list of commentary rows (one per content_type),
	// not the single { sections: [...] } object this page renders — reshape it.
	function toCommentaryView(rows: any[]): any {
		if (!rows.length) return null;
		const generatedAtMs = Math.max(...rows.map((r) => (r.created_at || 0) * 1000));
		const allApproved = rows.every((r) => r.status === 'APPROVED');
		return {
			id: rows[0].reporting_period_id,
			period: periods.find((p) => p.id === rows[0].reporting_period_id)?.name || rows[0].reporting_period_id,
			generated_at: generatedAtMs ? new Date(generatedAtMs).toISOString() : new Date().toISOString(),
			status: allApproved ? 'APPROVED' : 'DRAFT',
			sections: rows.map((r) => ({
				id: r.id,
				title: r.title || titleCase(r.content_type),
				content: r.content,
				ai_generated: r.generated_by === 'ai',
				status: r.status
			}))
		};
	}

	async function loadCommentary() {
		try {
			const data = await getCommentary(
				localStorage.token,
				selectedPeriodId ? { period_id: selectedPeriodId } : undefined
			);
			commentary = Array.isArray(data) ? toCommentaryView(data) : null;
		} catch (e: any) {
			commentary = null;
			toast.error(e?.message || 'Failed to load commentary');
		}
		editedContent = {};
	}

	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		await loadCommentary();
		loading = false;
	});

	async function handlePeriodChange() {
		loading = true;
		await loadCommentary();
		loading = false;
	}

	async function handleRegenerate() {
		if (!selectedPeriodId) {
			toast.error('Select a reporting period first');
			return;
		}
		regenerating = true;
		try {
			const hasRealSections = commentary?.sections?.some((s: any) => s.id);
			if (hasRealSections) {
				await Promise.all(
					commentary.sections.map((s: any) => regenerateCommentary(localStorage.token, s.id))
				);
			} else {
				await generateCommentary(localStorage.token, selectedPeriodId);
			}
			await loadCommentary();
			toast.success('Commentary regenerated');
		} catch (e: any) {
			toast.error(e?.message || 'Failed to regenerate commentary');
		}
		regenerating = false;
	}

	function handleExportPdf() {
		window.print();
	}

	function toggleEditMode() {
		if (editMode) {
			editedContent = {};
		}
		editMode = !editMode;
	}

	async function handleSaveEdits() {
		const changed = Object.entries(editedContent).filter(([, content]) => content !== undefined);
		if (!changed.length) {
			editMode = false;
			return;
		}
		saving = true;
		try {
			await Promise.all(
				changed.map(([id, content]) => updateCommentary(localStorage.token, id, { content }))
			);
			await loadCommentary();
			toast.success('Commentary saved');
			editMode = false;
		} catch (e: any) {
			toast.error(e?.message || 'Failed to save commentary');
		}
		saving = false;
	}

	async function handleApprove() {
		const ids = (commentary?.sections || []).map((s: any) => s.id).filter(Boolean);
		if (!ids.length) {
			toast.error('Nothing to approve yet — generate commentary first');
			return;
		}
		approving = true;
		try {
			await Promise.all(ids.map((id: string) => approveCommentary(localStorage.token, id)));
			await loadCommentary();
			toast.success('Commentary approved');
		} catch (e: any) {
			toast.error(e?.message || 'Failed to approve commentary');
		}
		approving = false;
	}

	async function handleReturn() {
		const ids = (commentary?.sections || []).map((s: any) => s.id).filter(Boolean);
		if (!ids.length) {
			toast.error('Nothing to return yet — generate commentary first');
			return;
		}
		returning = true;
		try {
			await Promise.all(
				ids.map((id: string) => updateCommentary(localStorage.token, id, { status: 'EDITED' }))
			);
			await loadCommentary();
			reviewComment = '';
			toast.success('Commentary returned for edits');
		} catch (e: any) {
			toast.error(e?.message || 'Failed to return commentary');
		}
		returning = false;
	}

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			DRAFT: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			REVIEWED: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
			APPROVED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Commentary</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Month-End Commentary</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-generated month-end narrative with human review and approval</p>
			</div>
			<div class="flex items-center gap-2">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={handlePeriodChange}
				>
					{#if periods.length === 0}
						<option value="">Current period</option>
					{/if}
					{#each periods as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
				<button
					on:click={handleRegenerate}
					disabled={regenerating}
					class="px-4 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center gap-2"
				>
					{#if regenerating}<Spinner className="size-3.5" />{/if}
					Regenerate
				</button>
				<button
					on:click={handleExportPdf}
					class="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
				>
					Export PDF
				</button>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else if !commentary}
		<div class="flex-1 flex items-center justify-center">
			<div class="text-center max-w-sm">
				<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">No commentary generated yet for this period.</p>
				<button
					on:click={handleRegenerate}
					disabled={regenerating}
					class="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
				>
					Generate Commentary
				</button>
			</div>
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
				<!-- Meta bar -->
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
					<div class="flex items-center gap-6">
						<div>
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Period</div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">{commentary.period}</div>
						</div>
						<div>
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Generated</div>
							<div class="text-sm text-gray-600 dark:text-gray-400">{new Date(commentary.generated_at).toLocaleDateString('en-SG')}</div>
						</div>
						<div>
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Status</div>
							<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(commentary.status)}">{commentary.status}</span>
						</div>
					</div>
					<div class="flex items-center gap-2">
						{#if editMode}
							<button
								class="px-3 py-1.5 text-xs rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
								on:click={handleSaveEdits}
								disabled={saving}
							>
								{saving ? 'Saving…' : 'Save Changes'}
							</button>
						{/if}
						<button
							class="px-3 py-1.5 text-xs rounded-lg border transition-colors {editMode ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
							on:click={toggleEditMode}
						>
							{editMode ? 'Cancel' : 'Edit Mode'}
						</button>
					</div>
				</div>

				<!-- Sections -->
				{#each commentary.sections as section, idx}
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
						<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
							<div class="flex items-center gap-2">
								<span class="text-xs font-mono text-gray-400">{String(idx + 1).padStart(2, '0')}</span>
								<h3 class="text-base font-semibold text-gray-900 dark:text-white">{section.title}</h3>
							</div>
							{#if section.ai_generated}
								<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400">
									<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
									AI Generated
								</span>
							{/if}
						</div>
						<div class="px-6 py-4">
							{#if editMode}
								<textarea
									class="w-full min-h-[120px] text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 resize-y"
									value={editedContent[section.id] ?? section.content}
									on:input={(e) => (editedContent[section.id] = e.currentTarget.value)}
								></textarea>
							{:else}
								<div class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">{section.content}</div>
							{/if}
						</div>
					</div>
				{/each}

				<!-- Approval Actions -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-6">
					<h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Approval</h3>
					<div class="flex items-center gap-3">
						<textarea
							bind:value={reviewComment}
							placeholder="Add review comments..."
							class="flex-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 resize-none h-[72px]"
						></textarea>
						<div class="flex flex-col gap-2">
							<button
								on:click={handleApprove}
								disabled={approving || commentary.status === 'APPROVED'}
								class="px-6 py-2 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
							>
								{approving ? 'Approving…' : 'Approve'}
							</button>
							<button
								on:click={handleReturn}
								disabled={returning}
								class="px-6 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
							>
								{returning ? 'Returning…' : 'Return'}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
