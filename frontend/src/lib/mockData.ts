export type WorkdayEmployee = {
  acf2_id: string;
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

export const MOCK_EMPLOYEES: Record<string, WorkdayEmployee> = {
  ARUN01: {
    acf2_id: 'ARUN01',
    name: 'Arun Mehta',
    team: 'Cloud Infrastructure',
    manager: 'Raj Kumar',
    dept: 'Technology',
    employment_type: 'full-time',
  },
  NEHA02: {
    acf2_id: 'NEHA02',
    name: 'Neha Kapoor',
    team: 'Finance Analytics',
    manager: 'Deepa Menon',
    dept: 'Finance',
    employment_type: 'contract',
  },
  SARA03: {
    acf2_id: 'SARA03',
    name: 'Sara Chen',
    team: 'TBD',
    manager: 'TBD',
    dept: 'TBD',
    employment_type: 'full-time',
  },
};
