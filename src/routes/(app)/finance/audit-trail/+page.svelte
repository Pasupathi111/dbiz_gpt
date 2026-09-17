<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { get } from 'svelte/store';
	import { user } from '$lib/stores';
	import { getAuditTrail } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	let loading = true;
	let auditLogs: any[] = [];
	let filterAction = '';
	let searchQuery = '';

	$: registerAssistantContext({
		page: 'audit-trail',
		pageTitle: 'Audit Trail',
		module: 'Bond Reporting',
		availableActions: ['audit_trail.list'],
		pageData: { entryCount: auditLogs.length }
	});

	function toAuditLog(row: any) {
		return {
			id: row.id,
			timestamp: row.timestamp,
			user_name: (() => {
				const currentUser = get(user);
				const uid = row.user_id;
				if (uid === 'system' || uid === 'finance_service') return 'System';
				if (currentUser && uid === currentUser.id) return currentUser.name;
				return uid;
			})(),
			action: row.action,
			object_type: row.entity_type,
			object_id: row.entity_id,
			details: row.details,
			source: row.source || 'System'
		};
	}

	const actionColors: Record<string, string> = {
		DOCUMENT_UPLOADED: 'bg-blue-500',
		DOCUMENT_PROCESSED: 'bg-emerald-500',
		DATA_EXTRACTED: 'bg-emerald-500',
		RECONCILIATION_EXECUTED: 'bg-indigo-500',
		EXCEPTION_CREATED: 'bg-amber-500',
		MOVEMENT_DETECTED: 'bg-purple-500',
		SCHEDULE_GENERATED: 'bg-blue-500',
		JOURNAL_GENERATED: 'bg-indigo-500',
		JOURNAL_APPROVED: 'bg-emerald-500',
		DATA_EDITED: 'bg-amber-500',
		COMMENTARY_GENERATED: 'bg-violet-500'
	};

	const actions = ['DOCUMENT_UPLOADED', 'DOCUMENT_PROCESSED', 'DATA_EXTRACTED', 'RECONCILIATION_EXECUTED', 'EXCEPTION_CREATED', 'MOVEMENT_DETECTED', 'SCHEDULE_GENERATED', 'JOURNAL_GENERATED', 'JOURNAL_APPROVED', 'DATA_EDITED', 'COMMENTARY_GENERATED'];

	onMount(async () => {
		try {
			const data = await getAuditTrail(localStorage.token);
			auditLogs = Array.isArray(data) ? data.map(toAuditLog) : [];
		} catch {
			auditLogs = [];
		}
		loading = false;
	});

	$: filtered = auditLogs.filter(log => {
		if (filterAction && log.action !== filterAction) return false;
		if (searchQuery) {
			const q = searchQuery.toLowerCase();
			return log.details?.toLowerCase().includes(q) || log.user_name?.toLowerCase().includes(q) || log.object_id?.toLowerCase().includes(q);
		}
		return true;
	});

	function formatTime(ts: string): string {
		return new Date(ts).toLocaleString('en-SG', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
	}
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Audit Trail</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Audit Trail</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Complete immutable record of all finance operations and changes</p>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-4">
				<!-- Filters -->
				<div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
					<div class="relative flex-1 max-w-sm">
						<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
						<input type="text" bind:value={searchQuery} placeholder="Search audit logs..." class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400" />
					</div>
					<select bind:value={filterAction} class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300">
						<option value="">All Actions</option>
						{#each actions as action}
							<option value={action}>{action.replace(/_/g, ' ')}</option>
						{/each}
					</select>
				</div>

				<!-- Timeline -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
					<div class="divide-y divide-gray-100 dark:divide-gray-800">
						{#each filtered as log}
							<div class="px-4 sm:px-5 py-4 flex items-start gap-3 sm:gap-4 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
								<div class="mt-1 w-2.5 h-2.5 rounded-full flex-shrink-0 {actionColors[log.action] || 'bg-gray-400'}"></div>
								<div class="flex-1 min-w-0">
									<div class="flex flex-wrap items-center gap-2 mb-0.5">
										<span class="text-sm font-medium text-gray-900 dark:text-white">{log.action.replace(/_/g, ' ')}</span>
										<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-mono">{log.object_type}</span>
									</div>
									<div class="text-sm text-gray-600 dark:text-gray-400 break-words">{log.details}</div>
									<div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
										<span class="text-[10px] text-gray-400 dark:text-gray-500">{formatTime(log.timestamp)}</span>
										<span class="text-[10px] text-gray-400 dark:text-gray-500">by {log.user_name}</span>
										<span class="text-[10px] text-gray-400 dark:text-gray-500">via {log.source}</span>
									</div>
									<div class="sm:hidden text-xs text-gray-400 dark:text-gray-500 font-mono mt-1 truncate">{log.object_id}</div>
								</div>
								<div class="text-xs text-gray-400 dark:text-gray-500 font-mono flex-shrink-0 hidden sm:block">{log.object_id}</div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
