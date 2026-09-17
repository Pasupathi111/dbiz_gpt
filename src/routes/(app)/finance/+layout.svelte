<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { getLogoutRedirectUrl, userSignOut } from '$lib/apis/auths';
	import GlobalAgenticAssistant from '$lib/components/assistant/GlobalAgenticAssistant.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';

	const i18n = getContext('i18n');

	interface NavItem {
		id: string;
		label: string;
		href: string;
		iconPath: string;
	}

	const navItems: NavItem[] = [
		{ id: 'dashboard', label: 'Dashboard', href: '/finance',
		  iconPath: 'M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z' },
		{ id: 'ai-assistant', label: 'AI Assistant', href: '/finance/ai-assistant',
		  iconPath: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z' },
		{ id: 'documents', label: 'Upload Documents', href: '/finance/documents',
		  iconPath: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5' },
		{ id: 'bonds', label: 'Bond Data', href: '/finance/bonds',
		  iconPath: 'M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z' },
		{ id: 'reconciliation', label: 'Reconciliation', href: '/finance/reconciliation',
		  iconPath: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5' },
		{ id: 'movements', label: 'Movements', href: '/finance/movements',
		  iconPath: 'M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941' },
		{ id: 'schedule', label: 'Bond Schedule', href: '/finance/schedule',
		  iconPath: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5' }
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
	let mobileMenuOpen = false;
	let agenticPanelOpen = false;

	function handleNavClick(href: string) {
		mobileMenuOpen = false;
		goto(href);
	}

	function getCurrentMonth(): string {
		return new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
	}

	let userMenuOpen = false;

	async function handleSignOut() {
		mobileMenuOpen = false;
		userMenuOpen = false;
		const res = await userSignOut().catch((error) => {
			console.error(error);
			return null;
		});
		localStorage.removeItem('token');
		location.href = getLogoutRedirectUrl(res?.redirect_url);
	}
</script>

<div class="flex h-full w-full relative">
	<!-- Mobile Top Bar -->
	<div class="md:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 py-3 bg-[#0f172a] border-b border-slate-700/50 shadow-sm">
		<button
			class="p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
			on:click={() => (mobileMenuOpen = !mobileMenuOpen)}
			aria-label="Toggle menu"
		>
			<svg class="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				{#if mobileMenuOpen}
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				{:else}
					<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
				{/if}
			</svg>
		</button>
		<div class="flex items-center gap-2">
			<div class="w-7 h-7 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
				<svg class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
				</svg>
			</div>
			<span class="text-sm font-semibold text-white">AI SCS Copilot</span>
		</div>
		<button
			class="p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
			on:click={() => goto('/')}
			aria-label="Back to chat"
		>
			<svg class="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
			</svg>
		</button>
	</div>

	<!-- Mobile Overlay -->
	{#if mobileMenuOpen}
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="md:hidden fixed inset-0 z-40 bg-black/30 dark:bg-black/50" on:click={() => (mobileMenuOpen = false)}></div>
	{/if}

	<!-- Sidebar -->
	<div
		class="finance-sidebar flex flex-col h-full border-r border-slate-700/50 bg-[#0f172a] transition-all duration-200
			fixed md:relative z-50 md:z-auto
			{mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0"
		class:w-[210px]={!sidebarCollapsed}
		class:w-16={sidebarCollapsed}
	>
		<!-- Brand Header -->
		<div class="px-3 pt-4 pb-3 border-b border-slate-700/40">
			{#if !sidebarCollapsed}
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2.5 min-w-0">
						<div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
							<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
							</svg>
						</div>
						<div class="min-w-0">
							<div class="text-sm font-semibold text-white truncate">AI SCS Copilot</div>
							<div class="text-[10px] text-slate-400 truncate">Finance Intelligence</div>
						</div>
					</div>
					<button
						class="hidden md:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors flex-shrink-0"
						on:click={() => (sidebarCollapsed = true)}
						title="Collapse sidebar"
					>
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
						</svg>
					</button>
				</div>
			{:else}
				<div class="flex flex-col items-center gap-2">
					<div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
						<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
						</svg>
					</div>
					<button
						class="hidden md:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
						on:click={() => (sidebarCollapsed = false)}
						title="Expand sidebar"
					>
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
						</svg>
					</button>
				</div>
			{/if}
		</div>

		<!-- Navigation Items -->
		<nav class="flex-1 overflow-y-auto px-2.5 py-3 space-y-0.5">
			{#each navItems as item}
				<button
					class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all duration-150 group
						{activeId === item.id
							? 'bg-blue-600/90 text-white shadow-sm shadow-blue-500/20'
							: 'text-slate-300 hover:bg-slate-700/50 hover:text-white'}"
					on:click={() => handleNavClick(item.href)}
					title={sidebarCollapsed ? item.label : ''}
				>
					<svg
						class="w-[18px] h-[18px] flex-shrink-0 {activeId === item.id ? 'text-blue-200' : 'text-slate-400 group-hover:text-slate-300'}"
						fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d={item.iconPath} />
					</svg>
					{#if !sidebarCollapsed}
						<span class="text-[13px] font-medium truncate">{item.label}</span>
					{/if}
				</button>
			{/each}
		</nav>

		<!-- Back to Chat -->
		<div class="px-2.5 pb-2 pt-2 border-t border-slate-700/40">
			<button
				class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-slate-400 hover:bg-slate-700/50 hover:text-white transition-colors"
				on:click={() => { mobileMenuOpen = false; goto('/'); }}
			>
				<svg class="w-[18px] h-[18px] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
				</svg>
				{#if !sidebarCollapsed}
					<span class="text-[13px] font-medium">Back to Chat</span>
				{/if}
			</button>
			<button
				class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-slate-400 hover:bg-slate-700/50 hover:text-white transition-colors"
				on:click={handleSignOut}
				title={sidebarCollapsed ? 'Sign Out' : ''}
			>
				<SignOut className="w-[18px] h-[18px] flex-shrink-0" strokeWidth="1.5" />
				{#if !sidebarCollapsed}
					<span class="text-[13px] font-medium">Sign Out</span>
				{/if}
			</button>
		</div>

		<!-- User -->
		{#if $user}
			<div class="px-3 pb-2 border-t border-slate-700/40 pt-2">
				<div class="flex items-center gap-2.5 px-1">
					<div class="relative flex-shrink-0">
						<div class="w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-cyan-500 flex items-center justify-center text-xs font-semibold text-white">
							{($user.name || 'U').charAt(0).toUpperCase()}{($user.name || 'U').split(' ')[1]?.charAt(0)?.toUpperCase() || ''}
						</div>
						<span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#0f172a]"></span>
					</div>
					{#if !sidebarCollapsed}
						<div class="min-w-0 flex-1">
							<div class="text-xs font-medium text-white truncate">{$user.name}</div>
							<div class="text-[10px] text-slate-400 truncate">Finance User</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<div class="pb-2"></div>
	</div>

	<!-- Main Area -->
	<div class="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
		<!-- Top Header Bar (desktop) -->
		<header class="hidden md:flex items-center justify-between px-6 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700/50 flex-shrink-0">
			<!-- Search -->
			<div class="relative flex-1 max-w-xl">
				<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
				<input
					type="text"
					placeholder="Search bonds, ISIN, issuer, or use natural language..."
					class="w-full pl-10 pr-16 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-colors"
				/>
				<div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-gray-400">
					<kbd class="text-[10px] font-mono bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded px-1.5 py-0.5">&#8984;K</kbd>
				</div>
			</div>

			<!-- Right controls -->
			<div class="flex items-center gap-3 ml-6">
				<!-- Date selector -->
				<button class="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
					<svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" /></svg>
					<span>{getCurrentMonth()}</span>
					<svg class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
				</button>

				<!-- Notifications -->
				<button class="relative p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Notifications">
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>
					<span class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 border border-white dark:border-gray-900"></span>
				</button>

				<!-- AI toggle -->
				<button
					class="p-2 rounded-lg transition-colors {agenticPanelOpen ? 'text-indigo-600 bg-indigo-50 dark:text-indigo-400 dark:bg-indigo-500/10' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					on:click={() => (agenticPanelOpen = !agenticPanelOpen)}
					aria-label="Toggle AI panel"
				>
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" /></svg>
				</button>

				<!-- Settings -->
				<button class="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Settings">
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
				</button>

				<!-- User Avatar -->
				{#if $user}
					<div class="relative">
						<button
							class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-semibold text-white flex-shrink-0 cursor-pointer hover:ring-2 hover:ring-indigo-300 transition-all"
							on:click={() => (userMenuOpen = !userMenuOpen)}
							aria-label="User menu"
						>
							{($user.name || 'U').charAt(0).toUpperCase()}{($user.name || 'U').split(' ')[1]?.charAt(0)?.toUpperCase() || ''}
						</button>
						{#if userMenuOpen}
							<!-- svelte-ignore a11y-click-events-have-key-events -->
							<!-- svelte-ignore a11y-no-static-element-interactions -->
							<div class="fixed inset-0 z-40" on:click={() => (userMenuOpen = false)}></div>
							<div class="absolute right-0 top-full mt-2 z-50 w-44 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg py-1">
								<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
									<div class="text-sm font-medium text-gray-900 dark:text-white truncate">{$user.name}</div>
									<div class="text-xs text-gray-400 truncate">{$user.email}</div>
								</div>
								<button
									class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
									on:click={handleSignOut}
								>
									<SignOut className="size-4 shrink-0" strokeWidth="1.5" />
									<span>Sign Out</span>
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</header>

		<!-- Content + AI Panel -->
		<div class="flex-1 flex overflow-hidden bg-gray-50 dark:bg-gray-950 pt-14 md:pt-0">
			<!-- Page Content -->
			<div class="flex-1 overflow-y-auto min-w-0">
				<slot />
			</div>

			<!-- Desktop AI Panel (inline) -->
			{#if agenticPanelOpen}
				<div class="hidden xl:flex w-[380px] flex-shrink-0 border-l border-gray-200 dark:border-gray-700/50 h-full">
					<GlobalAgenticAssistant onClose={() => (agenticPanelOpen = false)} />
				</div>
			{/if}

			<!-- Mobile/Tablet AI Panel (overlay) -->
			{#if agenticPanelOpen}
				<div class="xl:hidden fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Agentic AI">
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div class="absolute inset-0 bg-black/20 dark:bg-black/40" on:click={() => (agenticPanelOpen = false)}></div>
					<div class="relative w-full max-w-[400px] shadow-2xl animate-slide-in">
						<GlobalAgenticAssistant onClose={() => (agenticPanelOpen = false)} />
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<!-- Floating AI button (visible only when panel is closed, on non-xl screens or when closed) -->
{#if !agenticPanelOpen}
	<button
		class="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:scale-105 flex items-center justify-center transition-all duration-200 group"
		on:click={() => (agenticPanelOpen = true)}
		aria-label="Open Agentic AI"
	>
		<svg class="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
			<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
		</svg>
		<span class="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-white dark:border-gray-900 copilot-pulse"></span>
	</button>
{/if}

<style>
	.finance-sidebar {
		scrollbar-width: thin;
		scrollbar-color: rgba(156, 163, 175, 0.3) transparent;
	}
	@keyframes slideIn {
		from { transform: translateX(100%); }
		to { transform: translateX(0); }
	}
	.animate-slide-in {
		animation: slideIn 0.25s ease-out;
	}
	@keyframes copilotPulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.6; transform: scale(1.15); }
	}
	.copilot-pulse {
		animation: copilotPulse 2s ease-in-out infinite;
	}
</style>
