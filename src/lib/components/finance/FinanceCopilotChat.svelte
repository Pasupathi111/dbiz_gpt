<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';

	export let open = false;
	export let onClose: () => void = () => {};

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: Date;
		toolCalls?: { name: string; result: string }[];
	}

	let messages: ChatMessage[] = [];
	let inputValue = '';
	let isTyping = false;
	let messagesContainer: HTMLDivElement;

	const quickActions = [
		'Portfolio summary',
		'Show exceptions',
		'Reconciliation status',
		'Pending reviews',
		'Generate commentary'
	];

	// --- Mock chat handler ---
	function generateMockResponse(query: string): { content: string; toolCalls?: { name: string; result: string }[] } {
		const q = query.toLowerCase();

		if (q.includes('portfolio') || q.includes('bond') || q.includes('summary')) {
			return {
				content: 'Here is your current portfolio summary for September 2026.',
				toolCalls: [
					{
						name: 'get_portfolio_summary',
						result: JSON.stringify({
							total_bonds: 82,
							total_market_value: 'SGD 45,200,000',
							total_face_value: 'SGD 42,800,000',
							reconciliation_rate: '98.7%',
							currency: 'SGD',
							top_holdings: [
								{ name: 'Singapore Govt 3.375% 2033', value: 'SGD 4,250,000' },
								{ name: 'Temasek 4.125% 2034', value: 'SGD 5,420,000' },
								{ name: 'HDB 2.750% 2029', value: 'SGD 3,180,000' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('exception') || q.includes('issue') || q.includes('problem')) {
			return {
				content: 'There are currently 2 open exceptions requiring attention.',
				toolCalls: [
					{
						name: 'get_open_exceptions',
						result: JSON.stringify({
							open_count: 2,
							resolved_count: 3,
							exceptions: [
								{ id: 'EXC-001', title: 'Market Value Variance — Mapletree Logistics Trust', severity: 'HIGH', status: 'OPEN', variance: 'SGD 5,200' },
								{ id: 'EXC-004', title: 'Extraction Confidence Below Threshold', severity: 'MEDIUM', status: 'OPEN', bond: 'BOND-006' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('reconciliation') || q.includes('recon') || q.includes('match')) {
			return {
				content: 'Reconciliation for September 2026 is complete. Here are the results.',
				toolCalls: [
					{
						name: 'get_reconciliation_summary',
						result: JSON.stringify({
							period: 'September 2026',
							total_items: 82,
							matched: 79,
							variances: 2,
							missing: 1,
							match_rate: '96.3%',
							total_variance: 'SGD 5,400',
							status: 'Complete with exceptions'
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('review') || q.includes('pending') || q.includes('approval')) {
			return {
				content: 'There are 6 items pending review in the approval queue.',
				toolCalls: [
					{
						name: 'get_pending_reviews',
						result: JSON.stringify({
							pending_count: 6,
							approved_count: 2,
							items: [
								{ type: 'JOURNAL', title: 'Bond Purchase Journal JV-2026-09-001', priority: 'HIGH', amount: 'SGD 3,550,000' },
								{ type: 'JOURNAL', title: 'Accrued Interest Journal JV-2026-09-003', priority: 'MEDIUM', amount: 'SGD 84,024' },
								{ type: 'MOVEMENT', title: 'Bond Sold — HDB 2.50% 2027', priority: 'HIGH', amount: 'SGD 400,000' },
								{ type: 'EXCEPTION', title: 'Market Value Variance — Mapletree', priority: 'HIGH', amount: 'SGD 5,200' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('commentary') || q.includes('narrative') || q.includes('report')) {
			return {
				content: 'I can generate month-end commentary for September 2026. The commentary will cover portfolio movements, reconciliation results, and key observations. The current draft covers 6 sections with approximately 520 words.\n\nWould you like me to generate a fresh commentary draft, or review the existing one?'
			};
		}

		if (q.includes('journal') || q.includes('entries') || q.includes('accounting')) {
			return {
				content: 'There are 12 draft journal entries for September 2026.',
				toolCalls: [
					{
						name: 'get_journal_summary',
						result: JSON.stringify({
							total_journals: 12,
							status: '4 pending review, 2 approved, 6 draft',
							total_debits: 'SGD 5,796,024',
							total_credits: 'SGD 5,796,024',
							balanced: true,
							types: ['Bond Purchase', 'Bond Maturity', 'Accrued Interest', 'Fair Value Adjustment']
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('audit') || q.includes('schedule')) {
			return {
				content: 'The audit schedule for September 2026 has been generated with 82 bond line items. All bonds have been mapped to the required SFRS(I) 9 disclosures. The schedule is ready for review.'
			};
		}

		if (q.includes('hello') || q.includes('hi') || q.includes('hey')) {
			return {
				content: `Hello! I'm the AI Bond Copilot. I can help you with:\n\n- **Portfolio analysis** — bond holdings, market values, and allocations\n- **Reconciliation** — matching status, variances, and exceptions\n- **Journals** — draft entries, approvals, and balances\n- **Commentary** — month-end narrative generation\n- **Reviews** — pending approvals and action items\n\nWhat would you like to know?`
			};
		}

		return {
			content: `I understand you're asking about "${query}". Let me help you with that.\n\nFor the September 2026 reporting period, here's what I can tell you:\n\n- **82 bonds** in the active portfolio (SGD 45.2M market value)\n- **98.7%** reconciliation match rate\n- **2 open exceptions** requiring attention\n- **6 items** pending review\n- **12 draft journals** generated\n\nCould you be more specific about what you'd like to explore? I can drill into portfolio details, reconciliation results, exceptions, journals, or commentary.`
		};
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

		// Simulate typing delay
		const delay = 500 + Math.random() * 500;
		await new Promise((r) => setTimeout(r, delay));

		const response = generateMockResponse(msg);

		const assistantMsg: ChatMessage = {
			id: `msg-${Date.now()}-assistant`,
			role: 'assistant',
			content: response.content,
			timestamp: new Date(),
			toolCalls: response.toolCalls
		};
		messages = [...messages, assistantMsg];
		isTyping = false;

		await scrollToBottom();

		// --- Real API call (commented out for mock backend) ---
		// try {
		//   const res = await fetch('/api/chat/completions', {
		//     method: 'POST',
		//     headers: {
		//       'Authorization': `Bearer ${localStorage.token}`,
		//       'Content-Type': 'application/json'
		//     },
		//     body: JSON.stringify({
		//       model: 'finance-copilot',
		//       messages: messages.map(m => ({ role: m.role, content: m.content })),
		//       stream: false,
		//       tools: [
		//         { type: 'function', function: { name: 'get_portfolio_summary', description: 'Get bond portfolio summary' } },
		//         { type: 'function', function: { name: 'get_open_exceptions', description: 'Get open exceptions list' } },
		//         { type: 'function', function: { name: 'get_reconciliation_summary', description: 'Get reconciliation summary' } },
		//         { type: 'function', function: { name: 'get_pending_reviews', description: 'Get pending review items' } },
		//         { type: 'function', function: { name: 'get_journal_summary', description: 'Get journal entries summary' } }
		//       ]
		//     })
		//   });
		//   const data = await res.json();
		//   const assistantMsg: ChatMessage = {
		//     id: `msg-${Date.now()}-assistant`,
		//     role: 'assistant',
		//     content: data.choices?.[0]?.message?.content || 'Sorry, I could not process that request.',
		//     timestamp: new Date(),
		//     toolCalls: data.choices?.[0]?.message?.tool_calls?.map((tc: any) => ({
		//       name: tc.function.name,
		//       result: tc.function.arguments
		//     }))
		//   };
		//   messages = [...messages, assistantMsg];
		// } catch (err) {
		//   messages = [...messages, {
		//     id: `msg-${Date.now()}-error`,
		//     role: 'assistant',
		//     content: 'Sorry, I encountered an error. Please try again.',
		//     timestamp: new Date()
		//   }];
		// }
		// isTyping = false;
		// await scrollToBottom();
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
