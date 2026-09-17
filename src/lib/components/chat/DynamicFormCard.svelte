<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	type FieldSchema = {
		type?: string;
		title?: string;
		enum?: string[];
		format?: string;
	};

	type FormSchema = {
		title?: string;
		submitLabel?: string;
		properties?: Record<string, FieldSchema>;
		required?: string[];
	};

	// Generic renderer: works for ANY schema of this shape (properties + enum/
	// format hints), so one component services every agentic-form tool.
	export let show = false;
	export let title = '';
	export let submitLabel = '';
	export let schema: FormSchema = { properties: {} };
	export let prefill: Record<string, any> = {};

	let values: Record<string, any> = {};
	let wasOpen = false;

	$: fieldEntries = Object.entries(schema?.properties ?? {});
	$: requiredFields = schema?.required ?? [];

	$: if (show && !wasOpen) {
		values = { ...prefill };
		wasOpen = true;
	}
	$: if (!show && wasOpen) {
		wasOpen = false;
	}

	const fieldKind = (field: FieldSchema) => {
		if (field.type === 'boolean') return 'checkbox';
		if (Array.isArray(field.enum)) return 'select';
		if (field.format === 'textarea') return 'textarea';
		if (field.format === 'date') return 'date';
		if (field.type === 'number' || field.type === 'integer') return 'number';
		return 'text';
	};

	$: complete = requiredFields.every((key) => {
		const value = values[key];
		return value !== undefined && value !== null && String(value).trim() !== '';
	});

	const setValue = (key: string, value: any) => {
		values = { ...values, [key]: value };
	};

	const cancel = () => {
		show = false;
		dispatch('cancel');
	};

	const submit = () => {
		if (!complete) return;
		show = false;
		dispatch('confirm', values);
	};
</script>

{#if show}
	<section class="my-1 rounded-2xl bg-gray-50/70 px-3.5 py-3 dark:bg-white/[0.035]">
		<div class="space-y-2.5">
			<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{title || schema?.title || $i18n.t('Form')}
			</div>

			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
				{#each fieldEntries as [key, field]}
					{@const kind = fieldKind(field)}
					<div class="flex flex-col gap-1 {kind === 'textarea' ? 'sm:col-span-2' : ''}">
						<label
							for={`agentic-form-${key}`}
							class="text-xs text-gray-600 dark:text-gray-300"
						>
							{field.title || key}{requiredFields.includes(key) ? ' *' : ''}
						</label>

						{#if kind === 'select'}
							<select
								id={`agentic-form-${key}`}
								class="w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-800 outline-hidden dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100"
								value={values[key] ?? ''}
								on:change={(e) => setValue(key, (e.currentTarget as HTMLSelectElement).value)}
							>
								<option value="" disabled selected={!values[key]}
									>{$i18n.t('Select...')}</option
								>
								{#each field.enum ?? [] as option}
									<option value={option}>{option}</option>
								{/each}
							</select>
						{:else if kind === 'checkbox'}
							<label class="flex items-center gap-2 py-1">
								<input
									id={`agentic-form-${key}`}
									type="checkbox"
									checked={!!values[key]}
									on:change={(e) => setValue(key, (e.currentTarget as HTMLInputElement).checked)}
								/>
								<span class="text-xs text-gray-600 dark:text-gray-300">{$i18n.t('Yes')}</span>
							</label>
						{:else if kind === 'textarea'}
							<textarea
								id={`agentic-form-${key}`}
								rows="2"
								class="w-full resize-none rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-800 outline-hidden placeholder:text-gray-400 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500"
								value={values[key] ?? ''}
								on:input={(e) => setValue(key, (e.currentTarget as HTMLTextAreaElement).value)}
							></textarea>
						{:else}
							<input
								id={`agentic-form-${key}`}
								type={kind === 'date' ? 'date' : kind === 'number' ? 'number' : 'text'}
								class="w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-800 outline-hidden placeholder:text-gray-400 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500"
								value={values[key] ?? ''}
								on:input={(e) =>
									setValue(
										key,
										kind === 'number'
											? Number((e.currentTarget as HTMLInputElement).value)
											: (e.currentTarget as HTMLInputElement).value
									)}
							/>
						{/if}
					</div>
				{/each}
			</div>

			<div class="flex items-center justify-end gap-2">
				<button
					type="button"
					class="rounded-full py-1 pr-2.5 text-xs text-gray-500 transition-colors hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100"
					on:click={cancel}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="button"
					class="rounded-full bg-gray-900 px-3 py-1 text-xs font-medium text-white transition hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-black"
					disabled={!complete}
					on:click={submit}
				>
					{submitLabel || schema?.submitLabel || $i18n.t('Submit')}
				</button>
			</div>
		</div>
	</section>
{/if}
