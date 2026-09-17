<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import dayjs from 'dayjs';

	import { addAssessment } from '$lib/apis/clinical';
	import { avatarColor, initialsOf } from '$lib/constants/clinical';
	import type { Assessment } from '$lib/types/clinical';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	export let caseId = '';
	/** Every assessment on the case. Rendered read-only — never editable. */
	export let assessments: Assessment[] = [];
	export let disabled = false;

	// Assessments are APPEND-ONLY on the server, so this panel must never autosave:
	// a debounced save would append a new record on every typing pause. Drafts are
	// held in localStorage and only committed when the doctor presses Save.
	const DRAFT_DEBOUNCE_MS = 400;

	const draftKey = (id: string) => `clinical:assessment-draft:${id}`;

	const readDraft = (id: string): string => {
		try {
			return id ? (localStorage.getItem(draftKey(id)) ?? '') : '';
		} catch {
			return '';
		}
	};

	const persistDraft = () => {
		try {
			if (!loadedCaseId) return;
			if (body.trim() === '') localStorage.removeItem(draftKey(loadedCaseId));
			else localStorage.setItem(draftKey(loadedCaseId), body);
		} catch {
			// Private mode or blocked storage — the draft simply is not persisted.
		}
	};

	let body = '';
	let status: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
	let lastSavedBody = '';
	let lastSavedAt: number | null = null;
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	let loadedCaseId = '';

	// Assessments this session wrote. They are shown in the editor, not in the
	// read-only history, so the doctor never sees their own draft twice.
	let mySavedIds: string[] = [];

	// A new case starts a clean sheet.
	$: if (caseId !== loadedCaseId) {
		loadedCaseId = caseId;
		body = readDraft(caseId);
		lastSavedBody = '';
		lastSavedAt = null;
		mySavedIds = [];
		status = 'idle';
		if (saveTimer) {
			clearTimeout(saveTimer);
			saveTimer = null;
		}
	}

	$: priorAssessments = (assessments ?? []).filter((a) => !mySavedIds.includes(a.id));

	const authoredAt = (at?: number): string => {
		if (!at || !Number.isFinite(at)) {
			return '';
		}
		return dayjs(at > 1e12 ? at : at * 1000).format('DD MMM, HH:mm');
	};

	const save = async () => {
		const value = body.trim();

		if (disabled || caseId === '' || value === '' || value === lastSavedBody) {
			return;
		}

		status = 'saving';
		const created = await addAssessment(localStorage.token, caseId, value).catch((error) => {
			console.error(error);
			toast.error(`${error}`);
			return null;
		});

		if (!created) {
			status = 'error';
			return;
		}

		lastSavedBody = value;
		lastSavedAt = Date.now();
		status = 'saved';

		try {
			localStorage.removeItem(draftKey(loadedCaseId));
		} catch {
			// ignore
		}

		if (!mySavedIds.includes(created.id)) {
			mySavedIds = [...mySavedIds, created.id];
		}

		// Keep the case's own list in step so a later refresh does not duplicate.
		const idx = (assessments ?? []).findIndex((a) => a.id === created.id);
		if (idx === -1) {
			assessments = [...(assessments ?? []), created];
		} else {
			assessments = assessments.map((a) => (a.id === created.id ? created : a));
		}
	};

	const onInput = () => {
		status = 'idle';
		if (saveTimer) {
			clearTimeout(saveTimer);
		}
		saveTimer = setTimeout(persistDraft, DRAFT_DEBOUNCE_MS);
	};

	// Exported so the consult page can commit a pending assessment before referring.
	export const saveNow = async () => {
		if (saveTimer) {
			clearTimeout(saveTimer);
			saveTimer = null;
		}
		await save();
	};

	onDestroy(() => {
		if (saveTimer) {
			clearTimeout(saveTimer);
			saveTimer = null;
		}
		// Keep the draft locally. Committing here would append a duplicate record.
		persistDraft();
	});
</script>

<div class="flex flex-col h-full min-h-0">
	<div class="flex items-center justify-between gap-2 px-4 py-2.5 shrink-0">
		<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
			{$i18n.t('Assessment')}
		</div>

		<Tooltip content={$i18n.t('Assessments are append-only — earlier entries are never edited.')}>
			<div class="flex items-center gap-1 text-[10px] text-gray-400 dark:text-gray-600">
				<LockClosed className="size-3" />
				{$i18n.t('Append-only')}
			</div>
		</Tooltip>
	</div>

	<div class="flex-1 min-h-0 overflow-y-auto px-4 pb-3 flex flex-col gap-3">
		{#if priorAssessments.length > 0}
			<div class="flex flex-col gap-2.5">
				{#each priorAssessments as assessment (assessment.id)}
					<div
						class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-850/50 px-3 py-2.5"
					>
						<div class="flex items-center gap-2 mb-1.5">
							<div
								class="size-6 rounded-full flex items-center justify-center text-[9px] font-semibold text-white shrink-0"
								style="background-color: {avatarColor(
									assessment.author_email ?? assessment.author_name ?? ''
								)};"
							>
								{initialsOf(assessment.author_name ?? '')}
							</div>

							<div class="min-w-0 flex-1">
								<div class="text-xs font-medium text-gray-800 dark:text-gray-100 truncate">
									{assessment.author_name}
								</div>
								<div class="text-[10px] text-gray-400 dark:text-gray-600 truncate">
									{assessment.department}
									{#if authoredAt(assessment.created_at)}
										<span class="mx-1">·</span>{authoredAt(assessment.created_at)}
									{/if}
								</div>
							</div>
						</div>

						<div
							class="text-sm leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words"
						>
							{assessment.body}
						</div>
					</div>
				{/each}
			</div>

			<div class="flex items-center gap-2 pt-0.5">
				<div class="h-px flex-1 bg-gray-100 dark:bg-gray-850"></div>
				<span class="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-600">
					{$i18n.t('Your assessment')}
				</span>
				<div class="h-px flex-1 bg-gray-100 dark:bg-gray-850"></div>
			</div>
		{/if}

		<textarea
			class="w-full flex-1 min-h-40 rounded-2xl px-3.5 py-3 text-sm leading-relaxed bg-gray-50 dark:bg-gray-850 text-gray-800 dark:text-gray-100 outline-hidden resize-none placeholder:text-gray-400 dark:placeholder:text-gray-600 disabled:opacity-50"
			placeholder={$i18n.t('Your clinical assessment…')}
			aria-label={$i18n.t('Your clinical assessment')}
			bind:value={body}
			on:input={onInput}
			{disabled}
		></textarea>
	</div>

	<div
		class="flex items-center justify-between gap-2 px-4 py-2.5 border-t border-gray-100 dark:border-gray-850 shrink-0"
	>
		<div class="text-[11px] text-gray-400 dark:text-gray-600 flex items-center gap-1.5 min-w-0">
			{#if status === 'saving'}
				<Spinner className="size-3" />
				{$i18n.t('Saving…')}
			{:else if status === 'saved'}
				{$i18n.t('Saved')}
				{lastSavedAt ? dayjs(lastSavedAt).format('HH:mm') : ''}
			{:else if status === 'error'}
				<span class="text-rose-500">{$i18n.t('Could not save')}</span>
			{:else if body.trim() !== '' && body.trim() !== lastSavedBody}
				{$i18n.t('Unsaved changes')}
			{/if}
		</div>

		<button
			type="button"
			class="px-3.5 py-1.5 rounded-full text-xs font-medium bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
			disabled={disabled || status === 'saving' || body.trim() === '' || body.trim() === lastSavedBody}
			on:click={saveNow}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
