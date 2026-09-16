<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getExceptions } from '$lib/apis/finance';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let exceptions: any[] = [];
	let filterStatus = '';

	const sampleExceptions = [
		{ id: 'EXC-001', title: 'Market Value Variance — Mapletree Logistics Trust', type: 'RECONCILIATION', severity: 'HIGH', status: 'OPEN', created_at: '2026-09-16T14:41:00', bond_id: 'BOND-006', description: 'Market value differs SGD 5,200 between UBS custodian report (SGD 795,000) and LGI investment ledger (SGD 800,200). Variance exceeds SGD 1,000 materiality threshold.', root_cause: 'Timing difference: UBS uses T-1 closing price while LGI uses T+0 indicative pricing from Bloomberg.', impact: 'SGD 5,200 — Immaterial at portfolio level (0.05% of total market value) but exceeds line-item materiality threshold.', resolution: 'LGI has confirmed updated value of SGD 800,200 will be reflected in October price feed. Manual override applied for September close.', assigned_to: 'S. Lim', escalated_to: 'A. Tan' },
		{ id: 'EXC-002', title: 'Missing Bond — LGI Record Not in UBS', type: 'RECONCILIATION', severity: 'MEDIUM', status: 'RESOLVED', created_at: '2026-09-15T10:20:00', resolved_at: '2026-09-15T16:45:00', bond_id: 'BOND-011', description: 'LGI contains a record for BOND-011 (Ascendas REIT 3.15% 2029) that does not appear in the UBS custodian report.', root_cause: 'Bond was purchased on 2026-09-14 (T+1 settlement). UBS report generated before settlement completed.', impact: 'No financial impact — timing difference only.', resolution: 'Confirmed with UBS operations. Bond appeared in T+2 report. No action required.', assigned_to: 'S. Lim', resolved_by: 'S. Lim' },
		{ id: 'EXC-003', title: 'Coupon Rate Mismatch — DBS 3.25% 2028', type: 'DATA_QUALITY', severity: 'LOW', status: 'RESOLVED', created_at: '2026-09-14T09:15:00', resolved_at: '2026-09-14T11:30:00', bond_id: 'BOND-001', description: 'Extracted coupon rate shows 3.250% from UBS but LGI shows 3.252%. Difference of 0.002%.', root_cause: 'LGI stores the effective yield (3.252%) rather than the nominal coupon rate (3.250%).', impact: 'Negligible — SGD 20 per annum difference on SGD 1,000,000 face value.', resolution: 'LGI field confirmed as effective yield. System mapping updated to use nominal rate from UBS as source of truth for coupon rate.', assigned_to: 'A. Tan', resolved_by: 'A. Tan' },
		{ id: 'EXC-004', title: 'Extraction Confidence Below Threshold', type: 'EXTRACTION', severity: 'MEDIUM', status: 'OPEN', created_at: '2026-09-16T14:33:30', bond_id: 'BOND-006', description: 'AI extraction confidence for Mapletree bond (BOND-006) from LGI PDF is 92%, below the 95% auto-accept threshold.', root_cause: 'LGI PDF has non-standard formatting for this issuer — table rows are split across pages.', impact: 'Manual verification required before data can be accepted into the bond schedule.', resolution: '', assigned_to: 'S. Lim' },
		{ id: 'EXC-005', title: 'Journal Balance Check Warning', type: 'JOURNAL', severity: 'LOW', status: 'RESOLVED', created_at: '2026-09-16T14:57:00', resolved_at: '2026-09-16T15:05:00', description: 'Fair value adjustment journal initially generated with SGD 0.50 rounding difference between debits and credits.', root_cause: 'Rounding in individual bond fair value calculations accumulated to SGD 0.50 at portfolio level.', impact: 'Immaterial — sub-dollar rounding.', resolution: 'AI re-generated journal with forced balance using rounding adjustment line to GL account 9990 (Rounding Adjustments).', assigned_to: 'System', resolved_by: 'System' }
	];

	onMount(async () => {
		try {
			const data = await getExceptions(localStorage.token);
			exceptions = Array.isArray(data) ? data : sampleExceptions;
		} catch {
			exceptions = sampleExceptions;
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
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>Exceptions</span>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Exception Management</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Track, investigate, and resolve data quality issues and reconciliation breaks</p>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner /></div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-8 py-6 space-y-4">
				<!-- Summary -->
				<div class="grid grid-cols-3 gap-4">
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
				<div class="flex items-center gap-1.5">
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
								<div class="flex items-center gap-2 mb-2">
									<span class="text-xs font-mono text-gray-400">{exc.id}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {typeBadge(exc.type)}">{exc.type.replace(/_/g, ' ')}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {severityBadge(exc.severity)}">{exc.severity}</span>
									<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {statusBadge(exc.status)}">{exc.status}</span>
								</div>
								<h3 class="text-sm font-medium text-gray-900 dark:text-white mb-1">{exc.title}</h3>
								<p class="text-xs text-gray-600 dark:text-gray-400 mb-3">{exc.description}</p>

								<div class="grid grid-cols-2 gap-4 text-xs">
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

								<div class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 text-[10px] text-gray-400">
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
