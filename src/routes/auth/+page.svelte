<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	let submitting = false;

	const forgotPasswordHandler = () => {
		toast.info($i18n.t('Please contact your administrator to reset your password.'));
	};

	// Email-based default landing pages, applied after login when no explicit
	// `?redirect=` deep link is present.
	const FINANCE_LANDING_EMAILS = ['pasupathi.shanmugam@dbizsolution.com'];
	const CONSULT_LANDING_EMAILS = [
		'naveen.pattathil@dbizsolution.com',
		'chandrukhasan.ramachandran@dbizsolution.com',
		'durga.prasad@dbizsolution.com',
		'princy.jala@dbizsolution.com',
		'chandru@northvale.health',
		'naveen@northvale.health',
		'valen@northvale.health'
	];

	const getDefaultLandingPath = (userEmail?: string | null): string | null => {
		if (!userEmail) {
			return null;
		}

		const normalizedEmail = userEmail.toLowerCase();

		if (FINANCE_LANDING_EMAILS.includes(normalizedEmail)) {
			return '/finance';
		}

		if (CONSULT_LANDING_EMAILS.includes(normalizedEmail)) {
			return '/consult';
		}

		return null;
	};

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath =
					$page.url.searchParams.get('redirect') ||
					getDefaultLandingPath(sessionUser.email) ||
					'/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (submitting) {
			return;
		}

		submitting = true;
		try {
			if (mode === 'ldap') {
				await ldapSignInHandler();
			} else if (mode === 'signin') {
				await signInHandler();
			} else {
				await signUpHandler();
			}
		} finally {
			submitting = false;
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		const logout = $page.url.searchParams.get('state') === 'logout';

		if ($user && !logout) {
			goto(redirectPath || getDefaultLandingPath($user.email) || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		// Auto-redirect to SSO when OAUTH_AUTO_REDIRECT is enabled and the
		// deployment is unambiguously SSO-only (single provider, no login form,
		// no LDAP). Suppressed after logout, by ?form=, ?error=, onboarding,
		// trusted-header auth, or an existing session/token.
		if ($config?.oauth?.auto_redirect && !logout && !form && !error) {
			const providers = Object.keys($config?.oauth?.providers ?? {});
			if (
				providers.length === 1 &&
				$config?.features?.auth !== false &&
				$config?.features?.enable_login_form === false &&
				!$config?.features?.enable_ldap &&
				!$config?.features?.auth_trusted_header &&
				!$config?.onboarding &&
				!localStorage.token &&
				!document.cookie.split('; ').some((c) => c.startsWith('token='))
			) {
				window.location.href = `${WEBUI_BASE_URL}/oauth/${providers[0]}/login`;
				return;
			}
		}

		loaded = true;

		if (($config?.features?.auth_trusted_header ?? false) || $config?.features?.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] relative" id="auth-page">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div class="fixed inset-0 z-50 flex text-black dark:text-white" id="auth-container">
			{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
				<div class="w-full flex items-center justify-center">
					<div class="my-auto pb-10 w-full sm:max-w-md text-center px-10">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-normal dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				</div>
			{:else}
				<!-- Left brand panel -->
				<div
					class="hidden lg:flex lg:w-[46%] xl:w-[42%] relative flex-col justify-between overflow-hidden px-12 py-10 text-white"
					style="background: radial-gradient(120% 120% at 15% 10%, #16305c 0%, #0b1f3f 45%, #060f24 100%);"
				>
					<div
						class="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-orange-500/10 blur-3xl"
					/>
					<div
						class="pointer-events-none absolute -bottom-32 -left-16 size-96 rounded-full bg-blue-500/10 blur-3xl"
					/>

					<div class="relative z-10 flex items-center gap-2">
						<img
							id="logo"
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class="size-9 rounded-full"
							alt="{$WEBUI_NAME} logo"
						/>
						<div class="leading-tight text-left">
							<div class="text-xl font-bold tracking-tight">
								DBiz<span class="text-orange-400">.</span>
							</div>
							<div class="text-[0.6rem] uppercase tracking-widest text-blue-200/70">
								{$i18n.t('Accelerating Business')}
							</div>
						</div>
					</div>

					<div class="relative z-10 text-left">
						<div class="flex items-center gap-2 mb-5">
							<span class="h-px w-8 bg-orange-400" />
							<span class="text-xs font-semibold uppercase tracking-[0.2em] text-orange-400">
								{$i18n.t('AI for a smarter tomorrow')}
							</span>
						</div>

						<h1 class="text-4xl xl:text-[2.75rem] font-bold leading-tight mb-4">
							{$i18n.t('Your AI Partner')}<br />
							{$i18n.t('for a')}
							<span class="text-orange-400">{$i18n.t('Smarter Workplace')}</span>
						</h1>

						<p class="text-blue-100/80 text-sm max-w-md mb-10">
							{$i18n.t(
								'DBiz GPT brings powerful AI to your everyday work — helping you think, create, analyze, and automate faster.'
							)}
						</p>

						<div class="flex flex-col gap-5">
							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('Chat & Create')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t('Ask questions, generate content, brainstorm, and summarize')}
									</div>
								</div>
							</div>

							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('Work With Your Data')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t('Upload documents, analyze information, and uncover insights')}
									</div>
								</div>
							</div>

							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('Enterprise Ready')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t('Secure, controlled, and built for modern business teams')}
									</div>
								</div>
							</div>

							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('Automate Your Work')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t('Let AI handle repetitive tasks and multi-step workflows')}
									</div>
								</div>
							</div>

							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('AI Agents')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t('Give AI tasks to plan, execute, and complete using connected tools')}
									</div>
								</div>
							</div>

							<div class="flex items-start gap-3">
								<div
									class="flex items-center justify-center size-10 shrink-0 rounded-xl bg-white/10"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
										/>
									</svg>
								</div>
								<div>
									<div class="text-sm font-semibold">{$i18n.t('Your Knowledge, With AI')}</div>
									<div class="text-xs text-blue-200/70">
										{$i18n.t("Search and interact with your organization's trusted knowledge")}
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="relative z-10 border-l-2 border-orange-400 pl-4 text-left">
						<p class="italic text-sm text-blue-100/80">
							{$i18n.t('"AI that helps your people work smarter, faster, and better."')}
						</p>
					</div>
				</div>

				<!-- Right sign-in panel -->
				<div class="flex-1 flex flex-col bg-gray-50 dark:bg-gray-950 overflow-y-auto">
					<div class="flex items-center justify-between px-6 sm:px-10 py-6 text-sm">
						<div class="flex items-center gap-2 lg:hidden">
							<img
								id="logo-mobile"
								crossorigin="anonymous"
								src="{WEBUI_BASE_URL}/static/favicon.png"
								class="size-7 rounded-full"
								alt="{$WEBUI_NAME} logo"
							/>
							<span class="font-bold">DBiz</span>
						</div>
						<div class="hidden lg:block" />

						{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
							<div class="flex items-center gap-4 text-gray-500 dark:text-gray-400">
								<span class="hidden sm:inline">
									{mode === 'signin'
										? $i18n.t('New to {{WEBUI_NAME}}?', { WEBUI_NAME: $WEBUI_NAME })
										: $i18n.t('Already have an account?')}
								</span>
								<button
									type="button"
									class="font-semibold text-blue-700 dark:text-blue-400 hover:underline"
									on:click={() => {
										mode = mode === 'signin' ? 'signup' : 'signin';
									}}
								>
									{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
								</button>
							</div>
						{/if}
					</div>

					<div class="flex-1 flex items-center justify-center px-6 sm:px-10 pb-10">
						<div class="w-full sm:max-w-md">
							<div
								class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-xl shadow-gray-200/60 dark:shadow-none p-8"
							>
								{#if $config?.metadata?.auth_logo_position === 'center'}
									<div class="flex justify-center mb-6">
										<!-- LICENSE covers this Open WebUI sign-in logo.
										Do not alter, remove, obscure, or replace it except as LICENSE permits:
										https://docs.openwebui.com/license. -->
										<img
											id="logo"
											crossorigin="anonymous"
											src="{WEBUI_BASE_URL}/static/favicon.png"
											class="size-16 rounded-full"
											alt="{$WEBUI_NAME} logo"
										/>
									</div>
								{/if}
								<form
									class="flex flex-col justify-center text-left"
									on:submit={(e) => {
										e.preventDefault();
										submitHandler();
									}}
								>
									<div class="mb-1">
										<div class="text-sm text-gray-500 dark:text-gray-400">
											{$i18n.t('Welcome to')}
										</div>
										<div class="text-2xl font-bold">
											{#if $config?.onboarding ?? false}
												{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
											{:else if mode === 'ldap'}
												{$i18n.t(`{{WEBUI_NAME}} LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
											{:else if mode === 'signin'}
												{$WEBUI_NAME}
											{:else}
												{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
											{/if}
										</div>
										<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
											{#if $config?.onboarding ?? false}
												ⓘ {$WEBUI_NAME}
												{$i18n.t(
													'does not make any external connections, and your data stays securely on your locally hosted server.'
												)}
											{:else if mode === 'ldap'}
												{$i18n.t('Sign in to {{WEBUI_NAME}} with LDAP', { WEBUI_NAME: $WEBUI_NAME })}
											{:else if mode === 'signin'}
												{$i18n.t('Sign in to continue to your workspace')}
											{:else}
												{$i18n.t('Create an account to continue')}
											{/if}
										</div>
									</div>

									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<div class="flex flex-col mt-5 gap-4">
											{#if mode === 'signup'}
												<div>
													<label for="name" class="text-sm font-medium text-left mb-1 block"
														>{$i18n.t('Name')}</label
													>
													<input
														bind:value={name}
														type="text"
														id="name"
														class="w-full text-sm outline-hidden bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3.5 py-2.5 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:border-blue-500 dark:focus:border-blue-500 transition-colors"
														autocomplete="name"
														placeholder={$i18n.t('Enter Your Full Name')}
														required
													/>
												</div>
											{/if}

											{#if mode === 'ldap'}
												<div>
													<label for="username" class="text-sm font-medium text-left mb-1 block"
														>{$i18n.t('Username')}</label
													>
													<input
														bind:value={ldapUsername}
														type="text"
														class="w-full text-sm outline-hidden bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3.5 py-2.5 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:border-blue-500 dark:focus:border-blue-500 transition-colors"
														autocomplete="username"
														name="username"
														id="username"
														placeholder={$i18n.t('Enter Your Username')}
														required
													/>
												</div>
											{:else}
												<div>
													<label for="email" class="text-sm font-medium text-left mb-1 block"
														>{$i18n.t('Email')}</label
													>
													<div class="relative">
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="1.5"
															class="size-4.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"
															/>
														</svg>
														<input
															bind:value={email}
															type="email"
															id="email"
															class="w-full text-sm outline-hidden bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pl-10 pr-3.5 py-2.5 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:border-blue-500 dark:focus:border-blue-500 transition-colors"
															autocomplete="email"
															name="email"
															placeholder={$i18n.t('Enter your email address')}
															required
														/>
													</div>
												</div>
											{/if}

											<div>
												<div class="flex items-center justify-between mb-1">
													<label for="password" class="text-sm font-medium text-left block"
														>{$i18n.t('Password')}</label
													>
													{#if mode === 'signin'}
														<button
															type="button"
															class="text-xs font-medium text-blue-700 dark:text-blue-400 hover:underline"
															on:click={forgotPasswordHandler}
														>
															{$i18n.t('Forgot password?')}
														</button>
													{/if}
												</div>
												<div class="relative">
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
														class="size-4.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
														/>
													</svg>
													<SensitiveInput
														bind:value={password}
														type="password"
														id="password"
														class="w-full text-sm outline-hidden bg-transparent placeholder:text-gray-400 dark:placeholder:text-gray-500"
														outerClassName="flex flex-1 items-center bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pl-10 pr-3.5 py-2.5 focus-within:border-blue-500 dark:focus-within:border-blue-500 transition-colors"
														placeholder={$i18n.t('Enter your password')}
														autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
														name="password"
														screenReader={true}
														required
														aria-required="true"
													/>
												</div>
											</div>

											{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
												<div>
													<label
														for="confirm-password"
														class="text-sm font-medium text-left mb-1 block"
														>{$i18n.t('Confirm Password')}</label
													>
													<SensitiveInput
														bind:value={confirmPassword}
														type="password"
														id="confirm-password"
														class="w-full text-sm outline-hidden bg-transparent"
														outerClassName="flex flex-1 items-center bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3.5 py-2.5 focus-within:border-blue-500 dark:focus-within:border-blue-500 transition-colors"
														placeholder={$i18n.t('Confirm Your Password')}
														autocomplete="new-password"
														name="confirm-password"
														required
													/>
												</div>
											{/if}
										</div>
									{/if}
									<div class="mt-6">
										{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
											{#if mode === 'ldap'}
												<button
													class="flex justify-center items-center w-full rounded-xl font-semibold text-sm py-3 text-white bg-gradient-to-r from-blue-700 to-blue-600 hover:from-blue-800 hover:to-blue-700 transition disabled:opacity-50"
													type="submit"
													disabled={submitting}
												>
													<div class="self-center">{$i18n.t('Authenticate')}</div>

													{#if submitting}
														<div class="ml-1.5 self-center">
															<Spinner />
														</div>
													{/if}
												</button>
											{:else}
												<button
													class="flex justify-center items-center gap-1.5 w-full rounded-xl font-semibold text-sm py-3 text-white bg-gradient-to-r from-blue-700 to-blue-600 hover:from-blue-800 hover:to-blue-700 transition disabled:opacity-50"
													type="submit"
													disabled={submitting}
												>
													<div class="self-center">
														{mode === 'signin'
															? $i18n.t('Sign in')
															: ($config?.onboarding ?? false)
																? $i18n.t('Create Admin Account')
																: $i18n.t('Create Account')}
													</div>

													{#if submitting}
														<div class="ml-1.5 self-center">
															<Spinner />
														</div>
													{:else if mode === 'signin'}
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
															class="size-4 self-center"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
															/>
														</svg>
													{/if}
												</button>
											{/if}
										{/if}
									</div>
								</form>

								{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
									<div class="inline-flex items-center justify-center w-full">
										<hr class="grow h-px my-5 border-0 dark:bg-gray-800 bg-gray-200" />
										{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
											<span
												class="px-3 text-xs font-medium text-gray-500 dark:text-gray-400 bg-transparent"
												>{$i18n.t('Or continue with')}</span
											>
										{/if}

										<hr class="grow h-px my-5 border-0 dark:bg-gray-800 bg-gray-200" />
									</div>
									<div class="flex flex-col space-y-2">
										{#if $config?.oauth?.providers?.google}
											<button
												class="flex justify-center items-center bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5"
												on:click={() => {
													window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 48 48"
													class="size-5 mr-3"
													aria-hidden="true"
												>
													<path
														fill="#EA4335"
														d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
													/><path
														fill="#4285F4"
														d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
													/><path
														fill="#FBBC05"
														d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
													/><path
														fill="#34A853"
														d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
													/><path fill="none" d="M0 0h48v48H0z" />
												</svg>
												<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
											</button>
										{/if}
										{#if $config?.oauth?.providers?.microsoft}
											<button
												class="flex justify-center items-center bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5"
												on:click={() => {
													window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 21 21"
													class="size-5 mr-3"
													aria-hidden="true"
												>
													<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
														x="1"
														y="11"
														width="9"
														height="9"
														fill="#00a4ef"
													/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
														x="11"
														y="11"
														width="9"
														height="9"
														fill="#ffb900"
													/>
												</svg>
												<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
												>
											</button>
										{/if}
										{#if $config?.oauth?.providers?.github}
											<button
												class="flex justify-center items-center bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5"
												on:click={() => {
													window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 24 24"
													class="size-5 mr-3"
													aria-hidden="true"
												>
													<path
														fill="currentColor"
														d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
													/>
												</svg>
												<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
											</button>
										{/if}
										{#if $config?.oauth?.providers?.oidc}
											<button
												class="flex justify-center items-center bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5"
												on:click={() => {
													window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="1.5"
													stroke="currentColor"
													class="size-5 mr-3"
													aria-hidden="true"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
													/>
												</svg>

												<span
													>{$i18n.t('Continue with {{provider}}', {
														provider: $config?.oauth?.providers?.oidc ?? 'SSO'
													})}</span
												>
											</button>
										{/if}
										{#if $config?.oauth?.providers?.feishu}
											<button
												class="flex justify-center items-center bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5"
												on:click={() => {
													window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
												}}
											>
												<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
											</button>
										{/if}
									</div>
								{/if}

								{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
									<div class="mt-3">
										<button
											class="flex justify-center items-center text-xs w-full text-center underline text-gray-500 dark:text-gray-400"
											type="button"
											on:click={() => {
												if (mode === 'ldap')
													mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
												else mode = 'ldap';
											}}
										>
											<span
												>{mode === 'ldap'
													? $i18n.t('Continue with Email')
													: $i18n.t('Continue with LDAP')}</span
											>
										</button>
									</div>
								{/if}

								<div
									class="mt-6 flex items-start gap-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 px-4 py-3"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-5 shrink-0 text-blue-700 dark:text-blue-400 mt-0.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m9 12.75 2.25 2.25 4.5-4.5m4.5 2.25a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
										/>
									</svg>
									<div class="text-left">
										<div class="text-sm font-semibold text-blue-900 dark:text-blue-300">
											{$i18n.t('Secure access for {{WEBUI_NAME}} team members only', {
												WEBUI_NAME: 'DBiz'
											})}
										</div>
										<div class="text-xs text-blue-700/80 dark:text-blue-400/70">
											{$i18n.t('Protected by enterprise-grade security')}
										</div>
									</div>
								</div>
							</div>

							{#if $config?.metadata?.login_footer}
								<div class="max-w-3xl mx-auto">
									<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
										{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
									</div>
								</div>
							{/if}

							<div
								class="mt-6 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs text-gray-400 dark:text-gray-600"
							>
								<span>{$i18n.t('© {{year}} DBiz. All rights reserved.', { year: '2025' })}</span>
								<span>|</span>
								<span>{$i18n.t('Privacy')}</span>
								<span>|</span>
								<span>{$i18n.t('Terms')}</span>
								<span>|</span>
								<span>{$i18n.t('Support')}</span>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
