import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TallerService } from '../../services/taller.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-taller-config',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './taller-config.html',
  styleUrl: './taller-config.css'
})
export class TallerConfigComponent implements OnInit {
  todasEspecialidades: any[] = [];
  seleccionadas: Set<number> = new Set();
  loading = true;
  saving = false;
  mensaje = '';
  isError = false;
  tallerId: number | null = null;

  constructor(
    private tallerService: TallerService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.tallerId = this.authService.getTallerId();
    this.cargar();
  }

  cargar() {
    this.loading = true;
    this.tallerService.listarEspecialidades().subscribe({
      next: (res) => {
        this.todasEspecialidades = res.especialidades;
        if (this.tallerId) {
          this.tallerService.obtenerEspecialidadesTaller(this.tallerId).subscribe({
            next: (res2) => {
              this.seleccionadas = new Set(res2.especialidades.map((e: any) => e.id));
              this.loading = false;
              this.cdr.detectChanges();
            },
            error: () => { this.loading = false; this.cdr.detectChanges(); }
          });
        } else {
          this.loading = false;
          this.cdr.detectChanges();
        }
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  toggleEspecialidad(id: number) {
    if (this.seleccionadas.has(id)) {
      this.seleccionadas.delete(id);
    } else {
      this.seleccionadas.add(id);
    }
  }

  isSelected(id: number): boolean {
    return this.seleccionadas.has(id);
  }

  guardar() {
    if (!this.tallerId) return;
    this.saving = true;
    this.mensaje = '';

    this.tallerService.asignarEspecialidades(
      this.tallerId,
      Array.from(this.seleccionadas)
    ).subscribe({
      next: () => {
        this.saving = false;
        this.mensaje = '✅ Especialidades actualizadas exitosamente';
        this.isError = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.saving = false;
        this.mensaje = err.error?.detail || 'Error al guardar';
        this.isError = true;
        this.cdr.detectChanges();
      }
    });
  }
}
