import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BitacoraService } from '../../services/bitacora.service';

@Component({
  selector: 'app-bitacora',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bitacora.html',
  styleUrl: './bitacora.css'
})
export class BitacoraComponent implements OnInit {
  registros: any[] = [];
  loading = true;
  pagina = 1;
  limite = 15;
  total = 0;
  totalPaginas = 0;

  filtroTabla = '';

  constructor(private bitacoraService: BitacoraService, private cdr: ChangeDetectorRef) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.loading = true;
    this.bitacoraService.listar(
      this.pagina,
      this.limite,
      undefined,
      this.filtroTabla || undefined
    ).subscribe({
      next: (res) => {
        this.registros = res.registros;
        this.total = res.total;
        this.totalPaginas = res.total_paginas;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  filtrar() {
    this.pagina = 1;
    this.cargar();
  }

  limpiarFiltro() {
    this.filtroTabla = '';
    this.pagina = 1;
    this.cargar();
  }

  paginaAnterior() {
    if (this.pagina > 1) {
      this.pagina--;
      this.cargar();
    }
  }

  paginaSiguiente() {
    if (this.pagina < this.totalPaginas) {
      this.pagina++;
      this.cargar();
    }
  }
}
