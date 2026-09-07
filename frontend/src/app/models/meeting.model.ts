export interface Meeting {
  id: string;
  title: string;
  meetingType: string;
  inputType: string;
  status: 'pending' | 'transcribing' | 'processing' | 'completed' | 'failed';
  progressPct: number;
  currentAgent: string;
  createdBy: string;
  createdAt: string;
  summary?: string;
}

export interface ActionItem {
  id: string;
  meetingId: string;
  meetingTitle?: string;
  task: string;
  assignee: string;
  dueDate: string;
  priority: 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'done';
  context?: string;
}

export interface Risk {
  id: string;
  meetingId: string;
  description: string;
  category: string;
  severity: 'high' | 'medium' | 'low';
  mitigation: string;
}

export interface MeetingDetail extends Meeting {
  transcript?: string;
  momDocument?: string;
  emailDraft?: string;
  actionItems: ActionItem[];
  risks: Risk[];
}

export interface SearchResult {
  meetingId: string;
  excerpt: string;
  score: number;
  metadata: {
    title: string;
    meetingType: string;
    createdAt: string;
  };
}

export interface User {
  id: string;
  name: string;
  createdAt: string;
}

export interface ProgressEvent {
  status: string;
  progressPct: number;
  currentAgent: string;
  message?: string;
}

export interface ActionStats {
  open: number;
  in_progress: number;
  done: number;
  high: number;
  medium: number;
  low: number;
}

export interface DashboardStats {
  totalMeetings: number;
  openActions: number;
  completedActions: number;
  risksIdentified: number;
}
