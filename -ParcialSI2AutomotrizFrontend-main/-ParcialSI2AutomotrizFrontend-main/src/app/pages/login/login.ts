import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent {
  correo = '';
  contrasena = '';
  mensaje = '';
  isError = false;
  loading = false;
  showPassword = false;

  constructor(private authService: AuthService, private router: Router) {
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
    }
  }

  iniciarSesion() {
    if (!this.correo || !this.contrasena) {
      this.mensaje = 'Por favor completa todos los campos';
      this.isError = true;
      return;
    }

    this.loading = true;
    this.mensaje = '';

    this.authService.login(this.correo, this.contrasena).subscribe({
      next: (res: any) => {
        this.loading = false;
        this.mensaje = '✅ ¡Bienvenido!';
        this.isError = false;
        setTimeout(() => this.router.navigate(['/dashboard']), 500);
      },
      error: (err) => {
        this.loading = false;
        this.mensaje = err.error?.detail || 'Error al iniciar sesión';
        this.isError = true;
      }
    });
  }
}
