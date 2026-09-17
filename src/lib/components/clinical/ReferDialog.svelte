<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { user } from '$lib/stores';
	import { createReferral } from '$lib/apis/clinical';
	import {
		DEPARTMENTS,
		getSpecialistByEmail,
		getSpecialistsByDepartment,
		avatarColor,
		initialsOf
	} from '$lib/constants/clinical';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show: boolean;
	export let caseId: string;
	export let patientCode: string;
	export let patientName: string;
	export let onSent: () => void;

	let department = '';
	let toEmail = '';
	let note = '';
	let sending = false;

	$: myDepartment = getSpecialistByEmail($user?.email)?.department ?? '';

	// Default to a department other than my own — this flow is cross-department.
	$: if (show && department === '') {
		department = DEPARTMENTS.find((d) => d !== myDepartment) ?? DEPARTMENTS[0];
	}

	// Never offer to refer the case to myself.
	$: availableSpecialists = getSpecialistsByDepartment(department).filter(
		(s) => s.email.toLowerCase() !== ($user?.email ?? '').toLowerCase()
	);

	$: if (!availableSpecialists.some((s) => s.email === toEmail)) {
		toEmail = availableSpecialists[0]?.email ?? '';
	}

	$: selectedSpecialist = availableSpecialists.find((s) => s.email === toEmail);

	const close = () => {
		show = false;
	};

	const send = async () => {
		if (caseId === '') {
			toast.error($i18n.t('No active case to refer.'));
			return;
		}

		if (toEmail === '') {
			toast.error($i18n.t('Select a specialist to refer to.'));
			return;
		}

		sending = true;
		const referral = await createReferral(localStorage.token, {
			case_id: caseId,
			to_email: toEmail,
			note: note.trim()
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		sending = false;

		if (!referral) {
			return;
		}

		toast.success(
			$i18n.t('Referred to {{name}}', { name: selectedSpecialist?.name ?? toEmail })
		);

		note = '';
		show = false;
		onSent();
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-1.5">
			<h1 class="text-lg font-medium self-center font-primary">
				{$i18n.t('Refer to another department')}
			</h1>
			<button class="self-center" aria-label={$i18n.t('Close modal')} on:click={close}>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="px-5 pb-5 pt-1 w-full dark:text-gray-200">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				{$i18n.t('Case')}
				<span class="font-mono text-gray-700 dark:text-gray-300">{patientCode}</span>
				<span class="text-gray-400 dark:text-gray-600 mx-0.5">—</span>
				<span class="text-gray-700 dark:text-gray-300">{patientName}</span>
			</div>

			<form
				class="flex flex-col gap-3"
				on:submit={(e) => {
					e.preventDefault();
					send();
				}}
			>
				<div class="flex gap-3">
					<div class="flex-1">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Department')}</div>
						<select
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden"
							bind:value={department}
						>
							{#each DEPARTMENTS as dept (dept)}
								<option value={dept}>{dept}</option>
							{/each}
						</select>
					</div>

					<div class="flex-1">
						<div class="text-xs text-gray-500 mb-1">{$i18n.t('Specialist')}</div>
						<select
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden disabled:opacity-50"
							bind:value={toEmail}
							disabled={availableSpecialists.length === 0}
						>
							{#if availableSpecialists.length === 0}
								<option value="">{$i18n.t('No other specialist in this department')}</option>
							{/if}
							{#each availableSpecialists as specialist (specialist.email)}
								<option value={specialist.email}>{specialist.name}</option>
							{/each}
						</select>
					</div>
				</div>

				{#if selectedSpecialist}
					<div
						class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-850"
					>
						<div
							class="size-7 rounded-full flex items-center justify-center text-[10px] font-semibold text-white shrink-0"
							style="background-color: {avatarColor(selectedSpecialist.email)};"
						>
							{initialsOf(selectedSpecialist.name)}
						</div>
						<div class="min-w-0">
							<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
								{selectedSpecialist.name}
							</div>
							<div class="text-[11px] text-gray-400 dark:text-gray-600 truncate">
								{selectedSpecialist.department}
							</div>
						</div>
					</div>
				{/if}

				<div>
					<div class="text-xs text-gray-500 mb-1">{$i18n.t('Note to specialist')}</div>
					<textarea
						class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-hidden resize-none placeholder:text-gray-400 dark:placeholder:text-gray-600"
						rows="3"
						placeholder={$i18n.t('What would you like them to look at?')}
						bind:value={note}
					></textarea>
				</div>

				<div
					class="text-[11px] leading-relaxed text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2.5"
				>
					{$i18n.t(
						'Attached automatically: the full conversation transcript, the structured note, your assessment, and the complete referral chain history. The patient will not be asked to repeat themselves.'
					)}
				</div>

				<div class="flex justify-end gap-2 pt-1">
					<button
						type="button"
						class="px-3.5 py-2 text-sm font-medium rounded-full text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={close}
					>
						{$i18n.t('Cancel')}
					</button>

					<button
						type="submit"
						class="px-3.5 py-2 text-sm font-medium rounded-full bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
						disabled={sending || toEmail === ''}
					>
						{#if sending}
							<Spinner className="size-3.5" />
						{/if}
						{$i18n.t('Send referral')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
