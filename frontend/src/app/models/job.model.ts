export interface Job {
  jobId: string;
}

export interface ProgressEvent {
  status: string;
  progress: number;
  currentAgent: string;
}

export interface ActionItem {
  task: string;
  assignee: string;
  due_date: string | null;
  priority: 'High' | 'Medium' | 'Low';
  context: string;
}

export interface Risk {
  description: string;
  category: 'risk' | 'dependency' | 'blocker';
  severity: 'High' | 'Medium' | 'Low';
  mitigation: string;
}

export interface Results {
  job_id: string;
  status: string;
  transcript: string;
  summary: string;
  output_mode: 'meeting_analysis' | 'content_analysis';
  // Meeting Analysis
  action_items: ActionItem[];
  risks: Risk[];
  mom_document: string;
  email_draft: string;
  // Content Analysis
  detailed_explanation: string;
  steps_detail: string | null;
}
