<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { v4 as uuidv4 } from 'uuid';
	import { page } from '$app/stores';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import dayjs from 'dayjs';

	import { models as modelsStore, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getModels } from '$lib/apis';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { getCase, saveStructuredNote, saveTranscript } from '$lib/apis/clinical';
	import { getSpecialistByEmail } from '$lib/constants/clinical';
	import type {
		Assessment,
		Patient,
		Speaker,
		StagedSegment,
		TranscriptTurn
	} from '$lib/types/clinical';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	import PatientHeader, { describePatient } from '$lib/components/clinical/PatientHeader.svelte';
	import SpeakerToggle from '$lib/components/clinical/SpeakerToggle.svelte';
	import StagingArea from '$lib/components/clinical/StagingArea.svelte';
	import ContinuousVoiceRecorder from '$lib/components/clinical/ContinuousVoiceRecorder.svelte';
	import AssessmentPanel from '$lib/components/clinical/AssessmentPanel.svelte';
	import ReferDialog from '$lib/components/clinical/ReferDialog.svelte';
	import TranscriptView from '$lib/components/clinical/TranscriptView.svelte';

	const MODEL_STORAGE_KEY = 'clinical-note-model';

	let caseId = '';
	let patient: Patient | null = null;
	let loadingCase = false;

	let transcript: TranscriptTurn[] = [];
	let assessments: Assessment[] = [];
	let structuredNote = '';

	let speaker: Speaker = 'patient';
	let staged: StagedSegment[] = [];
	let typed = '';
	let sendingStaged = false;
	let listening = false;

	let availableModels: any[] = [];
	let selectedModelId = '';
	let generating = false;

	let showRefer = false;
	let assessmentPanel: { saveNow: () => Promise<void> } | null = null;
	let showDiscardConfirm = false;
	let handledNewToken = '';
	let conversationElement: HTMLDivElement | null = null;

	$: ready = caseId !== '';

	const scrollToBottom = async () => {
		await tick();
		if (conversationElement) {
			conversationElement.scrollTop = conversationElement.scrollHeight;
		}
	};

	// Keep the newest turn in view as the consultation grows.
	$: transcript, staged, scrollToBottom();

	const loadCase = async () => {
		if (caseId === '') {
			return;
		}

		loadingCase = true;
		const detail = await getCase(localStorage.token, caseId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		loadingCase = false;

		if (!detail) {
			return;
		}

		transcript = detail.transcript ?? [];
		assessments = detail.assessments ?? [];
		structuredNote = detail.structured_note ?? '';
	};

	const onPatientBound = async (detail: { caseId: string; patient: Patient }) => {
		caseId = detail.caseId;
		patient = detail.patient;

		staged = [];
		typed = '';
		transcript = [];
		assessments = [];
		structuredNote = '';

		await loadCase();
	};

	const onPatientUnbound = () => {
		caseId = '';
		patient = null;
		staged = [];
		typed = '';
		transcript = [];
		assessments = [];
		structuredNote = '';
	};

	/** Captured but never committed to the record — lost if we reset now. */
	const hasUncommittedWork = (): boolean =>
		caseId !== '' && (staged.length > 0 || typed.trim() !== '');

	const startNewConsultation = () => {
		if (hasUncommittedWork()) {
			showDiscardConfirm = true;
			return;
		}
		onPatientUnbound();
	};

	/**
	 * The sidebar's "New Consultation" navigates to /consult?new=<timestamp>.
	 * Arriving from another page mounts this component fresh, but when we are
	 * ALREADY here SvelteKit reuses it — so the changing param is what tells us to
	 * start over. The param is one-shot: it is stripped as soon as it is handled
	 * (same idiom as MessageInput.svelte) so a refresh never wipes live work.
	 */
	const consumeNewParam = (token: string) => {
		if (token === '' || token === handledNewToken) {
			return;
		}
		handledNewToken = token;

		window.history.replaceState(null, '', location.pathname);
		startNewConsultation();
	};

	$: consumeNewParam($page.url.searchParams.get('new') ?? '');

	/** Everything captured — dictated or typed — lands here tagged, never committed. */
	const stage = (text: string) => {
		const value = text.trim();
		if (value === '') {
			return;
		}
		staged = [...staged, { id: uuidv4(), speaker, text: value }];
	};

	const submitTyped = () => {
		if (!ready || typed.trim() === '') {
			return;
		}
		stage(typed);
		typed = '';
	};

	const sendAll = async () => {
		const additions: TranscriptTurn[] = staged
			.filter((segment) => segment.text.trim() !== '')
			.map((segment) => ({
				speaker: segment.speaker,
				text: segment.text.trim(),
				at: Date.now()
			}));

		if (additions.length === 0) {
			return;
		}

		const next = [...transcript, ...additions];

		sendingStaged = true;
		const updated = await saveTranscript(localStorage.token, caseId, next).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		sendingStaged = false;

		if (!updated) {
			return;
		}

		transcript = updated.transcript ?? next;
		staged = [];
	};

	/**
	 * Exact payload the Workspace model preset expects: a header block, a blank
	 * line, then one `[Doctor]`/`[Patient]` labelled line per COMMITTED turn.
	 * The system prompt lives in the preset — we never send one from here.
	 */
	const buildNotePayload = (): string => {
		const me = getSpecialistByEmail($user?.email);
		const attending = me
			? `${me.name}, ${me.department}`
			: ($user?.name ?? $user?.email ?? 'Unknown');

		const header = [
			`PATIENT: ${patient ? `${patient.code} — ${describePatient(patient)}` : 'Unknown'}`,
			`DATE: ${dayjs().format('YYYY-MM-DD')}`,
			`ATTENDING: ${attending}`
		];

		const turns = transcript.map(
			(turn) => `[${turn.speaker === 'doctor' ? 'Doctor' : 'Patient'}] ${turn.text}`
		);

		return [...header, '', ...turns].join('\n');
	};

	const generateNote = async () => {
		if (!ready) {
			return;
		}

		if (transcript.length === 0) {
			toast.error($i18n.t('Send the conversation to the record first.'));
			return;
		}

		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		generating = true;
		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: selectedModelId,
				stream: false,
				messages: [{ role: 'user', content: buildNotePayload() }]
			},
			`${WEBUI_BASE_URL}/api`
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		const content = `${res?.choices?.[0]?.message?.content ?? ''}`.trim();

		if (content === '') {
			generating = false;
			if (res) {
				toast.error($i18n.t('The model returned an empty note.'));
			}
			return;
		}

		const saved = await saveStructuredNote(localStorage.token, caseId, content).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		generating = false;

		structuredNote = saved?.structured_note ?? content;
		scrollToBottom();
	};

	const onModelChange = () => {
		try {
			localStorage.setItem(MODEL_STORAGE_KEY, selectedModelId);
		} catch (error) {
			console.error(error);
		}
	};

	onMount(async () => {
		const list = await getModels(localStorage.token).catch((error) => {
			console.error(error);
			return null;
		});

		availableModels = list ?? $modelsStore ?? [];

		let remembered = '';
		try {
			remembered = localStorage.getItem(MODEL_STORAGE_KEY) ?? '';
		} catch (error) {
			console.error(error);
		}

		selectedModelId = availableModels.some((model) => model.id === remembered)
			? remembered
			: (availableModels[0]?.id ?? '');
	});
</script>

<svelte:head>
	<title>{$i18n.t('Consultation')}</title>
</svelte:head>

<ReferDialog
	bind:show={showRefer}
	{caseId}
	patientCode={patient?.code ?? ''}
	patientName={patient?.name ?? ''}
	onSent={loadCase}
/>

<ConfirmDialog
	bind:show={showDiscardConfirm}
	title={$i18n.t('Start a new consultation?')}
	message={$i18n.t(
		'This consultation has captured text that was never sent to the record. Starting a new one discards it.'
	)}
	confirmLabel={$i18n.t('Discard and start new')}
	cancelLabel={$i18n.t('Keep working')}
	on:confirm={onPatientUnbound}
/>

<div class="flex flex-col flex-1 w-full h-full min-h-0 overflow-hidden">
	<!-- Patient bar -->
	<div
		class="flex items-center justify-between gap-3 px-3 py-2 border-b border-gray-50 dark:border-gray-850 shrink-0"
	>
		<PatientHeader bind:patient onBound={onPatientBound} onUnbound={onPatientUnbound} />

		<div class="flex items-center gap-1.5 shrink-0">
			<Tooltip content={$i18n.t('Coming soon')}>
				<button
					type="button"
					class="px-3 py-1.5 rounded-full text-sm font-medium text-gray-400 dark:text-gray-600 bg-gray-50 dark:bg-gray-850 cursor-not-allowed"
					disabled
				>
					{$i18n.t('Send within department')}
				</button>
			</Tooltip>

			<button
				type="button"
				class="px-3 py-1.5 rounded-full text-sm font-medium bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
				disabled={!ready}
				on:click={async () => {
					// Commit any in-progress assessment so it travels with the referral.
					await assessmentPanel?.saveNow();
					showRefer = true;
				}}
			>
				{$i18n.t('Refer to another department')}
			</button>
		</div>
	</div>

	<!-- Conversation | Assessment -->
	<div class="flex-1 min-h-0 flex overflow-hidden">
		<div class="flex-1 min-w-0 flex flex-col min-h-0">
			<div class="flex items-center justify-between gap-2 px-4 py-2.5 shrink-0">
				<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
					{$i18n.t('Conversation')}
					{#if loadingCase}
						<Spinner className="size-3 inline-block ml-1 text-gray-400" />
					{/if}
				</div>

				<div class="flex items-center gap-1.5">
					<select
						class="text-xs rounded-lg py-1.5 px-2 bg-gray-50 dark:bg-gray-850 text-gray-600 dark:text-gray-300 outline-hidden max-w-44 disabled:opacity-50"
						bind:value={selectedModelId}
						on:change={onModelChange}
						aria-label={$i18n.t('Model for the structured note')}
						disabled={availableModels.length === 0}
					>
						{#if availableModels.length === 0}
							<option value="">{$i18n.t('No models')}</option>
						{/if}
						{#each availableModels as model (model.id)}
							<option value={model.id}>{model.name ?? model.id}</option>
						{/each}
					</select>

					<button
						type="button"
						class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-40 disabled:cursor-not-allowed"
						disabled={!ready || generating || transcript.length === 0}
						on:click={generateNote}
					>
						{#if generating}
							<Spinner className="size-3" />
						{:else}
							<Sparkles className="size-3.5" />
						{/if}
						{$i18n.t('Generate structured note')}
					</button>
				</div>
			</div>

			<div bind:this={conversationElement} class="flex-1 min-h-0 overflow-y-auto px-4 pb-4">
				{#if !ready}
					<div class="h-full flex flex-col items-center justify-center text-center gap-1.5 py-10">
						<div class="text-sm font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('No patient selected')}
						</div>
						<div class="text-xs text-gray-400 dark:text-gray-600 max-w-xs">
							{$i18n.t(
								'Search for a patient or create a new one to open a case. The conversation panel unlocks once a patient is bound.'
							)}
						</div>
					</div>
				{:else}
					{#if transcript.length === 0}
						<div class="text-sm text-gray-400 dark:text-gray-600 italic py-6 text-center">
							{$i18n.t('Nothing committed yet. Capture the conversation below, then Send all.')}
						</div>
					{:else}
						<TranscriptView turns={transcript} />
					{/if}

					{#if structuredNote}
						<div
							class="mt-5 rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-850/50 px-4 py-3"
						>
							<div class="flex items-center gap-1.5 mb-2">
								<Sparkles className="size-3.5 text-gray-400 dark:text-gray-500" />
								<span
									class="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
								>
									{$i18n.t('Structured note')}
								</span>
							</div>

							<div class="text-sm prose dark:prose-invert markdown-prose-sm min-w-full max-w-full">
								<Markdown id={`clinical-note-${caseId}`} content={structuredNote} />
							</div>
						</div>
					{/if}
				{/if}
			</div>

			<!-- Capture -->
			<div
				class="shrink-0 border-t border-gray-50 dark:border-gray-850 px-3 py-2.5 flex flex-col gap-2"
			>
				<StagingArea
					bind:segments={staged}
					disabled={!ready}
					sending={sendingStaged}
					onSendAll={sendAll}
				/>

				<div class="flex items-center gap-2">
					<SpeakerToggle bind:speaker disabled={!ready} />

					<div
						class="flex-1 min-w-0 flex items-center gap-1 px-3 py-1 rounded-full bg-gray-50 dark:bg-gray-850 {listening
							? 'hidden sm:flex'
							: ''}"
					>
						<input
							class="w-full bg-transparent text-sm py-1 outline-hidden dark:text-gray-100 disabled:cursor-not-allowed"
							placeholder={ready
								? $i18n.t('Type what was said — tagged as {{speaker}}', {
										speaker: speaker === 'doctor' ? $i18n.t('Doctor') : $i18n.t('Patient')
									})
								: $i18n.t('Select a patient to begin')}
							aria-label={$i18n.t('Type a segment')}
							bind:value={typed}
							disabled={!ready}
							on:keydown={(e) => {
								if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
									e.preventDefault();
									submitTyped();
								}
							}}
						/>

						<Tooltip content={$i18n.t('Add to staging')}>
							<button
								type="button"
								aria-label={$i18n.t('Add to staging')}
								class="p-1.5 rounded-full transition disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
								disabled={!ready || typed.trim() === ''}
								on:click={submitTyped}
							>
								<ArrowRight className="size-4" strokeWidth="2" />
							</button>
						</Tooltip>
					</div>

					<ContinuousVoiceRecorder
						bind:listening
						disabled={!ready}
						onSegment={(text) => stage(text)}
					/>
				</div>
			</div>
		</div>

		<div
			class="w-[22rem] xl:w-[26rem] shrink-0 border-l border-gray-50 dark:border-gray-850 min-h-0 hidden md:flex flex-col"
		>
			<AssessmentPanel bind:this={assessmentPanel} {caseId} bind:assessments disabled={!ready} />
		</div>
	</div>
</div>
