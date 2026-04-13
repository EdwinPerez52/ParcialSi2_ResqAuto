import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { VehiculoService } from '../../services/vehiculo.service';
import { TallerService } from '../../services/taller.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit {
  nombre = '';
  rol = '';
  correo = '';
  stats: any[] = [];
  loading = true;

  constructor(
    private authService: AuthService,
    private vehiculoService: VehiculoService,
    private tallerService: TallerService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    const usuario = this.authService.getUsuario();
    this.nombre = this.authService.getNombre();
    this.rol = this.authService.getRol();
    this.correo = usuario?.correo || '';

    this.cargarStats();
  }

  cargarStats() {
    this.loading = true;

    if (this.rol === 'conductor') {
      this.vehiculoService.listar().subscribe({
        next: (res) => {
          this.stats = [
            { icon: '🚙', label: 'Mis Vehículos', value: res.vehiculos.length, color: '#3b82f6' },
            { icon: '✅', label: 'Estado', value: 'Activo', color: '#22c55e' },
            { icon: '📋', label: 'Rol', value: 'Conductor', color: '#f59e0b' }
          ];
          this.loading = false;
          this.cdr.detectChanges();
        },
        error: () => { this.loading = false; this.setDefaultStats(); this.cdr.detectChanges(); }
      });
    } else if (this.rol === 'administrador_taller') {
      const tallerId = this.authService.getTallerId();
      if (tallerId) {
        this.tallerService.listarTecnicos(tallerId).subscribe({
          next: (res) => {
            const disponibles = res.tecnicos.filter((t: any) => t.estadisponible).length;
            this.stats = [
              { icon: '👷', label: 'Técnicos', value: res.tecnicos.length, color: '#3b82f6' },
              { icon: '✅', label: 'Disponibles', value: disponibles, color: '#22c55e' },
              { icon: '🔧', label: 'Rol', value: 'Admin Taller', color: '#f59e0b' }
            ];
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: () => { this.loading = false; this.setDefaultStats(); this.cdr.detectChanges(); }
        });
      } else {
        this.loading = false;
        this.setDefaultStats();
        this.cdr.detectChanges();
      }
    } else if (this.rol === 'tecnico') {
      const usuario = this.authService.getUsuario();
      this.stats = [
        { icon: '👷', label: 'Estado', value: usuario?.disponible ? 'Disponible' : 'No disponible', color: usuario?.disponible ? '#22c55e' : '#ef4444' },
        { icon: '🏪', label: 'Taller', value: usuario?.nombre_taller || 'N/A', color: '#3b82f6' },
        { icon: '🔧', label: 'Rol', value: 'Técnico', color: '#f59e0b' }
      ];
      this.loading = false;
      this.cdr.detectChanges();
    } else {
      this.loading = false;
      this.setDefaultStats();
      this.cdr.detectChanges();
    }
  }

  setDefaultStats() {
    this.stats = [
      { icon: '📋', label: 'Rol', value: this.rol, color: '#f59e0b' },
      { icon: '✅', label: 'Estado', value: 'Activo', color: '#22c55e' },
      { icon: '🕐', label: 'Sesión', value: 'Activa', color: '#3b82f6' }
    ];
  }

  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 18) return 'Buenas tardes';
    return 'Buenas noches';
  }
}
