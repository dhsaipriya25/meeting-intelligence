import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';

import { ApiService } from '../../services/api.service';
import { MeetingDetail, ActionItem, Risk } from '../../models/meeting.model';
import { StatusBadgeComponent } from '../../components/status-badge/status-badge.component';

@Component({
  selector: 'app-meeting-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatChipsModule,
    MatSelectModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDividerModule,
    StatusBadgeComponent
  ],
  templateUrl: './meeting-detail.component.html',
  styleUrl: './meeting-detail.component.scss'
})
export class MeetingDetailComponent implements OnInit {
  meetingId = '';
  meeting: MeetingDetail | null = null;
  loading = true;
  error = '';
  updatingActionId = '';

  actionColumns = ['task', 'assignee', 'dueDate', 'priority', 'status', 'context'];
  statusOptions = ['open', 'in_progress', 'done'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private snackBar: MatSnackBar,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.meetingId = this.route.snapshot.paramMap.get('meetingId') || '';
    if (!this.meetingId) {
      this.router.navigate(['/']);
      return;
    }
    this.loadMeeting();
  }

  loadMeeting(): void {
    this.loading = true;
    this.error = '';
    this.apiService.getMeeting(this.meetingId).subscribe({
      next: (meeting) => {
        this.meeting = meeting;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load meeting details.';
        this.loading = false;
      }
    });
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  getMeetingTypeColor(type: string): string {
    const colors: Record<string, string> = {
      'Sprint Planning': '#4f46e5',
      'Daily Standup': '#0284c7',
      'Requirement Discussion': '#7c3aed',
      'Client Call': '#16a34a',
      'Status Meeting': '#d97706'
    };
    return colors[type] || '#64748b';
  }

  updateActionStatus(action: ActionItem, newStatus: string): void {
    const prevStatus = action.status;
    action.status = newStatus as ActionItem['status'];
    this.updatingActionId = action.id;

    this.apiService.updateActionStatus(action.id, newStatus).subscribe({
      next: () => {
        this.updatingActionId = '';
        this.snackBar.open('Status updated', 'Close', { duration: 2000 });
      },
      error: () => {
        action.status = prevStatus;
        this.updatingActionId = '';
        this.snackBar.open('Failed to update status', 'Close', { duration: 3000 });
      }
    });
  }

  getSafeMom(): SafeHtml {
    if (!this.meeting?.momDocument) return '';
    const html = this.meeting.momDocument
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^#{1,3}\s+(.+)$/gm, '<h3 class="mom-heading">$1</h3>')
      .replace(/^-\s+(.+)$/gm, '<li>$1</li>');
    return this.sanitizer.bypassSecurityTrustHtml(`<p>${html}</p>`);
  }

  copyEmailToClipboard(): void {
    const text = this.meeting?.emailDraft || '';
    navigator.clipboard.writeText(text).then(() => {
      this.snackBar.open('Email copied to clipboard!', 'Close', { duration: 3000 });
    });
  }

  exportMom(format: 'docx' | 'pdf'): void {
    this.apiService.exportMom(this.meetingId, format);
    this.snackBar.open(`Downloading MOM as ${format.toUpperCase()}...`, 'Close', { duration: 2000 });
  }

  exportActions(): void {
    this.apiService.exportActions(this.meetingId);
    this.snackBar.open('Downloading Action Items as Excel...', 'Close', { duration: 2000 });
  }

  getSeverityColor(severity: string): string {
    const colors: Record<string, string> = {
      high: '#fee2e2',
      medium: '#ffedd5',
      low: '#dcfce7'
    };
    return colors[severity] || '#f1f5f9';
  }

  getSeverityTextColor(severity: string): string {
    const colors: Record<string, string> = {
      high: '#b91c1c',
      medium: '#c2410c',
      low: '#166534'
    };
    return colors[severity] || '#64748b';
  }
}
