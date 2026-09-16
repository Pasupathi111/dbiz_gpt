<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import {
		copilotChat,
		getReportingPeriods,
		getFinanceDashboard,
		getAuditTrail
	} from '$lib/apis/finance';

	const i18n = getContext('i18n');

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant' | 'system';
		content: string;
		timestamp: Date;
		toolCalls?: { name: string; result: string }[];
	}

	let messages: ChatMessage[] = [];
	let inputValue = '';
	let isTyping = false;
	let messagesContainer: HTMLDivElement;
	let periods: any[] = [];
	let selectedPeriodId = '';

	const quickActions = [
		{ label: 'Generate Month-End Commentary', icon: 'doc', query: 'Generate month-end commentary for the current period' },
		{ label: 'Run Reconciliation Analysis', icon: 'recon', query: 'Run reconciliation analysis and show me the current status' },
		{ label: 'Review Exception Summary', icon: 'exception', query: 'Show me a summary of all open exceptions' },
		{ label: 'Generate Journal Entries', icon: 'journal', query: 'Show me the draft journal entries for the current period' },
		{ label: 'Check Review Queue', icon: 'audit', query: 'What reviews are pending?' }
	];

	// Real recent finance actions (from the audit trail) and live period KPIs —
	// replaces the previously hardcoded "Recent Insights" / "Data Context" panels.
	let recentActivity: any[] = [];
	let dataContext: { name: string; count: number | null; description: string }[] = [];

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

	async function sendMessage(text?: string) {
		const msg = (text || inputValue).trim();
		if (!msg || isTyping) return;

		inputValue = '';

		const userMsg: ChatMessage = {
			id: `msg-${Date.now()}-user`,
			role: 'user',
			content: msg,
			timestamp: new Date()
		};
		messages = [...messages, userMsg];

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
		await loadSidebar();
	});

	async function scrollToBottom() {
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
		inputValue = query;
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
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- Header -->
	<div class="px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span><span>/</span><span>AI Assistant</span>
		</div>
		<div class="flex items-center justify-between gap-3">
			<div class="flex items-center gap-3">
				<div class="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
					</svg>
				</div>
				<div>
					<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">AI Assistant</h1>
					<p class="text-sm text-gray-500 dark:text-gray-400">Your intelligent assistant for bond portfolio management</p>
				</div>
			</div>
			<select
				class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
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
		</div>
	</div>

	<!-- Main content -->
	<div class="flex-1 flex overflow-hidden">
		<!-- Left: Chat (2/3) -->
		<div class="flex-[2] flex flex-col min-w-0 border-r border-gray-200 dark:border-gray-800">
			<!-- System message -->
			<div class="px-6 py-3 bg-indigo-50 dark:bg-indigo-500/5 border-b border-indigo-100 dark:border-indigo-500/10">
				<div class="flex items-center gap-2">
					<svg class="w-4 h-4 text-indigo-500 dark:text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
					</svg>
					<span class="text-xs text-indigo-700 dark:text-indigo-300 font-medium">AI Bond Copilot</span>
					<span class="text-xs text-indigo-500 dark:text-indigo-400">&mdash;</span>
					<span class="text-xs text-indigo-600/80 dark:text-indigo-400/70">Your intelligent assistant for bond portfolio management</span>
				</div>
			</div>

			<!-- Messages -->
			<div class="flex-1 overflow-y-auto px-6 py-5 space-y-4" bind:this={messagesContainer}>
				{#if messages.length === 0}
					<div class="flex flex-col items-center justify-center h-full text-center px-8">
						<div class="w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-500/10 flex items-center justify-center mb-5">
							<svg class="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
							</svg>
						</div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">How can I help you today?</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 max-w-md">
							Ask me about your bond portfolio, run analyses, generate reports, or use the Quick Actions panel to get started.
						</p>
					</div>
				{:else}
					{#each messages as msg}
						{#if msg.role !== 'system'}
							<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
								<div class="max-w-[75%]">
									{#if msg.role === 'assistant'}
										<div class="flex items-center gap-2 mb-1.5">
											<div class="w-5 h-5 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
												<svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
													<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
												</svg>
											</div>
											<span class="text-[10px] font-medium text-gray-500 dark:text-gray-400">AI Bond Copilot</span>
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
											<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
												<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center gap-1.5">
													<svg class="w-3 h-3 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
														<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17l-5.658 3.163 1.078-6.29L1.34 6.82l6.328-.92L11.42.956l2.752 5.944 6.328.92-4.5 5.223 1.078 6.29z" />
													</svg>
													<span class="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{tool.name}</span>
												</div>
												<pre class="px-3 py-2.5 text-[11px] font-mono text-gray-600 dark:text-gray-400 overflow-x-auto max-h-64 bg-white dark:bg-gray-900">{tool.result}</pre>
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
				{/if}
			</div>

			<!-- Input -->
			<div class="border-t border-gray-200 dark:border-gray-800 px-6 py-4 bg-white dark:bg-gray-900 flex-shrink-0">
				<div class="flex items-end gap-3">
					<textarea
						bind:value={inputValue}
						on:keydown={handleKeydown}
						placeholder="Ask the AI Bond Copilot anything..."
						rows="1"
						class="flex-1 resize-none text-sm border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
					></textarea>
					<button
						on:click={() => sendMessage()}
						disabled={!inputValue.trim() || isTyping}
						class="flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white flex items-center justify-center transition-colors"
						aria-label="Send message"
					>
						<svg class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
						</svg>
					</button>
				</div>
			</div>
		</div>

		<!-- Right: Sidebar (1/3) -->
		<div class="flex-1 flex flex-col overflow-y-auto bg-gray-50 dark:bg-gray-950 min-w-[300px] max-w-[400px]">
			<div class="p-5 space-y-5">
				<!-- Quick Actions -->
				<div>
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Quick Actions</div>
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
				</div>

				<!-- Recent Activity -->
				<div>
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
				</div>

				<!-- Data Context -->
				<div>
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
				</div>
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
