<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	// Generic JSON-Schema-driven form card. One reusable renderer services every
	// registered form -- adding a new form to the backend registry (forms.py)
	// never requires a new Svelte component here.
	type FieldSchema = {
		type?: string;
		title?: string;
		enum?: string[];
		items?: { type?: string; enum?: string[] };
	};

	type FormSchema = {
		type?: string;
		properties?: Record<string, FieldSchema>;
		required?: string[];
	};

	type UiSchema = {
		order?: string[];
		widgets?: Record<string, string>;
		enumLabels?: Record<string, Record<string, string>>;
	};

	export let formId = '';
	export let formInstanceId = '';
	export let status: string = 'ACTIVE';
	export let payload: {
		title?: string;
		description?: string;
		submitLabel?: string;
		schema?: FormSchema;
		uiSchema?: UiSchema;
		data?: Record<string, any>;
	} = {};

	export let onSubmit: (values: Record<string, any>) => void | Promise<void> = () => {};
	export let onCancel: () => void | Promise<void> = () => {};

	$: schema = payload?.schema ?? { properties: {} };
	$: uiSchema = payload?.uiSchema ?? {};
	$: requiredFields = schema?.required ?? [];
	$: fieldOrder =
		uiSchema?.order && uiSchema.order.length > 0
			? uiSchema.order
			: Object.keys(schema?.properties ?? {});

	let values: Record<string, any> = {};
	let lastInstanceId = '';

	// Re-seed local edit state whenever the backend hands us a new/updated
	// instance (initial show, or a FORM_UPDATE patch from natural language).
	$: if (formInstanceId && (formInstanceId !== lastInstanceId || status === 'ACTIVE')) {
		values = { ...(payload?.data ?? {}) };
		lastInstanceId = formInstanceId;
	}

	const widgetFor = (key: string, field: FieldSchema) => {
		const explicit = uiSchema?.widgets?.[key];
		if (explicit) return explicit;
		if (field.type === 'array') return 'checkboxes';
		if (field.type === 'boolean') return 'radio';
		if (Array.isArray(field.enum)) return 'select';
		return 'text';
	};

	const labelFor = (key: string, value: string) => uiSchema?.enumLabels?.[key]?.[value] ?? value;

	$: complete = requiredFields.every((key) => {
		const value = values[key];
		return value !== undefined && value !== null && String(value).trim() !== '';
	});

	const setValue = (key: string, value: any) => {
		values = { ...values, [key]: value };
	};

	const toggleCheck = (key: string, option: string, checked: boolean) => {
		const current: string[] = Array.isArray(values[key]) ? values[key] : [];
		setValue(key, checked ? [...current, option] : current.filter((o) => o !== option));
	};

	const submitting = () => status === 'SUBMITTING' || status === 'SUBMITTED';
</script>

{#if status !== 'CANCELLED'}
	<section
		class="my-1.5 max-w-xl rounded-2xl border border-gray-100 bg-white px-4 py-3.5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
	>
		<div class="space-y-3">
			<div>
				<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{payload?.title || $i18n.t('Form')}
				</div>
				{#if payload?.description}
					<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
						{payload.description}
					</div>
				{/if}
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				{#each fieldOrder as key}
					{@const field = schema?.properties?.[key]}
					{#if field}
						{@const kind = widgetFor(key, field)}
						<div class="flex flex-col gap-1 {kind === 'checkboxes' ? 'sm:col-span-2' : ''}">
							<label
								for={`dynform-${formInstanceId}-${key}`}
								class="text-xs font-medium text-gray-600 dark:text-gray-300"
							>
								{field.title || key}{requiredFields.includes(key) ? ' *' : ''}
							</label>

							{#if kind === 'select'}
								<select
									id={`dynform-${formInstanceId}-${key}`}
									disabled={submitting()}
									class="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-800 outline-hidden disabled:opacity-60 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
									value={values[key] ?? ''}
									on:change={(e) => setValue(key, (e.currentTarget as HTMLSelectElement).value)}
								>
									<option value="" disabled selected={!values[key]}>{$i18n.t('Select...')}</option>
									{#each field.enum ?? [] as option}
										<option value={option}>{labelFor(key, option)}</option>
									{/each}
								</select>
							{:else if kind === 'radio'}
								<div class="flex items-center gap-4 py-1">
									{#each field.type === 'boolean' ? ['true', 'false'] : field.enum ?? [] as option}
										{@const optionValue = field.type === 'boolean' ? option === 'true' : option}
										<label class="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-200">
											<input
												type="radio"
												name={`dynform-${formInstanceId}-${key}`}
												disabled={submitting()}
												checked={values[key] === optionValue}
												on:change={() => setValue(key, optionValue)}
											/>
											{field.type === 'boolean' ? $i18n.t(option === 'true' ? 'Yes' : 'No') : labelFor(key, option)}
										</label>
									{/each}
								</div>
							{:else if kind === 'checkboxes'}
								<div class="flex flex-col gap-1.5 py-0.5">
									{#each field.items?.enum ?? [] as option}
										<label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
											<input
												type="checkbox"
												disabled={submitting()}
												checked={Array.isArray(values[key]) && values[key].includes(option)}
												on:change={(e) =>
													toggleCheck(key, option, (e.currentTarget as HTMLInputElement).checked)}
											/>
											{labelFor(key, option)}
										</label>
									{/each}
								</div>
							{:else}
								<input
									id={`dynform-${formInstanceId}-${key}`}
									type={field.type === 'number' ? 'number' : 'text'}
									disabled={submitting()}
									class="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm text-gray-800 outline-hidden placeholder:text-gray-400 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder:text-gray-500"
									value={values[key] ?? ''}
									on:input={(e) =>
										setValue(
											key,
											field.type === 'number'
												? Number((e.currentTarget as HTMLInputElement).value)
												: (e.currentTarget as HTMLInputElement).value
										)}
								/>
							{/if}
						</div>
					{/if}
				{/each}
			</div>

			<div class="flex items-center justify-end gap-2 pt-1">
				<button
					type="button"
					class="rounded-full py-1.5 px-3 text-xs text-gray-500 transition-colors hover:text-gray-800 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-100"
					disabled={submitting()}
					on:click={onCancel}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="button"
					class="rounded-full bg-gray-900 px-3.5 py-1.5 text-xs font-medium text-white transition hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-black"
					disabled={!complete || submitting()}
					on:click={() => onSubmit(values)}
				>
					{submitting() ? $i18n.t('Submitting...') : payload?.submitLabel || $i18n.t('Submit')}
				</button>
			</div>
		</div>
	</section>
{/if}
