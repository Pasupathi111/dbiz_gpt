import { WEBUI_API_BASE_URL } from '$lib/constants';
import type {
	Assessment,
	CaseDetail,
	ClinicalCase,
	InboxItem,
	Patient,
	Referral,
	TranscriptTurn
} from '$lib/types/clinical';

const CLINICAL_API_BASE_URL = `${WEBUI_API_BASE_URL}/clinical`;

type PatientForm = {
	code: string;
	name: string;
	age?: number | null;
	sex?: string | null;
};

type ReferralForm = {
	case_id: string;
	to_email: string;
	note: string;
};

export const createPatient = async (token: string, form: PatientForm): Promise<Patient> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/patients`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const searchPatients = async (token: string, q: string = ''): Promise<Patient[]> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (q) {
		searchParams.append('q', q);
	}
	const query = searchParams.toString();

	const res = await fetch(`${CLINICAL_API_BASE_URL}/patients${query ? `?${query}` : ''}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const getPatient = async (token: string, id: string): Promise<Patient> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/patients/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createCase = async (token: string, patientId: string): Promise<ClinicalCase> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ patient_id: patientId })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getCases = async (token: string): Promise<ClinicalCase[]> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const getCase = async (token: string, id: string): Promise<CaseDetail> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const saveTranscript = async (
	token: string,
	caseId: string,
	transcript: TranscriptTurn[]
): Promise<ClinicalCase> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases/${caseId}/transcript`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ transcript: transcript })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const saveStructuredNote = async (
	token: string,
	caseId: string,
	note: string
): Promise<ClinicalCase> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases/${caseId}/note`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ structured_note: note })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addAssessment = async (
	token: string,
	caseId: string,
	body: string
): Promise<Assessment> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/cases/${caseId}/assessments`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ body: body })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createReferral = async (token: string, form: ReferralForm): Promise<Referral> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/referrals`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getInbox = async (token: string): Promise<InboxItem[]> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/referrals/inbox`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const getSent = async (token: string): Promise<InboxItem[]> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/referrals/sent`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const markReferralRead = async (token: string, id: string): Promise<Referral> => {
	let error = null;

	const res = await fetch(`${CLINICAL_API_BASE_URL}/referrals/${id}/read`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
