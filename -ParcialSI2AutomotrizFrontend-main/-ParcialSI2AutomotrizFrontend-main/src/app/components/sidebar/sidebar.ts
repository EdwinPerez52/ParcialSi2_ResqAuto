import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css'
})
export class SidebarComponent implements OnInit {
  nombre = '';
  rol = '';
  userInitial = '';

  constructor(public authService: AuthService, private router: Router) {}

  ngOnInit() {
    this.nombre = this.authService.getNombre();
    this.rol = this.authService.getRol();
    this.userInitial = this.nombre ? this.nombre.charAt(0).toUpperCase() : '?';
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
