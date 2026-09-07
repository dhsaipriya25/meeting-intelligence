import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { ApiService } from '../../services/api.service';
import { Results, ActionItem, Risk } from '../../models/job.model';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatCardModule,
    MatTooltipModule,
    MatSnackBarModule
  ],
  templateUrl: './results.component.html',
  styleUrl: './results.component.scss'
})
export class ResultsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private apiService = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  jobId: string = '';
  results: Results | null = null;
  isLoading: boolean = true;
  error: string = '';
  activeTab: number = 0;
  copied: boolean = false;

  actionColumns: string[] = ['index', 'task', 'assignee', 'due_date', 'priority', 'context'];
  riskColumns: string[] = ['category', 'description', 'severity', 'mitigation'];

  get outputMode(): string {
    return this.results?.output_mode ?? 'meeting_analysis';
  }

  get isMeetingAnalysis(): boolean {
    return this.outputMode === 'meeting_analysis';
  }

  get isContentAnalysis(): boolean {
    return this.outputMode === 'content_analysis';
  }

  get highCount(): number {
    return this.results?.action_items?.filter(a => a.priority === 'High').length ?? 0;
  }

  get mediumCount(): number {
    return this.results?.action_items?.filter(a => a.priority === 'Medium').length ?? 0;
  }

  get lowCount(): number {
    return this.results?.action_items?.filter(a => a.priority === 'Low').length ?? 0;
  }

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') || '';
    if (!this.jobId) {
      this.router.navigate(['/']);
      return;
    }
    this.loadResults();
  }

  loadResults(): void {
    this.isLoading = true;
    this.error = '';
    this.apiService.getResults(this.jobId).subscribe({
      next: (data) => {
        this.results = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 404) {
          this.error = 'Results not found. The job may still be processing or may have expired.';
        } else {
          this.error = 'Failed to load results. Please try again.';
        }
      }
    });
  }

  download(fileType: string): void {
    this.apiService.downloadFile(this.jobId, fileType);
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      this.copied = true;
      this.snackBar.open('Copied to clipboard!', 'Dismiss', { duration: 2000 });
      setTimeout(() => { this.copied = false; }, 2000);
    }).catch(() => {
      this.snackBar.open('Failed to copy. Please select and copy manually.', 'Dismiss', { duration: 3000 });
    });
  }

  getPriorityColor(priority: string): string {
    const map: Record<string, string> = {
      'High': 'warn',
      'Medium': 'accent',
      'Low': 'primary'
    };
    return map[priority] ?? 'primary';
  }

  getSeverityColor(severity: string): string {
    const map: Record<string, string> = {
      'High': 'warn',
      'Medium': 'accent',
      'Low': 'primary'
    };
    return map[severity] ?? 'primary';
  }

  getCategoryIcon(category: string): string {
    const map: Record<string, string> = {
      'risk': 'warning',
      'dependency': 'link',
      'blocker': 'block'
    };
    return map[category] ?? 'info';
  }

  getCategoryLabel(category: string): string {
    const map: Record<string, string> = {
      'risk': 'Risk',
      'dependency': 'Dependency',
      'blocker': 'Blocker'
    };
    return map[category] ?? category;
  }

  getPriorityClass(priority: string): string {
    const map: Record<string, string> = {
      'High': 'priority-high',
      'Medium': 'priority-medium',
      'Low': 'priority-low'
    };
    return map[priority] ?? '';
  }

  getSeverityClass(severity: string): string {
    const map: Record<string, string> = {
      'High': 'severity-high',
      'Medium': 'severity-medium',
      'Low': 'severity-low'
    };
    return map[severity] ?? '';
  }

  getCategoryClass(category: string): string {
    const map: Record<string, string> = {
      'risk': 'category-risk',
      'dependency': 'category-dependency',
      'blocker': 'category-blocker'
    };
    return map[category] ?? '';
  }

  goHome(): void {
    this.router.navigate(['/']);
  }
}
