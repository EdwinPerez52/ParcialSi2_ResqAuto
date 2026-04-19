import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./pages/login/login').then(m => m.LoginComponent) },
  { path: 'registro', loadComponent: () => import('./pages/registro/registro').then(m => m.RegistroComponent) },
  { path: 'recuperar-password', loadComponent: () => import('./pages/recuperar-password/recuperar-password').then(m => m.RecuperarPasswordComponent) },
  { path: 'dashboard', loadComponent: () => import('./pages/dashboard/dashboard').then(m => m.DashboardComponent), canActivate: [authGuard] },
  { path: 'vehiculos', loadComponent: () => import('./pages/vehiculos/vehiculos').then(m => m.VehiculosComponent), canActivate: [authGuard] },
  { path: 'taller-config', loadComponent: () => import('./pages/taller-config/taller-config').then(m => m.TallerConfigComponent), canActivate: [authGuard] },
  { path: 'tecnicos', loadComponent: () => import('./pages/tecnicos/tecnicos').then(m => m.TecnicosComponent), canActivate: [authGuard] },
  { path: 'bitacora', loadComponent: () => import('./pages/bitacora/bitacora').then(m => m.BitacoraComponent), canActivate: [authGuard] },
  { path: 'solicitar-auxilio', loadComponent: () => import('./pages/solicitar-auxilio/solicitar-auxilio').then(m => m.SolicitarAuxilioComponent), canActivate: [authGuard] },
  { path: 'emergencias', loadComponent: () => import('./pages/emergencias/emergencias').then(m => m.EmergenciasComponent), canActivate: [authGuard] },
  { path: '**', redirectTo: '/login' }
];
