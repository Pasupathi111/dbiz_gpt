<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';

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

	const quickActions = [
		{ label: 'Generate Month-End Commentary', icon: 'doc', query: 'Generate month-end commentary for September 2026' },
		{ label: 'Run Reconciliation Analysis', icon: 'recon', query: 'Run reconciliation analysis and show me the current status' },
		{ label: 'Analyze Portfolio Risk', icon: 'risk', query: 'Analyze portfolio risk for the current bond holdings' },
		{ label: 'Review Exception Summary', icon: 'exception', query: 'Show me a summary of all open exceptions' },
		{ label: 'Generate Journal Entries', icon: 'journal', query: 'Show me the draft journal entries for September 2026' },
		{ label: 'Check Audit Progress', icon: 'audit', query: 'Check audit schedule progress for September 2026' }
	];

	const recentInsights = [
		{
			title: 'Reconciliation Rate Improved',
			description: 'Match rate increased from 96.1% to 98.7% after resolving 3 exceptions in the September reporting cycle.',
			type: 'positive',
			time: '2 hours ago'
		},
		{
			title: 'Market Value Variance Detected',
			description: 'Mapletree Logistics Trust (BOND-006) shows SGD 5,200 variance between UBS and LGI reports.',
			type: 'warning',
			time: '3 hours ago'
		},
		{
			title: 'Journal Auto-Balance Applied',
			description: 'Fair value adjustment journal had SGD 0.50 rounding difference. System applied auto-balance using GL 9990.',
			type: 'info',
			time: '4 hours ago'
		},
		{
			title: 'New Bond Detected',
			description: 'Ascendas REIT 3.15% 2029 (BOND-011) added to portfolio. Pending UBS settlement confirmation.',
			type: 'neutral',
			time: '5 hours ago'
		}
	];

	const dataContext = [
		{ name: 'Bond Portfolio', count: 82, description: 'Active bond line items' },
		{ name: 'Reporting Period', count: null, description: 'September 2026' },
		{ name: 'Source Documents', count: 4, description: 'UBS Excel, LGI PDF, prior schedules' },
		{ name: 'Journal Entries', count: 12, description: 'AI-generated draft journals' },
		{ name: 'Exceptions', count: 5, description: '2 open, 3 resolved' }
	];

	// --- Mock chat handler (same logic as floating panel) ---
	function generateMockResponse(query: string): { content: string; toolCalls?: { name: string; result: string }[] } {
		const q = query.toLowerCase();

		if (q.includes('portfolio') || q.includes('bond') || q.includes('summary') || q.includes('holding')) {
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
							classification_breakdown: {
								'Amortised Cost': { count: 45, value: 'SGD 24,100,000' },
								'FVOCI': { count: 28, value: 'SGD 15,800,000' },
								'FVTPL': { count: 9, value: 'SGD 5,300,000' }
							},
							top_holdings: [
								{ name: 'Singapore Govt 3.375% 2033', value: 'SGD 4,250,000', classification: 'Amortised Cost' },
								{ name: 'Temasek 4.125% 2034', value: 'SGD 5,420,000', classification: 'FVOCI' },
								{ name: 'HDB 2.750% 2029', value: 'SGD 3,180,000', classification: 'Amortised Cost' },
								{ name: 'DBS 3.250% 2028', value: 'SGD 2,500,000', classification: 'Amortised Cost' },
								{ name: 'CapitaLand 3.65% 2030', value: 'SGD 2,100,000', classification: 'FVTPL' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('risk')) {
			return {
				content: 'Here is the portfolio risk analysis for September 2026.',
				toolCalls: [
					{
						name: 'analyze_portfolio_risk',
						result: JSON.stringify({
							portfolio_duration: 4.2,
							modified_duration: 3.9,
							convexity: 18.5,
							yield_to_maturity: '3.45%',
							credit_distribution: {
								'AAA/AA': '42% (SGD 19.0M)',
								'A': '35% (SGD 15.8M)',
								'BBB': '18% (SGD 8.1M)',
								'Unrated': '5% (SGD 2.3M)'
							},
							maturity_profile: {
								'< 1 year': 'SGD 3,200,000',
								'1-3 years': 'SGD 12,400,000',
								'3-5 years': 'SGD 18,600,000',
								'5-10 years': 'SGD 8,200,000',
								'> 10 years': 'SGD 2,800,000'
							},
							risk_flags: [
								'Concentration risk: Top 5 holdings represent 38.6% of portfolio',
								'Interest rate sensitivity: 100bps parallel shift = SGD 1.76M impact',
								'One unrated corporate bond (SGD 2.3M) exceeds 5% threshold'
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('exception') || q.includes('issue') || q.includes('problem')) {
			return {
				content: 'Here is the current exception summary for September 2026.',
				toolCalls: [
					{
						name: 'get_exception_summary',
						result: JSON.stringify({
							total: 5,
							open: 2,
							resolved: 3,
							by_type: {
								RECONCILIATION: { total: 2, open: 1 },
								EXTRACTION: { total: 1, open: 1 },
								DATA_QUALITY: { total: 1, open: 0 },
								JOURNAL: { total: 1, open: 0 }
							},
							open_exceptions: [
								{ id: 'EXC-001', title: 'Market Value Variance — Mapletree Logistics Trust', severity: 'HIGH', variance: 'SGD 5,200', assigned_to: 'S. Lim' },
								{ id: 'EXC-004', title: 'Extraction Confidence Below Threshold', severity: 'MEDIUM', bond: 'BOND-006', assigned_to: 'S. Lim' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('reconciliation') || q.includes('recon') || q.includes('match')) {
			return {
				content: 'Here are the reconciliation results for September 2026.',
				toolCalls: [
					{
						name: 'get_reconciliation_analysis',
						result: JSON.stringify({
							period: 'September 2026',
							total_items: 82,
							matched: 79,
							variances: 2,
							missing: 1,
							match_rate: '96.3%',
							sources_compared: ['UBS Custody Statement', 'LGI General Ledger', 'Prior Period Schedule'],
							variance_details: [
								{ bond: 'BOND-006 (Mapletree)', ubs: 'SGD 795,000', lgi: 'SGD 800,200', diff: 'SGD 5,200', reason: 'Pricing source timing difference' },
								{ bond: 'BOND-009 (Keppel)', ubs: 'SGD 1,020,000', lgi: 'SGD 1,020,200', diff: 'SGD 200', reason: 'Accrued interest rounding' }
							],
							missing_items: [
								{ bond: 'BOND-011 (Ascendas REIT)', status: 'In UBS, not in LGI', reason: 'T+1 settlement pending' }
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('commentary') || q.includes('narrative') || q.includes('month-end')) {
			return {
				content: 'Here is the AI-generated month-end commentary for September 2026.\n\n---\n\n**Executive Summary**\n\nThe September 2026 bond portfolio reporting cycle has been completed with a 98.7% reconciliation match rate across 82 bond line items. Total portfolio market value stands at SGD 45.2 million against face value of SGD 42.8 million.\n\n**Portfolio Movements**\n\nDuring September, 4 new bond purchases totalling SGD 3.55 million were recorded, alongside 3 bond maturities with face value SGD 1.6 million. One inter-portfolio transfer reclassified BOND-005 (CapitaLand) from FVTPL to Held-to-Maturity.\n\n**Reconciliation**\n\n79 of 82 items fully matched between UBS custody, LGI general ledger, and prior period schedules. Two variances and one timing-related missing item were identified and documented.\n\n**Observations**\n\nOne high-severity exception (EXC-001) relating to Mapletree Logistics Trust market value variance of SGD 5,200 remains under investigation. All other exceptions have been resolved.\n\n---\n\nWould you like me to refine any section or add additional detail?'
			};
		}

		if (q.includes('journal') || q.includes('entries') || q.includes('accounting')) {
			return {
				content: 'Here are the draft journal entries for September 2026.',
				toolCalls: [
					{
						name: 'get_journal_entries',
						result: JSON.stringify({
							total_journals: 12,
							total_debits: 'SGD 5,796,024',
							total_credits: 'SGD 5,796,024',
							balanced: true,
							journals: [
								{ ref: 'JV-2026-09-001', type: 'Bond Purchase', entries: 4, amount: 'SGD 3,550,000', status: 'PENDING' },
								{ ref: 'JV-2026-09-002', type: 'Bond Maturity', entries: 3, amount: 'SGD 1,600,000', status: 'APPROVED' },
								{ ref: 'JV-2026-09-003', type: 'Accrued Interest', entries: 82, amount: 'SGD 84,024', status: 'PENDING' },
								{ ref: 'JV-2026-09-004', type: 'Fair Value Adjustment', entries: 1, amount: 'SGD 112,000', status: 'PENDING' }
							],
							review_status: '2 approved, 4 pending review, 6 draft'
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('audit')) {
			return {
				content: 'The audit schedule for September 2026 has been fully generated.',
				toolCalls: [
					{
						name: 'get_audit_progress',
						result: JSON.stringify({
							period: 'September 2026',
							total_bonds: 82,
							schedule_generated: true,
							sections: ['Classification', 'Amortised Cost', 'Fair Value', 'Impairment', 'Interest Income', 'Movements'],
							completeness: '100%',
							disclosure_mapping: 'SFRS(I) 9 / IFRS 9 mapped',
							pending_items: [
								'Final review sign-off required',
								'External auditor access to be provisioned'
							]
						}, null, 2)
					}
				]
			};
		}

		if (q.includes('hello') || q.includes('hi') || q.includes('hey')) {
			return {
				content: `Hello! I'm the AI Bond Copilot, your intelligent assistant for bond portfolio management.\n\nI can help you with:\n\n- **Portfolio analysis** — holdings, valuations, risk metrics\n- **Reconciliation** — three-way matching, variances, exceptions\n- **Journals** — draft entries, balances, approvals\n- **Commentary** — month-end narrative generation and refinement\n- **Audit** — schedule progress, SFRS(I) 9 disclosures\n- **Risk** — duration, credit quality, concentration analysis\n\nUse the Quick Actions panel on the right, or just type your question below.`
			};
		}

		return {
			content: `I understand you're asking about "${query}". Let me help you with that.\n\nFor the September 2026 reporting period, here is a high-level overview:\n\n- **82 bonds** in the active portfolio (SGD 45.2M market value)\n- **98.7%** reconciliation match rate\n- **2 open exceptions** requiring attention\n- **6 items** pending review in the approval queue\n- **12 draft journals** generated and balanced\n\nCould you be more specific about what you'd like to explore? Use the Quick Actions on the right or ask me directly.`
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

				<!-- Recent Insights -->
				<div>
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">Recent Insights</div>
					<div class="space-y-2">
						{#each recentInsights as insight}
							<div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 border-l-4 {insightTypeColor(insight.type)} p-3">
								<div class="flex items-center gap-1.5 mb-1">
									<span class="w-1.5 h-1.5 rounded-full {insightDotColor(insight.type)} flex-shrink-0"></span>
									<span class="text-xs font-medium text-gray-900 dark:text-white truncate">{insight.title}</span>
								</div>
								<p class="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">{insight.description}</p>
								<div class="mt-1.5 text-[10px] text-gray-400 dark:text-gray-500">{insight.time}</div>
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
