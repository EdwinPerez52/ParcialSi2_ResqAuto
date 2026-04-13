import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-recuperar-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './recuperar-password.html',
  styleUrl: './recuperar-password.css'
})
export class RecuperarPasswordComponent {
  correo = '';
  nuevaContrasena = '';
  tokenReset = '';
  mensaje = '';
  isError = false;
  loading = false;
  paso = 1; // 1 = solicitar, 2 = resetear

  constructor(private authService: AuthService, private router: Router) {}

  solicitarReset() {
    if (!this.correo) {
      this.mensaje = 'Ingresa tu correo electrónico';
      this.isError = true;
      return;
    }

    this.loading = true;
    this.mensaje = '';

    this.authService.recuperarPassword(this.correo).subscribe({
      next: (res: any) => {
        this.loading = false;
        if (res.token_reset) {
          this.tokenReset = res.token_reset;
          this.paso = 2;
          this.mensaje = '✅ Token generado. Ingresa tu nueva contraseña.';
          this.isError = false;
        } else {
          this.mensaje = res.mensaje;
          this.isError = false;
        }
      },
      error: (err) => {
        this.loading = false;
        this.mensaje = err.error?.detail || 'Error al solicitar recuperación';
        this.isError = true;
      }
    });
  }

  resetearPassword() {
    if (!this.nuevaContrasena || this.nuevaContrasena.length < 6) {
      this.mensaje = 'La contraseña debe tener al menos 6 caracteres';
      this.isError = true;
      return;
    }

    this.loading = true;
    this.mensaje = '';

    this.authService.resetPassword(this.correo, this.nuevaContrasena, this.tokenReset).subscribe({
      next: () => {
        this.loading = false;
        this.mensaje = '✅ ¡Contraseña actualizada! Redirigiendo al login...';
        this.isError = false;
        setTimeout(() => this.router.navigate(['/login']), 1500);
      },
      error: (err) => {
        this.loading = false;
        this.mensaje = err.error?.detail || 'Error al cambiar contraseña';
        this.isError = true;
      }
    });
  }
}
