import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VehiculoService } from '../../services/vehiculo.service';

@Component({
  selector: 'app-vehiculos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './vehiculos.html',
  styleUrl: './vehiculos.css'
})
export class VehiculosComponent implements OnInit {
  vehiculos: any[] = [];
  loading = true;
  showModal = false;
  editMode = false;
  mensaje = '';
  isError = false;

  form = { placa: '', marca: '', modelo: '', anio: new Date().getFullYear(), color: '' };
  editPlaca = '';

  constructor(private vehiculoService: VehiculoService, private cdr: ChangeDetectorRef) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.loading = true;
    this.vehiculoService.listar().subscribe({
      next: (res) => { this.vehiculos = res.vehiculos; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  abrirModal(vehiculo?: any) {
    if (vehiculo) {
      this.editMode = true;
      this.editPlaca = vehiculo.placa;
      this.form = { placa: vehiculo.placa, marca: vehiculo.marca, modelo: vehiculo.modelo, anio: vehiculo.anio, color: vehiculo.color };
    } else {
      this.editMode = false;
      this.form = { placa: '', marca: '', modelo: '', anio: new Date().getFullYear(), color: '' };
    }
    this.mensaje = '';
    this.showModal = true;
  }

  cerrarModal() { this.showModal = false; this.mensaje = ''; }

  guardar() {
    if (!this.form.placa || !this.form.marca || !this.form.modelo) {
      this.mensaje = 'Completa los campos obligatorios';
      this.isError = true;
      return;
    }

    if (this.editMode) {
      this.vehiculoService.actualizar(this.editPlaca, {
        marca: this.form.marca, modelo: this.form.modelo, anio: this.form.anio, color: this.form.color
      }).subscribe({
        next: () => { this.cerrarModal(); this.cargar(); },
        error: (err) => { this.mensaje = err.error?.detail || 'Error al actualizar'; this.isError = true; this.cdr.detectChanges(); }
      });
    } else {
      this.vehiculoService.registrar(this.form).subscribe({
        next: () => { this.cerrarModal(); this.cargar(); },
        error: (err) => { this.mensaje = err.error?.detail || 'Error al registrar'; this.isError = true; this.cdr.detectChanges(); }
      });
    }
  }

  eliminar(placa: string) {
    if (confirm('¿Estás seguro de eliminar este vehículo?')) {
      this.vehiculoService.eliminar(placa).subscribe({
        next: () => this.cargar(),
        error: (err) => alert(err.error?.detail || 'Error al eliminar')
      });
    }
  }
}
