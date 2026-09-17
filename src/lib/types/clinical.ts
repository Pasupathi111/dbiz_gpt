export type Speaker = 'doctor' | 'patient';

export interface TranscriptTurn {
	speaker: Speaker;
	text: string;
	at: number;
}

export interface StagedSegment {
	id: string;
	speaker: Speaker;
	text: string;
}

export interface Patient {
	id: string;
	code: string;
	name: string;
	age?: number | null;
	sex?: string | null;
	created_at: number;
}

export interface Assessment {
	id: string;
	case_id: string;
	author_email: string;
	author_name: string;
	department: string;
	body: string;
	created_at: number;
}

export interface Referral {
	id: string;
	case_id: string;
	from_email: string;
	from_name: string;
	from_department: string;
	to_email: string;
	to_name: string;
	to_department: string;
	note: string;
	created_at: number;
	read_at?: number | null;
}

export interface ClinicalCase {
	id: string;
	patient_id: string;
	patient_code: string;
	patient_name: string;
	created_by_email: string;
	created_by_name: string;
	department: string;
	transcript: TranscriptTurn[];
	structured_note?: string | null;
	created_at: number;
	updated_at: number;
}

export interface CaseDetail extends ClinicalCase {
	assessments: Assessment[];
	referrals: Referral[];
}

export interface InboxItem extends Referral {
	patient_code: string;
	patient_name: string;
}
