import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TallerService } from '../../services/taller.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-tecnicos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tecnicos.html',
  styleUrl: './tecnicos.css'
})
export class TecnicosComponent implements OnInit {
  tecnicos: any[] = [];
  loading = true;
  showModal = false;
  mensaje = '';
  isError = false;
  tallerId: number | null = null;
  rol = '';
  tecnicoId: number | null = null;

  form = { nombre_completo: '', correo: '', contrasena: '' };

  constructor(
    private tallerService: TallerService,
    public authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.tallerId = this.authService.getTallerId();
    this.rol = this.authService.getRol();
    this.tecnicoId = this.authService.getTecnicoId();
    this.cargar();
  }

  cargar() {
    if (!this.tallerId) { this.loading = false; return; }
    this.loading = true;
    this.tallerService.listarTecnicos(this.tallerId).subscribe({
      next: (res) => { this.tecnicos = res.tecnicos; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  abrirModal() {
    this.form = { nombre_completo: '', correo: '', contrasena: '' };
    this.mensaje = '';
    this.showModal = true;
  }

  cerrarModal() { this.showModal = false; this.mensaje = ''; }

  guardar() {
    if (!this.form.nombre_completo || !this.form.correo || !this.form.contrasena) {
      this.mensaje = 'Completa todos los campos';
      this.isError = true;
      return;
    }

    if (this.form.contrasena.length < 6) {
      this.mensaje = 'La contraseña debe tener al menos 6 caracteres';
      this.isError = true;
      return;
    }

    this.tallerService.agregarTecnico(this.tallerId!, this.form).subscribe({
      next: () => { this.cerrarModal(); this.cargar(); this.cdr.detectChanges(); },
      error: (err) => { this.mensaje = err.error?.detail || 'Error al agregar'; this.isError = true; this.cdr.detectChanges(); }
    });
  }

  toggleDisponibilidad(tecnico: any) {
    const nuevoEstado = !tecnico.estadisponible;
    this.tallerService.cambiarDisponibilidad(tecnico.id, nuevoEstado).subscribe({
      next: () => { tecnico.estadisponible = nuevoEstado; this.cdr.detectChanges(); },
      error: (err) => alert(err.error?.detail || 'Error al cambiar disponibilidad')
    });
  }

  eliminar(tecnicoId: number) {
    if (confirm('¿Estás seguro de eliminar este técnico?')) {
      this.tallerService.eliminarTecnico(this.tallerId!, tecnicoId).subscribe({
        next: () => this.cargar(),
        error: (err) => alert(err.error?.detail || 'Error al eliminar')
      });
    }
  }

  toggleMiDisponibilidad() {
    if (!this.tecnicoId) return;
    const usuario = this.authService.getUsuario();
    const nuevoEstado = !usuario.disponible;
    this.tallerService.cambiarDisponibilidad(this.tecnicoId, nuevoEstado).subscribe({
      next: () => {
        usuario.disponible = nuevoEstado;
        localStorage.setItem('usuario', JSON.stringify(usuario));
        this.cdr.detectChanges();
      },
      error: (err) => alert(err.error?.detail || 'Error al cambiar disponibilidad')
    });
  }
}
