import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { NotificacionService } from '../../services/notificacion.service';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css'
})
export class SidebarComponent implements OnInit, OnDestroy {
  nombre = '';
  rol = '';
  userInitial = '';
  notifCount = 0;
  private pollSub?: Subscription;

  constructor(
    public authService: AuthService,
    private notificacionService: NotificacionService,
    private router: Router
  ) {}

  ngOnInit() {
    this.nombre = this.authService.getNombre();
    this.rol = this.authService.getRol();
    this.userInitial = this.nombre ? this.nombre.charAt(0).toUpperCase() : '?';

    // Poll for notifications every 15 seconds
    this.checkNotifications();
    this.pollSub = interval(15000).subscribe(() => this.checkNotifications());
  }

  ngOnDestroy() {
    this.pollSub?.unsubscribe();
  }

  checkNotifications() {
    this.notificacionService.contarNoLeidas().subscribe({
      next: (res) => { this.notifCount = res.no_leidas; },
      error: () => {}
    });
  }

  getRolLabel(): string {
    switch (this.rol) {
      case 'conductor': return 'Conductor';
      case 'administrador_taller': return 'Admin Taller';
      case 'tecnico': return 'Técnico';
      default: return this.rol;
    }
  }

  onLogout() {
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => {
        this.authService.clearSession();
        this.router.navigate(['/login']);
      }
    });
  }
}
