<script lang="ts">
	// Reusable "Live" indicator used across Dashboard, AI Assistant, Upload
	// Document, Bond Data and Reconciliation to signal live data/processing.
	export let label: string = 'Live';
	export let title: string = 'Connected to live data';
	export let size: 'xs' | 'sm' = 'xs';
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 {size === 'sm'
		? 'text-xs px-2.5 py-1'
		: 'text-[10px] px-2 py-0.5'}"
	{title}
>
	<span class="relative flex h-1.5 w-1.5 flex-shrink-0">
		<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
		<span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
	</span>
	{label}
</span>
