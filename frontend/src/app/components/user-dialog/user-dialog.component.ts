import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl, Validators } from '@angular/forms';

import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ApiService } from '../../services/api.service';
import { User } from '../../models/meeting.model';

@Component({
  selector: 'app-user-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    MatIconModule,
    MatDividerModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="p-6">
      <h2 class="text-xl font-bold text-gray-800 mb-2">
        {{ data.currentUser ? 'Switch User' : 'Welcome! Who are you?' }}
      </h2>
      <p class="text-gray-500 text-sm mb-4">
        {{ data.currentUser ? 'Select a user or create a new one.' : 'Select your name to get started, or create a new profile.' }}
      </p>

      <!-- Existing users -->
      @if (data.users && data.users.length > 0) {
        <div class="mb-4">
          <p class="text-xs font-semibold text-gray-400 uppercase mb-2">Existing Users</p>
          <mat-selection-list [multiple]="false" (selectionChange)="onUserSelected($event.options[0]?.value)">
            @for (user of data.users; track user.id) {
              <mat-list-option [value]="user.name" [selected]="user.name === data.currentUser">
                <mat-icon matListItemIcon>person</mat-icon>
                <span>{{ user.name }}</span>
              </mat-list-option>
            }
          </mat-selection-list>
        </div>
        <mat-divider class="my-4"></mat-divider>
      }

      <!-- Create new user -->
      <div>
        <p class="text-xs font-semibold text-gray-400 uppercase mb-2">Create New User</p>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Your Name</mat-label>
          <input matInput [formControl]="nameControl" placeholder="e.g. Alice Johnson"
                 (keyup.enter)="createUser()" />
          <mat-icon matSuffix>person_add</mat-icon>
          @if (nameControl.hasError('required')) {
            <mat-error>Name is required</mat-error>
          }
          @if (nameControl.hasError('minlength')) {
            <mat-error>Name must be at least 2 characters</mat-error>
          }
        </mat-form-field>

        <button
          mat-flat-button
          color="primary"
          class="w-full"
          [disabled]="nameControl.invalid || creating"
          (click)="createUser()"
        >
          @if (creating) {
            <mat-spinner diameter="20" class="inline-block mr-2"></mat-spinner>
          }
          {{ creating ? 'Creating...' : 'Create & Select' }}
        </button>
      </div>

      @if (error) {
        <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {{ error }}
        </div>
      }
    </div>
  `
})
export class UserDialogComponent implements OnInit {
  nameControl = new FormControl('', [Validators.required, Validators.minLength(2)]);
  creating = false;
  error = '';
  selectedUser = '';

  constructor(
    public dialogRef: MatDialogRef<UserDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { users: User[]; currentUser: string },
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.selectedUser = this.data.currentUser || '';
  }

  onUserSelected(userName: string): void {
    if (userName) {
      this.dialogRef.close(userName);
    }
  }

  createUser(): void {
    if (this.nameControl.invalid) return;

    this.creating = true;
    this.error = '';
    const name = this.nameControl.value!.trim();

    this.apiService.createUser(name).subscribe({
      next: (user) => {
        this.creating = false;
        this.dialogRef.close(user.name);
      },
      error: (err) => {
        this.creating = false;
        // If API fails, still allow local user
        this.dialogRef.close(name);
      }
    });
  }
}
