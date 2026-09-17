<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { getInbox, markReferralRead } from '$lib/apis/clinical';
	import type { InboxItem } from '$lib/types/clinical';
	import { avatarColor, initialsOf } from '$lib/constants/clinical';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	let items: InboxItem[] | null = null;
	let loading = true;
	let error = '';
	let openingId = '';

	const toMs = (at?: number | null): number => {
		if (!at || !Number.isFinite(at)) return 0;
		return at > 1e12 ? at : at * 1000;
	};

	const load = async () => {
		loading = true;
		error = '';

		const res = await getInbox(localStorage.token).catch((err: unknown) => {
			error = `${err}`;
			return null;
		});

		if (res) {
			items = [...res].sort((a, b) => (b?.created_at ?? 0) - (a?.created_at ?? 0));
		}

		loading = false;
	};

	const openHandler = async (item: InboxItem) => {
		if (openingId) return;
		openingId = item.id;

		if (!item.read_at) {
			await markReferralRead(localStorage.token, item.id).catch((err: unknown) => {
				// Opening the case matters more than the read receipt.
				console.error(err);
				return null;
			});
		}

		openingId = '';
		await goto(`/consult/case/${item.case_id}`);
	};

	$: unreadCount = (items ?? []).filter((item) => !item.read_at).length;

	onMount(() => {
		load();
	});
</script>

<svelte:head>
	<title>Inbox | Referrals</title>
</svelte:head>

<div class="w-full">
	<div class="max-w-6xl mx-auto px-4 md:px-6 py-5">
		<div class="flex items-center justify-between gap-3 mb-4">
			<div class="min-w-0">
				<h1 class="text-xl font-medium text-gray-900 dark:text-gray-100">Inbox</h1>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
					Referrals sent to you
					{#if unreadCount > 0}
						· <span class="text-gray-800 dark:text-gray-200 font-medium"
							>{unreadCount} unread</span
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
				<div class="font-medium mb-1">Could not load your inbox</div>
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
				<div class="text-base font-medium text-gray-700 dark:text-gray-200">No referrals yet</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
					When a colleague refers a patient to you, the full conversation and every assessment so
					far will land right here.
				</div>
			</div>
		{:else}
			<div class="rounded-2xl border border-gray-50 dark:border-gray-850 overflow-hidden">
				<div
					class="hidden md:flex items-center gap-3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-850/50"
				>
					<span class="w-2 shrink-0" aria-hidden="true"></span>
					<span class="w-16 shrink-0">Patient</span>
					<span class="w-36 shrink-0">Name</span>
					<span class="w-52 shrink-0">From</span>
					<span class="flex-1 min-w-0">Note</span>
					<span class="w-20 shrink-0 text-right">Time</span>
				</div>

				<div class="divide-y divide-gray-50 dark:divide-gray-850">
					{#each items ?? [] as item (item.id)}
						{@const unread = !item.read_at}
						<button
							type="button"
							class="w-full text-left flex items-center gap-3 px-3 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-850/50 disabled:opacity-60 {unread
								? 'bg-sky-50/40 dark:bg-sky-500/5'
								: ''}"
							disabled={openingId === item.id}
							on:click={() => openHandler(item)}
						>
							<span class="w-2 shrink-0 flex justify-center" aria-hidden="true">
								{#if unread}
									<span class="size-2 rounded-full bg-sky-500"></span>
								{/if}
							</span>

							<span
								class="w-16 shrink-0 text-xs font-mono {unread
									? 'text-gray-900 dark:text-gray-100'
									: 'text-gray-500 dark:text-gray-400'}"
							>
								{item.patient_code}
							</span>

							<span
								class="w-36 shrink-0 truncate text-sm {unread
									? 'font-semibold text-gray-900 dark:text-white'
									: 'text-gray-700 dark:text-gray-300'}"
							>
								{item.patient_name}
							</span>

							<span class="w-52 shrink-0 flex items-center gap-2 min-w-0">
								<span
									class="size-7 shrink-0 rounded-full flex items-center justify-center text-[10px] font-semibold text-white select-none"
									style="background-color: {avatarColor(item.from_name ?? '')}"
									aria-hidden="true"
								>
									{initialsOf(item.from_name ?? '')}
								</span>
								<span class="min-w-0">
									<span
										class="block truncate text-sm {unread
											? 'font-medium text-gray-900 dark:text-gray-100'
											: 'text-gray-700 dark:text-gray-300'}"
									>
										{item.from_name}
									</span>
									<span class="block truncate text-[11px] text-gray-500 dark:text-gray-400">
										{item.from_department}
									</span>
								</span>
							</span>

							<span
								class="flex-1 min-w-0 hidden md:block truncate text-sm {unread
									? 'text-gray-700 dark:text-gray-200'
									: 'text-gray-500 dark:text-gray-400'}"
							>
								{item.note || '—'}
							</span>

							<span class="w-20 shrink-0 text-right">
								<Tooltip
									content={item.created_at ? dayjs(toMs(item.created_at)).format('LLLL') : ''}
									className="flex justify-end"
									as="span"
									placement="left"
								>
									<span class="text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{item.created_at ? dayjs(toMs(item.created_at)).fromNow() : ''}
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
