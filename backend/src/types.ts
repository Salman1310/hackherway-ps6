export type WorkdayContext = {
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

export type SessionState = {
  acf2_id: string | null;
  workday_context: WorkdayContext | null;
  resolved_role: unknown | null;
  selected_template: unknown | null;
  final_bundle: unknown[];
  request_id: string | null;
};

export type ChatMessage = {
  role: 'user' | 'bot';
  content: string;
};

export type AgentResponse = {
  reply: string;
  session_update?: Partial<SessionState>;
};
