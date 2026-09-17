<script lang="ts">
	import dayjs from 'dayjs';

	import type { TranscriptTurn } from '$lib/types/clinical';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	export let turns: TranscriptTurn[] = [];
	// When true only the first `previewCount` turns are shown, behind an expander.
	export let collapsed = false;
	export let previewCount = 4;
	export let className = '';

	let expanded = false;

	// `at` may be an absolute timestamp (seconds or milliseconds) or an offset from the
	// start of the consultation — render whichever reads sensibly.
	const turnTime = (at?: number): string => {
		if (at === undefined || at === null || !Number.isFinite(at) || at <= 0) {
			return '';
		}

		if (at > 1e12) {
			return dayjs(at).format('HH:mm');
		}

		if (at > 1e9) {
			return dayjs(at * 1000).format('HH:mm');
		}

		const seconds = at > 10000 ? Math.floor(at / 1000) : Math.floor(at);
		const minutes = Math.floor(seconds / 60);
		return `${minutes}:${`${seconds % 60}`.padStart(2, '0')}`;
	};

	$: allTurns = (turns ?? []).filter((turn) => (turn?.text ?? '').trim().length > 0);
	$: showAll = !collapsed || expanded;
	$: visibleTurns = showAll ? allTurns : allTurns.slice(0, Math.max(1, previewCount));
	$: hiddenCount = Math.max(0, allTurns.length - visibleTurns.length);
</script>

<div class={className}>
	{#if allTurns.length === 0}
		<div class="text-sm text-gray-400 dark:text-gray-600 italic py-2">
			No transcript was captured for this consultation.
		</div>
	{:else}
		<div class="relative">
			<div class="flex flex-col gap-3">
				{#each visibleTurns as turn, turnIdx (turnIdx)}
					{@const isDoctor = turn.speaker === 'doctor'}
					<div class="flex w-full {isDoctor ? 'justify-start' : 'justify-end'}">
						<div class="max-w-[85%] min-w-0">
							<div
								class="flex items-baseline gap-1.5 mb-1 {isDoctor ? '' : 'justify-end'}"
							>
								<span
									class="text-[10px] font-medium uppercase tracking-wider {isDoctor
										? 'text-sky-600 dark:text-sky-400'
										: 'text-emerald-600 dark:text-emerald-400'}"
								>
									{isDoctor ? 'Doctor' : 'Patient'}
								</span>

								{#if turnTime(turn.at)}
									<span class="text-[10px] text-gray-400 dark:text-gray-600 tabular-nums">
										{turnTime(turn.at)}
									</span>
								{/if}
							</div>

							<div
								class="rounded-2xl px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words border {isDoctor
									? 'bg-sky-50 dark:bg-sky-500/10 border-sky-100 dark:border-sky-500/20 text-gray-800 dark:text-gray-100 rounded-tl-sm'
									: 'bg-gray-50 dark:bg-gray-850 border-gray-100 dark:border-gray-800 text-gray-800 dark:text-gray-100 rounded-tr-sm'}"
							>
								{turn.text}
							</div>
						</div>
					</div>
				{/each}
			</div>

			{#if hiddenCount > 0}
				<div
					class="pointer-events-none absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-white dark:from-gray-900 to-transparent"
				></div>
			{/if}
		</div>

		{#if collapsed && allTurns.length > Math.max(1, previewCount)}
			<div class="flex justify-center mt-2">
				<button
					type="button"
					class="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					on:click={() => (expanded = !expanded)}
				>
					{#if expanded}
						<ChevronUp className="size-3" />
						Collapse transcript
					{:else}
						<ChevronDown className="size-3" />
						View full transcript
						<span class="text-gray-400 dark:text-gray-600">({hiddenCount} more)</span>
					{/if}
				</button>
			</div>
		{/if}
	{/if}
</div>
