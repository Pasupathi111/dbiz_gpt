<script lang="ts">
	import { assistantContext } from '$lib/assistant/context';
	import { getSuggestionsForPage, type Suggestion } from '$lib/assistant/capabilities';
	import { isHighRisk } from '$lib/assistant/tools';
	import { executeAgentAction, copilotChat } from '$lib/apis/finance';
	import AssistantResultCard from './AssistantResultCard.svelte';
	import ConfirmActionModal from './ConfirmActionModal.svelte';

	export let onClose: () => void = () => {};

	let agentMode = true;

	interface TimelineEntry {
		id: string;
		role: 'user' | 'assistant';
		kind: 'text' | 'result' | 'error' | 'running';
		content?: string;
		action?: string;
		result?: any;
		timestamp: Date;
		legacyToolCalls?: { name: string; result: string }[];
	}

	let timeline: TimelineEntry[] = [];
	let inputValue = '';
	let isBusy = false;
	let messagesContainer: HTMLDivElement;

	let confirmOpen = false;
	let confirmMessage = '';
	let pendingSuggestion: Suggestion | null = null;

	$: suggestions = getSuggestionsForPage($assistantContext);

	function newId(prefix: string) {
		return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
	}

	async function scrollToBottom() {
		await new Promise((r) => setTimeout(r, 20));
		if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
	}

	function buildContext(): Record<string, unknown> {
		const ctx = $assistantContext;
		return {
			page: ctx.page,
			module: ctx.module,
			periodId: ctx.periodId,
			selectedBondIds: ctx.selectedBondIds || [],
			selectedRecords: ctx.selectedRecords || [],
			entityId: ctx.entityId,
			filters: ctx.filters || {},
			pageData: ctx.pageData || {}
		};
	}

	function getToken(): string {
		return localStorage.token;
	}

	async function runAction(suggestion: Suggestion, confirmed = false) {
		isBusy = true;
		const runningId = newId('run');
		timeline = [
			...timeline,
			{ id: runningId, role: 'assistant', kind: 'running', content: `Running "${suggestion.label}"...`, timestamp: new Date() }
		];
		await scrollToBottom();

		try {
			const res = await executeAgentAction(getToken(), suggestion.action, buildContext(), suggestion.label, confirmed);
			timeline = timeline.filter((t) => t.id !== runningId);

			if (res.status === 'confirmation_required') {
				pendingSuggestion = suggestion;
				confirmMessage = res.message || 'Proceed with this action?';
				confirmOpen = true;
				isBusy = false;
				return;
			}

			if (!res.success) {
				timeline = [
					...timeline,
					{
						id: newId('err'),
						role: 'assistant',
						kind: 'error',
						content: res.message || `"${suggestion.label}" could not be completed.`,
						timestamp: new Date()
					}
				];
			} else {
				timeline = [
					...timeline,
					{
						id: newId('res'),
						role: 'assistant',
						kind: 'result',
						action: res.action,
						result: res.result,
						timestamp: new Date()
					}
				];
			}
		} catch (err: any) {
			timeline = timeline.filter((t) => t.id !== runningId);
			timeline = [
				...timeline,
				{
					id: newId('err'),
					role: 'assistant',
					kind: 'error',
					content: err?.message || `"${suggestion.label}" could not be completed.`,
					timestamp: new Date()
				}
			];
		} finally {
			isBusy = false;
			await scrollToBottom();
		}
	}

	function handleSuggestionClick(suggestion: Suggestion) {
		if (isBusy) return;
		timeline = [
			...timeline,
			{ id: newId('u'), role: 'user', kind: 'text', content: suggestion.label, timestamp: new Date() }
		];
		if (isHighRisk(suggestion.action)) {
			runAction(suggestion, false);
		} else {
			runAction(suggestion, true);
		}
	}

	function confirmPending() {
		confirmOpen = false;
		if (pendingSuggestion) runAction(pendingSuggestion, true);
		pendingSuggestion = null;
	}

	function cancelPending() {
		confirmOpen = false;
		timeline = [
			...timeline,
			{ id: newId('cancel'), role: 'assistant', kind: 'text', content: 'Cancelled.', timestamp: new Date() }
		];
		pendingSuggestion = null;
	}

	async function sendChat() {
		const msg = inputValue.trim();
		if (!msg || isBusy) return;
		inputValue = '';
		timeline = [...timeline, { id: newId('u'), role: 'user', kind: 'text', content: msg, timestamp: new Date() }];
		isBusy = true;
		await scrollToBottom();

		try {
			const data = await copilotChat(getToken(), msg, $assistantContext.periodId);
			timeline = [
				...timeline,
				{
					id: newId('a'),
					role: 'assistant',
					kind: 'text',
					content: data.content || "Sorry, I couldn't process that request.",
					legacyToolCalls: (data.tool_calls || []).map((tc: any) => ({ name: tc.name, result: tc.result })),
					timestamp: new Date()
				}
			];
		} catch (err: any) {
			timeline = [
				...timeline,
				{
					id: newId('e'),
					role: 'assistant',
					kind: 'error',
					content: err?.message || 'Something went wrong processing that request.',
					timestamp: new Date()
				}
			];
		} finally {
			isBusy = false;
			await scrollToBottom();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendChat();
		}
	}

	function handleExampleClick(text: string) {
		inputValue = text;
		sendChat();
	}

	function formatTime(d: Date): string {
		return d.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' });
	}

	const examples = [
		{ icon: 'chart', text: 'Show me active bonds with market value > $1M' },
		{ icon: 'doc', text: 'Create a monthly market value summary' },
		{ icon: 'calendar', text: 'Find bonds maturing next year' },
		{ icon: 'alert', text: 'Highlight bonds with low confidence' }
	];
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-900">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2.5">
				<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
					<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
					</svg>
				</div>
				<div>
					<div class="text-sm font-semibold text-gray-900 dark:text-white">Agentic AI</div>
					<div class="flex items-center gap-1.5">
						<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
						<span class="text-[11px] text-gray-500 dark:text-gray-400">Online &bull; Ready to help</span>
					</div>
				</div>
			</div>
			<div class="flex items-center gap-1">
				<button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Expand">
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" /></svg>
				</button>
				<button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="History">
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
				</button>
				<button
					on:click={onClose}
					class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					aria-label="Close"
				>
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
				</button>
			</div>
		</div>
	</div>

	<!-- Body -->
	<div class="flex-1 overflow-y-auto px-4 py-4 space-y-4" bind:this={messagesContainer}>
		{#if timeline.length === 0}
			<!-- Welcome message -->
			<div class="space-y-4">
				<div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">Hi there! <span class="text-lg">&#x1F44B;</span></h3>
					<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						I'm your Agentic AI, powered by your bond data. I can help you with:
					</p>
				</div>

				<div class="space-y-2.5">
					{#each [
						'Answer questions about bond data',
						'Create reports and visualizations',
						'Analyze risks and trends',
						'Automate routine tasks',
						'Guide you through workflows'
					] as capability}
						<div class="flex items-center gap-2.5">
							<div class="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
								<svg class="w-3 h-3 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
							</div>
							<span class="text-sm text-gray-700 dark:text-gray-300">{capability}</span>
						</div>
					{/each}
				</div>

				<!-- Page-specific suggestions -->
				{#if suggestions.length > 0}
					<div class="pt-2">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
							Suggested for this page
						</div>
						<div class="space-y-1.5">
							{#each suggestions as s (s.id)}
								<button
									disabled={isBusy}
									class="w-full flex items-center justify-between gap-2 text-left px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors disabled:opacity-50"
									on:click={() => handleSuggestionClick(s)}
								>
									<span class="flex items-center gap-1.5">
										<span class="text-indigo-400">&#x2726;</span>
										{s.label}
									</span>
									{#if isHighRisk(s.action)}
										<span class="text-[9px] uppercase tracking-wide text-amber-500 flex-shrink-0">confirm</span>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Example prompts -->
				<div class="pt-2">
					<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Try these examples:</div>
					<div class="space-y-2">
						{#each examples as ex}
							<button
								class="w-full flex items-center gap-3 text-left px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5 transition-colors group"
								on:click={() => handleExampleClick(ex.text)}
							>
								<div class="w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-800 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 flex items-center justify-center flex-shrink-0 transition-colors">
									{#if ex.icon === 'chart'}
										<svg class="w-3.5 h-3.5 text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>
									{:else if ex.icon === 'doc'}
										<svg class="w-3.5 h-3.5 text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
									{:else if ex.icon === 'calendar'}
										<svg class="w-3.5 h-3.5 text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" /></svg>
									{:else}
										<svg class="w-3.5 h-3.5 text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
									{/if}
								</div>
								<span class="text-sm text-indigo-600 dark:text-indigo-400 group-hover:text-indigo-700 dark:group-hover:text-indigo-300">{ex.text}</span>
							</button>
						{/each}
					</div>
				</div>
			</div>
		{:else}
			<!-- Chat timeline -->
			{#if suggestions.length > 0}
				<div>
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
						Suggested for this page
					</div>
					<div class="space-y-1.5">
						{#each suggestions as s (s.id)}
							<button
								disabled={isBusy}
								class="w-full flex items-center justify-between gap-2 text-left px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors disabled:opacity-50"
								on:click={() => handleSuggestionClick(s)}
							>
								<span class="flex items-center gap-1.5">
									<span class="text-indigo-400">&#x2726;</span>
									{s.label}
								</span>
								{#if isHighRisk(s.action)}
									<span class="text-[9px] uppercase tracking-wide text-amber-500 flex-shrink-0">confirm</span>
								{/if}
							</button>
						{/each}
					</div>
				</div>
			{/if}

			{#each timeline as entry (entry.id)}
				<div class="flex {entry.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[90%] w-full">
						{#if entry.kind === 'running'}
							<div class="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
								<span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
								{entry.content}
							</div>
						{:else if entry.kind === 'result'}
							<AssistantResultCard action={entry.action} result={entry.result} />
						{:else}
							<div
								class="px-3.5 py-2.5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap
									{entry.role === 'user'
										? 'bg-indigo-600 text-white rounded-br-md ml-auto max-w-[85%]'
										: entry.kind === 'error'
											? 'bg-red-50 dark:bg-red-900/10 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800/60 rounded-bl-md'
											: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md'}"
							>
								{entry.content}
							</div>
							{#if entry.legacyToolCalls && entry.legacyToolCalls.length > 0}
								{#each entry.legacyToolCalls as tool}
									<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
										<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
											<span class="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{tool.name}</span>
										</div>
										<pre class="px-3 py-2 text-[11px] font-mono text-gray-600 dark:text-gray-400 overflow-x-auto max-h-48 bg-white dark:bg-gray-900">{tool.result}</pre>
									</div>
								{/each}
							{/if}
						{/if}
						<div class="mt-1 px-1 text-[10px] text-gray-400 dark:text-gray-500 {entry.role === 'user' ? 'text-right' : 'text-left'}">
							{formatTime(entry.timestamp)}
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</div>

	<!-- Input -->
	<div class="border-t border-gray-200 dark:border-gray-800 px-4 py-3 flex-shrink-0">
		<div class="flex items-end gap-2">
			<button class="flex-shrink-0 p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Attach file">
				<svg class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" /></svg>
			</button>
			<textarea
				bind:value={inputValue}
				on:keydown={handleKeydown}
				placeholder="Ask the AI Bond Copilot anything..."
				rows="1"
				class="flex-1 resize-none text-sm border border-gray-200 dark:border-gray-700 rounded-xl px-3.5 py-2.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
			></textarea>
			<button
				on:click={sendChat}
				disabled={!inputValue.trim() || isBusy}
				class="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white flex items-center justify-center transition-colors"
				aria-label="Send message"
			>
				<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
				</svg>
			</button>
		</div>
		<!-- Agent mode toggle -->
		<div class="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
			<div class="flex items-center gap-2">
				<span class="text-xs font-medium text-gray-700 dark:text-gray-300">Use agent mode</span>
				<button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" aria-label="Agent mode info">
					<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
				</button>
			</div>
			<button
				on:click={() => (agentMode = !agentMode)}
				class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {agentMode ? 'bg-indigo-600' : 'bg-gray-300 dark:bg-gray-600'}"
				aria-label="Toggle agent mode"
			>
				<span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform {agentMode ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
			</button>
		</div>
		<div class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">Let AI take actions (create reports, run analysis, etc.)</div>
	</div>
</div>

<ConfirmActionModal
	open={confirmOpen}
	message={confirmMessage}
	confirmLabel="Confirm"
	onConfirm={confirmPending}
	onCancel={cancelPending}
/>
