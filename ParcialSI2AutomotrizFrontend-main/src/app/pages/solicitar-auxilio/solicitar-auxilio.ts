import { Component, OnInit, AfterViewInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { EmergenciaService } from '../../services/emergencia.service';
import { VehiculoService } from '../../services/vehiculo.service';
import { AuthService } from '../../services/auth.service';
import * as L from 'leaflet';

@Component({
  selector: 'app-solicitar-auxilio',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './solicitar-auxilio.html',
  styleUrl: './solicitar-auxilio.css'
})
export class SolicitarAuxilioComponent implements OnInit, AfterViewInit, OnDestroy {
  vehiculos: any[] = [];
  loading = true;
  enviando = false;
  mensaje = '';
  isError = false;
  ubicacionObtenida = false;

  form = {
    vehiculo_placa: '',
    descripcion: '',
    latitud: 0,
    longitud: 0
  };

  map: any;
  marker: any;
  resultado: any = null;

  constructor(
    private emergenciaService: EmergenciaService,
    private vehiculoService: VehiculoService,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.vehiculoService.listar().subscribe({
      next: (res) => {
        this.vehiculos = res.vehiculos;
        if (this.vehiculos.length > 0) {
          this.form.vehiculo_placa = this.vehiculos[0].placa;
        }
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  ngAfterViewInit() {
    this.initMap();
    this.obtenerUbicacion();
  }

  ngOnDestroy() {
    if (this.map) {
      this.map.off();
      this.map.remove();
      this.map = null;
    }
  }

  initMap() {
    // Default: Santa Cruz de la Sierra
    this.map = L.map('map').setView([-17.7833, -63.1821], 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap'
    }).addTo(this.map);

    // Fix icon issue
    const iconDefault = L.icon({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41]
    });
    L.Marker.prototype.options.icon = iconDefault;
  }

  obtenerUbicacion() {
    if (!navigator.geolocation) {
      this.mensaje = 'Tu navegador no soporta geolocalización';
      this.isError = true;
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.form.latitud = pos.coords.latitude;
        this.form.longitud = pos.coords.longitude;
        this.ubicacionObtenida = true;

        this.map.setView([pos.coords.latitude, pos.coords.longitude], 15);

        if (this.marker) this.map.removeLayer(this.marker);
        this.marker = L.marker([pos.coords.latitude, pos.coords.longitude])
          .addTo(this.map)
          .bindPopup('📍 Tu ubicación')
          .openPopup();

        this.cdr.detectChanges();
      },
      (err) => {
        // Fallback a Santa Cruz centro
        this.form.latitud = -17.7833;
        this.form.longitud = -63.1821;
        this.ubicacionObtenida = true;
        this.mensaje = 'No se pudo obtener tu GPS. Usando ubicación por defecto (Santa Cruz).';
        this.isError = false;

        this.marker = L.marker([-17.7833, -63.1821])
          .addTo(this.map)
          .bindPopup('📍 Ubicación por defecto')
          .openPopup();

        this.cdr.detectChanges();
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  solicitar() {
    if (!this.form.vehiculo_placa) {
      this.mensaje = 'Selecciona un vehículo';
      this.isError = true;
      return;
    }
    if (!this.form.descripcion.trim()) {
      this.mensaje = 'Describe el problema que tienes';
      this.isError = true;
      return;
    }

    this.enviando = true;
    this.mensaje = '';

    this.emergenciaService.solicitar(this.form).subscribe({
      next: (res) => {
        this.resultado = res;
        this.enviando = false;
        this.mensaje = '✅ ¡Auxilio solicitado exitosamente!';
        this.isError = false;

        // Mostrar taller en el mapa si fue asignado
        if (res.taller_asignado) {
          // Se podría agregar el marker del taller aquí si tuviéramos sus coords
        }

        this.cdr.detectChanges();
      },
      error: (err) => {
        this.enviando = false;
        this.mensaje = err.error?.detail || 'Error al solicitar auxilio';
        this.isError = true;
        this.cdr.detectChanges();
      }
    });
  }

  irAEmergencias() {
    this.router.navigate(['/emergencias']);
  }
}
