<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { user } from '$lib/stores';

	import ClinicalSidebar from '$lib/components/clinical/ClinicalSidebar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	// The root layout (src/routes/+layout.svelte) already bootstraps the session:
	// it loads the backend config, restores $user from the stored token and sets up
	// the socket. This shell only guards the route and renders the clinical console,
	// deliberately WITHOUT the DBiz GPT sidebar / settings modals from (app).

	let loaded = false;

	const gotoAuth = async () => {
		const currentUrl = `${$page.url.pathname}${$page.url.search}`;
		await goto(`/auth?redirect=${encodeURIComponent(currentUrl)}`);
	};

	onMount(async () => {
		if ($user === undefined || $user === null) {
			await gotoAuth();
			return;
		}

		loaded = true;
	});

	$: if (loaded && ($user === undefined || $user === null)) {
		void gotoAuth();
	}
</script>

{#if $user}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-row overflow-hidden bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100"
	>
		<ClinicalSidebar />

		{#if loaded}
			<main id="main-content" class="flex-1 min-w-0 h-full overflow-y-auto">
				<slot />
			</main>
		{:else}
			<div class="flex-1 min-w-0 h-full flex items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{/if}
	</div>
{/if}
