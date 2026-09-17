<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let result: {
		title?: string;
		summary?: string;
		checksCompleted?: string[];
		details?: string;
	} = {};
	export let onRunAgain: (() => void) | null = null;

	let showDetails = false;
</script>

<section
	class="my-1.5 max-w-xl rounded-2xl border border-gray-100 bg-white px-4 py-3.5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
>
	<div class="space-y-2.5">
		<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
			{result?.title || $i18n.t('Result')}
		</div>

		{#if result?.summary}
			<div class="text-sm text-gray-700 dark:text-gray-300">{result.summary}</div>
		{/if}

		{#if (result?.checksCompleted ?? []).length > 0}
			<div>
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
					{$i18n.t('Checks completed')}
				</div>
				<ul class="mt-1 space-y-1">
					{#each result.checksCompleted as check}
						<li class="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-200">
							<span class="text-green-600 dark:text-green-500">✓</span>
							{check}
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if showDetails && result?.details}
			<div
				class="rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-white/[0.04] dark:text-gray-300"
			>
				{result.details}
			</div>
		{/if}

		<div class="flex items-center justify-end gap-2 pt-1">
			{#if result?.details}
				<button
					type="button"
					class="rounded-full py-1.5 px-3 text-xs text-gray-500 transition-colors hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100"
					on:click={() => (showDetails = !showDetails)}
				>
					{showDetails ? $i18n.t('Hide Details') : $i18n.t('View Details')}
				</button>
			{/if}
			{#if onRunAgain}
				<button
					type="button"
					class="rounded-full bg-gray-900 px-3.5 py-1.5 text-xs font-medium text-white transition hover:opacity-90 active:scale-[0.98] dark:bg-white dark:text-black"
					on:click={onRunAgain}
				>
					{$i18n.t('Run Again')}
				</button>
			{/if}
		</div>
	</div>
</section>
