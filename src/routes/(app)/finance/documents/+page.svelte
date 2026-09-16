<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { get } from 'svelte/store';
	import { user } from '$lib/stores';
	import {
		uploadFinanceDocument,
		getFinanceDocuments,
		getReportingPeriods,
		processDocument,
		deleteFinanceDocument
	} from '$lib/apis/finance';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { registerAssistantContext } from '$lib/assistant/context';

	const i18n = getContext('i18n');

	// --- State ---
	let loading = true;
	let periods: any[] = [];
	let selectedPeriodId = '';
	let documents: any[] = [];

	$: registerAssistantContext({
		page: 'documents',
		pageTitle: 'Upload Documents',
		module: 'Bond Reporting',
		periodId: selectedPeriodId || undefined,
		availableActions: ['audit_trail.list', 'reconciliation.summary'],
		pageData: { documentCount: documents?.length ?? 0 }
	});
	let dragOver = false;
	let selectedDocType = 'UBS_EXCEL';
	let uploadQueue: UploadItem[] = [];
	let fileInput: HTMLInputElement;

	interface UploadItem {
		file: File;
		docType: string;
		progress: number;
		status: 'pending' | 'uploading' | 'done' | 'error';
		error?: string;
	}

	const docTypeOptions = [
		{ value: 'UBS_EXCEL', label: 'UBS Excel' },
		{ value: 'LGI_PDF', label: 'LGI PDF' },
		{ value: 'PREVIOUS_SCHEDULE', label: 'Previous Schedule' },
		{ value: 'TEMPLATE', label: 'Template' }
	];

	const acceptedExtensions = ['.xlsx', '.xls', '.pdf'];

	// --- Mount ---
	onMount(async () => {
		periods = (await getReportingPeriods(localStorage.token).catch(() => [])) ?? [];
		if (!selectedPeriodId && periods.length) selectedPeriodId = periods[0].id;
		await refreshDocuments();
		loading = false;
	});

	function periodName(periodId: string): string {
		return periods.find((p) => p.id === periodId)?.name || periodId || '—';
	}

	function uploaderName(uploadedBy: string): string {
		const currentUser = get(user);
		if (currentUser && uploadedBy === currentUser.id) return currentUser.name;
		return uploadedBy || '—';
	}

	// --- Helpers ---
	function getDocTypeBadge(type: string) {
		switch (type) {
			case 'UBS_EXCEL':
				return {
					label: 'UBS Excel',
					classes: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400'
				};
			case 'LGI_PDF':
				return {
					label: 'LGI PDF',
					classes: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400'
				};
			case 'PREVIOUS_SCHEDULE':
				return {
					label: 'Prev Schedule',
					classes: 'bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400'
				};
			case 'TEMPLATE':
				return {
					label: 'Template',
					classes: 'bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400'
				};
			default:
				return {
					label: type,
					classes: 'bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400'
				};
		}
	}

	function getStatusBadge(status: string) {
		switch (status) {
			case 'UPLOADED':
				return { label: 'Uploaded', classes: 'bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400', icon: '' };
			case 'PROCESSING':
				return { label: 'Processing', classes: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400', icon: 'spinner' };
			case 'PROCESSED':
				return { label: 'Processed', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400', icon: '' };
			case 'WARNING':
				return { label: 'Warning', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400', icon: '' };
			case 'FAILED':
				return { label: 'Failed', classes: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400', icon: '' };
			case 'VALIDATED':
				return { label: 'Validated', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400', icon: 'check' };
			default:
				return { label: status, classes: 'bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400', icon: '' };
		}
	}

	function formatFileSize(bytes: number): string {
		if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
		if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(0)} KB`;
		return `${bytes} B`;
	}

	function formatDate(epochSeconds: number): string {
		if (!epochSeconds) return '—';
		const d = new Date(epochSeconds * 1000);
		return d.toLocaleDateString('en-SG', { day: '2-digit', month: 'short', year: 'numeric' }) +
			' ' +
			d.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit', hour12: false });
	}

	function validateFile(file: File): string | null {
		const ext = '.' + file.name.split('.').pop()?.toLowerCase();
		if (!acceptedExtensions.includes(ext)) {
			return `Invalid file type: ${ext}. Accepted: ${acceptedExtensions.join(', ')}`;
		}
		if (file.size > 50 * 1_048_576) {
			return `File too large: ${formatFileSize(file.size)}. Maximum: 50 MB`;
		}
		return null;
	}

	// --- Drop / File Selection ---
	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		dragOver = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		if (e.dataTransfer?.files) {
			addFilesToQueue(Array.from(e.dataTransfer.files));
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files) {
			addFilesToQueue(Array.from(input.files));
			input.value = '';
		}
	}

	function addFilesToQueue(files: File[]) {
		for (const file of files) {
			const error = validateFile(file);
			if (error) {
				toast.error(error);
				continue;
			}
			uploadQueue = [
				...uploadQueue,
				{ file, docType: selectedDocType, progress: 0, status: 'pending' }
			];
		}
	}

	function removeFromQueue(index: number) {
		uploadQueue = uploadQueue.filter((_, i) => i !== index);
	}

	// --- Upload ---
	async function uploadAll() {
		for (let i = 0; i < uploadQueue.length; i++) {
			if (uploadQueue[i].status !== 'pending') continue;
			uploadQueue[i].status = 'uploading';
			uploadQueue[i].progress = 0;
			uploadQueue = uploadQueue;

			// Simulate progress increments while the API call runs
			const progressInterval = setInterval(() => {
				if (uploadQueue[i] && uploadQueue[i].progress < 90) {
					uploadQueue[i].progress += 10;
					uploadQueue = uploadQueue;
				}
			}, 200);

			try {
				await uploadFinanceDocument(
					localStorage.token,
					uploadQueue[i].file,
					uploadQueue[i].docType,
					selectedPeriodId
				);
				clearInterval(progressInterval);
				uploadQueue[i].progress = 100;
				uploadQueue[i].status = 'done';
				uploadQueue = uploadQueue;
				toast.success(`Uploaded ${uploadQueue[i].file.name}`);
			} catch (err: any) {
				clearInterval(progressInterval);
				uploadQueue[i].status = 'error';
				uploadQueue[i].error = err.message || 'Upload failed';
				uploadQueue = uploadQueue;
				toast.error(`Failed to upload ${uploadQueue[i].file.name}: ${err.message}`);
			}
		}

		// Refresh document list after uploads
		await refreshDocuments();

		// Clear completed items from queue after a short delay
		setTimeout(() => {
			uploadQueue = uploadQueue.filter((item) => item.status !== 'done');
		}, 2000);
	}

	async function refreshDocuments() {
		try {
			const fetched = await getFinanceDocuments(localStorage.token, selectedPeriodId);
			documents = Array.isArray(fetched) ? fetched : [];
		} catch (e: any) {
			toast.error(e?.message || 'Failed to load documents');
		}
	}

	// --- Document Actions ---
	async function handleProcess(doc: any) {
		const idx = documents.findIndex((d) => d.id === doc.id);
		if (idx === -1) return;
		documents[idx] = { ...documents[idx], status: 'PROCESSING' };
		documents = documents;

		try {
			await processDocument(localStorage.token, doc.id);
			toast.success(`Processing started for ${doc.filename}`);
			await refreshDocuments();
		} catch (err: any) {
			documents[idx] = { ...documents[idx], status: 'FAILED' };
			documents = documents;
			toast.error(`Process failed: ${err.message}`);
		}
	}

	async function handleDelete(doc: any) {
		if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;

		try {
			await deleteFinanceDocument(localStorage.token, doc.id);
			documents = documents.filter((d) => d.id !== doc.id);
			toast.success(`Deleted ${doc.filename}`);
		} catch (err: any) {
			toast.error(`Delete failed: ${err.message}`);
		}
	}

	function handlePreview(doc: any) {
		toast.info(`Preview not yet available for ${doc.filename}`);
	}
</script>

<div class="flex flex-col h-full overflow-y-auto">
	<!-- Header -->
	<div class="px-4 sm:px-6 lg:px-8 pt-6 pb-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
		<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-1">
			<span>AI Bond Copilot</span>
			<span>/</span>
			<span>Upload Documents</span>
		</div>
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">Document Management</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Upload and manage UBS, LGI and schedule documents for bond processing
				</p>
			</div>
			<div class="flex items-center gap-3">
				<select
					class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
					bind:value={selectedPeriodId}
					on:change={refreshDocuments}
				>
					{#if periods.length === 0}
						<option value="">No periods</option>
					{/if}
					{#each periods as period}
						<option value={period.id}>{period.name}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<Spinner />
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
				<!-- Upload Area Card -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
					<div class="flex items-center justify-between mb-4">
						<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
							Upload Documents
						</div>
						<div class="flex items-center gap-3">
							<label class="text-xs text-gray-500 dark:text-gray-400">Document Type:</label>
							<select
								class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
								bind:value={selectedDocType}
							>
								{#each docTypeOptions as opt}
									<option value={opt.value}>{opt.label}</option>
								{/each}
							</select>
						</div>
					</div>

					<!-- Drop Zone -->
					<button
						class="w-full border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 cursor-pointer
							{dragOver
								? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-500/5 dark:border-indigo-500'
								: 'border-gray-300 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
						on:dragover={handleDragOver}
						on:dragleave={handleDragLeave}
						on:drop={handleDrop}
						on:click={() => fileInput.click()}
					>
						<input
							bind:this={fileInput}
							type="file"
							class="hidden"
							accept=".xlsx,.xls,.pdf"
							multiple
							on:change={handleFileSelect}
						/>
						<div class="flex flex-col items-center gap-3">
							<div class="w-14 h-14 rounded-full flex items-center justify-center
								{dragOver
									? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'}">
								<svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
								</svg>
							</div>
							<div>
								<p class="text-sm font-medium text-gray-700 dark:text-gray-300">
									{dragOver ? 'Drop files here' : 'Drag and drop files here or click to browse'}
								</p>
								<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
									Accepted formats: .xlsx, .xls, .pdf (max 50 MB)
								</p>
							</div>
						</div>
					</button>

					<!-- Upload Queue -->
					{#if uploadQueue.length > 0}
						<div class="mt-4 space-y-2">
							<div class="flex items-center justify-between">
								<div class="text-xs font-medium text-gray-500 dark:text-gray-400">
									Upload Queue ({uploadQueue.length} file{uploadQueue.length !== 1 ? 's' : ''})
								</div>
								<button
									class="text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
									on:click={uploadAll}
									disabled={uploadQueue.every((item) => item.status !== 'pending')}
								>
									Upload All
								</button>
							</div>
							{#each uploadQueue as item, index}
								<div class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
									<!-- File Icon -->
									<div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
										{item.file.name.endsWith('.pdf')
											? 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400'
											: 'bg-green-100 dark:bg-green-500/10 text-green-600 dark:text-green-400'}">
										{#if item.file.name.endsWith('.pdf')}
											<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
											</svg>
										{:else}
											<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12c-.621 0-1.125.504-1.125 1.125M12 12c.621 0 1.125.504 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 1.5v-1.5m0 0c0-.621.504-1.125 1.125-1.125m0 0h1.5c.621 0 1.125.504 1.125 1.125m0 0v1.5m-3.75-4.5A1.125 1.125 0 0112 10.875" />
											</svg>
										{/if}
									</div>

									<!-- File Info -->
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2">
											<span class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{item.file.name}</span>
											<span class="text-[10px] text-gray-400 dark:text-gray-500 flex-shrink-0">{formatFileSize(item.file.size)}</span>
											<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {getDocTypeBadge(item.docType).classes} flex-shrink-0">{getDocTypeBadge(item.docType).label}</span>
										</div>
										{#if item.status === 'uploading' || item.status === 'done'}
											<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1.5">
												<div
													class="h-1.5 rounded-full transition-all duration-300 {item.status === 'done' ? 'bg-emerald-500' : 'bg-indigo-500'}"
													style="width: {item.progress}%"
												></div>
											</div>
										{/if}
										{#if item.status === 'error'}
											<p class="text-[10px] text-red-500 dark:text-red-400 mt-1">{item.error}</p>
										{/if}
									</div>

									<!-- Status / Remove -->
									<div class="flex items-center gap-2 flex-shrink-0">
										{#if item.status === 'done'}
											<svg class="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										{:else if item.status === 'uploading'}
											<Spinner className="size-4 text-indigo-500" />
										{:else if item.status === 'error'}
											<svg class="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
											</svg>
										{:else}
											<button
												class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
												on:click={() => removeFromQueue(index)}
												title="Remove from queue"
											>
												<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
													<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
												</svg>
											</button>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Document List Table -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
					<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
						<div>
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
								Uploaded Documents
							</div>
							<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
								{documents.length} document{documents.length !== 1 ? 's' : ''}
							</div>
						</div>
						<button
							class="text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
							on:click={refreshDocuments}
						>
							Refresh
						</button>
					</div>

					{#if documents.length === 0}
						<div class="px-6 py-12 text-center">
							<div class="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-3">
								<svg class="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
								</svg>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400">No documents uploaded yet</p>
							<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Upload documents using the area above to get started</p>
						</div>
					{:else}
						<div class="overflow-x-auto">
							<table class="w-full text-sm">
								<thead>
									<tr class="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Document Type</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Filename</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Period</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Uploaded By</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Uploaded At</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Size</th>
										<th class="text-left px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Status</th>
										<th class="text-right px-6 py-3 text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 whitespace-nowrap">Actions</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-gray-100 dark:divide-gray-800">
									{#each documents as doc}
										{@const typeBadge = getDocTypeBadge(doc.document_type)}
										{@const statusBadge = getStatusBadge(doc.status)}
										<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
											<!-- Document Type -->
											<td class="px-6 py-3.5">
												<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium {typeBadge.classes}">
													{typeBadge.label}
												</span>
											</td>
											<!-- Filename -->
											<td class="px-6 py-3.5">
												<div class="flex items-center gap-2">
													<div class="w-6 h-6 rounded flex items-center justify-center flex-shrink-0
														{doc.filename.endsWith('.pdf')
															? 'bg-red-100 dark:bg-red-500/10 text-red-500 dark:text-red-400'
															: 'bg-green-100 dark:bg-green-500/10 text-green-500 dark:text-green-400'}">
														{#if doc.filename.endsWith('.pdf')}
															<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
																<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
															</svg>
														{:else}
															<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
																<path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-2.625 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625" />
															</svg>
														{/if}
													</div>
													<span class="text-sm text-gray-700 dark:text-gray-300 font-medium truncate">{doc.filename}</span>
												</div>
											</td>
											<!-- Period -->
											<td class="px-6 py-3.5 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">{periodName(doc.reporting_period_id)}</td>
											<!-- Uploaded By -->
											<td class="px-6 py-3.5 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">{uploaderName(doc.uploaded_by)}</td>
											<!-- Uploaded At -->
											<td class="px-6 py-3.5 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">{formatDate(doc.created_at)}</td>
											<!-- Size -->
											<td class="px-6 py-3.5 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">{formatFileSize(doc.file_size)}</td>
											<!-- Status -->
											<td class="px-6 py-3.5">
												<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium {statusBadge.classes}">
													{#if statusBadge.icon === 'spinner'}
														<Spinner className="size-3" />
													{:else if statusBadge.icon === 'check'}
														<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
															<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
														</svg>
													{/if}
													{statusBadge.label}
												</span>
											</td>
											<!-- Actions -->
											<td class="px-6 py-3.5">
												<div class="flex items-center justify-end gap-1">
													{#if doc.status === 'UPLOADED' || doc.status === 'VALIDATED'}
														<button
															class="p-1.5 rounded-lg text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 transition-colors"
															title="Process document"
															on:click={() => handleProcess(doc)}
														>
															<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
																<path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
															</svg>
														</button>
													{/if}
													<button
														class="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
														title="Preview document"
														on:click={() => handlePreview(doc)}
													>
														<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
															<path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
															<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
														</svg>
													</button>
													<button
														class="p-1.5 rounded-lg text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
														title="Delete document"
														on:click={() => handleDelete(doc)}
													>
														<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
															<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
														</svg>
													</button>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
