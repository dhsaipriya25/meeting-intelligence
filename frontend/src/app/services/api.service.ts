import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Results } from '../models/job.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  submitFile(file: File, inputType: string, outputMode: string = 'meeting_analysis'): Observable<{ job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('input_type', inputType);
    formData.append('output_mode', outputMode);
    return this.http.post<{ job_id: string }>(`${this.base}/api/process`, formData);
  }

  submitYoutube(url: string): Observable<{ job_id: string }> {
    const formData = new FormData();
    formData.append('input_type', 'youtube');
    formData.append('youtube_url', url);
    formData.append('output_mode', 'content_analysis');
    return this.http.post<{ job_id: string }>(`${this.base}/api/process`, formData);
  }

  submitText(text: string, outputMode: string = 'meeting_analysis'): Observable<{ job_id: string }> {
    const formData = new FormData();
    formData.append('input_type', 'raw_text');
    formData.append('raw_text', text);
    formData.append('output_mode', outputMode);
    return this.http.post<{ job_id: string }>(`${this.base}/api/process`, formData);
  }

  getResults(jobId: string): Observable<Results> {
    return this.http.get<Results>(`${this.base}/api/results/${jobId}`);
  }

  getProgressStream(jobId: string): EventSource {
    return new EventSource(`${this.base}/api/progress/${jobId}`);
  }

  downloadFile(jobId: string, fileType: string): void {
    const anchor = document.createElement('a');
    anchor.href = `${this.base}/api/download/${jobId}/${fileType}`;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  }
}
