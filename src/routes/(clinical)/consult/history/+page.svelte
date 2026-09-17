<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { getCases, getSent } from '$lib/apis/clinical';
	import type { ClinicalCase, InboxItem } from '$lib/types/clinical';
	import { avatarColor, initialsOf } from '$lib/constants/clinical';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	let items: ClinicalCase[] | null = null;
	/** case_id -> the most recent referral this doctor sent for that case. */
	let referrals: Record<string, InboxItem> = {};
	let loading = true;
	let error = '';

	const toMs = (at?: number | null): number => {
		if (!at || !Number.isFinite(at)) return 0;
		return at > 1e12 ? at : at * 1000;
	};

	const lastTurnOf = (item: ClinicalCase): string => {
		const turns = item.transcript ?? [];
		const turn = turns[turns.length - 1];
		if (!turn) return '';
		return `${turn.speaker === 'doctor' ? 'Doctor' : 'Patient'}: ${turn.text}`;
	};

	const load = async () => {
		loading = true;
		error = '';

		// The case payload carries no referral state, so the sent list supplies the
		// "referred onward" marker. It is decoration only — if it fails every case
		// still lists, which is the whole point of this screen.
		const [cases, sent] = await Promise.all([
			getCases(localStorage.token).catch((err: unknown) => {
				error = `${err}`;
				return null;
			}),
			getSent(localStorage.token).catch((err: unknown) => {
				console.error(err);
				return null;
			})
		]);

		if (cases) {
			items = [...cases].sort((a, b) => (b?.updated_at ?? 0) - (a?.updated_at ?? 0));
		}

		if (sent) {
			const latest: Record<string, InboxItem> = {};
			for (const referral of sent) {
				const current = latest[referral.case_id];
				if (!current || (referral.created_at ?? 0) > (current.created_at ?? 0)) {
					latest[referral.case_id] = referral;
				}
			}
			referrals = latest;
		}

		loading = false;
	};

	$: referredCount = (items ?? []).filter((item) => referrals[item.id]).length;

	onMount(() => {
		load();
	});
</script>

<svelte:head>
	<title>Consultations | Referrals</title>
</svelte:head>

<div class="w-full">
	<div class="max-w-6xl mx-auto px-4 md:px-6 py-5">
		<div class="flex items-center justify-between gap-3 mb-4">
			<div class="min-w-0">
				<h1 class="text-xl font-medium text-gray-900 dark:text-gray-100">Consultations</h1>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
					Every case you opened or were referred — referred onward or not
					{#if referredCount > 0}
						· <span class="text-gray-800 dark:text-gray-200 font-medium"
							>{referredCount} referred onward</span
						>
					{/if}
				</p>
			</div>

			<button
				type="button"
				class="text-xs font-medium px-3 py-1.5 rounded-full text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition disabled:opacity-50"
				disabled={loading}
				on:click={load}
			>
				Refresh
			</button>
		</div>

		{#if loading && items === null}
			<div class="w-full flex justify-center items-center py-20">
				<Spinner className="size-5" />
			</div>
		{:else if error}
			<div
				class="rounded-2xl border border-red-100 dark:border-red-500/20 bg-red-50 dark:bg-red-500/10 px-4 py-5 text-sm text-red-700 dark:text-red-300"
			>
				<div class="font-medium mb-1">Could not load your consultations</div>
				<div class="text-xs opacity-80 break-words">{error}</div>
				<button
					type="button"
					class="mt-3 text-xs font-medium px-3 py-1.5 rounded-full bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					on:click={load}
				>
					Try again
				</button>
			</div>
		{:else if (items ?? []).length === 0}
			<div
				class="rounded-2xl border border-dashed border-gray-100 dark:border-gray-850 px-4 py-16 flex flex-col items-center justify-center text-center"
			>
				<div class="text-base font-medium text-gray-700 dark:text-gray-200">
					No consultations yet
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
					Every consultation you open lands here — whether or not you ever refer it onward.
				</div>
				<a
					href="/consult"
					class="mt-4 inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition"
				>
					<Plus className="size-3.5" strokeWidth="2" />
					Start a consultation
				</a>
			</div>
		{:else}
			<div class="rounded-2xl border border-gray-50 dark:border-gray-850 overflow-hidden">
				<div
					class="hidden md:flex items-center gap-3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-850/50"
				>
					<span class="w-16 shrink-0">Patient</span>
					<span class="w-36 shrink-0">Name</span>
					<span class="w-52 shrink-0">Department</span>
					<span class="flex-1 min-w-0">Last turn</span>
					<span class="w-28 shrink-0">Referral</span>
					<span class="w-20 shrink-0 text-right">Updated</span>
				</div>

				<div class="divide-y divide-gray-50 dark:divide-gray-850">
					{#each items ?? [] as item (item.id)}
						{@const referral = referrals[item.id]}
						<button
							type="button"
							class="w-full text-left flex items-center gap-3 px-3 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-850/50"
							on:click={() => goto(`/consult/case/${item.id}`)}
						>
							<span class="w-16 shrink-0 text-xs font-mono text-gray-500 dark:text-gray-400">
								{item.patient_code}
							</span>

							<span
								class="w-36 shrink-0 truncate text-sm font-medium text-gray-800 dark:text-gray-100"
							>
								{item.patient_name}
							</span>

							<span class="w-52 shrink-0 flex items-center gap-2 min-w-0">
								<span
									class="size-7 shrink-0 rounded-full flex items-center justify-center text-[10px] font-semibold text-white select-none"
									style="background-color: {avatarColor(item.created_by_name ?? '')}"
									aria-hidden="true"
								>
									{initialsOf(item.created_by_name ?? '')}
								</span>
								<span class="min-w-0">
									<span class="block truncate text-sm text-gray-700 dark:text-gray-300">
										{item.department}
									</span>
									<span class="block truncate text-[11px] text-gray-500 dark:text-gray-400">
										{item.created_by_name}
									</span>
								</span>
							</span>

							<span
								class="flex-1 min-w-0 hidden md:block truncate text-sm text-gray-500 dark:text-gray-400"
							>
								{lastTurnOf(item) || '—'}
							</span>

							<span class="w-28 shrink-0">
								{#if referral}
									<Tooltip
										content="Referred to {referral.to_name} · {referral.to_department}"
										className="flex"
										placement="top"
										as="span"
									>
										<span
											class="inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400"
										>
											<span class="size-1.5 rounded-full bg-sky-500 shrink-0" aria-hidden="true"
											></span>
											Referred
										</span>
									</Tooltip>
								{:else}
									<span
										class="inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-850 dark:text-gray-400"
									>
										Not referred
									</span>
								{/if}
							</span>

							<span class="w-20 shrink-0 text-right">
								<Tooltip
									content={item.updated_at ? dayjs(toMs(item.updated_at)).format('LLLL') : ''}
									className="flex justify-end"
									placement="left"
									as="span"
								>
									<span class="text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{item.updated_at ? dayjs(toMs(item.updated_at)).fromNow() : ''}
									</span>
								</Tooltip>
							</span>
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>
