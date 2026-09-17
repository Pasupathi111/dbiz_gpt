<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getLogoutRedirectUrl, userSignOut } from '$lib/apis/auths';
	import { getInbox } from '$lib/apis/clinical';
	import { avatarColor, getSpecialistByEmail, initialsOf } from '$lib/constants/clinical';
	import { user } from '$lib/stores';

	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';

	const POLL_INTERVAL_MS = 20000;

	let mounted = false;
	let unreadCount = 0;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	$: specialist = getSpecialistByEmail($user?.email);
	$: doctorName = specialist?.name ?? $user?.name ?? '';
	$: doctorDepartment = specialist?.department ?? 'Clinical Console';

	$: pathname = $page.url.pathname;
	// Everything else under /consult — the live console and /consult/case/... —
	// belongs to Consultations.
	$: activeHref = pathname.startsWith('/consult/inbox')
		? '/consult/inbox'
		: pathname.startsWith('/consult/sent')
			? '/consult/sent'
			: '/consult/history';

	/**
	 * SvelteKit keeps /consult mounted when we are already on it, so a plain link
	 * would leave the previous consultation on screen. The changing `new` param is
	 * what the consult page watches to run its reset (behind its own unsaved-work
	 * guard); it strips the param once handled.
	 */
	const newConsultationHandler = async () => {
		await goto(`/consult?new=${Date.now()}`);
	};

	const refreshUnreadCount = async () => {
		const token = localStorage.token;
		if (!token) {
			return;
		}

		const items = await getInbox(token).catch((error) => {
			console.error('Failed to load clinical inbox:', error);
			return null;
		});

		if (!items) {
			return;
		}

		unreadCount = items.filter((item) => !item.read_at).length;
	};

	const signOutHandler = async () => {
		const res = await userSignOut().catch((error) => {
			console.error(error);
			return null;
		});
		localStorage.removeItem('token');

		location.href = getLogoutRedirectUrl(res?.redirect_url);
	};

	onMount(() => {
		mounted = true;
		// Poll so a referral sent from another browser window shows up live.
		pollTimer = setInterval(refreshUnreadCount, POLL_INTERVAL_MS);
	});

	onDestroy(() => {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	});

	// Fetches once on mount and again on every navigation (so the badge clears
	// right after the inbox page marks referrals as read).
	$: if (mounted && pathname) {
		void refreshUnreadCount();
	}
</script>

<nav
	aria-label="Clinical console"
	class="w-56 shrink-0 h-full flex flex-col border-r border-gray-100 dark:border-gray-850 bg-gray-50 dark:bg-gray-950 text-gray-700 dark:text-gray-200"
>
	<div class="px-3 py-4 border-b border-gray-100 dark:border-gray-850">
		<div class="flex items-center gap-2.5">
			<div
				class="size-9 shrink-0 rounded-full flex items-center justify-center text-white text-xs font-semibold"
				style="background-color: {avatarColor(doctorName)}"
				aria-hidden="true"
			>
				{initialsOf(doctorName)}
			</div>

			<div class="min-w-0 flex-1">
				<div class="text-sm font-medium truncate text-gray-900 dark:text-gray-100">
					{doctorName}
				</div>
				<div class="text-xs truncate text-gray-500 dark:text-gray-400">
					{doctorDepartment}
				</div>
			</div>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-0.5">
		<button
			type="button"
			class="mb-2 flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm font-medium bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition"
			on:click={newConsultationHandler}
		>
			<Plus className="size-4 shrink-0" strokeWidth="2" />
			<span class="truncate">New Consultation</span>
		</button>

		<a
			href="/consult/history"
			aria-current={activeHref === '/consult/history' ? 'page' : undefined}
			class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition {activeHref ===
			'/consult/history'
				? 'bg-gray-200 dark:bg-gray-850 text-gray-900 dark:text-gray-100 font-medium'
				: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
		>
			<ChatBubble className="size-4 shrink-0" strokeWidth="1.5" />
			<span class="truncate">Consultations</span>
		</a>

		<a
			href="/consult/sent"
			aria-current={activeHref === '/consult/sent' ? 'page' : undefined}
			class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition {activeHref ===
			'/consult/sent'
				? 'bg-gray-200 dark:bg-gray-850 text-gray-900 dark:text-gray-100 font-medium'
				: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
		>
			<!-- paper plane: no equivalent exists in $lib/components/icons -->
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				aria-hidden="true"
				class="size-4 shrink-0"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
				/>
			</svg>
			<span class="truncate">Sent</span>
		</a>

		<a
			href="/consult/inbox"
			aria-current={activeHref === '/consult/inbox' ? 'page' : undefined}
			class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition {activeHref ===
			'/consult/inbox'
				? 'bg-gray-200 dark:bg-gray-850 text-gray-900 dark:text-gray-100 font-medium'
				: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
		>
			<ArchiveBox className="size-4 shrink-0" strokeWidth="1.5" />
			<span class="truncate">Inbox</span>

			{#if unreadCount > 0}
				<span
					class="ml-auto shrink-0 min-w-5 px-1.5 py-0.5 rounded-full bg-red-500 text-white text-[0.625rem] font-semibold leading-none flex items-center justify-center"
					aria-label="{unreadCount} unread referrals"
				>
					{unreadCount > 99 ? '99+' : unreadCount}
				</span>
			{/if}
		</a>
	</div>

	<div class="px-2 py-3 border-t border-gray-100 dark:border-gray-850">
		<button
			type="button"
			class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition hover:bg-gray-100 dark:hover:bg-gray-900"
			on:click={signOutHandler}
		>
			<SignOut className="size-4 shrink-0" strokeWidth="1.5" />
			<span class="truncate">Sign Out</span>
		</button>
	</div>
</nav>
