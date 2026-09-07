import { Injectable } from '@angular/core';
import { Observable, tap, of } from 'rxjs';
import { ApiService } from './api.service';
import { User } from '../models/meeting.model';

const STORAGE_KEY = 'meeting_intelligence_user';
const STORAGE_USERS_KEY = 'meeting_intelligence_cached_users';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private api: ApiService) {}

  getCurrentUser(): string {
    return localStorage.getItem(STORAGE_KEY) || '';
  }

  setCurrentUser(name: string): void {
    localStorage.setItem(STORAGE_KEY, name);
  }

  isUserSet(): boolean {
    const user = this.getCurrentUser();
    return !!user && user.trim().length > 0;
  }

  getUsers(): Observable<User[]> {
    return this.api.getUsers();
  }

  createAndSelectUser(name: string): Observable<User> {
    return this.api.createUser(name).pipe(
      tap((user: User) => {
        this.setCurrentUser(user.name);
      })
    );
  }

  getUserInitials(name: string): string {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }
}
