import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/home/home.component').then(m => m.HomeComponent)
  },
  {
    path: 'processing/:jobId',
    loadComponent: () =>
      import('./pages/processing/processing.component').then(m => m.ProcessingComponent)
  },
  {
    path: 'results/:jobId',
    loadComponent: () =>
      import('./pages/results/results.component').then(m => m.ResultsComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];
