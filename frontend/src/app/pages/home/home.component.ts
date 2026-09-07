import { Component, inject, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';

import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatCardModule
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  private router = inject(Router);
  private apiService = inject(ApiService);

  inputType: string = 'file';
  outputMode: 'meeting_analysis' | 'content_analysis' = 'meeting_analysis';
  selectedFile: File | null = null;
  youtubeUrl: string = '';
  rawText: string = '';
  isLoading: boolean = false;
  error: string = '';
  isDragOver: boolean = false;

  inputTypeCards = [
    { type: 'file', icon: 'upload_file', label: 'File Upload', subtitle: 'MP3 / MP4' },
    { type: 'youtube', icon: 'play_circle', label: 'YouTube Link', subtitle: 'Paste URL' },
    { type: 'text_file', icon: 'description', label: 'Text File', subtitle: '.txt / .pdf / .docx' },
    { type: 'raw_text', icon: 'edit_note', label: 'Paste Text', subtitle: 'Type or paste' }
  ];

  selectInputType(type: string): void {
    this.inputType = type;
    this.selectedFile = null;
    this.error = '';
    if (type === 'youtube') {
      this.outputMode = 'content_analysis';
    } else {
      this.outputMode = 'meeting_analysis';
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.error = '';
    }
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.selectedFile = event.dataTransfer.files[0];
      this.error = '';
    }
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

  triggerFileInput(): void {
    this.fileInput.nativeElement.click();
  }

  removeFile(): void {
    this.selectedFile = null;
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
  }

  getAcceptedFormats(): string {
    if (this.inputType === 'file') return 'audio/*, video/*, .mp3, .mp4, .m4a, .wav, .webm';
    if (this.inputType === 'text_file') return '.txt, .pdf, .docx, .doc';
    return '*';
  }

  getAcceptedFormatsLabel(): string {
    if (this.inputType === 'file') return 'MP3, MP4, M4A, WAV, WEBM';
    if (this.inputType === 'text_file') return 'TXT, PDF, DOCX, DOC';
    return 'All files';
  }

  validate(): boolean {
    this.error = '';

    if (this.inputType === 'file' || this.inputType === 'text_file') {
      if (!this.selectedFile) {
        this.error = 'Please select a file to upload.';
        return false;
      }
    } else if (this.inputType === 'youtube') {
      if (!this.youtubeUrl.trim()) {
        this.error = 'Please enter a YouTube URL.';
        return false;
      }
      const youtubePattern = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/;
      if (!youtubePattern.test(this.youtubeUrl.trim())) {
        this.error = 'Please enter a valid YouTube URL.';
        return false;
      }
    } else if (this.inputType === 'raw_text') {
      if (!this.rawText.trim()) {
        this.error = 'Please paste or type your meeting content.';
        return false;
      }
      if (this.rawText.trim().length < 50) {
        this.error = 'Content is too short. Please provide more text.';
        return false;
      }
    }

    return true;
  }

  submit(): void {
    if (!this.validate()) return;

    this.isLoading = true;
    this.error = '';

    let request$;

    if (this.inputType === 'file' || this.inputType === 'text_file') {
      request$ = this.apiService.submitFile(this.selectedFile!, this.inputType, this.outputMode);
    } else if (this.inputType === 'youtube') {
      request$ = this.apiService.submitYoutube(this.youtubeUrl.trim());
    } else {
      request$ = this.apiService.submitText(this.rawText.trim(), this.outputMode);
    }

    request$.subscribe({
      next: (response) => {
        this.isLoading = false;
        this.router.navigate(['/processing', response.job_id]);
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 0) {
          this.error = 'Cannot connect to server. Make sure the backend is running on port 8000.';
        } else if (err.error?.detail) {
          this.error = err.error.detail;
        } else {
          this.error = 'An error occurred while submitting. Please try again.';
        }
      }
    });
  }
}
