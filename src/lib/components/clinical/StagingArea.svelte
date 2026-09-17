<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import type { StagedSegment } from '$lib/types/clinical';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	import { speakerChipClass, speakerLabel } from './SpeakerToggle.svelte';

	/** Captured but NOT yet committed to the case. Bindable. */
	export let segments: StagedSegment[] = [];
	export let disabled = false;
	export let sending = false;
	/** The page owns the transcript, so committing is delegated upward. */
	export let onSendAll: () => void = () => {};

	const flip = (id: string) => {
		segments = segments.map((segment) =>
			segment.id === id
				? { ...segment, speaker: segment.speaker === 'doctor' ? 'patient' : 'doctor' }
				: segment
		);
	};

	const remove = (id: string) => {
		segments = segments.filter((segment) => segment.id !== id);
	};

	$: sendable = segments.filter((segment) => segment.text.trim() !== '').length;
</script>

{#if segments.length > 0}
	<div
		class="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-850/40"
	>
		<div class="flex items-center justify-between gap-2 px-3 pt-2.5 pb-1.5">
			<div class="flex items-center gap-2 min-w-0">
				<span class="text-xs font-medium text-gray-700 dark:text-gray-200">
					{$i18n.t('Staged')}
					<span class="text-gray-400 dark:text-gray-600">({segments.length})</span>
				</span>
				<span class="text-xs text-gray-400 dark:text-gray-600 truncate hidden sm:inline">
					{$i18n.t('Not in the record yet — edit or re-tag before sending.')}
				</span>
			</div>

			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
				disabled={disabled || sending || sendable === 0}
				on:click={onSendAll}
			>
				{#if sending}
					<Spinner className="size-3" />
				{/if}
				{$i18n.t('Send all')}
			</button>
		</div>

		<div class="max-h-52 overflow-y-auto px-2 pb-2 flex flex-col gap-1">
			{#each segments as segment (segment.id)}
				<div
					class="group flex items-start gap-2 px-1.5 py-1.5 rounded-xl hover:bg-white dark:hover:bg-gray-900/60 transition"
				>
					<button
						type="button"
						class="mt-0.5 text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded-md shrink-0 transition {speakerChipClass(
							segment.speaker
						)}"
						title={$i18n.t('Switch speaker')}
						disabled={disabled || sending}
						on:click={() => flip(segment.id)}
					>
						{speakerLabel(segment.speaker)}
					</button>

					<Textarea
						bind:value={segment.text}
						rows={1}
						ariaLabel={$i18n.t('Staged segment text')}
						className="flex-1 min-w-0 bg-transparent text-sm leading-relaxed text-gray-800 dark:text-gray-100 outline-hidden resize-none py-0.5"
					/>

					<div class="flex items-center gap-0.5 shrink-0">
						<Tooltip content={$i18n.t('Switch speaker')}>
							<button
								type="button"
								aria-label={$i18n.t('Switch speaker')}
								class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								disabled={disabled || sending}
								on:click={() => flip(segment.id)}
							>
								<ArrowPath className="size-3.5" strokeWidth="2" />
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Delete')}>
							<button
								type="button"
								aria-label={$i18n.t('Delete')}
								class="p-1.5 rounded-lg text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								disabled={disabled || sending}
								on:click={() => remove(segment.id)}
							>
								<GarbageBin className="size-3.5" strokeWidth="2" />
							</button>
						</Tooltip>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
