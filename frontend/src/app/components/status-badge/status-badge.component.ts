import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule, MatChipsModule, MatIconModule],
  template: `
    <span class="status-badge" [ngClass]="getBadgeClass()">
      <mat-icon class="status-icon">{{ getIcon() }}</mat-icon>
      {{ getLabel() }}
    </span>
  `,
  styles: [`
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 500;
      line-height: 1.4;
    }
    .status-icon {
      font-size: 13px;
      width: 13px;
      height: 13px;
    }
    .badge-pending { background: #f1f5f9; color: #64748b; }
    .badge-transcribing { background: #dbeafe; color: #1d4ed8; }
    .badge-processing { background: #ffedd5; color: #c2410c; }
    .badge-completed { background: #dcfce7; color: #166534; }
    .badge-failed { background: #fee2e2; color: #b91c1c; }
    .badge-open { background: #dbeafe; color: #1d4ed8; }
    .badge-in_progress { background: #ffedd5; color: #c2410c; }
    .badge-done { background: #dcfce7; color: #166534; }
    .badge-high { background: #fee2e2; color: #b91c1c; }
    .badge-medium { background: #ffedd5; color: #c2410c; }
    .badge-low { background: #dcfce7; color: #166534; }
  `]
})
export class StatusBadgeComponent {
  @Input() status = '';
  @Input() type: 'meeting' | 'action' | 'priority' = 'meeting';

  getBadgeClass(): string {
    return `badge-${this.status}`;
  }

  getIcon(): string {
    const iconMap: Record<string, string> = {
      pending: 'schedule',
      transcribing: 'mic',
      processing: 'autorenew',
      completed: 'check_circle',
      failed: 'error',
      open: 'radio_button_unchecked',
      in_progress: 'pending',
      done: 'check_circle',
      high: 'priority_high',
      medium: 'remove',
      low: 'arrow_downward'
    };
    return iconMap[this.status] || 'info';
  }

  getLabel(): string {
    const labelMap: Record<string, string> = {
      pending: 'Pending',
      transcribing: 'Transcribing',
      processing: 'Processing',
      completed: 'Completed',
      failed: 'Failed',
      open: 'Open',
      in_progress: 'In Progress',
      done: 'Done',
      high: 'High',
      medium: 'Medium',
      low: 'Low'
    };
    return labelMap[this.status] || this.status;
  }
}
