import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFabButton } from '@angular/material/button';

import { ApiService } from '../../services/api.service';
import { Meeting, DashboardStats } from '../../models/meeting.model';
import { StatusBadgeComponent } from '../../components/status-badge/status-badge.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    StatusBadgeComponent
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  stats: DashboardStats = { totalMeetings: 0, openActions: 0, completedActions: 0, risksIdentified: 0 };
  meetings: Meeting[] = [];
  loading = true;
  error = '';

  displayedColumns = ['title', 'meetingType', 'createdAt', 'status', 'actions'];

  constructor(private apiService: ApiService, private router: Router) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.error = '';

    this.apiService.getMeetings(1, 10).subscribe({
      next: (meetings) => {
        this.meetings = meetings;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load meetings. Please ensure the backend is running.';
        this.loading = false;
      }
    });

    this.apiService.getDashboardStats().subscribe({
      next: (stats) => { this.stats = stats; },
      error: () => {
        // Stats fail silently, compute from meetings
      }
    });
  }

  navigateToMeeting(id: string): void {
    this.router.navigate(['/meeting', id]);
  }

  navigateToUpload(): void {
    this.router.navigate(['/upload']);
  }

  getMeetingTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      'Sprint Planning': 'sprint',
      'Daily Standup': 'today',
      'Requirement Discussion': 'description',
      'Client Call': 'call',
      'Status Meeting': 'bar_chart'
    };
    return icons[type] || 'meeting_room';
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }
}
