import { WEBUI_API_BASE_URL } from '$lib/constants';

const FINANCE_API = `${WEBUI_API_BASE_URL}/finance`;

async function request(token: string, path: string, options: RequestInit = {}) {
	const res = await fetch(`${FINANCE_API}${path}`, {
		...options,
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json',
			...options.headers
		}
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || res.statusText);
	}
	return res.json();
}

// Dashboard
export const getFinanceDashboard = (token: string, periodId?: string) =>
	request(token, `/dashboard${periodId ? `?period_id=${periodId}` : ''}`);

// Reporting Periods
export const getReportingPeriods = (token: string) =>
	request(token, '/periods');

export const createReportingPeriod = (token: string, data: { name: string; year: number; month: number; previous_period_id?: string }) =>
	request(token, '/periods', { method: 'POST', body: JSON.stringify(data) });

export const getReportingPeriod = (token: string, id: string) =>
	request(token, `/periods/${id}`);

export const updateReportingPeriod = (token: string, id: string, data: any) =>
	request(token, `/periods/${id}`, { method: 'PUT', body: JSON.stringify(data) });

// Documents
export const uploadFinanceDocument = async (token: string, file: File, documentType: string, periodId: string) => {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('document_type', documentType);
	formData.append('reporting_period_id', periodId);

	const res = await fetch(`${FINANCE_API}/documents/upload`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${token}` },
		body: formData
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || res.statusText);
	}
	return res.json();
};

export const getFinanceDocuments = (token: string, periodId?: string) =>
	request(token, `/documents${periodId ? `?period_id=${periodId}` : ''}`);

export const getFinanceDocument = (token: string, id: string) =>
	request(token, `/documents/${id}`);

export const processDocument = (token: string, id: string) =>
	request(token, `/documents/${id}/process`, { method: 'POST' });

export const deleteFinanceDocument = (token: string, id: string) =>
	request(token, `/documents/${id}`, { method: 'DELETE' });

// Bonds
export const getBonds = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/bonds${qs}`);
};

export const getBond = (token: string, id: string) =>
	request(token, `/bonds/${id}`);

export const updateBond = (token: string, id: string, data: any) =>
	request(token, `/bonds/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const getBondSources = (token: string, id: string) =>
	request(token, `/bonds/${id}/sources`);

// Reconciliation
export const runReconciliation = (token: string, periodId: string) =>
	request(token, '/reconciliation/run', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getReconciliation = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/reconciliation${qs}`);
};

export const getReconciliationSummary = (token: string, periodId: string) =>
	request(token, `/reconciliation/summary?period_id=${periodId}`);

export const getReconciliationExceptions = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/reconciliation/exceptions${qs}`);
};

export const updateException = (token: string, id: string, data: any) =>
	request(token, `/reconciliation/exceptions/${id}`, { method: 'PUT', body: JSON.stringify(data) });

// Movements
export const analyzeMovements = (token: string, periodId: string) =>
	request(token, '/movements/analyze', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getMovements = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/movements${qs}`);
};

export const updateMovement = (token: string, id: string, data: any) =>
	request(token, `/movements/${id}`, { method: 'PUT', body: JSON.stringify(data) });

// Schedule
export const generateSchedule = (token: string, periodId: string) =>
	request(token, '/schedule/generate', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getSchedule = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/schedule${qs}`);
};

export const validateSchedule = (token: string, periodId: string) =>
	request(token, '/schedule/validate', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const exportSchedule = (token: string, periodId: string) =>
	`${FINANCE_API}/schedule/export?period_id=${periodId}&token=${token}`;

// Journals
export const generateJournals = (token: string, periodId: string) =>
	request(token, '/journals/generate', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getJournals = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/journals${qs}`);
};

export const getJournal = (token: string, id: string) =>
	request(token, `/journals/${id}`);

export const updateJournal = (token: string, id: string, data: any) =>
	request(token, `/journals/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const approveJournal = (token: string, id: string, comment?: string) =>
	request(token, `/journals/${id}/approve`, { method: 'POST', body: JSON.stringify({ comment }) });

export const rejectJournal = (token: string, id: string, reason: string) =>
	request(token, `/journals/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) });

// Audit Schedule
export const generateAuditSchedule = (token: string, periodId: string) =>
	request(token, '/audit-schedule/generate', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getAuditSchedule = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/audit-schedule${qs}`);
};

export const exportAuditSchedule = (token: string, periodId: string) =>
	`${FINANCE_API}/audit-schedule/export?period_id=${periodId}&token=${token}`;

// Commentary
export const generateCommentary = (token: string, periodId: string) =>
	request(token, '/commentary/generate', { method: 'POST', body: JSON.stringify({ period_id: periodId }) });

export const getCommentary = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/commentary${qs}`);
};

export const updateCommentary = (token: string, id: string, data: any) =>
	request(token, `/commentary/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const regenerateCommentary = (token: string, id: string) =>
	request(token, `/commentary/${id}/regenerate`, { method: 'POST' });

export const approveCommentary = (token: string, id: string) =>
	request(token, `/commentary/${id}/approve`, { method: 'POST' });

// Review & Approval
export const submitForReview = (token: string, data: { output_type: string; output_id: string; period_id: string; title?: string }) =>
	request(token, '/review/submit', { method: 'POST', body: JSON.stringify(data) });

export const approveOutput = (token: string, reviewId: string, comments?: string) =>
	request(token, '/review/approve', { method: 'POST', body: JSON.stringify({ review_id: reviewId, comments }) });

export const rejectOutput = (token: string, reviewId: string, reason: string, comments?: string) =>
	request(token, '/review/reject', { method: 'POST', body: JSON.stringify({ review_id: reviewId, reason, comments }) });

export const getPendingReviews = (token: string) =>
	request(token, '/review/pending');

// Audit Trail
export const getAuditTrail = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/audit-trail${qs}`);
};

// Exceptions
export const getExceptions = (token: string, params?: Record<string, string>) => {
	const qs = params ? '?' + new URLSearchParams(params).toString() : '';
	return request(token, `/reconciliation/exceptions${qs}`);
};

// Copilot chat
export const copilotChat = (
	token: string,
	query: string,
	reportingPeriodId?: string
) =>
	request(token, '/copilot/chat', {
		method: 'POST',
		body: JSON.stringify({ query, reporting_period_id: reportingPeriodId })
	});
