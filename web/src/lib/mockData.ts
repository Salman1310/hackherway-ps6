export type WorkdayEmployee = {
  acf2_id: string;
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

export const MOCK_EMPLOYEES: Record<string, WorkdayEmployee> = {
  RIYA001: {
    acf2_id: 'RIYA001',
    name: 'Riya Sharma',
    team: 'Payments Backend',
    manager: 'Anjali Singh',
    dept: 'Technology',
    employment_type: 'full-time',
  },
  JOHN002: {
    acf2_id: 'JOHN002',
    name: 'John Mathews',
    team: 'Cloud Infrastructure',
    manager: 'Raj Kumar',
    dept: 'Technology',
    employment_type: 'full-time',
  },
  PRIYA003: {
    acf2_id: 'PRIYA003',
    name: 'Priya Nair',
    team: 'Finance Analytics',
    manager: 'Deepa Menon',
    dept: 'Finance',
    employment_type: 'contract',
  },
  SAM004: {
    acf2_id: 'SAM004',
    name: 'Sam Wilson',
    team: 'TBD',
    manager: 'TBD',
    dept: 'TBD',
    employment_type: 'full-time',
  },
};
