<script lang="ts">
	/**
	 * Global Agentic Assistant — floating button + right-side drawer.
	 *
	 * Mounted once (finance/+layout.svelte). Pages never import this
	 * component; they only call `registerAssistantContext(...)` from
	 * `$lib/assistant/context`. Suggestions come from
	 * `$lib/assistant/capabilities`; execution goes through
	 * `executeAgentAction` (backend `/finance/agent/execute`), which is the
	 * single place tools are actually run — this component never calls
	 * finance business logic directly.
	 */
	import { assistantContext } from '$lib/assistant/context';
	import { getSuggestionsForPage, type Suggestion } from '$lib/assistant/capabilities';
	import { isHighRisk } from '$lib/assistant/tools';
	import { executeAgentAction, copilotChat } from '$lib/apis/finance';
	import AssistantResultCard from './AssistantResultCard.svelte';
	import ConfirmActionModal from './ConfirmActionModal.svelte';

	let open = false;

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

	// @ts-expect-error - localStorage.token populated at runtime after sign-in
	function getToken(): string {
		return localStorage.token;
	}

	async function runAction(suggestion: Suggestion, confirmed = false) {
		isBusy = true;
		const runningId = newId('run');
		timeline = [
			...timeline,
			{ id: runningId, role: 'assistant', kind: 'running', content: `Running "${suggestion.label}"…`, timestamp: new Date() }
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
			// Let the backend supply the exact confirmation copy (it knows the
			// tool's real-world consequence) — call unconfirmed first.
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

	function formatTime(d: Date): string {
		return d.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' });
	}
</script>

<!-- Floating button -->
<button
	class="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:scale-105 flex items-center justify-center transition-all duration-200 group"
	on:click={() => (open = !open)}
	aria-label="Toggle Agentic Assistant"
>
	<svg class="w-5.5 h-5.5 group-hover:scale-110 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
		<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
	</svg>
	<span class="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-amber-400 border-2 border-white dark:border-gray-900 copilot-pulse"></span>
</button>

{#if open}
	<div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Agentic Assistant">
		<div class="absolute inset-0 bg-black/20 dark:bg-black/40 transition-opacity" on:click={() => (open = false)}></div>

		<div
			class="relative w-full max-w-[400px] bg-white dark:bg-gray-900 shadow-2xl flex flex-col border-l border-gray-200 dark:border-gray-700 animate-slide-in"
		>
			<!-- Header -->
			<div class="px-5 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
				<div class="flex items-center justify-between mb-1">
					<div class="flex items-center gap-2.5">
						<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
							<svg class="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
							</svg>
						</div>
						<div class="text-sm font-semibold text-gray-900 dark:text-white">Agentic Assistant</div>
					</div>
					<button
						on:click={() => (open = false)}
						class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						aria-label="Close assistant"
					>
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				{#if $assistantContext.pageTitle}
					<div class="text-[11px] text-gray-400 dark:text-gray-500 pl-[42px]">
						Aware of: {$assistantContext.module || 'App'} &gt; {$assistantContext.pageTitle}
					</div>
				{/if}
			</div>

			<!-- Body -->
			<div class="flex-1 overflow-y-auto px-4 py-4 space-y-4" bind:this={messagesContainer}>
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
										<span class="text-indigo-400">✦</span>
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

				{#if timeline.length === 0}
					<div class="text-center px-2 py-6 text-xs text-gray-400 dark:text-gray-500">
						Pick a suggestion above, or ask a question below.
					</div>
				{:else}
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
			<div class="border-t border-gray-200 dark:border-gray-800 px-4 py-3 bg-white dark:bg-gray-900">
				<div class="flex items-end gap-2">
					<textarea
						bind:value={inputValue}
						on:keydown={handleKeydown}
						placeholder="Ask the assistant to take an action…"
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
			</div>
		</div>
	</div>
{/if}

<ConfirmActionModal
	open={confirmOpen}
	message={confirmMessage}
	confirmLabel="Confirm"
	onConfirm={confirmPending}
	onCancel={cancelPending}
/>

<style>
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
