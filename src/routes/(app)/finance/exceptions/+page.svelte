<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getExceptions } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let exceptions: any[] = [];
	let filterStatus = '';

	$: registerAssistantContext({
		page: 'exceptions',
		pageTitle: 'Exceptions',
		module: 'Bond Reporting',
		availableActions: ['exceptions.analyze', 'exceptions.list'],
		pageData: {
			openExceptions: exceptions.filter((e) => e.status === 'OPEN').length,
			highRiskExceptions: exceptions.filter((e) => e.status === 'OPEN' && (e.severity === 'HIGH' || e.severity === 'CRITICAL')).length
		}
	});

	function toException(row: any) {
		return {
			id: row.id,
			title: `${(row.category || 'EXCEPTION').replace(/_/g, ' ')}${row.bond_id ? ' — ' + row.bond_id : ''}`,
			type: row.category,
			severity: row.severity,
			status: row.status,
			created_at: row.created_at ? new Date(row.created_at * 1000).toISOString() : null,
			resolved_at: row.resolved_at ? new Date(row.resolved_at * 1000).toISOString() : null,
			bond_id: row.bond_id,
			description: row.description,
			root_cause: row.ai_recommendation,
			resolution: row.resolution,
			resolved_by: row.resolved_by
		};
	}

	onMount(async () => {
		try {
			const data = await getExceptions(localStorage.token);
			exceptions = Array.isArray(data) ? data.map(toException) : [];
		} catch (e: any) {
			exceptions = [];
		}
		loading = false;
	});

	$: filtered = exceptions.filter(e => !filterStatus || e.status === filterStatus);

	function severityBadge(s: string): string {
		const m: Record<string, string> = {
			HIGH: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
			LOW: 'bg-gray-100 text-gray-500 dark:bg-gray-700/30 dark:text-gray-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}

	function statusBadge(s: string): string {
		const m: Record<string, string> = {
			OPEN: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400',
			IN_PROGRESS: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
			RESOLVED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
		};
		return m[s] || 'bg-gray-100 text-gray-500';
	}

	function typeBadge(t: string): string {
		const m: Record<string, string> = {
			RECONCILIATION: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400',
			DATA_QUALITY: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400',
			EXTRACTION: 'bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400',
			JOURNAL: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400'
		};
		return m[t] || 'bg-gray-100 text-gray-500';
	}

	$: openCount = exceptions.filter(e => e.status === 'OPEN').length;
	$: resolvedCount = exceptions.filter(e => e.status === 'RESOLVED').length;
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI SCS Copilot</span><span>/</span><span>Exceptions</span>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Exception Management</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Track, investigate, and resolve data quality issues and reconciliation breaks</p>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-4">
				<!-- Summary -->
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Open Exceptions</div>
						<div class="text-2xl font-semibold text-red-600 dark:text-red-400 font-mono">{openCount}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Resolved</div>
						<div class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{resolvedCount}</div>
					</div>
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-1">Total</div>
						<div class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">{exceptions.length}</div>
					</div>
				</div>

				<!-- Filters -->
				<div class="flex flex-wrap items-center gap-1.5">
					{#each ['', 'OPEN', 'IN_PROGRESS', 'RESOLVED'] as s}
						<button
							class="px-3 py-1.5 text-xs rounded-lg border transition-colors {filterStatus === s ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}"
							on:click={() => (filterStatus = s)}
						>
							{s || 'All'}
						</button>
					{/each}
				</div>

				<!-- Exception Cards -->
				<div class="space-y-4">
					{#each filtered as exc}
						<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm {exc.status === 'OPEN' && exc.severity === 'HIGH' ? 'border-l-4 border-l-red-500' : ''}">
							<div class="px-5 py-4">
								<div class="flex flex-wrap items-center gap-2 mb-2">
									<span class="text-xs font-mono text-gray-400">{exc.id}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(exc.type)}">{exc.type.replace(/_/g, ' ')}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {severityBadge(exc.severity)}">{exc.severity}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(exc.status)}">{exc.status}</span>
								</div>
								<h3 class="text-sm font-medium text-gray-900 dark:text-white mb-1">{exc.title}</h3>
								<p class="text-xs text-gray-600 dark:text-gray-400 mb-3">{exc.description}</p>

								<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
									{#if exc.root_cause}
										<div>
											<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Root Cause</div>
											<div class="text-gray-600 dark:text-gray-400">{exc.root_cause}</div>
										</div>
									{/if}
									{#if exc.impact}
										<div>
											<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Impact</div>
											<div class="text-gray-600 dark:text-gray-400">{exc.impact}</div>
										</div>
									{/if}
									{#if exc.resolution}
										<div class="col-span-2">
											<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 mb-0.5">Resolution</div>
											<div class="text-gray-600 dark:text-gray-400">{exc.resolution}</div>
										</div>
									{/if}
								</div>

								<div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 text-[10px] text-gray-400">
									<span>Created {new Date(exc.created_at).toLocaleString('en-SG')}</span>
									{#if exc.assigned_to}<span>Assigned to {exc.assigned_to}</span>{/if}
									{#if exc.resolved_by}<span class="text-emerald-500">Resolved by {exc.resolved_by}</span>{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
