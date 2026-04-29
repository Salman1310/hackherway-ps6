export type WorkdayContext = {
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

export type ResolvedRole = {
  role: string;
  seniority: string;
  employment_type: string;
  team: string;
};

export type AccessItem = {
  id: string;
  name: string;
  system: string;
  reason: string;
  mandatory: boolean;
};

export type SelectedTemplate = {
  id: string;
  name: string;
  mandatory_access: AccessItem[];
  optional_access: AccessItem[];
};

export type SessionState = {
  acf2_id: string | null;
  workday_context: WorkdayContext | null;
  resolved_role: ResolvedRole | null;
  selected_template: SelectedTemplate | null;
  final_bundle: AccessItem[];
  request_id: string | null;
};

export type Message = {
  id: string;
  role: 'bot' | 'user';
  content: string;
  timestamp: Date;
};
