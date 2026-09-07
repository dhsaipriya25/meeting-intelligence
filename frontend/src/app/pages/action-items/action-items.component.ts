import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatBadgeModule } from '@angular/material/badge';

import { ApiService } from '../../services/api.service';
import { ActionItem, ActionStats } from '../../models/meeting.model';
import { StatusBadgeComponent } from '../../components/status-badge/status-badge.component';

@Component({
  selector: 'app-action-items',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDividerModule,
    MatBadgeModule,
    StatusBadgeComponent
  ],
  templateUrl: './action-items.component.html',
  styleUrl: './action-items.component.scss'
})
export class ActionItemsComponent implements OnInit {
  allActions: ActionItem[] = [];
  filteredActions: ActionItem[] = [];
  stats: ActionStats = { open: 0, in_progress: 0, done: 0, high: 0, medium: 0, low: 0 };
  loading = true;
  error = '';

  filterStatus = 'all';
  filterPriority = 'all';
  filterAssignee = '';

  displayedColumns = ['meetingTitle', 'task', 'assignee', 'dueDate', 'priority', 'status', 'context'];
  statusOptions = ['open', 'in_progress', 'done'];

  constructor(private apiService: ApiService, private snackBar: MatSnackBar) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.error = '';

    this.apiService.getActions().subscribe({
      next: (actions) => {
        this.allActions = actions;
        this.applyFilters();
        this.loading = false;
        this.computeStats();
      },
      error: () => {
        this.error = 'Failed to load action items.';
        this.loading = false;
      }
    });

    this.apiService.getActionStats().subscribe({
      next: (stats) => { this.stats = stats; },
      error: () => {}
    });
  }

  computeStats(): void {
    this.stats = {
      open: this.allActions.filter(a => a.status === 'open').length,
      in_progress: this.allActions.filter(a => a.status === 'in_progress').length,
      done: this.allActions.filter(a => a.status === 'done').length,
      high: this.allActions.filter(a => a.priority === 'high').length,
      medium: this.allActions.filter(a => a.priority === 'medium').length,
      low: this.allActions.filter(a => a.priority === 'low').length
    };
  }

  applyFilters(): void {
    this.filteredActions = this.allActions.filter(action => {
      if (this.filterStatus !== 'all' && action.status !== this.filterStatus) return false;
      if (this.filterPriority !== 'all' && action.priority !== this.filterPriority) return false;
      if (this.filterAssignee && !action.assignee?.toLowerCase().includes(this.filterAssignee.toLowerCase())) return false;
      return true;
    });
  }

  setStatusFilter(status: string): void {
    this.filterStatus = status;
    this.applyFilters();
  }

  clearFilters(): void {
    this.filterStatus = 'all';
    this.filterPriority = 'all';
    this.filterAssignee = '';
    this.applyFilters();
  }

  updateStatus(action: ActionItem, newStatus: string): void {
    const prev = action.status;
    action.status = newStatus as ActionItem['status'];

    this.apiService.updateActionStatus(action.id, newStatus).subscribe({
      next: () => {
        this.computeStats();
        this.snackBar.open('Status updated', 'Close', { duration: 2000 });
      },
      error: () => {
        action.status = prev;
        this.snackBar.open('Failed to update status', 'Close', { duration: 3000 });
      }
    });
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }
}
