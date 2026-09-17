<script context="module" lang="ts">
	import type { Speaker } from '$lib/types/clinical';

	/** Human label for a speaker. Shared by every clinical surface. */
	export const speakerLabel = (speaker: Speaker): string =>
		speaker === 'doctor' ? 'Doctor' : 'Patient';

	/** Small pill used on staged segments and committed turns. */
	export const speakerChipClass = (speaker: Speaker): string =>
		speaker === 'doctor'
			? 'bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300'
			: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300';

	/** Conversation bubble styling — doctor and patient must never be confusable. */
	export const speakerBubbleClass = (speaker: Speaker): string =>
		speaker === 'doctor'
			? 'bg-sky-50 text-gray-800 dark:bg-sky-500/10 dark:text-gray-100 border-sky-100 dark:border-sky-500/20'
			: 'bg-gray-50 text-gray-800 dark:bg-gray-850 dark:text-gray-100 border-gray-100 dark:border-gray-800';
</script>

<script lang="ts">
	export let speaker: Speaker = 'patient';
	export let disabled = false;
	export let onChange: (speaker: Speaker) => void = () => {};

	const options: Speaker[] = ['doctor', 'patient'];

	const select = (next: Speaker) => {
		if (disabled || speaker === next) {
			return;
		}
		speaker = next;
		onChange(next);
	};
</script>

<div
	class="flex items-center gap-1 p-1 rounded-full bg-gray-50 dark:bg-gray-850 shrink-0 {disabled
		? 'opacity-50'
		: ''}"
	role="radiogroup"
	aria-label="Speaker for the next segment"
>
	{#each options as option (option)}
		{@const active = speaker === option}
		<button
			type="button"
			role="radio"
			aria-checked={active}
			{disabled}
			class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-medium transition
				{active
				? option === 'doctor'
					? 'bg-sky-600 text-white shadow-xs'
					: 'bg-emerald-600 text-white shadow-xs'
				: 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'}
				{disabled ? 'cursor-not-allowed' : ''}"
			on:click={() => select(option)}
		>
			<span
				class="size-1.5 rounded-full {active
					? 'bg-white'
					: option === 'doctor'
						? 'bg-sky-400/60'
						: 'bg-emerald-400/60'}"
			></span>
			{speakerLabel(option)}
		</button>
	{/each}
</div>
