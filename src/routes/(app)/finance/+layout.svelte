<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import FinanceCopilotChat from '$lib/components/finance/FinanceCopilotChat.svelte';

	const i18n = getContext('i18n');

	interface NavItem {
		id: string;
		label: string;
		href: string;
		icon: string;
		number: string;
	}

	const navItems: NavItem[] = [
		{ id: 'dashboard', label: 'Dashboard', href: '/finance', icon: 'dashboard', number: '01' },
		{ id: 'ai-assistant', label: 'AI Assistant', href: '/finance/ai-assistant', icon: 'ai', number: '02' },
		{ id: 'documents', label: 'Upload Documents', href: '/finance/documents', icon: 'upload', number: '03' },
		{ id: 'bonds', label: 'Bond Data', href: '/finance/bonds', icon: 'bonds', number: '04' },
		{ id: 'reconciliation', label: 'Reconciliation', href: '/finance/reconciliation', icon: 'reconciliation', number: '05' },
		{ id: 'movements', label: 'Movements', href: '/finance/movements', icon: 'movements', number: '06' },
		{ id: 'schedule', label: 'Bond Schedule', href: '/finance/schedule', icon: 'schedule', number: '07' },
		{ id: 'journals', label: 'Draft Journals', href: '/finance/journals', icon: 'journals', number: '08' },
		{ id: 'audit-schedule', label: 'Audit Schedule', href: '/finance/audit-schedule', icon: 'audit', number: '09' },
		{ id: 'commentary', label: 'Commentary', href: '/finance/commentary', icon: 'commentary', number: '10' },
		{ id: 'review', label: 'Review & Approval', href: '/finance/review', icon: 'review', number: '11' },
		{ id: 'exceptions', label: 'Exceptions', href: '/finance/exceptions', icon: 'exceptions', number: '12' },
		{ id: 'audit-trail', label: 'Audit Trail', href: '/finance/audit-trail', icon: 'trail', number: '13' },
		{ id: 'settings', label: 'Settings', href: '/finance/settings', icon: 'settings', number: '14' }
	];

	$: activeId = getActiveId($page.url.pathname);

	function getActiveId(pathname: string): string {
		if (pathname === '/finance' || pathname === '/finance/') return 'dashboard';
		for (const item of navItems) {
			if (item.href !== '/finance' && pathname.startsWith(item.href)) return item.id;
		}
		return 'dashboard';
	}

	let sidebarCollapsed = false;
	let showCopilotChat = false;
</script>

<div class="flex h-full w-full">
	<!-- Finance Sidebar -->
	<div
		class="finance-sidebar flex flex-col h-full border-r border-gray-200 dark:border-gray-700/50 bg-white dark:bg-gray-900 transition-all duration-200"
		class:w-60={!sidebarCollapsed}
		class:w-16={sidebarCollapsed}
	>
		<!-- Brand Header -->
		<div class="px-4 pt-5 pb-3 border-b border-gray-100 dark:border-gray-800">
			{#if !sidebarCollapsed}
				<div class="flex items-center gap-2.5">
					<div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
						<svg class="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
					<div class="min-w-0">
						<div class="text-sm font-semibold text-gray-900 dark:text-white truncate">AI Bond Copilot</div>
						<div class="text-[10px] text-gray-500 dark:text-gray-400 truncate">Finance Intelligence</div>
					</div>
				</div>
			{:else}
				<div class="flex justify-center">
					<div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
						<svg class="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
				</div>
			{/if}
		</div>

		<!-- Workspace Selector -->
		{#if !sidebarCollapsed}
			<div class="px-3 py-3 border-b border-gray-100 dark:border-gray-800">
				<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2 px-1">Workspace</div>
				<button
					class="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-left"
				>
					<div class="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
					<div class="min-w-0 flex-1">
						<div class="text-xs font-medium text-indigo-900 dark:text-indigo-300 truncate">Bond Reporting</div>
						<div class="text-[10px] text-indigo-600/70 dark:text-indigo-400/60 truncate">Monthly close & reconciliation</div>
					</div>
				</button>
			</div>
		{/if}

		<!-- Nav Section Label -->
		{#if !sidebarCollapsed}
			<div class="px-4 pt-3 pb-1">
				<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Bond Copilot</div>
			</div>
		{/if}

		<!-- Navigation Items -->
		<nav class="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
			{#each navItems as item}
				<button
					class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all duration-150 group
						{activeId === item.id
							? 'bg-indigo-600 text-white shadow-sm'
							: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => goto(item.href)}
					title={sidebarCollapsed ? item.label : ''}
				>
					{#if item.id === 'ai-assistant'}
						<svg
							class="w-4 h-4 flex-shrink-0 {activeId === item.id ? 'text-indigo-200' : 'text-indigo-400 dark:text-indigo-500'}"
							fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
						</svg>
					{:else}
						<span
							class="text-[10px] font-mono font-medium w-5 text-center flex-shrink-0
								{activeId === item.id ? 'text-indigo-200' : 'text-gray-400 dark:text-gray-500'}"
						>
							{item.number}
						</span>
					{/if}
					{#if !sidebarCollapsed}
						<span class="text-[13px] font-medium truncate">{item.label}</span>
					{/if}
				</button>
			{/each}
		</nav>

		<!-- Back to Chat -->
		<div class="px-2 pb-3 pt-2 border-t border-gray-100 dark:border-gray-800">
			<button
				class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
				on:click={() => goto('/')}
			>
				<svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
				</svg>
				{#if !sidebarCollapsed}
					<span class="text-[13px] font-medium">Back to Chat</span>
				{/if}
			</button>

			<!-- Collapse toggle -->
			<button
				class="w-full flex items-center justify-center mt-1 py-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
				on:click={() => (sidebarCollapsed = !sidebarCollapsed)}
			>
				<svg class="w-4 h-4 transition-transform {sidebarCollapsed ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
				</svg>
			</button>
		</div>

		<!-- User -->
		{#if !sidebarCollapsed && $user}
			<div class="px-3 pb-3 border-t border-gray-100 dark:border-gray-800 pt-2">
				<div class="flex items-center gap-2 px-1">
					<div class="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center text-xs font-semibold text-indigo-700 dark:text-indigo-300 flex-shrink-0">
						{($user.name || 'U').charAt(0).toUpperCase()}
					</div>
					<div class="min-w-0 flex-1">
						<div class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{$user.name}</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500 truncate">Finance User</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Main Content Area -->
	<div class="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-gray-50 dark:bg-gray-950 relative">
		<slot />

		<!-- Floating Copilot Chat Button -->
		<button
			class="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:scale-105 flex items-center justify-center transition-all duration-200 group"
			on:click={() => (showCopilotChat = !showCopilotChat)}
			aria-label="Toggle AI Copilot Chat"
		>
			<svg class="w-5.5 h-5.5 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
			</svg>
			<!-- Pulse dot -->
			<span class="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-amber-400 border-2 border-white dark:border-gray-900 copilot-pulse"></span>
		</button>

		<!-- Copilot Chat Panel -->
		<FinanceCopilotChat bind:open={showCopilotChat} onClose={() => (showCopilotChat = false)} />
	</div>
</div>

<style>
	.finance-sidebar {
		scrollbar-width: thin;
		scrollbar-color: rgba(156, 163, 175, 0.3) transparent;
	}

	@keyframes copilotPulse {
		0%, 100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.6;
			transform: scale(1.15);
		}
	}

	.copilot-pulse {
		animation: copilotPulse 2s ease-in-out infinite;
	}
</style>
