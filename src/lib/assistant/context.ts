/**
 * Global Agentic Assistant — context registration.
 *
 * Pages call `registerAssistantContext(...)` (typically in a reactive
 * `$:` block so it re-registers whenever period/filters/selection change)
 * to tell the globally-mounted assistant what page it's on and what it can
 * do there. The assistant drawer subscribes to `assistantContext` and never
 * needs page-specific code of its own.
 */

import { writable, type Writable } from 'svelte/store';

export interface AssistantContext {
	page: string;
	pageTitle: string;
	module: string;
	userRole?: string;

	periodId?: string;
	periodLabel?: string;

	selectedBondIds?: string[];
	selectedRecords?: string[];
	entityId?: string;

	filters?: Record<string, unknown>;
	availableActions?: string[];
	permissions?: string[];

	// Lightweight page-state snapshot used to make suggestions data-aware
	// (e.g. exception counts, whether reconciliation is complete). Kept
	// small and serializable — this is passed straight through to the
	// backend as `context` on every agent execution from this page.
	pageData?: Record<string, unknown>;
}

const EMPTY_CONTEXT: AssistantContext = {
	page: '',
	pageTitle: '',
	module: ''
};

export const assistantContext: Writable<AssistantContext> = writable(EMPTY_CONTEXT);

export function registerAssistantContext(ctx: AssistantContext) {
	assistantContext.set(ctx);
}

export function clearAssistantContext() {
	assistantContext.set(EMPTY_CONTEXT);
}
