import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EmergenciaService } from '../../services/emergencia.service';
import { TallerService } from '../../services/taller.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-emergencias',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './emergencias.html',
  styleUrl: './emergencias.css'
})
export class EmergenciasComponent implements OnInit {
  emergencias: any[] = [];
  loading = true;
  rol = '';
  tallerId: number | null = null;
  tecnicoId: number | null = null;

  // Detalle
  detalleVisible = false;
  detalleData: any = null;
  historial: any[] = [];

  // Aceptar modal
  showAceptarModal = false;
  modalIncidenteId: number | null = null;
  tecnicos: any[] = [];
  selectedTecnicoId: number | null = null;

  mensaje = '';
  isError = false;

  filtroEstado = '';

  constructor(
    private emergenciaService: EmergenciaService,
    private tallerService: TallerService,
    public authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.rol = this.authService.getRol();
    this.tallerId = this.authService.getTallerId();
    this.tecnicoId = this.authService.getTecnicoId();
    this.cargar();
  }

  cargar() {
    this.loading = true;
    this.emergenciaService.listar(this.filtroEstado || undefined).subscribe({
      next: (res) => {
        this.emergencias = res.emergencias;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  filtrar() {
    this.cargar();
  }

  verDetalle(id: number) {
    this.emergenciaService.detalle(id).subscribe({
      next: (res) => {
        this.detalleData = res.incidente;
        this.historial = res.historial;
        this.detalleVisible = true;
        this.cdr.detectChanges();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al obtener detalle');
      }
    });
  }

  cerrarDetalle() {
    this.detalleVisible = false;
    this.detalleData = null;
  }

  // --- Admin Taller: Aceptar ---
  abrirAceptar(incidenteId: number) {
    this.modalIncidenteId = incidenteId;
    this.selectedTecnicoId = null;
    this.mensaje = '';

    if (this.tallerId) {
      this.tallerService.listarTecnicos(this.tallerId).subscribe({
        next: (res) => {
          this.tecnicos = res.tecnicos.filter((t: any) => t.estadisponible);
          this.showAceptarModal = true;
          this.cdr.detectChanges();
        }
      });
    }
  }

  confirmarAceptar() {
    if (!this.selectedTecnicoId || !this.modalIncidenteId) return;

    this.emergenciaService.aceptar(this.modalIncidenteId, this.selectedTecnicoId).subscribe({
      next: (res) => {
        this.showAceptarModal = false;
        this.mensaje = '✅ ' + res.mensaje;
        this.isError = false;
        this.cargar();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.mensaje = err.error?.detail || 'Error al aceptar';
        this.isError = true;
        this.cdr.detectChanges();
      }
    });
  }

  rechazar(incidenteId: number) {
    if (!confirm('¿Rechazar esta emergencia? Se reasignará a otro taller.')) return;
    this.emergenciaService.rechazar(incidenteId).subscribe({
      next: (res) => {
        this.mensaje = '⚠️ ' + res.mensaje;
        this.isError = false;
        this.cargar();
        this.cdr.detectChanges();
      },
      error: (err) => { alert(err.error?.detail || 'Error'); }
    });
  }

  // --- Técnico: Cambiar estado ---
  avanzarEstado(incidenteId: number, estadoActual: string) {
    const siguienteEstado: Record<string, string> = {
      'En camino': 'En sitio',
      'En sitio': 'En reparación',
      'En reparación': 'Finalizado'
    };
    const nuevo = siguienteEstado[estadoActual];
    if (!nuevo) return;

    if (!confirm(`¿Cambiar estado a "${nuevo}"?`)) return;

    this.emergenciaService.actualizarEstado(incidenteId, nuevo).subscribe({
      next: (res) => {
        this.mensaje = '✅ ' + res.mensaje;
        this.isError = false;
        this.cargar();
        this.cdr.detectChanges();
      },
      error: (err) => { alert(err.error?.detail || 'Error'); }
    });
  }

  // --- Conductor: Cancelar ---
  cancelar(incidenteId: number) {
    if (!confirm('¿Estás seguro de cancelar esta emergencia?')) return;

    this.emergenciaService.cancelar(incidenteId).subscribe({
      next: (res) => {
        this.mensaje = '❌ ' + res.mensaje;
        this.isError = false;
        this.cargar();
        this.cdr.detectChanges();
      },
      error: (err) => { alert(err.error?.detail || 'Error'); }
    });
  }

  // Helpers
  getEstadoClass(estado: string): string {
    const map: Record<string, string> = {
      'Reportado': 'estado-reportado',
      'Asignado': 'estado-asignado',
      'En camino': 'estado-encamino',
      'En sitio': 'estado-ensitio',
      'En reparación': 'estado-reparacion',
      'Finalizado': 'estado-finalizado',
      'Cancelado': 'estado-cancelado'
    };
    return map[estado] || '';
  }

  getSiguienteEstadoLabel(estado: string): string {
    const map: Record<string, string> = {
      'En camino': '📍 Llegué al sitio',
      'En sitio': '🔧 Iniciar reparación',
      'En reparación': '✅ Finalizar servicio'
    };
    return map[estado] || '';
  }

  puedeAvanzar(estado: string): boolean {
    return ['En camino', 'En sitio', 'En reparación'].includes(estado);
  }

  puedeCancelar(estado: string): boolean {
    return ['Reportado', 'Asignado'].includes(estado);
  }
}
