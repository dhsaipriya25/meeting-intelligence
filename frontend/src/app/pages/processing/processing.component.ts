import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../services/api.service';

interface PipelineStep {
  key: string;
  label: string;
  icon: string;
  state: 'pending' | 'active' | 'done';
}

@Component({
  selector: 'app-processing',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './processing.component.html',
  styleUrl: './processing.component.scss'
})
export class ProcessingComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private apiService = inject(ApiService);

  jobId: string = '';
  progress: number = 0;
  status: string = 'pending';
  currentAgent: string = '';
  error: boolean = false;
  errorMessage: string = '';

  private eventSource?: EventSource;
  private navTimer?: ReturnType<typeof setTimeout>;

  pipelineSteps: PipelineStep[] = [
    { key: 'transcribing',       label: 'Transcription',       icon: 'mic',                    state: 'pending' },
    { key: 'summarizing',        label: 'Summary',              icon: 'summarize',              state: 'pending' },
    { key: 'extracting_actions', label: 'Action Items',         icon: 'task_alt',               state: 'pending' },
    { key: 'analyzing_risks',    label: 'Risk Analysis',        icon: 'warning_amber',          state: 'pending' },
    { key: 'generating_mom',     label: 'MOM Document',         icon: 'description',            state: 'pending' },
    { key: 'drafting_email',     label: 'Email Draft',          icon: 'email',                  state: 'pending' },
    { key: 'explaining',         label: 'Detailed Explanation', icon: 'school',                 state: 'pending' },
    { key: 'extracting_steps',   label: 'Steps Extraction',     icon: 'format_list_numbered',   state: 'pending' },
  ];

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') || '';
    if (!this.jobId) {
      this.router.navigate(['/']);
      return;
    }
    this.connectSSE();
  }

  connectSSE(): void {
    this.eventSource = this.apiService.getProgressStream(this.jobId);

    this.eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        this.handleEvent(data);
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    this.eventSource.addEventListener('progress', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        this.handleEvent(data);
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    });

    this.eventSource.onerror = () => {
      if (this.status !== 'completed' && this.status !== 'failed') {
        this.eventSource?.close();
        setTimeout(() => {
          if (this.status !== 'completed' && this.status !== 'failed') {
            this.connectSSE();
          }
        }, 3000);
      }
    };
  }

  handleEvent(data: { status: string; progress: number; current_agent: string; error?: string; message?: string }): void {
    this.progress = data.progress ?? 0;
    this.status = data.status ?? 'pending';
    this.currentAgent = data.current_agent ?? '';

    this.updateSteps();

    if (data.status === 'completed') {
      this.eventSource?.close();
      this.navTimer = setTimeout(() => {
        this.router.navigate(['/results', this.jobId]);
      }, 1000);
    } else if (data.status === 'failed') {
      this.error = true;
      this.errorMessage = data.error || 'An unknown error occurred.';
      this.eventSource?.close();
    }
  }

  updateSteps(): void {
    const agentOrder = [
      'transcribing',
      'summarizing',
      'extracting_actions',
      'analyzing_risks',
      'generating_mom',
      'drafting_email',
      'explaining',
      'extracting_steps'
    ];

    const currentIdx = agentOrder.indexOf(this.currentAgent);

    this.pipelineSteps = this.pipelineSteps.map((step, idx) => {
      let state: PipelineStep['state'] = 'pending';
      if (this.status === 'completed') {
        state = 'done';
      } else if (idx < currentIdx) {
        state = 'done';
      } else if (idx === currentIdx) {
        state = 'active';
      }
      return { ...step, state };
    });
  }

  getAgentLabel(agent: string): string {
    const labels: Record<string, string> = {
      'transcribing':       'Transcribing audio...',
      'summarizing':        'Generating summary...',
      'extracting_actions': 'Extracting action items...',
      'analyzing_risks':    'Analyzing risks...',
      'generating_mom':     'Generating MOM document...',
      'drafting_email':     'Drafting follow-up email...',
      'explaining':         'Generating detailed explanation...',
      'extracting_steps':   'Extracting step-by-step details...',
      'completed':          'Analysis complete!'
    };
    return labels[agent] || (agent ? agent : 'Initializing...');
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  ngOnDestroy(): void {
    this.eventSource?.close();
    if (this.navTimer) clearTimeout(this.navTimer);
  }
}
