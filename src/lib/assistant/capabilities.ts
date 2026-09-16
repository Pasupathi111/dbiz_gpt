/**
 * Global Agentic Assistant — per-page suggestion configuration.
 *
 * Each entry maps a page id (matches AssistantContext.page, and the finance
 * layout's navItems ids) to a set of suggested actions. `action` must be a
 * tool name registered in the backend AGENT_TOOLS registry
 * (backend/open_webui/services/agent_tools.py) — the drawer never
 * hard-codes what a tool does, it only looks up label/action pairs here.
 *
 * `dynamic(ctx)` optionally adds/replaces suggestions based on the page's
 * live `pageData` (e.g. exception counts) so suggestions aren't purely
 * static. To add a new page: add one entry here — no changes needed to the
 * drawer component itself.
 */

import type { AssistantContext } from './context';

export interface Suggestion {
	id: string;
	label: string;
	action: string;
}

export interface PageCapability {
	title: string;
	module: string;
	suggestions: Suggestion[];
	dynamic?: (ctx: AssistantContext) => Suggestion[];
}

export const assistantCapabilities: Record<string, PageCapability> = {
	dashboard: {
		title: 'Dashboard',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'd1', label: 'Summarize portfolio status', action: 'portfolio.summary' },
			{ id: 'd2', label: 'Identify unusual movements', action: 'movements.analyze' },
			{ id: 'd3', label: 'Summarize reconciliation status', action: 'reconciliation.summary' },
			{ id: 'd4', label: 'Prepare month-end summary', action: 'commentary.generate_with_movements' }
		]
	},

	'ai-assistant': {
		title: 'AI Assistant',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'a1', label: 'Summarize portfolio status', action: 'portfolio.summary' },
			{ id: 'a2', label: 'Analyze reconciliation exceptions', action: 'exceptions.analyze' },
			{ id: 'a3', label: 'Summarize reconciliation results', action: 'reconciliation.summary' }
		]
	},

	documents: {
		title: 'Upload Documents',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'doc1', label: 'Show recent document activity', action: 'audit_trail.list' },
			{ id: 'doc2', label: 'Summarize reconciliation status', action: 'reconciliation.summary' }
		]
	},

	bonds: {
		title: 'Bond Data',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'bd1', label: 'Summarize portfolio status', action: 'portfolio.summary' },
			{ id: 'bd2', label: 'Show open exceptions', action: 'exceptions.list' }
		]
	},

	reconciliation: {
		title: 'Reconciliation',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'r1', label: 'Run reconciliation', action: 'reconciliation.run' },
			{ id: 'r2', label: 'Explain reconciliation exceptions', action: 'exceptions.analyze' },
			{ id: 'r3', label: "Summarize today's reconciliation", action: 'reconciliation.summary' },
			{ id: 'r4', label: 'Prepare exception report', action: 'exceptions.list' }
		],
		dynamic: (ctx) => {
			const openExceptions = Number(ctx.pageData?.openExceptions ?? 0);
			const highRisk = Number(ctx.pageData?.highRiskExceptions ?? 0);
			const incomplete = Boolean(ctx.pageData?.reconciliationIncomplete);
			const out: Suggestion[] = [];
			if (incomplete) {
				out.push({ id: 'r-dyn-complete', label: 'Complete reconciliation', action: 'reconciliation.run' });
			}
			if (highRisk > 0) {
				out.push({
					id: 'r-dyn-highrisk',
					label: `Explain the ${highRisk} high-risk exception${highRisk === 1 ? '' : 's'}`,
					action: 'exceptions.analyze'
				});
			} else if (openExceptions === 0) {
				out.push({ id: 'r-dyn-clean', label: 'Export reconciliation report', action: 'reconciliation.summary' });
			}
			return out;
		}
	},

	movements: {
		title: 'Movements',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'm1', label: 'Analyze bond movements', action: 'movements.analyze' },
			{ id: 'm2', label: 'Identify unusual movements', action: 'movements.analyze' },
			{ id: 'm3', label: 'Explain significant changes', action: 'movements.list' },
			{ id: 'm4', label: 'Generate movement summary', action: 'commentary.generate_with_movements' }
		]
	},

	schedule: {
		title: 'Bond Schedule',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 's1', label: 'Generate bond schedule', action: 'schedule.generate' },
			{ id: 's2', label: 'Check schedule inconsistencies', action: 'schedule.validate' },
			{ id: 's3', label: 'Summarize schedule', action: 'schedule.validate' }
		]
	},

	journals: {
		title: 'Draft Journals',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'j1', label: 'Generate draft journals', action: 'journals.generate' },
			{ id: 'j2', label: 'Review journal entries', action: 'review.pending' },
			{ id: 'j3', label: 'Prepare journal summary', action: 'review.pending' }
		],
		dynamic: (ctx) => {
			// Approve/reject only make sense once a specific journal is
			// selected on the page — surface them contextually instead of
			// as always-on suggestions with no target.
			if (!ctx.entityId) return [];
			return [
				{ id: 'j-dyn-approve', label: 'Approve the selected journal', action: 'journals.approve' },
				{ id: 'j-dyn-reject', label: 'Reject the selected journal', action: 'journals.reject' }
			];
		}
	},

	'audit-schedule': {
		title: 'Audit Schedule',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'as1', label: 'Generate audit schedule', action: 'audit_schedule.generate' },
			{ id: 'as2', label: 'Summarize audit status', action: 'audit_trail.list' }
		]
	},

	commentary: {
		title: 'Commentary',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'c1', label: 'Generate month-end commentary', action: 'commentary.generate' },
			{ id: 'c2', label: 'Regenerate commentary', action: 'commentary.generate' },
			{ id: 'c3', label: 'Explain unusual movements', action: 'commentary.generate_with_movements' },
			{ id: 'c4', label: 'Summarize portfolio performance', action: 'portfolio.summary' }
		]
	},

	review: {
		title: 'Review & Approval',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'rv1', label: 'Summarize items awaiting review', action: 'review.pending' },
			{ id: 'rv2', label: 'Explain pending approvals', action: 'review.pending' }
		],
		dynamic: (ctx) => {
			if (!ctx.entityId) return [];
			return [
				{ id: 'rv-dyn-approve', label: 'Approve the selected item', action: 'review.approve' },
				{ id: 'rv-dyn-reject', label: 'Reject the selected item', action: 'review.reject' }
			];
		}
	},

	exceptions: {
		title: 'Exceptions',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'e1', label: 'Summarize exceptions', action: 'exceptions.analyze' },
			{ id: 'e2', label: 'Prioritize exceptions', action: 'exceptions.analyze' },
			{ id: 'e3', label: 'Prepare exception report', action: 'exceptions.list' }
		]
	},

	'audit-trail': {
		title: 'Audit Trail',
		module: 'Bond Reporting',
		suggestions: [
			{ id: 'at1', label: "Summarize recent activity", action: 'audit_trail.list' },
			{ id: 'at2', label: 'Find unusual activity', action: 'audit_trail.list' }
		]
	}
};

export function getSuggestionsForPage(ctx: AssistantContext): Suggestion[] {
	const cap = assistantCapabilities[ctx.page];
	if (!cap) return [];
	const dynamicOnes = cap.dynamic ? cap.dynamic(ctx) : [];
	// Dynamic suggestions surface first — they reflect what's actually
	// happening on the page right now (e.g. high-risk exceptions present).
	return [...dynamicOnes, ...cap.suggestions];
}
