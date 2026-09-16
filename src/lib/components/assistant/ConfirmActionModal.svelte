<script lang="ts">
	export let open = false;
	export let message = 'Are you sure?';
	export let confirmLabel = 'Confirm';
	export let onConfirm: () => void = () => {};
	export let onCancel: () => void = () => {};
</script>

{#if open}
	<div class="fixed inset-0 z-[60] flex items-center justify-center px-4" role="alertdialog" aria-modal="true">
		<div class="absolute inset-0 bg-black/40" on:click={onCancel}></div>
		<div class="relative w-full max-w-sm rounded-xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 p-5">
			<div class="flex items-start gap-3 mb-4">
				<div class="w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-500/10 flex items-center justify-center flex-shrink-0">
					<svg class="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
					</svg>
				</div>
				<div>
					<div class="text-sm font-semibold text-gray-900 dark:text-white mb-1">Confirmation required</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{message}</div>
				</div>
			</div>
			<div class="flex justify-end gap-2">
				<button
					class="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
					on:click={onCancel}
				>
					Cancel
				</button>
				<button
					class="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-600 hover:bg-amber-700 text-white transition-colors"
					on:click={onConfirm}
				>
					{confirmLabel}
				</button>
			</div>
		</div>
	</div>
{/if}
