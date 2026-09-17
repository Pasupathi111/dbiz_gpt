export interface Specialist {
	email: string;
	name: string;
	department: string;
}

export const DEPARTMENTS = ['Cardiology', 'Neurology', 'General Surgery'] as const;

export const SPECIALISTS: Specialist[] = [
	{ email: 'chandru@northvale.health', name: 'Dr. Chandru', department: 'Cardiology' },
	{ email: 'naveen@northvale.health', name: 'Dr. Naveen', department: 'Neurology' },
	{ email: 'valen@northvale.health', name: 'Dr. Valen', department: 'General Surgery' }
];

export const getSpecialistByEmail = (email?: string): Specialist | undefined =>
	SPECIALISTS.find((s) => s.email.toLowerCase() === (email ?? '').toLowerCase());

export const getSpecialistsByDepartment = (department: string): Specialist[] =>
	SPECIALISTS.filter((s) => s.department === department);

export const initialsOf = (name: string): string =>
	name
		.replace(/^Dr\.?\s*/i, '')
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0]?.toUpperCase() ?? '')
		.join('');

export const avatarColor = (seed: string): string => {
	let hash = 0;
	for (let i = 0; i < seed.length; i++) {
		hash = (hash << 5) - hash + seed.charCodeAt(i);
		hash |= 0;
	}
	return `hsl(${Math.abs(hash) % 360}, 62%, 48%)`;
};
