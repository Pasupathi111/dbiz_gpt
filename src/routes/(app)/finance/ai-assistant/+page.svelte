<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { user, models } from '$lib/stores';
	import {
		copilotChat,
		getReportingPeriods,
		getFinanceDashboard,
		getAuditTrail
	} from '$lib/apis/finance';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant' | 'system';
		content: string;
		timestamp: Date;
		toolCalls?: { name: string; result: string }[];
		files?: { name: string; size: number; type: string }[];
	}

	let messages: ChatMessage[] = [];
	let inputValue = '';
	let isTyping = false;
	let messagesContainer: HTMLDivElement;
	let periods: any[] = [];
	let selectedPeriodId = '';
	let selectedModelId = '';
	let attachedFiles: File[] = [];
	let fileInput: HTMLInputElement;
	let showModelDropdown = false;
	let showQuickActions = true;

	const quickActions = [
		{ label: 'Run Reconciliation', icon: 'recon', query: 'Run reconciliation for this period' },
		{ label: 'Analyze Movements', icon: 'recon', query: 'Analyze movements for this period' },
		{ label: 'Generate Bond Schedule', icon: 'doc', query: 'Generate the bond schedule for this period' },
		{ label: 'Generate Draft Journals', icon: 'journal', query: 'Generate journals for this period' },
		{ label: 'Generate Audit Schedule', icon: 'audit', query: 'Generate the audit schedule for this period' },
		{ label: 'Generate Commentary', icon: 'doc', query: 'Generate commentary for this period' },
		{ label: 'Review Exceptions', icon: 'exception', query: 'Show me a summary of all open exceptions' },
		{ label: 'Check Review Queue', icon: 'audit', query: 'What reviews are pending?' },
		{ label: 'Portfolio Summary', icon: 'doc', query: 'Give me a full portfolio summary' },
		{ label: 'Risk Analysis', icon: 'risk', query: 'Analyze the risk profile of my current bond portfolio' }
	];

	let recentActivity: any[] = [];
	let dataContext: { name: string; count: number | null; description: string }[] = [];

	$: registerAssistantContext({
		page: 'ai-assistant',
		pageTitle: 'AI Assistant',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['portfolio.summary', 'exceptions.analyze', 'reconciliation.summary']
	});

	$: availableModels = $models || [];

	function activityType(action: string): string {
		const a = (action || '').toLowerCase();
		if (a.includes('approve')) return 'positive';
		if (a.includes('reject') || a.includes('exception')) return 'warning';
		if (a.includes('upload') || a.includes('generate') || a.includes('process')) return 'info';
		return 'neutral';
	}

	function relativeTime(iso: string): string {
		const diffMs = Date.now() - new Date(iso).getTime();
		const mins = Math.floor(diffMs / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins} min${mins === 1 ? '' : 's'} ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
		return `${Math.floor(hours / 24)} day${Math.floor(hours / 24) === 1 ? '' : 's'} ago`;
	}

	async function loadSidebar() {
		try {
			const dash = await getFinanceDashboard(localStorage.token, selectedPeriodId || undefined);
			const kpis = dash?.kpis || {};
			dataContext = [
				{ name: 'Bond Portfolio', count: kpis.total_bonds ?? 0, description: 'Active bond line items' },
				{ name: 'Reporting Period', count: null, description: dash?.period_name || 'Not set' },
				{ name: 'Source Documents', count: kpis.documents_uploaded ?? 0, description: 'Uploaded UBS/LGI documents' },
				{ name: 'Journal Entries', count: kpis.journal_count ?? 0, description: 'AI-generated draft journals' },
				{
					name: 'Exceptions',
					count: kpis.exceptions_open ?? 0,
					description: `${kpis.exceptions_open ?? 0} open, ${kpis.exceptions_resolved ?? 0} resolved`
				}
			];
		} catch {
			dataContext = [];
		}

		try {
			const logs = await getAuditTrail(
				localStorage.token,
				selectedPeriodId ? { period_id: selectedPeriodId } : undefined
			);
			recentActivity = Array.isArray(logs) ? logs.slice(0, 5) : [];
		} catch {
			recentActivity = [];
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files) {
			attachedFiles = [...attachedFiles, ...Array.from(input.files)];
		}
		input.value = '';
	}

	function removeFile(index: number) {
		attachedFiles = attachedFiles.filter((_, i) => i !== index);
	}

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function sendMessage(text?: string) {
		const msg = (text || inputValue).trim();
		if (!msg || isTyping) return;

		inputValue = '';
		showQuickActions = false;

		const userMsg: ChatMessage = {
			id: `msg-${Date.now()}-user`,
			role: 'user',
			content: msg,
			timestamp: new Date(),
			files: attachedFiles.map(f => ({ name: f.name, size: f.size, type: f.type }))
		};
		messages = [...messages, userMsg];
		attachedFiles = [];

		await scrollToBottom();

		isTyping = true;
		try {
			const response = await copilotChat(localStorage.token, msg, selectedPeriodId || undefined);
			const assistantMsg: ChatMessage = {
				id: `msg-${Date.now()}-assistant`,
				role: 'assistant',
				content: response?.content || "Sorry, I couldn't generate a response.",
				timestamp: new Date(),
				toolCalls: response?.tool_calls
			};
			messages = [...messages, assistantMsg];
		} catch (e: any) {
			messages = [
				...messages,
				{
					id: `msg-${Date.now()}-assistant`,
					role: 'assistant',
					content: `Sorry, I couldn't reach the Bond Copilot backend: ${e?.message || e}`,
					timestamp: new Date()
				}
			];
		}
		isTyping = false;

		await scrollToBottom();
	}

	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		if (availableModels.length && !selectedModelId) {
			selectedModelId = availableModels[0]?.id || '';
		}
		await loadSidebar();
	});

	async function scrollToBottom() {
		await tick();
		await new Promise((r) => setTimeout(r, 20));
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	function formatTime(d: Date): string {
		return d.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' });
	}

	function handleQuickAction(query: string) {
		sendMessage(query);
	}

	function insightTypeColor(type: string): string {
		const m: Record<string, string> = {
			positive: 'border-l-emerald-500',
			warning: 'border-l-amber-500',
			info: 'border-l-blue-500',
			neutral: 'border-l-gray-400 dark:border-l-gray-600'
		};
		return m[type] || '';
	}

	function insightDotColor(type: string): string {
		const m: Record<string, string> = {
			positive: 'bg-emerald-500',
			warning: 'bg-amber-500',
			info: 'bg-blue-500',
			neutral: 'bg-gray-400'
		};
		return m[type] || 'bg-gray-400';
	}

	function parseToolData(result: string): any {
		try {
			return JSON.parse(result);
		} catch {
			return null;
		}
	}

	function fmt(v: any): string {
		if (v === null || v === undefined || v === '') return '—';
		if (typeof v === 'number') return v.toLocaleString('en-SG');
		return String(v);
	}

	function fmtMoney(v: any): string {
		if (v === null || v === undefined) return '—';
		const n = Number(v);
		if (Number.isNaN(n)) return String(v);
		return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', minimumFractionDigits: 0 }).format(n);
	}

	function actionIcon(icon: string): string {
		const m: Record<string, string> = {
			doc: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
			recon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
			risk: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
			exception: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
			journal: 'M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z',
			audit: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
		};
		return m[icon] || m['doc'];
	}

	function clearChat() {
		messages = [];
		showQuickActions = true;
	}

	let rightPanelTab: 'actions' | 'context' | 'activity' = 'actions';
</script>

<div class="flex flex-col h-full overflow-hidden bg-white dark:bg-gray-900">
	<!-- Header Bar -->
	<div class="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
		<div class="flex items-center gap-3 min-w-0">
			<div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-sm">
				<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
				</svg>
			</div>
			<div class="min-w-0">
				<h1 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate">AI Bond Copilot</h1>
				<p class="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">Full-featured AI assistant for bond portfolio management</p>
			</div>
		</div>
		<div class="flex items-center gap-2 flex-shrink-0">
			<!-- Model Selector -->
			<div class="relative">
				<button
					class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
					on:click={() => (showModelDropdown = !showModelDropdown)}
				>
					<svg class="w-3.5 h-3.5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
					</svg>
					<span class="max-w-[120px] truncate">{selectedModelId ? (availableModels.find(m => m.id === selectedModelId)?.name || selectedModelId) : 'Select Model'}</span>
					<svg class="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
					</svg>
				</button>
				{#if showModelDropdown}
					<div class="absolute right-0 top-full mt-1 w-72 max-h-80 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-50">
						<div class="p-2 border-b border-gray-100 dark:border-gray-700">
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 px-2 py-1">Available Models ({availableModels.length})</div>
						</div>
						<div class="p-1.5">
							{#each availableModels as model}
								<button
									class="w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs rounded-lg transition-colors
										{selectedModelId === model.id
											? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300'
											: 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'}"
									on:click={() => { selectedModelId = model.id; showModelDropdown = false; }}
								>
									<div class="w-6 h-6 rounded-md bg-gray-100 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
										<svg class="w-3.5 h-3.5 {selectedModelId === model.id ? 'text-indigo-500' : 'text-gray-400'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
										</svg>
									</div>
									<div class="min-w-0 flex-1">
										<div class="font-medium truncate">{model.name || model.id}</div>
										{#if model.info?.meta?.description}
											<div class="text-[10px] text-gray-400 truncate mt-0.5">{model.info.meta.description}</div>
										{/if}
									</div>
									{#if selectedModelId === model.id}
										<svg class="w-4 h-4 text-indigo-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
										</svg>
									{/if}
								</button>
							{/each}
							{#if availableModels.length === 0}
								<div class="px-3 py-4 text-center text-xs text-gray-400">No models available</div>
							{/if}
						</div>
					</div>
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div class="fixed inset-0 z-40" on:click={() => (showModelDropdown = false)}></div>
				{/if}
			</div>

			<!-- Period Selector -->
			<select
				class="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hidden sm:block"
				bind:value={selectedPeriodId}
				on:change={loadSidebar}
			>
				{#if periods.length === 0}
					<option value="">Current period</option>
				{/if}
				{#each periods as p}
					<option value={p.id}>{p.name}</option>
				{/each}
			</select>

			<!-- Clear Chat -->
			<button
				class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
				on:click={clearChat}
				title="New chat"
			>
				<svg class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Main Content -->
	<div class="flex-1 flex overflow-hidden">
		<!-- Chat Area -->
		<div class="flex-1 flex flex-col min-w-0">
			<!-- Messages -->
			<div class="flex-1 overflow-y-auto" bind:this={messagesContainer}>
				{#if messages.length === 0}
					<!-- Welcome Screen -->
					<div class="flex flex-col items-center justify-center h-full px-4 sm:px-8">
						<div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 flex items-center justify-center mb-6">
							<svg class="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
							</svg>
						</div>
						<h2 class="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white mb-2 text-center">How can I help you today?</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 max-w-lg text-center mb-8">
							Ask about your bond portfolio, run analyses, generate reports, upload documents, or use any of the {availableModels.length} available models.
						</p>

						{#if showQuickActions}
							<div class="w-full max-w-2xl">
								<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
									{#each quickActions.slice(0, 6) as action}
										<button
											class="flex items-center gap-3 px-4 py-3 text-left text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-all group"
											on:click={() => handleQuickAction(action.query)}
										>
											<svg class="w-4.5 h-4.5 text-gray-400 group-hover:text-indigo-500 flex-shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
												<path stroke-linecap="round" stroke-linejoin="round" d={actionIcon(action.icon)} />
											</svg>
											<span>{action.label}</span>
										</button>
									{/each}
								</div>
								<button
									class="mt-3 text-xs text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 mx-auto block"
									on:click={() => (showQuickActions = !showQuickActions)}
								>
									Show all actions
								</button>
							</div>
						{/if}
					</div>
				{:else}
					<div class="px-4 sm:px-6 lg:px-8 py-5 space-y-4 max-w-4xl mx-auto w-full">
						{#each messages as msg}
							{#if msg.role !== 'system'}
								<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
									<div class="max-w-[80%] sm:max-w-[75%]">
										{#if msg.role === 'assistant'}
											<div class="flex items-center gap-2 mb-1.5">
												<div class="w-5 h-5 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
													<svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
														<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
													</svg>
												</div>
												<span class="text-[10px] font-medium text-gray-500 dark:text-gray-400">AI Bond Copilot</span>
												{#if selectedModelId}
													<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-400">{availableModels.find(m => m.id === selectedModelId)?.name || selectedModelId}</span>
												{/if}
											</div>
										{/if}

										{#if msg.files && msg.files.length > 0}
											<div class="flex flex-wrap gap-1.5 mb-1.5 {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
												{#each msg.files as f}
													<span class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 text-[10px]">
														<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
															<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
														</svg>
														{f.name}
													</span>
												{/each}
											</div>
										{/if}

										<div
											class="px-4 py-3 rounded-xl text-sm leading-relaxed whitespace-pre-wrap
												{msg.role === 'user'
													? 'bg-indigo-600 text-white rounded-br-md'
													: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md'}"
										>
											{@html msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/---/g, '<hr class="my-3 border-gray-300 dark:border-gray-600">').replace(/\n/g, '<br>')}
										</div>

										{#if msg.toolCalls && msg.toolCalls.length > 0}
											{#each msg.toolCalls as tool}
												{@const data = parseToolData(tool.result)}
												<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
													<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center gap-1.5">
														<svg class="w-3 h-3 text-indigo-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
															<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17l-5.658 3.163 1.078-6.29L1.34 6.82l6.328-.92L11.42.956l2.752 5.944 6.328.92-4.5 5.223 1.078 6.29z" />
														</svg>
														<span class="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{tool.name}</span>
													</div>
													<div class="p-3">
														{#if !data}
															<p class="text-xs text-gray-500 dark:text-gray-400">No structured data returned.</p>
														{:else}
															<div class="space-y-1">
																{#each Object.entries(data).slice(0, 8) as [k, v]}
																	{#if typeof v !== 'object'}
																		<div class="flex items-center justify-between text-[11px]">
																			<span class="text-gray-400 capitalize">{k.replace(/_/g, ' ')}</span>
																			<span class="font-mono text-gray-700 dark:text-gray-300">{fmt(v)}</span>
																		</div>
																	{/if}
																{/each}
															</div>
														{/if}
													</div>
												</div>
											{/each}
										{/if}

										<div class="mt-1 px-1 text-[10px] text-gray-400 dark:text-gray-500 {msg.role === 'user' ? 'text-right' : 'text-left'}">
											{formatTime(msg.timestamp)}
										</div>
									</div>
								</div>
							{/if}
						{/each}

						{#if isTyping}
							<div class="flex justify-start">
								<div class="flex items-center gap-2">
									<div class="w-5 h-5 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
										<svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
										</svg>
									</div>
									<div class="px-4 py-3 rounded-xl bg-gray-100 dark:bg-gray-800 rounded-bl-md">
										<div class="flex items-center gap-1">
											<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500"></span>
											<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" style="animation-delay: 0.15s"></span>
											<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" style="animation-delay: 0.3s"></span>
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Input Area -->
			<div class="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
				<!-- Attached Files -->
				{#if attachedFiles.length > 0}
					<div class="px-4 sm:px-6 pt-3 flex flex-wrap gap-2">
						{#each attachedFiles as file, i}
							<div class="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-xs text-indigo-700 dark:text-indigo-300">
								<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
								</svg>
								<span class="truncate max-w-[120px]">{file.name}</span>
								<span class="text-[10px] text-indigo-400">({formatFileSize(file.size)})</span>
								<button
									class="p-0.5 rounded hover:bg-indigo-100 dark:hover:bg-indigo-500/20 transition-colors"
									on:click={() => removeFile(i)}
								>
									<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>
						{/each}
					</div>
				{/if}

				<div class="px-4 sm:px-6 py-3 sm:py-4">
					<div class="flex items-end gap-2 max-w-4xl mx-auto">
						<!-- File Upload -->
						<button
							class="flex-shrink-0 p-2.5 rounded-xl text-gray-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 transition-colors"
							on:click={() => fileInput.click()}
							title="Attach files"
						>
							<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
							</svg>
						</button>
						<input
							type="file"
							multiple
							class="hidden"
							bind:this={fileInput}
							on:change={handleFileSelect}
							accept=".pdf,.xlsx,.xls,.csv,.doc,.docx,.txt,.json,.xml"
						/>

						<!-- Text Input -->
						<div class="flex-1 relative">
							<textarea
								bind:value={inputValue}
								on:keydown={handleKeydown}
								placeholder="Ask anything about your bond portfolio..."
								rows="1"
								class="w-full resize-none text-sm border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 focus:bg-white dark:focus:bg-gray-800 transition-all"
							></textarea>
						</div>

						<!-- Send -->
						<button
							on:click={() => sendMessage()}
							disabled={!inputValue.trim() || isTyping}
							class="flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors shadow-sm"
							aria-label="Send message"
						>
							<svg class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
							</svg>
						</button>
					</div>
					<div class="flex items-center justify-between mt-2 max-w-4xl mx-auto">
						<div class="text-[10px] text-gray-400 dark:text-gray-500">
							{#if selectedModelId}
								Using: <span class="font-medium text-gray-500 dark:text-gray-400">{availableModels.find(m => m.id === selectedModelId)?.name || selectedModelId}</span>
							{/if}
						</div>
						<div class="text-[10px] text-gray-400 dark:text-gray-500">
							Press <kbd class="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 font-mono text-[9px]">Enter</kbd> to send, <kbd class="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 font-mono text-[9px]">Shift+Enter</kbd> for new line
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Right Panel (desktop) -->
		<div class="hidden lg:flex w-72 xl:w-80 flex-col border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 overflow-hidden flex-shrink-0">
			<!-- Panel Tabs -->
			<div class="flex border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
				{#each [
					{ id: 'actions', label: 'Actions' },
					{ id: 'context', label: 'Context' },
					{ id: 'activity', label: 'Activity' }
				] as tab}
					<button
						class="flex-1 px-3 py-2.5 text-xs font-medium transition-colors
							{rightPanelTab === tab.id
								? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
								: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
						on:click={() => (rightPanelTab = tab.id)}
					>
						{tab.label}
					</button>
				{/each}
			</div>

			<div class="flex-1 overflow-y-auto p-4">
				{#if rightPanelTab === 'actions'}
					<!-- Quick Actions -->
					<div class="space-y-1.5">
						{#each quickActions as action}
							<button
								class="w-full flex items-center gap-2.5 px-3 py-2.5 text-left text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors group"
								on:click={() => handleQuickAction(action.query)}
							>
								<svg class="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 flex-shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
									<path stroke-linecap="round" stroke-linejoin="round" d={actionIcon(action.icon)} />
								</svg>
								<span class="truncate">{action.label}</span>
							</button>
						{/each}
					</div>

					<!-- Models Quick Access -->
					<div class="mt-5">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Available Models</div>
						<div class="space-y-1">
							{#each availableModels.slice(0, 10) as model}
								<button
									class="w-full flex items-center gap-2 px-3 py-2 text-left text-xs rounded-lg transition-colors
										{selectedModelId === model.id
											? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20'
											: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
									on:click={() => (selectedModelId = model.id)}
								>
									<div class="w-1.5 h-1.5 rounded-full flex-shrink-0 {selectedModelId === model.id ? 'bg-indigo-500' : 'bg-gray-300 dark:bg-gray-600'}"></div>
									<span class="truncate">{model.name || model.id}</span>
								</button>
							{/each}
							{#if availableModels.length === 0}
								<div class="text-[11px] text-gray-400 px-3">No models loaded yet.</div>
							{/if}
						</div>
					</div>
				{:else if rightPanelTab === 'context'}
					<!-- Data Context -->
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Data Context</div>
					<div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800">
						{#each dataContext as ctx}
							<div class="px-3 py-2.5 flex items-center justify-between">
								<div class="min-w-0">
									<div class="text-xs font-medium text-gray-700 dark:text-gray-300">{ctx.name}</div>
									<div class="text-[10px] text-gray-400 dark:text-gray-500 truncate">{ctx.description}</div>
								</div>
								{#if ctx.count !== null}
									<span class="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400 flex-shrink-0 ml-2">{ctx.count}</span>
								{/if}
							</div>
						{/each}
					</div>

					<!-- Capabilities -->
					<div class="mt-5">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Capabilities</div>
						<div class="space-y-2">
							{#each [
								{ name: 'Bond Analysis', desc: 'Portfolio & risk analytics' },
								{ name: 'Document Upload', desc: 'PDF, Excel, CSV processing' },
								{ name: 'Report Generation', desc: 'Journals, schedules, commentary' },
								{ name: 'Reconciliation', desc: 'Automated matching & variance' },
								{ name: 'Exception Handling', desc: 'Detection & resolution' },
								{ name: 'Multi-Model Chat', desc: `${availableModels.length} models available` }
							] as cap}
								<div class="flex items-start gap-2 px-3 py-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
									<svg class="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
									</svg>
									<div>
										<div class="text-xs font-medium text-gray-700 dark:text-gray-300">{cap.name}</div>
										<div class="text-[10px] text-gray-400">{cap.desc}</div>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{:else if rightPanelTab === 'activity'}
					<!-- Recent Activity -->
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Recent Activity</div>
					<div class="space-y-2">
						{#if recentActivity.length === 0}
							<div class="text-[11px] text-gray-400 dark:text-gray-500 px-1">No recent activity for this period.</div>
						{/if}
						{#each recentActivity as entry}
							<div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 border-l-4 {insightTypeColor(activityType(entry.action))} p-3">
								<div class="flex items-center gap-1.5 mb-1">
									<span class="w-1.5 h-1.5 rounded-full {insightDotColor(activityType(entry.action))} flex-shrink-0"></span>
									<span class="text-xs font-medium text-gray-900 dark:text-white truncate">{entry.action}</span>
								</div>
								<p class="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">{entry.details}</p>
								<div class="mt-1.5 text-[10px] text-gray-400 dark:text-gray-500">{relativeTime(entry.timestamp)}</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	@keyframes typingBounce {
		0%, 60%, 100% {
			transform: translateY(0);
			opacity: 0.4;
		}
		30% {
			transform: translateY(-4px);
			opacity: 1;
		}
	}

	.typing-dot {
		animation: typingBounce 1.2s ease-in-out infinite;
	}
</style>
