export type WorkdayContext = {
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

export type AuthUser = WorkdayContext & {
  acf2_id: string;
};

export type ResolvedRole = {
  role: string;
  designation_id: string;
  seniority: string;
  employment_type: string;
  team: string;
  dept: string;
  confidence: number;
};

export type AccessItem = {
  id: string;
  name: string;
  system: string;
  reason: string;
  mandatory: boolean;
  owner_team?: string;
  servicenow_catalog_item_id?: string;
  sort_order?: number;
};

export type SelectedTemplate = {
  id: string;
  name: string;
  description?: string;
  confidence?: number;
  reasoning?: string;
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
