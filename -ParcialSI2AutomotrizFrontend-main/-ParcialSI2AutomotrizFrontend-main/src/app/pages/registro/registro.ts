import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-registro',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './registro.html',
  styleUrl: './registro.css'
})
export class RegistroComponent {
  correo = '';
  contrasena = '';
  confirmarContrasena = '';
  nombre_completo = '';
  telefono = '';
  rol = 'conductor';
  // Campos taller
  nit = '';
  nombre_comercial = '';
  direccion = '';

  mensaje = '';
  isError = false;
  loading = false;
  showPassword = false;

  constructor(private authService: AuthService, private router: Router) {}

  registrar() {
    if (!this.correo || !this.contrasena || !this.nombre_completo) {
      this.mensaje = 'Por favor completa los campos obligatorios';
      this.isError = true;
      return;
    }

    if (this.contrasena !== this.confirmarContrasena) {
      this.mensaje = 'Las contraseñas no coinciden';
      this.isError = true;
      return;
    }

    if (this.contrasena.length < 6) {
      this.mensaje = 'La contraseña debe tener al menos 6 caracteres';
      this.isError = true;
      return;
    }

    this.loading = true;
    this.mensaje = '';

    const data: any = {
      correo: this.correo,
      contrasena: this.contrasena,
      nombre_completo: this.nombre_completo,
      telefono: this.telefono,
      rol: this.rol
    };

    if (this.rol === 'administrador_taller') {
      data.nit = this.nit;
      data.nombre_comercial = this.nombre_comercial;
      data.direccion = this.direccion;
    }

    this.authService.registro(data).subscribe({
      next: () => {
        this.loading = false;
        this.mensaje = '✅ ¡Registro exitoso! Redirigiendo al login...';
        this.isError = false;
        setTimeout(() => this.router.navigate(['/login']), 1500);
      },
      error: (err) => {
        this.loading = false;
        this.mensaje = err.error?.detail || 'Error al registrar usuario';
        this.isError = true;
      }
    });
  }
}
