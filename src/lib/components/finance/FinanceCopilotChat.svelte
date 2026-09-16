<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';
	import { copilotChat } from '$lib/apis/finance';

	export let open = false;
	export let onClose: () => void = () => {};

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: Date;
		toolCalls?: { name: string; result: string }[];
		error?: boolean;
	}

	let messages: ChatMessage[] = [];
	let inputValue = '';
	let isTyping = false;
	let messagesContainer: HTMLDivElement;
	let lastError: string | null = null;

	const quickActions = [
		'Portfolio summary',
		'Show exceptions',
		'Reconciliation status',
		'Pending reviews',
		'Generate commentary'
	];

	async function sendMessage(text?: string) {
		const msg = (text || inputValue).trim();
		if (!msg || isTyping) return;

		inputValue = '';
		lastError = null;

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
			// @ts-expect-error - localStorage.token populated at runtime by Open WebUI after sign-in
			const token: string = localStorage.token;
			const currentPeriod: string | undefined =
				// @ts-expect-error - current period optionally set on window by parent
				window.__FINANCE_CURRENT_PERIOD__ || undefined;
			const data = await copilotChat(token, msg, currentPeriod);

			const assistantMsg: ChatMessage = {
				id: `msg-${Date.now()}-assistant`,
				role: 'assistant',
				content: data.content || 'Sorry, I could not process that request.',
				timestamp: new Date(),
				toolCalls: (data.tool_calls || []).map((tc: any) => ({
					name: tc.name,
					result: tc.result
				}))
			};
			messages = [...messages, assistantMsg];
		} catch (err: any) {
			const detail = err?.detail || err?.message || String(err);
			lastError = detail;
			const errMsg: ChatMessage = {
				id: `msg-${Date.now()}-error`,
				role: 'assistant',
				content: `Sorry, I encountered an error while processing your request.\n\n**Error:** ${detail}`,
				timestamp: new Date(),
				error: true
			};
			messages = [...messages, errMsg];
		} finally {
			isTyping = false;
			await scrollToBottom();
		}
	}

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

	function handleQuickAction(action: string) {
		sendMessage(action);
	}

	function handleBackdropClick() {
		onClose();
	}
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="AI Copilot Chat">
		<!-- Backdrop -->
		<div
			class="absolute inset-0 bg-black/20 dark:bg-black/40 transition-opacity"
			on:click={handleBackdropClick}
		></div>

		<!-- Chat Panel -->
		<div
			class="relative w-full max-w-[420px] bg-white dark:bg-gray-900 shadow-2xl flex flex-col border-l border-gray-200 dark:border-gray-700 animate-slide-in"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
				<div class="flex items-center gap-3">
					<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
						<svg class="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
						</svg>
					</div>
					<div>
						<div class="text-sm font-semibold text-gray-900 dark:text-white">AI Bond Copilot</div>
						<div class="text-[10px] text-gray-500 dark:text-gray-400">Finance Intelligence Assistant</div>
					</div>
				</div>
				<button
					on:click={onClose}
					class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					aria-label="Close chat"
				>
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Messages Area -->
			<div class="flex-1 overflow-y-auto px-4 py-4 space-y-4" bind:this={messagesContainer}>
				<!-- Inline error banner for last request failure -->
				{#if lastError}
					<div class="mb-3 rounded-lg border border-red-200 dark:border-red-800/60 bg-red-50 dark:bg-red-900/10 px-3 py-2 flex items-start gap-2">
						<svg class="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
						</svg>
						<div class="text-xs text-red-700 dark:text-red-300">
							<div class="font-semibold mb-0.5">Request failed</div>
							<div class="break-all">{lastError}</div>
						</div>
					</div>
				{/if}

				{#if messages.length === 0}
					<!-- Welcome state -->
					<div class="flex flex-col items-center justify-center h-full text-center px-4">
						<div class="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-500/10 flex items-center justify-center mb-4">
							<svg class="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
							</svg>
						</div>
						<h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">AI Bond Copilot</h3>
						<p class="text-xs text-gray-500 dark:text-gray-400 mb-5 max-w-[280px]">
							Ask me about your bond portfolio, reconciliation status, exceptions, journals, or anything finance-related.
						</p>

						<!-- Quick Actions -->
						<div class="w-full space-y-1.5">
							<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Quick Actions</div>
							{#each quickActions as action}
								<button
									class="w-full text-left px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
									on:click={() => handleQuickAction(action)}
								>
									{action}
								</button>
							{/each}
						</div>
					</div>
				{:else}
					{#each messages as msg}
						<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
							<div class="max-w-[85%]">
								<!-- Bubble -->
								<div
									class="px-3.5 py-2.5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap
										{msg.role === 'user'
											? 'bg-indigo-600 text-white rounded-br-md'
											: msg.error
												? 'bg-red-50 dark:bg-red-900/10 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800/60 rounded-bl-md'
												: 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md'}"
								>
									{@html msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}
								</div>

								<!-- Tool call results -->
								{#if msg.toolCalls && msg.toolCalls.length > 0}
									{#each msg.toolCalls as tool}
										<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
											<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center gap-1.5">
												<svg class="w-3 h-3 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
													<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17l-5.658 3.163 1.078-6.29L1.34 6.82l6.328-.92L11.42.956l2.752 5.944 6.328.92-4.5 5.223 1.078 6.29z" />
												</svg>
												<span class="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{tool.name}</span>
											</div>
											<pre class="px-3 py-2 text-[11px] font-mono text-gray-600 dark:text-gray-400 overflow-x-auto max-h-48 bg-white dark:bg-gray-900">{tool.result}</pre>
										</div>
									{/each}
								{/if}

								<!-- Timestamp -->
								<div class="mt-1 px-1 text-[10px] text-gray-400 dark:text-gray-500 {msg.role === 'user' ? 'text-right' : 'text-left'}">
									{formatTime(msg.timestamp)}
								</div>
							</div>
						</div>
					{/each}

					<!-- Typing indicator -->
					{#if isTyping}
						<div class="flex justify-start">
							<div class="px-4 py-3 rounded-xl bg-gray-100 dark:bg-gray-800 rounded-bl-md">
								<div class="flex items-center gap-1">
									<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500"></span>
									<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" style="animation-delay: 0.15s"></span>
									<span class="typing-dot w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" style="animation-delay: 0.3s"></span>
								</div>
							</div>
						</div>
					{/if}
				{/if}
			</div>

			<!-- Input Area -->
			<div class="border-t border-gray-200 dark:border-gray-800 px-4 py-3 bg-white dark:bg-gray-900">
				{#if messages.length > 0}
					<div class="flex flex-wrap gap-1.5 mb-2">
						{#each quickActions.slice(0, 3) as action}
							<button
								class="px-2.5 py-1 text-[10px] rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
								on:click={() => handleQuickAction(action)}
							>
								{action}
							</button>
						{/each}
					</div>
				{/if}
				<div class="flex items-end gap-2">
					<textarea
						bind:value={inputValue}
						on:keydown={handleKeydown}
						placeholder="Ask the AI Copilot..."
						rows="1"
						class="flex-1 resize-none text-sm border border-gray-200 dark:border-gray-700 rounded-xl px-3.5 py-2.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
					></textarea>
					<button
						on:click={() => sendMessage()}
						disabled={!inputValue.trim() || isTyping}
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

<style>
	@keyframes slideIn {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	.animate-slide-in {
		animation: slideIn 0.25s ease-out;
	}

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
