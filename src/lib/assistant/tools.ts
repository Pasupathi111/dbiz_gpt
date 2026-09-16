/**
 * Frontend mirror of the backend AGENT_TOOLS registry — UI metadata only
 * (label, risk tier, icon). The actual execution logic lives entirely on
 * the backend (backend/open_webui/services/agent_tools.py); this file never
 * duplicates business logic, it only tells the drawer how to *render* a
 * tool (risk badge, confirmation copy) before/after calling
 * `executeAgentAction`.
 */

export const READ_ONLY = 'READ_ONLY';
export const LOW_RISK_WRITE = 'LOW_RISK_WRITE';
export const HIGH_RISK_WRITE = 'HIGH_RISK_WRITE';

export interface AgentToolMeta {
	name: string;
	label: string;
	risk: typeof READ_ONLY | typeof LOW_RISK_WRITE | typeof HIGH_RISK_WRITE;
}

export const agentTools: Record<string, AgentToolMeta> = {
	'portfolio.summary': { name: 'portfolio.summary', label: 'Portfolio Summary', risk: READ_ONLY },
	'exceptions.list': { name: 'exceptions.list', label: 'Open Exceptions', risk: READ_ONLY },
	'exceptions.analyze': { name: 'exceptions.analyze', label: 'Exception Analysis', risk: READ_ONLY },
	'reconciliation.run': { name: 'reconciliation.run', label: 'Reconciliation Run', risk: LOW_RISK_WRITE },
	'reconciliation.run_and_summarize': {
		name: 'reconciliation.run_and_summarize',
		label: 'Reconciliation Run',
		risk: LOW_RISK_WRITE
	},
	'reconciliation.summary': { name: 'reconciliation.summary', label: 'Reconciliation Summary', risk: READ_ONLY },
	'movements.analyze': { name: 'movements.analyze', label: 'Movement Analysis', risk: LOW_RISK_WRITE },
	'movements.list': { name: 'movements.list', label: 'Movements', risk: READ_ONLY },
	'schedule.generate': { name: 'schedule.generate', label: 'Bond Schedule', risk: LOW_RISK_WRITE },
	'schedule.validate': { name: 'schedule.validate', label: 'Schedule Validation', risk: LOW_RISK_WRITE },
	'journals.generate': { name: 'journals.generate', label: 'Draft Journals', risk: LOW_RISK_WRITE },
	'journals.approve': { name: 'journals.approve', label: 'Journal Approval', risk: HIGH_RISK_WRITE },
	'journals.reject': { name: 'journals.reject', label: 'Journal Rejection', risk: HIGH_RISK_WRITE },
	'audit_schedule.generate': { name: 'audit_schedule.generate', label: 'Audit Schedule', risk: LOW_RISK_WRITE },
	'commentary.generate': { name: 'commentary.generate', label: 'Commentary', risk: LOW_RISK_WRITE },
	'commentary.generate_with_movements': {
		name: 'commentary.generate_with_movements',
		label: 'Commentary',
		risk: LOW_RISK_WRITE
	},
	'commentary.approve': { name: 'commentary.approve', label: 'Commentary Approval', risk: HIGH_RISK_WRITE },
	'review.pending': { name: 'review.pending', label: 'Pending Reviews', risk: READ_ONLY },
	'review.approve': { name: 'review.approve', label: 'Review Approval', risk: HIGH_RISK_WRITE },
	'review.reject': { name: 'review.reject', label: 'Review Rejection', risk: HIGH_RISK_WRITE },
	'audit_trail.list': { name: 'audit_trail.list', label: 'Audit Trail', risk: READ_ONLY }
};

export function isHighRisk(action: string): boolean {
	return agentTools[action]?.risk === HIGH_RISK_WRITE;
}
