import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatStepperModule } from '@angular/material/stepper';
import { MatChipsModule } from '@angular/material/chips';

import { ApiService } from '../../services/api.service';
import { UserService } from '../../services/user.service';

type InputType = 'file' | 'youtube' | 'text';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatButtonToggleModule,
    MatStepperModule,
    MatChipsModule
  ],
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.scss'
})
export class UploadComponent implements OnInit {
  form: FormGroup;
  inputType: InputType = 'file';
  selectedFile: File | null = null;
  isDragOver = false;
  uploading = false;
  uploadProgress = 0;
  error = '';

  meetingTypes = [
    'Sprint Planning',
    'Daily Standup',
    'Requirement Discussion',
    'Client Call',
    'Status Meeting'
  ];

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private userService: UserService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      title: ['', [Validators.required, Validators.minLength(3)]],
      meetingType: ['Sprint Planning', Validators.required],
      createdBy: ['', Validators.required],
      youtubeUrl: [''],
      pastedText: ['']
    });
  }

  ngOnInit(): void {
    const currentUser = this.userService.getCurrentUser();
    if (currentUser) {
      this.form.patchValue({ createdBy: currentUser });
    }
  }

  selectInputType(type: InputType): void {
    this.inputType = type;
    this.selectedFile = null;
    this.error = '';
    // Update validators
    this.form.get('youtubeUrl')?.clearValidators();
    this.form.get('pastedText')?.clearValidators();
    if (type === 'youtube') {
      this.form.get('youtubeUrl')?.setValidators([Validators.required, Validators.pattern(/^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+/)]);
    } else if (type === 'text') {
      this.form.get('pastedText')?.setValidators([Validators.required, Validators.minLength(50)]);
    }
    this.form.get('youtubeUrl')?.updateValueAndValidity();
    this.form.get('pastedText')?.updateValueAndValidity();
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    const allowed = ['audio/mpeg', 'audio/mp3', 'video/mp4', 'video/quicktime', 'audio/wav', 'audio/x-m4a'];
    const ext = file.name.split('.').pop()?.toLowerCase();
    const allowedExt = ['mp3', 'mp4', 'wav', 'm4a', 'mov'];
    if (!allowedExt.includes(ext || '')) {
      this.error = 'Invalid file type. Please upload MP3, MP4, WAV, or M4A files.';
      return;
    }
    this.selectedFile = file;
    this.error = '';
    if (!this.form.get('title')?.value) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      this.form.patchValue({ title: nameWithoutExt });
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  isFormValid(): boolean {
    if (!this.form.get('title')?.valid) return false;
    if (!this.form.get('meetingType')?.valid) return false;
    if (!this.form.get('createdBy')?.valid) return false;
    if (this.inputType === 'file' && !this.selectedFile) return false;
    if (this.inputType === 'youtube' && !this.form.get('youtubeUrl')?.valid) return false;
    if (this.inputType === 'text' && !this.form.get('pastedText')?.valid) return false;
    return true;
  }

  submit(): void {
    if (!this.isFormValid()) {
      this.form.markAllAsTouched();
      return;
    }

    this.uploading = true;
    this.error = '';

    const title = this.form.get('title')!.value;
    const meetingType = this.form.get('meetingType')!.value;
    const createdBy = this.form.get('createdBy')!.value;

    if (this.inputType === 'file' && this.selectedFile) {
      this.apiService.submitFile(this.selectedFile, 'file').subscribe({
        next: (res) => {
          this.uploading = false;
          this.router.navigate(['/processing', res.job_id]);
        },
        error: (err) => {
          this.uploading = false;
          this.error = err?.error?.detail || 'Upload failed. Please try again.';
        }
      });
    } else if (this.inputType === 'youtube') {
      const url = this.form.get('youtubeUrl')!.value;
      this.apiService.submitYoutube(url).subscribe({
        next: (res) => {
          this.uploading = false;
          this.router.navigate(['/processing', res.job_id]);
        },
        error: (err) => {
          this.uploading = false;
          this.error = err?.error?.detail || 'Failed to process YouTube URL. Please try again.';
        }
      });
    } else if (this.inputType === 'text') {
      const text = this.form.get('pastedText')!.value;
      this.apiService.submitText(text).subscribe({
        next: (res) => {
          this.uploading = false;
          this.router.navigate(['/processing', res.job_id]);
        },
        error: (err) => {
          this.uploading = false;
          this.error = err?.error?.detail || 'Failed to process text. Please try again.';
        }
      });
    }
  }
}
