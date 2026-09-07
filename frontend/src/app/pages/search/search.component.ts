import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';

import { ApiService } from '../../services/api.service';
import { SearchResult } from '../../models/meeting.model';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDividerModule
  ],
  templateUrl: './search.component.html',
  styleUrl: './search.component.scss'
})
export class SearchComponent {
  query = '';
  selectedType = '';
  results: SearchResult[] = [];
  loading = false;
  searched = false;
  error = '';

  meetingTypes = [
    'Sprint Planning',
    'Daily Standup',
    'Requirement Discussion',
    'Client Call',
    'Status Meeting'
  ];

  suggestions = [
    'action items assigned to John',
    'risk related to deployment',
    'sprint velocity discussion',
    'client feedback on UI',
    'budget approval'
  ];

  constructor(private apiService: ApiService, private router: Router) {}

  search(): void {
    if (!this.query.trim()) return;

    this.loading = true;
    this.searched = true;
    this.error = '';

    this.apiService.search(this.query.trim(), this.selectedType || undefined).subscribe({
      next: (results) => {
        this.results = results;
        this.loading = false;
      },
      error: () => {
        this.error = 'Search failed. Please try again.';
        this.loading = false;
        this.results = [];
      }
    });
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.search();
    }
  }

  selectType(type: string): void {
    this.selectedType = this.selectedType === type ? '' : type;
    if (this.searched && this.query) this.search();
  }

  useSuggestion(suggestion: string): void {
    this.query = suggestion;
    this.search();
  }

  navigateToMeeting(meetingId: string): void {
    this.router.navigate(['/meeting', meetingId]);
  }

  highlightText(text: string, query: string): string {
    if (!query) return text;
    const words = query.split(' ').filter(w => w.length > 2);
    let highlighted = text;
    words.forEach(word => {
      const regex = new RegExp(`(${word})`, 'gi');
      highlighted = highlighted.replace(regex, '<mark class="search-highlight">$1</mark>');
    });
    return highlighted;
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }

  getTypeColor(type: string): string {
    const colors: Record<string, string> = {
      'Sprint Planning': '#4f46e5',
      'Daily Standup': '#0284c7',
      'Requirement Discussion': '#7c3aed',
      'Client Call': '#16a34a',
      'Status Meeting': '#d97706'
    };
    return colors[type] || '#64748b';
  }
}
