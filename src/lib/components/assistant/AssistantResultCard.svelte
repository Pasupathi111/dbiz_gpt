<script lang="ts">
	/**
	 * Structured result card renderer for the Global Agentic Assistant.
	 *
	 * `action` is the backend AGENT_TOOLS name (e.g. "reconciliation.run"),
	 * `result` is the real (already-parsed) object the /agent/execute
	 * endpoint returned — no JSON.parse needed. One layout per known action,
	 * generic key/value fallback for anything else, so adding a new backend
	 * tool never requires touching this file to "not crash" — it just gets
	 * the generic view until a dedicated layout is added.
	 */
	export let action: string;
	export let result: any;

	function fmt(v: any): string {
		if (v === null || v === undefined || v === '') return '—';
		if (typeof v === 'number') return v.toLocaleString('en-SG');
		return String(v);
	}

	function fmtMoney(v: any): string {
		if (v === null || v === undefined) return '—';
		const n = Number(v);
		if (Number.isNaN(n)) return String(v);
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(n);
	}

	function movementBadgeClass(t: string): string {
		const m: Record<string, string> = {
			PURCHASE: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
			NEW: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
			SALE: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
			SOLD: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
			MATURITY: 'bg-gray-200 text-gray-700 dark:bg-gray-600/30 dark:text-gray-400',
			MATURED: 'bg-gray-200 text-gray-700 dark:bg-gray-600/30 dark:text-gray-400',
			TRANSFER: 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400',
			TRANSFERRED: 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400',
			VALUE_CHANGE: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
			ACCRUAL: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400'
		};
		return m[(t || '').toUpperCase()] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
	}

	function severityBadgeClass(s: string): string {
		const m: Record<string, string> = {
			HIGH: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
			CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
			MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
			LOW: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
		};
		return m[(s || '').toUpperCase()] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
	}

	$: steps = Array.isArray(result?.steps) ? result.steps : null;
	$: summaryText = typeof result?.summary_text === 'string' ? result.summary_text : null;
</script>

<div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
	<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center gap-1.5">
		<svg class="w-3 h-3 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
			<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17l-5.658 3.163 1.078-6.29L1.34 6.82l6.328-.92L11.42.956l2.752 5.944 6.328.92-4.5 5.223 1.078 6.29z" />
		</svg>
		<span class="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{action}</span>
	</div>

	<div class="p-3">
		{#if steps}
			<div class="mb-3 space-y-1">
				{#each steps as step}
					<div class="flex items-center gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
						<span class="text-emerald-500">✓</span>
						<span>{step.label}</span>
					</div>
				{/each}
			</div>
		{/if}

		{#if !result}
			<p class="text-xs text-gray-500 dark:text-gray-400">No structured data returned.</p>

		{:else if action === 'reconciliation.run' || action === 'reconciliation.run_and_summarize'}
			<div class="grid grid-cols-4 gap-2 mb-3">
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2 text-center">
					<div class="text-lg font-semibold font-mono text-gray-900 dark:text-white">{fmt(result.total_bonds)}</div>
					<div class="text-[9px] uppercase tracking-wider text-gray-400">Total</div>
				</div>
				<div class="rounded-lg bg-emerald-50 dark:bg-emerald-500/10 p-2 text-center">
					<div class="text-lg font-semibold font-mono text-emerald-600 dark:text-emerald-400">{fmt(result.matched)}</div>
					<div class="text-[9px] uppercase tracking-wider text-emerald-600/70 dark:text-emerald-400/70">Matched</div>
				</div>
				<div class="rounded-lg bg-amber-50 dark:bg-amber-500/10 p-2 text-center">
					<div class="text-lg font-semibold font-mono text-amber-600 dark:text-amber-400">{fmt(result.variances)}</div>
					<div class="text-[9px] uppercase tracking-wider text-amber-600/70 dark:text-amber-400/70">Variances</div>
				</div>
				<div class="rounded-lg bg-red-50 dark:bg-red-500/10 p-2 text-center">
					<div class="text-lg font-semibold font-mono text-red-600 dark:text-red-400">{fmt(result.missing)}</div>
					<div class="text-[9px] uppercase tracking-wider text-red-600/70 dark:text-red-400/70">Missing</div>
				</div>
			</div>
			<div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
				<div
					class="h-2 rounded-full {result.match_rate >= 95 ? 'bg-emerald-500' : result.match_rate >= 80 ? 'bg-amber-500' : 'bg-red-500'}"
					style="width: {Math.min(result.match_rate ?? 0, 100)}%"
				></div>
			</div>
			<div class="text-[10px] text-gray-400 mt-1 text-right">{fmt(result.match_rate)}% match rate</div>

		{:else if action === 'reconciliation.summary'}
			<div class="grid grid-cols-2 gap-2">
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Total Bonds</div><div class="font-mono font-semibold text-gray-900 dark:text-white">{fmt(result.total_bonds)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Matched</div><div class="font-mono font-semibold text-emerald-600 dark:text-emerald-400">{fmt(result.matched)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Exceptions</div><div class="font-mono font-semibold text-amber-600 dark:text-amber-400">{fmt(result.exceptions)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Match Rate</div><div class="font-mono font-semibold text-gray-900 dark:text-white">{result.match_rate != null ? result.match_rate + '%' : '—'}</div></div>
			</div>

		{:else if action === 'exceptions.analyze'}
			<div class="flex items-center gap-3 mb-2 text-xs">
				<span><span class="font-semibold text-gray-900 dark:text-white">{fmt(result.open_count)}</span> open</span>
				<span><span class="font-semibold text-gray-900 dark:text-white">{fmt(result.total)}</span> total</span>
			</div>
			{#if result.by_severity && Object.keys(result.by_severity).length}
				<div class="flex flex-wrap gap-1.5 mb-2">
					{#each Object.entries(result.by_severity) as [sev, count]}
						<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium {severityBadgeClass(sev)}">{sev}: {count}</span>
					{/each}
				</div>
			{/if}
			{#if Array.isArray(result.exceptions) && result.exceptions.length}
				<div class="space-y-1.5 max-h-48 overflow-y-auto">
					{#each result.exceptions as e}
						<div class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
							<span class="inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-medium flex-shrink-0 {severityBadgeClass(e.severity)}">{e.severity}</span>
							<span class="text-[11px] text-gray-700 dark:text-gray-300 truncate">{e.description || e.category}</span>
						</div>
					{/each}
				</div>
			{/if}

		{:else if action === 'exceptions.list'}
			{#if Array.isArray(result.exceptions) && result.exceptions.length}
				<div class="space-y-1.5 max-h-48 overflow-y-auto">
					{#each result.exceptions as e}
						<div class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
							<span class="inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-medium flex-shrink-0 {severityBadgeClass(e.severity)}">{e.severity}</span>
							<span class="text-[11px] text-gray-700 dark:text-gray-300 truncate">{e.description || e.category}</span>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-xs text-gray-500 dark:text-gray-400">No open exceptions.</p>
			{/if}

		{:else if action === 'movements.analyze' || action === 'movements.list'}
			{@const movements = result.movements || []}
			<div class="text-xs text-gray-600 dark:text-gray-400 mb-2"><span class="font-semibold text-gray-900 dark:text-white">{fmt(result.movements_created ?? movements.length)}</span> movement(s)</div>
			{#if movements.length}
				<div class="space-y-1.5 max-h-48 overflow-y-auto">
					{#each movements as m}
						<div class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
							<span class="font-mono text-[11px] text-gray-700 dark:text-gray-300 truncate">{m.bond_id}</span>
							<span class="inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-medium flex-shrink-0 {movementBadgeClass(m.movement_type)}">{m.movement_type}</span>
							<span class="text-[11px] font-mono text-gray-500 dark:text-gray-400 flex-shrink-0">{fmtMoney(m.variance)}</span>
						</div>
					{/each}
				</div>
			{/if}

		{:else if action === 'schedule.generate'}
			<div class="rounded-lg bg-indigo-50 dark:bg-indigo-500/10 p-3 text-center">
				<div class="text-2xl font-semibold font-mono text-indigo-600 dark:text-indigo-400">{fmt(result.lines_generated)}</div>
				<div class="text-[10px] uppercase tracking-wider text-indigo-600/70 dark:text-indigo-400/70">Schedule Lines Generated</div>
			</div>

		{:else if action === 'schedule.validate'}
			<div class="flex items-center gap-2 mb-2 text-xs">
				<span
					class="font-semibold {result.validation_status === 'passed'
						? 'text-emerald-600 dark:text-emerald-400'
						: result.validation_status === 'warning'
							? 'text-amber-600 dark:text-amber-400'
							: 'text-red-600 dark:text-red-400'}"
				>
					{(result.validation_status || 'unknown').toUpperCase()}
				</span>
			</div>
			{#if Array.isArray(result.checks)}
				<div class="space-y-1">
					{#each result.checks as c}
						<div class="flex items-center justify-between text-[11px]">
							<span class="text-gray-500 dark:text-gray-400 capitalize">{c.check.replace(/_/g, ' ')}</span>
							<span class="font-mono {c.status === 'passed' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}">{c.status}</span>
						</div>
					{/each}
				</div>
			{/if}

		{:else if action === 'journals.generate'}
			<div class="rounded-lg bg-indigo-50 dark:bg-indigo-500/10 p-3 text-center">
				<div class="text-2xl font-semibold font-mono text-indigo-600 dark:text-indigo-400">{fmt(result.journals_created)}</div>
				<div class="text-[10px] uppercase tracking-wider text-indigo-600/70 dark:text-indigo-400/70">Journal(s) Created</div>
			</div>

		{:else if action === 'journals.approve' || action === 'journals.reject'}
			<div class="text-xs text-gray-700 dark:text-gray-300">Journal {result.journal_number || result.id}: <span class="font-semibold">{result.status}</span></div>

		{:else if action === 'audit_schedule.generate'}
			<div class="rounded-lg bg-indigo-50 dark:bg-indigo-500/10 p-3 text-center">
				<div class="text-2xl font-semibold font-mono text-indigo-600 dark:text-indigo-400">{fmt(result.entries_created)}</div>
				<div class="text-[10px] uppercase tracking-wider text-indigo-600/70 dark:text-indigo-400/70">Audit Entries Created</div>
			</div>

		{:else if action === 'commentary.generate'}
			<div class="flex flex-wrap gap-1.5">
				{#each (result.sections || []) as s}
					<span class="inline-flex px-2 py-1 rounded-full text-[10px] font-medium bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400">{String(s).replace(/_/g, ' ')}</span>
				{/each}
			</div>

		{:else if action === 'commentary.generate_with_movements'}
			{@const commentary = result.commentary || {}}
			<div class="flex flex-wrap gap-1.5 mb-2">
				{#each (commentary.sections || []) as s}
					<span class="inline-flex px-2 py-1 rounded-full text-[10px] font-medium bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400">{String(s).replace(/_/g, ' ')}</span>
				{/each}
			</div>
			{#if Array.isArray(result.unusual_movements) && result.unusual_movements.length}
				<div class="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Unusual Movements</div>
				<div class="space-y-1.5 max-h-40 overflow-y-auto">
					{#each result.unusual_movements as m}
						<div class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
							<span class="font-mono text-[11px] text-gray-700 dark:text-gray-300 truncate">{m.bond_id}</span>
							<span class="inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-medium flex-shrink-0 {movementBadgeClass(m.movement_type)}">{m.movement_type}</span>
							<span class="text-[11px] font-mono text-gray-500 dark:text-gray-400 flex-shrink-0">{fmtMoney(m.variance)}</span>
						</div>
					{/each}
				</div>
			{/if}

		{:else if action === 'commentary.approve'}
			<div class="text-xs text-gray-700 dark:text-gray-300">Status: <span class="font-semibold">{result.status}</span></div>

		{:else if action === 'review.pending'}
			{@const reviews = result.reviews || []}
			<div class="text-xs text-gray-600 dark:text-gray-400 mb-2"><span class="font-semibold text-gray-900 dark:text-white">{reviews.length}</span> pending</div>
			{#if reviews.length}
				<div class="space-y-1.5 max-h-48 overflow-y-auto">
					{#each reviews as r}
						<div class="px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
							<div class="flex items-center gap-2">
								<span class="inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400">{(r.output_type || '').toUpperCase()}</span>
								<span class="text-[11px] text-gray-700 dark:text-gray-300 truncate">{r.title || r.output_id}</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}

		{:else if action === 'review.approve' || action === 'review.reject'}
			<div class="text-xs text-gray-700 dark:text-gray-300">Review {result.review_id}: <span class="font-semibold">{result.status}</span></div>

		{:else if action === 'audit_trail.list'}
			{@const entries = result.entries || []}
			<div class="space-y-1.5 max-h-48 overflow-y-auto">
				{#each entries.slice(0, 10) as e}
					<div class="flex items-center justify-between px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800">
						<span class="text-[11px] font-mono text-gray-700 dark:text-gray-300 truncate">{e.action}</span>
						<span class="text-[10px] text-gray-400 flex-shrink-0">{e.source}</span>
					</div>
				{/each}
			</div>

		{:else if action === 'portfolio.summary'}
			{@const kpis = result.kpis || result}
			<div class="grid grid-cols-2 gap-2">
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Bonds</div><div class="font-mono font-semibold text-gray-900 dark:text-white">{fmt(kpis.total_bonds)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Market Value</div><div class="font-mono font-semibold text-gray-900 dark:text-white">{fmt(kpis.total_market_value)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Open Exceptions</div><div class="font-mono font-semibold text-amber-600 dark:text-amber-400">{fmt(kpis.exceptions_open)}</div></div>
				<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-2"><div class="text-[9px] uppercase text-gray-400">Match Rate</div><div class="font-mono font-semibold text-gray-900 dark:text-white">{fmt(kpis.recon_rate)}</div></div>
			</div>

		{:else}
			<div class="space-y-1">
				{#each Object.entries(result).slice(0, 8) as [k, v]}
					{#if typeof v !== 'object'}
						<div class="flex items-center justify-between text-[11px]">
							<span class="text-gray-400 capitalize">{k.replace(/_/g, ' ')}</span>
							<span class="font-mono text-gray-700 dark:text-gray-300">{fmt(v)}</span>
						</div>
					{/if}
				{/each}
			</div>
		{/if}

		{#if summaryText}
			<div class="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800 text-[11px] text-gray-600 dark:text-gray-400 leading-relaxed">
				{summaryText}
			</div>
		{/if}
	</div>
</div>
