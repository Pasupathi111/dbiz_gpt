<script lang="ts">
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { config, type Model, models, settings, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { addAssessment, getCase, getPatient } from '$lib/apis/clinical';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	import type {
		Assessment,
		CaseDetail,
		Patient,
		Referral,
		TranscriptTurn
	} from '$lib/types/clinical';
	import { avatarColor, initialsOf } from '$lib/constants/clinical';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import ChainTimeline from '$lib/components/clinical/ChainTimeline.svelte';
	import TranscriptView from '$lib/components/clinical/TranscriptView.svelte';
	import ReferDialog from '$lib/components/clinical/ReferDialog.svelte';

	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	let caseDetail: CaseDetail | null = null;
	// Age/sex are not carried on the case payload — fetched alongside it for the header.
	let patient: Patient | null = null;
	let loading = true;
	let error = '';

	let assessmentBody = '';
	let savingAssessment = false;

	let showReferDialog = false;

	let summary = '';
	let summaryError = '';
	let summarizing = false;

	const toMs = (at?: number | null): number => {
		if (!at || !Number.isFinite(at)) return 0;
		return at > 1e12 ? at : at * 1000;
	};

	$: caseId = $page.params.id ?? '';
	$: myEmail = ($user?.email ?? '').toLowerCase();

	const load = async (id: string) => {
		if (!id) return;

		loading = true;
		error = '';

		const res = await getCase(localStorage.token, id).catch((err: unknown) => {
			error = `${err}`;
			return null;
		});

		if (res) {
			caseDetail = res;

			if (res.patient_id) {
				patient = await getPatient(localStorage.token, res.patient_id).catch(() => null);
			}
		}

		loading = false;
	};

	// ---- patient identity -------------------------------------------------

	// `54M` — both halves are optional, so the header degrades to just the name.
	const demographicsOf = (
		detail: CaseDetail | null,
		patientRecord: Patient | null
	): string => {
		const loose = (detail ?? {}) as unknown as Record<string, unknown>;
		const age = patientRecord?.age ?? loose.patient_age ?? loose.age;
		const sex = patientRecord?.sex ?? loose.patient_sex ?? loose.sex;

		const ageShort =
			typeof age === 'number' || (typeof age === 'string' && age.trim().length > 0)
				? `${age}`.trim()
				: '';
		const sexShort =
			typeof sex === 'string' && sex.trim().length > 0 ? sex.trim()[0].toUpperCase() : '';

		return `${ageShort}${sexShort}`;
	};

	$: demographics = demographicsOf(caseDetail, patient);

	$: patientLine = caseDetail
		? `${caseDetail.patient_code} — ${caseDetail.patient_name}${
				demographics ? `, ${demographics}` : ''
			}`
		: '';

	// ---- derived case data ------------------------------------------------

	$: orderedReferrals = [...(caseDetail?.referrals ?? [])].sort(
		(a: Referral, b: Referral) => (a?.created_at ?? 0) - (b?.created_at ?? 0)
	);

	$: latestReferral =
		orderedReferrals.length > 0 ? orderedReferrals[orderedReferrals.length - 1] : null;

	// The note is only "addressed to me" when the most recent hop targets me.
	$: noteToMe =
		latestReferral &&
		myEmail !== '' &&
		(latestReferral.to_email ?? '').toLowerCase() === myEmail &&
		(latestReferral.note ?? '').trim().length > 0
			? latestReferral
			: null;

	$: orderedAssessments = [...(caseDetail?.assessments ?? [])].sort(
		(a: Assessment, b: Assessment) => (a?.created_at ?? 0) - (b?.created_at ?? 0)
	);

	// Append-only: one assessment per doctor, never editable once written.
	$: myAssessment =
		myEmail === ''
			? undefined
			: orderedAssessments.find(
					(assessment) => (assessment.author_email ?? '').toLowerCase() === myEmail
				);

	$: transcript = (caseDetail?.transcript ?? []) as TranscriptTurn[];

	// ---- assessment -------------------------------------------------------

	const saveAssessmentHandler = async () => {
		if (!caseDetail || savingAssessment) return;

		const body = assessmentBody.trim();
		if (!body) {
			toast.error('Write your assessment before saving.');
			return;
		}

		savingAssessment = true;

		const res = await addAssessment(localStorage.token, caseDetail.id, body).catch(
			(err: unknown) => {
				toast.error(`${err}`);
				return null;
			}
		);

		savingAssessment = false;

		if (res) {
			assessmentBody = '';
			toast.success('Assessment added');
			await load(caseDetail.id);
		}
	};

	// ---- summarize --------------------------------------------------------

	// Prefer the "Clinical Intake" workspace preset; fall back to the user's default model.
	const resolveSummaryModel = (
		candidates: Model[],
		preferredIds: string[],
		defaultModels: string
	): string => {
		if (candidates.length === 0) return '';

		const clinical = candidates.find((model) =>
			`${model?.name ?? ''} ${model?.id ?? ''}`.toLowerCase().includes('clinical')
		);
		if (clinical) return clinical.id;

		const preferred = preferredIds[0] ?? defaultModels.split(',')[0] ?? '';
		if (preferred && candidates.some((model) => model.id === preferred)) return preferred;

		return candidates[0].id;
	};

	$: availableModels = ($models ?? []).filter(
		(model) => model?.id && !(model?.info?.meta?.hidden ?? false)
	);

	$: summaryModelId = resolveSummaryModel(
		availableModels,
		$settings?.models ?? [],
		$config?.default_models ?? ''
	);

	$: canSummarize = !!summaryModelId && transcript.length > 0;

	const buildSummaryPrompt = (detail: CaseDetail): string => {
		const header = [
			`PATIENT: ${patientLine}`,
			`DATE: ${dayjs(toMs(detail.created_at)).format('YYYY-MM-DD')}`,
			`ATTENDING: ${detail.created_by_name}, ${detail.department}`
		].join('\n');

		const turns = (detail.transcript ?? [])
			.filter((turn) => (turn?.text ?? '').trim().length > 0)
			.map((turn) => `[${turn.speaker === 'doctor' ? 'Doctor' : 'Patient'}] ${turn.text.trim()}`)
			.join('\n');

		return `${header}\n\n${turns}\n\nSummarise the above in no more than five bullet points for a specialist who has not seen this patient.`;
	};

	const summarizeHandler = async () => {
		if (!caseDetail || summarizing || !canSummarize) return;

		summarizing = true;
		summaryError = '';

		try {
			const res = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: summaryModelId,
					stream: false,
					messages: [
						{
							role: 'user',
							content: buildSummaryPrompt(caseDetail)
						}
					]
				},
				`${WEBUI_BASE_URL}/api`
			);

			const content = `${res?.choices?.[0]?.message?.content ?? ''}`.trim();

			if (content) {
				summary = content;
			} else {
				summaryError = 'The model returned an empty summary.';
			}
		} catch (err) {
			summaryError = `${err}`;
		} finally {
			summarizing = false;
		}
	};

	// ---- lifecycle --------------------------------------------------------

	let loadedCaseId = '';
	$: if (caseId && caseId !== loadedCaseId) {
		loadedCaseId = caseId;
		summary = '';
		summaryError = '';
		assessmentBody = '';
		patient = null;
		load(caseId);
	}
</script>

<svelte:head>
	<title>{caseDetail ? `${caseDetail.patient_code} — ${caseDetail.patient_name}` : 'Case'}</title>
</svelte:head>

<div class="w-full">
	<!-- Patient identity: pinned, always visible -->
	<div
		class="sticky top-0 z-20 border-b border-gray-50 dark:border-gray-850 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm"
	>
		<div class="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
			<a
				href="/consult/inbox"
				class="shrink-0 p-1.5 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				aria-label="Back to inbox"
			>
				<ArrowLeft className="size-4" />
			</a>

			<div class="min-w-0 flex-1">
				{#if caseDetail}
					<div class="text-base font-medium text-gray-900 dark:text-white truncate">
						{patientLine}
					</div>
					<div class="text-[11px] text-gray-500 dark:text-gray-400 truncate">
						Opened by {caseDetail.created_by_name} · {caseDetail.department} ·
						{caseDetail.created_at ? dayjs(toMs(caseDetail.created_at)).format('LL') : ''}
					</div>
				{:else}
					<div class="text-base font-medium text-gray-400 dark:text-gray-600">Case</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="max-w-6xl mx-auto px-4 md:px-6 py-5">
		{#if loading && !caseDetail}
			<div class="w-full flex justify-center items-center py-24">
				<Spinner className="size-5" />
			</div>
		{:else if error && !caseDetail}
			<div
				class="rounded-2xl border border-red-100 dark:border-red-500/20 bg-red-50 dark:bg-red-500/10 px-4 py-5 text-sm text-red-700 dark:text-red-300"
			>
				<div class="font-medium mb-1">Could not load this case</div>
				<div class="text-xs opacity-80 break-words">{error}</div>
				<div class="flex items-center gap-2 mt-3">
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 rounded-full bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={() => load(caseId)}
					>
						Try again
					</button>
					<a
						href="/consult/inbox"
						class="text-xs font-medium px-3 py-1.5 rounded-full hover:bg-white/60 dark:hover:bg-gray-900/60 transition"
					>
						Back to inbox
					</a>
				</div>
			</div>
		{:else if caseDetail}
			<div class="flex flex-col lg:flex-row gap-6">
				<!-- Main column -->
				<div class="flex-1 min-w-0 flex flex-col gap-5">
					<!-- (a) the note addressed to me -->
					{#if noteToMe}
						<div
							class="rounded-2xl border border-amber-200/70 dark:border-amber-500/25 bg-amber-50 dark:bg-amber-500/10 px-4 py-3.5"
						>
							<div class="flex items-center gap-2 mb-1.5 flex-wrap">
								<span
									class="size-6 shrink-0 rounded-full flex items-center justify-center text-[10px] font-semibold text-white select-none"
									style="background-color: {avatarColor(noteToMe.from_name ?? '')}"
									aria-hidden="true"
								>
									{initialsOf(noteToMe.from_name ?? '')}
								</span>
								<div class="text-xs font-medium text-amber-900 dark:text-amber-200">
									Note from {noteToMe.from_name}
								</div>
								<div class="text-[11px] text-amber-700/70 dark:text-amber-300/60">
									{noteToMe.from_department} ·
									{noteToMe.created_at ? dayjs(toMs(noteToMe.created_at)).fromNow() : ''}
								</div>
							</div>
							<div
								class="text-sm leading-relaxed text-amber-950 dark:text-amber-100 whitespace-pre-wrap break-words"
							>
								{noteToMe.note}
							</div>
						</div>
					{/if}

					<!-- (b) structured note -->
					{#if (caseDetail.structured_note ?? '').trim()}
						<div class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-4">
							<div
								class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2.5"
							>
								Consultation record
							</div>
							<div class="markdown-prose">
								<Markdown id={`case-note-${caseDetail.id}`} content={caseDetail.structured_note} />
							</div>
						</div>
					{:else}
						<div
							class="rounded-2xl border border-dashed border-gray-100 dark:border-gray-850 px-4 py-4 text-sm text-gray-400 dark:text-gray-600 italic"
						>
							No structured note was generated for this consultation — the transcript below is the
							full record.
						</div>
					{/if}

					<!-- (c) transcript -->
					<div class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-4">
						<div class="flex items-baseline justify-between gap-2 mb-3">
							<div
								class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
							>
								Original conversation
							</div>
							{#if transcript.length > 0}
								<div class="text-[10px] text-gray-400 dark:text-gray-600">
									{transcript.length} turns · captured once, carried with the case
								</div>
							{/if}
						</div>

						<TranscriptView turns={transcript} collapsed={true} previewCount={4} />
					</div>

					<!-- (d) summary -->
					{#if canSummarize}
						<div>
							{#if !summary && !summaryError}
								<button
									type="button"
									class="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full border border-gray-100 dark:border-gray-850 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-850 transition disabled:opacity-60"
									disabled={summarizing}
									on:click={summarizeHandler}
								>
									{#if summarizing}
										<Spinner className="size-3" />
										Summarizing...
									{:else}
										<Sparkles className="size-3.5" />
										Summarize for me
									{/if}
								</button>
							{:else}
								<div class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-4">
									<div class="flex items-center justify-between gap-2 mb-2.5">
										<div
											class="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											<Sparkles className="size-3.5" />
											Summary
										</div>
										<button
											type="button"
											class="text-[11px] font-medium px-2.5 py-1 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition disabled:opacity-60"
											disabled={summarizing}
											on:click={summarizeHandler}
										>
											{summarizing ? 'Working...' : 'Regenerate'}
										</button>
									</div>

									{#if summaryError}
										<div class="text-sm text-red-600 dark:text-red-400 break-words">
											{summaryError}
										</div>
									{:else}
										<div class="markdown-prose">
											<Markdown id={`case-summary-${caseDetail.id}`} content={summary} />
										</div>
										<div class="text-[11px] text-gray-400 dark:text-gray-600 mt-2">
											Generated from the transcript above.
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/if}

					<!-- (e) prior assessments, read-only -->
					<div class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-4">
						<div
							class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3"
						>
							Assessments
						</div>

						{#if orderedAssessments.length === 0}
							<div class="text-sm text-gray-400 dark:text-gray-600 italic">No assessments yet.</div>
						{:else}
							<div class="flex flex-col gap-4">
								{#each orderedAssessments as assessment (assessment.id)}
									<div class="flex gap-3">
										<div
											class="size-8 shrink-0 rounded-full flex items-center justify-center text-[11px] font-semibold text-white select-none"
											style="background-color: {avatarColor(assessment.author_name ?? '')}"
											aria-hidden="true"
										>
											{initialsOf(assessment.author_name ?? '')}
										</div>

										<div class="min-w-0 flex-1">
											<div class="flex items-baseline gap-1.5 flex-wrap">
												<span class="text-sm font-medium text-gray-800 dark:text-gray-100">
													{assessment.author_name}
												</span>
												<span class="text-[11px] text-gray-500 dark:text-gray-400">
													{assessment.department}
												</span>
												<span class="text-[11px] text-gray-300 dark:text-gray-700">·</span>
												<Tooltip
													content={assessment.created_at
														? dayjs(toMs(assessment.created_at)).format('LLLL')
														: ''}
													className="flex"
													placement="top"
													as="span"
												>
													<span class="text-[11px] text-gray-400 dark:text-gray-600">
														{assessment.created_at
															? dayjs(toMs(assessment.created_at)).fromNow()
															: ''}
													</span>
												</Tooltip>
											</div>

											<div
												class="mt-1 text-sm leading-relaxed text-gray-700 dark:text-gray-200 whitespace-pre-wrap break-words"
											>
												{assessment.body}
											</div>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<!-- (f) my assessment - append only -->
					{#if myAssessment}
						<div
							class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-3 text-xs text-gray-500 dark:text-gray-400"
						>
							You added your assessment
							{myAssessment.created_at ? dayjs(toMs(myAssessment.created_at)).fromNow() : ''}.
							Assessments are append-only and cannot be edited.
						</div>
					{:else}
						<div class="rounded-2xl border border-gray-50 dark:border-gray-850 px-4 py-4">
							<label
								for="clinical-assessment"
								class="block text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2"
							>
								Your assessment
							</label>

							<textarea
								id="clinical-assessment"
								class="w-full rounded-xl bg-gray-50 dark:bg-gray-850 border border-transparent focus:border-gray-200 dark:focus:border-gray-800 px-3.5 py-2.5 text-sm text-gray-800 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-hidden resize-y min-h-24"
								rows="4"
								placeholder="What you found, and what you want the next doctor to know..."
								bind:value={assessmentBody}
								disabled={savingAssessment}
							></textarea>

							<div class="flex items-center justify-between gap-2 mt-2.5 flex-wrap">
								<span class="text-[11px] text-gray-400 dark:text-gray-600">
									Saved once - assessments cannot be edited afterwards.
								</span>

								<button
									type="button"
									class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap disabled:opacity-50"
									disabled={savingAssessment || assessmentBody.trim().length === 0}
									on:click={saveAssessmentHandler}
								>
									{#if savingAssessment}
										<Spinner className="size-3.5" />
									{/if}
									Save assessment
								</button>
							</div>
						</div>
					{/if}

					<!-- (g) actions -->
					<div class="flex flex-wrap items-center gap-2 pb-4">
						<Tooltip content="Coming soon" placement="top">
							<button
								type="button"
								class="px-3.5 py-1.5 text-sm font-medium rounded-full border border-gray-100 dark:border-gray-850 text-gray-400 dark:text-gray-600 cursor-not-allowed pointer-events-none"
								disabled
							>
								Send within department
							</button>
						</Tooltip>

						<button
							type="button"
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							on:click={() => (showReferDialog = true)}
						>
							Refer to another department
						</button>
					</div>
				</div>

				<!-- Right column: the chain -->
				<aside class="w-full lg:w-64 xl:w-72 shrink-0 order-first lg:order-none">
					<div class="lg:sticky lg:top-20">
						<ChainTimeline {caseDetail} currentEmail={$user?.email ?? ''} />
					</div>
				</aside>
			</div>
		{/if}
	</div>
</div>

{#if caseDetail}
	<ReferDialog
		bind:show={showReferDialog}
		caseId={caseDetail.id}
		patientCode={caseDetail.patient_code}
		patientName={caseDetail.patient_name}
		onSent={() => {
			// ReferDialog closes itself and raises its own toast — just refresh the chain.
			showReferDialog = false;
			load(caseId);
		}}
	/>
{/if}
