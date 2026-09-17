<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import type { CaseDetail, Referral } from '$lib/types/clinical';
	import { avatarColor, initialsOf } from '$lib/constants/clinical';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let caseDetail: CaseDetail | null = null;
	export let currentEmail = '';
	export let className = '';

	type ChainNode = {
		email: string;
		name: string;
		department: string;
		at: number;
		origin: boolean;
		fromName?: string;
		note?: string;
		readAt?: number | null;
	};

	const toMs = (at?: number): number => {
		if (!at || !Number.isFinite(at)) return 0;
		return at > 1e12 ? at : at * 1000;
	};

	$: meEmail = (currentEmail ?? '').toLowerCase();

	$: orderedReferrals = [...(caseDetail?.referrals ?? [])].sort(
		(a: Referral, b: Referral) => (a?.created_at ?? 0) - (b?.created_at ?? 0)
	);

	// The chain starts with whoever interviewed the patient, then follows each referral hop.
	$: nodes = (
		caseDetail
			? [
					{
						email: caseDetail.created_by_email,
						name: caseDetail.created_by_name,
						department: caseDetail.department,
						at: caseDetail.created_at,
						origin: true
					},
					...orderedReferrals.map((referral) => ({
						email: referral.to_email,
						name: referral.to_name,
						department: referral.to_department,
						at: referral.created_at,
						origin: false,
						fromName: referral.from_name,
						note: referral.note,
						readAt: referral.read_at ?? null
					}))
				]
			: []
	) as ChainNode[];
</script>

<div
	class="rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 px-4 py-4 {className}"
>
	<div class="flex items-baseline justify-between mb-3.5">
		<h2 class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
			Referral chain
		</h2>
		{#if nodes.length > 0}
			<span class="text-[10px] text-gray-400 dark:text-gray-600">
				{nodes.length}
				{nodes.length === 1 ? 'doctor' : 'doctors'}
			</span>
		{/if}
	</div>

	{#if nodes.length === 0}
		<div class="text-sm text-gray-400 dark:text-gray-600 italic">No chain yet.</div>
	{:else}
		<ol class="flex flex-col">
			{#each nodes as node, nodeIdx (`${node.email}-${node.at}-${nodeIdx}`)}
				{@const mine = meEmail !== '' && (node.email ?? '').toLowerCase() === meEmail}
				{@const current = nodeIdx === nodes.length - 1}
				<li class="relative flex gap-3 {current ? '' : 'pb-5'}">
					{#if !current}
						<span
							class="absolute left-[15px] top-9 -bottom-1 w-px bg-gray-100 dark:bg-gray-850"
							aria-hidden="true"
						></span>
					{/if}

					<div
						class="relative z-[1] size-8 shrink-0 rounded-full flex items-center justify-center text-[11px] font-semibold text-white select-none {current
							? 'ring-2 ring-offset-2 ring-gray-900 dark:ring-white ring-offset-white dark:ring-offset-gray-900'
							: ''}"
						style="background-color: {avatarColor(node.name ?? '')}"
						aria-hidden="true"
					>
						{initialsOf(node.name ?? '')}
					</div>

					<div class="min-w-0 flex-1 pt-0.5">
						<div class="flex items-center gap-1.5 flex-wrap">
							<span class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
								{node.name}
							</span>
							{#if mine}
								<span
									class="text-[10px] font-medium px-1.5 py-px rounded-full bg-gray-900 text-white dark:bg-white dark:text-gray-900"
								>
									you
								</span>
							{/if}
						</div>

						<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
							{node.department}
						</div>

						<div class="flex items-center gap-1.5 mt-0.5">
							<Tooltip
								content={node.at ? dayjs(toMs(node.at)).format('LLLL') : ''}
								className="flex"
								placement="top"
							>
								<span class="text-[11px] text-gray-400 dark:text-gray-600">
									{node.at ? dayjs(toMs(node.at)).fromNow() : ''}
								</span>
							</Tooltip>

							<span class="text-[11px] text-gray-300 dark:text-gray-700">·</span>

							<span class="text-[11px] text-gray-400 dark:text-gray-600 truncate">
								{#if node.origin}
									interviewed the patient
								{:else if node.readAt}
									referred by {node.fromName} · opened
								{:else}
									referred by {node.fromName}
								{/if}
							</span>
						</div>
					</div>
				</li>
			{/each}
		</ol>
	{/if}
</div>
