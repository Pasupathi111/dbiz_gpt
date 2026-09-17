<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import dayjs from 'dayjs';

	import { settings } from '$lib/stores';
	import { blobToFile } from '$lib/utils';
	import { transcribeAudio } from '$lib/apis/audio';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Mic from '$lib/components/icons/Mic.svelte';

	export let disabled = false;
	/** True for as long as the microphone is held open. Bindable. */
	export let listening = false;
	/** Fired once per transcribed burst, always in the order the bursts were spoken. */
	export let onSegment: (text: string) => void = () => {};
	/** Silence (ms) that ends a burst and triggers a re-arm. */
	export let silenceMs = 1500;
	/** Bursts shorter than this are discarded as noise. */
	export let minBurstMs = 500;

	export let echoCancellation = true;
	export let noiseSuppression = true;
	export let autoGainControl = true;

	// The microphone is acquired ONCE and held for the whole consultation. Only an
	// explicit stop releases it — a burst boundary never touches the stream.
	let stream: MediaStream | null = null;
	let audioContext: AudioContext | null = null;
	let analyser: AnalyserNode | null = null;
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];

	let starting = false;
	let capturing = false; // a burst is being recorded right now
	let tearingDown = false; // explicit stop in flight — do not re-arm
	let pendingCount = 0; // bursts uploaded but not yet emitted
	let emitChain: Promise<void> = Promise.resolve();

	let burstStartedAt = 0;
	let lastSoundTime = 0;
	let speechDetected = false;
	let frameHandle: number | null = null;

	let durationSeconds = 0;
	let durationCounter: ReturnType<typeof setInterval> | null = null;

	const MIN_DECIBELS = -45;
	const VISUALIZER_BUFFER_LENGTH = 96;
	let visualizerData: number[] = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

	const MIME_TYPES = [
		'audio/webm; codecs=opus',
		'audio/webm',
		'audio/ogg; codecs=opus',
		'audio/mp4',
		'audio/wav'
	];

	const formatSeconds = (seconds: number) => {
		const minutes = Math.floor(seconds / 60);
		const remaining = seconds % 60;
		return `${minutes}:${remaining < 10 ? `0${remaining}` : remaining}`;
	};

	// --- visualiser maths, lifted from MessageInput/VoiceRecording.svelte ---

	const calculateRMS = (data: Uint8Array) => {
		let sumSquares = 0;
		for (let i = 0; i < data.length; i++) {
			const normalizedValue = (data[i] - 128) / 128;
			sumSquares += normalizedValue * normalizedValue;
		}
		return Math.sqrt(sumSquares / data.length);
	};

	const normalizeRMS = (rms: number) => {
		rms = rms * 10;
		const exp = 1.5;
		const scaledRMS = Math.pow(rms, exp);
		return Math.min(1.0, Math.max(0.01, scaledRMS));
	};

	// --- wake lock ---

	let wakeLock: any = null;

	const requestWakeLock = async () => {
		if ('wakeLock' in navigator) {
			try {
				wakeLock = await (navigator as any).wakeLock.request('screen');
			} catch (err) {
				console.log('Wake Lock request failed:', err);
			}
		}
	};

	const releaseWakeLock = async () => {
		if (wakeLock) {
			try {
				await wakeLock.release();
			} catch (err) {
				console.log('Wake Lock release failed:', err);
			}
			wakeLock = null;
		}
	};

	// --- the loop ---

	/**
	 * One long-lived analyser over the persistent stream. Unlike the one-shot
	 * recorder this never pauses while a burst is uploading, so speech that lands
	 * during transcription is still captured by the burst that is already re-armed.
	 */
	const startAnalyser = (source: MediaStream) => {
		audioContext = new AudioContext();
		const audioStreamSource = audioContext.createMediaStreamSource(source);

		analyser = audioContext.createAnalyser();
		analyser.minDecibels = MIN_DECIBELS;
		audioStreamSource.connect(analyser);

		const domainData = new Uint8Array(analyser.frequencyBinCount);
		const timeDomainData = new Uint8Array(analyser.fftSize);

		lastSoundTime = Date.now();

		const processFrame = () => {
			if (!listening || !analyser) {
				return;
			}

			analyser.getByteTimeDomainData(timeDomainData);
			analyser.getByteFrequencyData(domainData);

			visualizerData.push(normalizeRMS(calculateRMS(timeDomainData)));
			if (visualizerData.length >= VISUALIZER_BUFFER_LENGTH) {
				visualizerData.shift();
			}
			visualizerData = visualizerData;

			// Same silence test as the stock recorder: minDecibels gates the bins.
			if (domainData.some((value) => value > 0)) {
				lastSoundTime = Date.now();
				if (capturing) {
					speechDetected = true;
				}
			}

			const now = Date.now();
			if (
				capturing &&
				speechDetected &&
				now - lastSoundTime > silenceMs &&
				now - burstStartedAt > minBurstMs
			) {
				cutBurst();
			}

			frameHandle = window.requestAnimationFrame(processFrame);
		};

		frameHandle = window.requestAnimationFrame(processFrame);
	};

	/** Start a new burst on the stream that is already open. */
	const armBurst = () => {
		if (!stream || tearingDown) {
			return;
		}

		audioChunks = [];
		speechDetected = false;
		burstStartedAt = Date.now();
		lastSoundTime = Date.now();

		let recorder: MediaRecorder;
		try {
			// A fresh recorder per burst guarantees a well-formed container. It is built
			// from the SAME MediaStream, so the microphone is never released or re-prompted.
			recorder = new MediaRecorder(stream, {
				mimeType: MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
			});
		} catch (error) {
			console.error('Error starting recording:', error);
			toast.error($i18n.t('Error starting recording.'));
			stopListening();
			return;
		}

		mediaRecorder = recorder;

		recorder.ondataavailable = (event) => {
			if (event.data && event.data.size > 0) {
				audioChunks.push(event.data);
			}
		};

		recorder.onstop = () => {
			const chunks = audioChunks;
			audioChunks = [];
			handleBurstStop(chunks, recorder.mimeType);
		};

		try {
			recorder.start();
			capturing = true;
		} catch (error) {
			console.error('Error starting recording:', error);
			toast.error($i18n.t('Error starting recording.'));
			stopListening();
		}
	};

	/** VAD found silence — close this burst. The stream stays live. */
	const cutBurst = () => {
		if (!capturing || !mediaRecorder) {
			return;
		}

		capturing = false; // guards against the VAD cutting the same burst twice
		try {
			mediaRecorder.stop();
		} catch (error) {
			console.error(error);
		}
	};

	const handleBurstStop = (chunks: Blob[], recorderMimeType: string) => {
		const hadSpeech = speechDetected;

		// Re-arm BEFORE uploading, so the microphone is already capturing the next
		// burst while this one is in flight to Whisper. This is the whole trick.
		if (tearingDown) {
			teardownStream();
		} else {
			armBurst();
		}

		if (!hadSpeech || chunks.length === 0) {
			return;
		}

		const type = chunks[0]?.type || recorderMimeType || 'audio/webm';
		let ext = type.split('/')[1]?.split(';')[0] || 'webm';
		if (!type.startsWith('audio/')) {
			ext = 'webm';
		}

		queueTranscription(new Blob(chunks, { type }), ext);
	};

	/**
	 * Uploads start immediately so overlapping bursts transcribe in parallel, but
	 * emission is chained so segments always reach staging in spoken order.
	 */
	const queueTranscription = (blob: Blob, ext: string) => {
		pendingCount += 1;

		const file = blobToFile(
			blob,
			`Consultation-${dayjs().format('YYYY-MM-DD-HH-mm-ss-SSS')}.${ext}`
		);

		const upload = transcribeAudio(
			localStorage.token,
			file,
			$settings?.audio?.stt?.language
		).catch((error) => {
			console.error(error);
			toast.error(`${error}`);
			return null;
		});

		emitChain = emitChain
			.then(() => upload)
			.then((res) => {
				const text = `${res?.text ?? ''}`.trim();
				if (text) {
					onSegment(text);
				}
			})
			.catch((error) => {
				console.error(error);
			})
			.finally(() => {
				pendingCount = Math.max(0, pendingCount - 1);
			});
	};

	const startListening = async () => {
		if (listening || starting || disabled) {
			return;
		}

		starting = true;
		try {
			stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: echoCancellation,
					noiseSuppression: noiseSuppression,
					autoGainControl: autoGainControl
				}
			});
		} catch (err) {
			console.error('Error accessing media devices.', err);
			toast.error($i18n.t('Error accessing media devices.'));
			starting = false;
			return;
		}

		starting = false;
		tearingDown = false;
		listening = true;

		durationSeconds = 0;
		durationCounter = setInterval(() => {
			durationSeconds++;
		}, 1000);

		await requestWakeLock();
		startAnalyser(stream);
		armBurst();
	};

	/** Releases the microphone. The final burst is still transcribed. */
	const stopListening = () => {
		if (!listening && !capturing) {
			return;
		}

		tearingDown = true;
		listening = false; // ends the analyser frame loop

		if (capturing && mediaRecorder) {
			capturing = false;
			try {
				// teardownStream() runs from onstop, once the final blob has flushed.
				mediaRecorder.stop();
			} catch (error) {
				console.error(error);
				teardownStream();
			}
		} else {
			teardownStream();
		}
	};

	const teardownStream = () => {
		if (frameHandle !== null) {
			window.cancelAnimationFrame(frameHandle);
			frameHandle = null;
		}

		if (durationCounter) {
			clearInterval(durationCounter);
			durationCounter = null;
		}
		durationSeconds = 0;
		visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

		releaseWakeLock();

		if (audioContext) {
			audioContext.close().catch((error) => console.error(error));
			audioContext = null;
		}
		analyser = null;

		if (stream) {
			stream.getTracks().forEach((track) => track.stop());
			stream = null;
		}

		mediaRecorder = null;
		listening = false;
		tearingDown = false;
	};

	const toggle = () => {
		if (listening) {
			stopListening();
		} else {
			startListening();
		}
	};

	$: if (disabled && listening) {
		stopListening();
	}

	onDestroy(() => {
		stopListening();
	});
</script>

<div class="flex items-center gap-2 min-w-0 {listening ? 'flex-1' : ''}">
	{#if listening}
		<div
			class="flex items-center gap-2 flex-1 min-w-0 pl-3 pr-1 py-1 rounded-full bg-rose-500/10 dark:bg-rose-500/15"
		>
			<div class="flex items-center gap-1.5 shrink-0">
				<span class="relative flex size-2">
					<span
						class="absolute inline-flex h-full w-full rounded-full bg-rose-500 opacity-75 animate-ping"
					></span>
					<span class="relative inline-flex rounded-full size-2 bg-rose-500"></span>
				</span>
				<span
					class="text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400"
				>
					{$i18n.t('Recording')}
				</span>
			</div>

			<div class="flex flex-1 items-center h-6 min-w-0 overflow-hidden" dir="rtl">
				<div class="flex items-center gap-0.5 h-6 w-full overflow-hidden">
					{#each visualizerData.slice().reverse() as rms}
						<div class="flex items-center h-full">
							<div
								class="w-[0.125rem] shrink-0 bg-rose-500 dark:bg-rose-400 inline-block h-full rounded-full"
								style="height: {Math.min(100, Math.max(14, rms * 100))}%;"
							></div>
						</div>
					{/each}
				</div>
			</div>

			{#if pendingCount > 0}
				<Tooltip content={$i18n.t('Transcribing')}>
					<div class="flex items-center gap-1 text-rose-600 dark:text-rose-400 shrink-0">
						<Spinner className="size-3.5" />
						<span class="text-xs tabular-nums">{pendingCount}</span>
					</div>
				</Tooltip>
			{/if}

			<div class="text-xs text-rose-600 dark:text-rose-400 tabular-nums shrink-0">
				{formatSeconds(durationSeconds)}
			</div>

			<Tooltip content={$i18n.t('Stop listening')}>
				<button
					type="button"
					aria-label={$i18n.t('Stop listening')}
					class="p-2 rounded-full bg-rose-500 hover:bg-rose-600 text-white transition shrink-0"
					on:click={toggle}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-3"
					>
						<rect x="5" y="5" width="14" height="14" rx="2" />
					</svg>
				</button>
			</Tooltip>
		</div>
	{:else}
		<Tooltip
			content={disabled
				? $i18n.t('Select a patient to begin')
				: $i18n.t('Start listening — stays live until you stop it')}
		>
			<button
				type="button"
				aria-label={$i18n.t('Start listening')}
				class="p-2.5 rounded-full transition {disabled
					? 'text-gray-300 dark:text-gray-700 cursor-not-allowed'
					: 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850'}"
				disabled={disabled || starting}
				on:click={toggle}
			>
				{#if starting}
					<Spinner className="size-4" />
				{:else}
					<Mic className="size-4" strokeWidth="2" />
				{/if}
			</button>
		</Tooltip>
	{/if}
</div>
