<script context="module" lang="ts">
	import type { Patient } from '$lib/types/clinical';

	/** `Ramesh K., 54M` — age and sex are both optional. */
	export const describePatient = (p: Patient): string => {
		const detail = `${p.age ?? ''}${p.sex ?? ''}`.trim();
		return detail ? `${p.name}, ${detail}` : p.name;
	};
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { createCase, createPatient, getCases, searchPatients } from '$lib/apis/clinical';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	/** The bound patient — null until the doctor picks one. Bindable. */
	export let patient: Patient | null = null;
	/** Fired once a case exists for the chosen patient. */
	export let onBound: (detail: { caseId: string; patient: Patient }) => void = () => {};
	/** Fired when the doctor unbinds, so the page can clear the consultation. */
	export let onUnbound: () => void = () => {};

	let query = '';
	let results: Patient[] = [];
	let searching = false;
	let showResults = false;
	let binding = false;
	let searchTimer: ReturnType<typeof setTimeout> | null = null;
	let containerElement: HTMLDivElement | null = null;
	let searchInputElement: HTMLInputElement | null = null;

	let showNewPatient = false;
	let creating = false;
	let form: { code: string; name: string; age: string; sex: string } = {
		code: '',
		name: '',
		age: '',
		sex: ''
	};

	const runSearch = async (term: string) => {
		const q = term.trim();

		if (q === '') {
			results = [];
			searching = false;
			return;
		}

		searching = true;
		const res = await searchPatients(localStorage.token, q).catch((error) => {
			console.error(error);
			return null;
		});
		searching = false;

		// A slow response from an earlier keystroke must not overwrite a newer one.
		if (q !== query.trim()) {
			return;
		}

		results = res ?? [];
		showResults = true;
	};

	const onQueryInput = () => {
		showResults = true;
		if (searchTimer) {
			clearTimeout(searchTimer);
		}
		searchTimer = setTimeout(() => runSearch(query), 250);
	};

	/** Picking a patient opens a fresh case and hands the id up to the page. */
	const bindPatient = async (selected: Patient, forceNewCase = false) => {
		if (binding) {
			return;
		}

		binding = true;

		// Selecting a patient RESUMES their most recent case, so the doctor sees the
		// existing transcript and assessments instead of a blank record. A new case is
		// only opened for a patient who has none.
		const existing = forceNewCase
			? undefined
			: (await getCases(localStorage.token).catch(() => []))
					.filter((c) => c.patient_id === selected.id)
					.sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0))[0];

		const clinicalCase =
			existing ??
			(await createCase(localStorage.token, selected.id).catch((error) => {
				toast.error(`${error}`);
				return null;
			}));
		binding = false;

		if (!clinicalCase) {
			return;
		}

		patient = selected;
		query = '';
		results = [];
		showResults = false;

		onBound({ caseId: clinicalCase.id, patient: selected });
	};

	const createPatientHandler = async () => {
		if (form.code.trim() === '' || form.name.trim() === '') {
			toast.error($i18n.t('Patient ID and name are required.'));
			return;
		}

		// `type="number"` inputs bind as numbers, so coerce before trimming.
		const ageValue = String(form.age ?? '').trim();
		const age = ageValue === '' ? undefined : Number(ageValue);

		const code = form.code.trim();

		creating = true;
		let subject = await createPatient(localStorage.token, {
			code,
			name: form.name.trim(),
			age: age !== undefined && Number.isFinite(age) ? age : undefined,
			sex: form.sex === '' ? undefined : form.sex
		}).catch(() => null);

		// The code is unique, so re-entering an existing patient here is taken to mean
		// "open another case for them" rather than an error.
		if (!subject) {
			const matches = await searchPatients(localStorage.token, code).catch(() => []);
			subject = matches.find((p) => p.code.toLowerCase() === code.toLowerCase()) ?? null;
		}
		creating = false;

		if (!subject) {
			toast.error($i18n.t('Could not create or find that patient.'));
			return;
		}

		showNewPatient = false;
		form = { code: '', name: '', age: '', sex: '' };
		await bindPatient(subject, true);
	};

	/** Unbinding lets the doctor start a fresh case without reloading the page. */
	const changePatient = async () => {
		patient = null;
		query = '';
		results = [];
		onUnbound();
		await tick();
		searchInputElement?.focus();
	};

	const handleDocumentClick = (event: MouseEvent) => {
		if (containerElement && !containerElement.contains(event.target as Node)) {
			showResults = false;
		}
	};

	onMount(() => {
		document.addEventListener('click', handleDocumentClick);
	});

	onDestroy(() => {
		document.removeEventListener('click', handleDocumentClick);
		if (searchTimer) {
			clearTimeout(searchTimer);
		}
	});
</script>

<Modal size="sm" bind:show={showNewPatient}>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-1.5">
			<h1 class="text-lg font-medium self-center font-primary">{$i18n.t('New Patient')}</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					showNewPatient = false;
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="px-5 pb-5 pt-1 w-full dark:text-gray-200">
			<form
				class="flex flex-col gap-3"
				on:submit={(e) => {
					e.preventDefault();
					createPatientHandler();
				}}
			>
				<div class="flex gap-3">
					<div class="w-1/3">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Patient ID')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden"
							placeholder="P001"
							bind:value={form.code}
						/>
					</div>
					<div class="flex-1">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Name')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden"
							placeholder={$i18n.t('Full name')}
							bind:value={form.name}
						/>
					</div>
				</div>

				<div class="flex gap-3">
					<div class="w-1/3">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Age')}</div>
						<input
							type="number"
							min="0"
							max="130"
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden"
							placeholder="54"
							bind:value={form.age}
						/>
					</div>
					<div class="flex-1">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Sex')}</div>
						<select
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden"
							bind:value={form.sex}
						>
							<option value="">{$i18n.t('Not specified')}</option>
							<option value="M">M</option>
							<option value="F">F</option>
							<option value="X">X</option>
						</select>
					</div>
				</div>

				<div class="flex justify-end pt-1">
					<button
						type="button"
						on:click={createPatientHandler}
						class="px-3.5 py-2 text-sm font-medium rounded-full bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition flex items-center gap-2 disabled:opacity-50"
						disabled={creating}
					>
						{#if creating}
							<Spinner className="size-3.5" />
						{/if}
						{$i18n.t('Create & start case')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>

<div class="flex items-center gap-2 min-w-0" bind:this={containerElement}>
	{#if patient}
		<div
			class="flex items-center gap-2 min-w-0 pl-2.5 pr-1 py-1 rounded-full bg-gray-50 dark:bg-gray-850"
		>
			<UserCircleSolid className="size-5 text-gray-400 dark:text-gray-500 shrink-0" />
			<span class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
				<span class="font-mono">{patient.code}</span>
				<span class="text-gray-400 dark:text-gray-600 mx-0.5">—</span>
				{describePatient(patient)}
			</span>

			<Tooltip content={$i18n.t('Change patient')}>
				<button
					class="p-1 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
					aria-label={$i18n.t('Change patient')}
					on:click={changePatient}
				>
					<XMark className="size-3.5" />
				</button>
			</Tooltip>
		</div>
	{:else}
		<div class="relative">
			<div
				class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-50 dark:bg-gray-850 w-64 max-w-[50vw]"
			>
				{#if searching || binding}
					<Spinner className="size-3.5 text-gray-400 shrink-0" />
				{:else}
					<Search className="size-3.5 text-gray-400 shrink-0" strokeWidth="2" />
				{/if}
				<input
					bind:this={searchInputElement}
					bind:value={query}
					on:input={onQueryInput}
					on:focus={() => {
						showResults = true;
					}}
					on:keydown={(e) => {
						if (e.key === 'Escape') {
							showResults = false;
						}
						if (e.key === 'Enter' && results.length > 0) {
							e.preventDefault();
							bindPatient(results[0]);
						}
					}}
					class="w-full bg-transparent text-sm outline-hidden dark:text-gray-100"
					placeholder={$i18n.t('Search patient by ID or name')}
					aria-label={$i18n.t('Search patient by ID or name')}
					disabled={binding}
				/>
			</div>

			{#if showResults && query.trim() !== ''}
				<div
					class="absolute left-0 top-full mt-1.5 w-80 max-w-[80vw] z-50 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-850 shadow-lg overflow-hidden"
				>
					{#if results.length === 0}
						<div class="px-3.5 py-3 text-xs text-gray-500">
							{searching ? $i18n.t('Searching...') : $i18n.t('No patients found.')}
						</div>
					{:else}
						<div class="max-h-72 overflow-y-auto py-1">
							{#each results as result (result.id)}
								<button
									class="w-full text-left px-3.5 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition flex items-center gap-2.5"
									on:click={() => bindPatient(result)}
								>
									<span
										class="font-mono text-xs px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 shrink-0"
									>
										{result.code}
									</span>
									<span class="text-sm text-gray-800 dark:text-gray-100 truncate">
										{describePatient(result)}
									</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<button
			class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition shrink-0"
			on:click={() => {
				showNewPatient = true;
			}}
		>
			<Plus className="size-3.5" />
			{$i18n.t('New Patient')}
		</button>
	{/if}
</div>
