import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  constructor(private http: HttpClient) {}

  login(correo: string, contrasena: string): Observable<any> {
    return this.http.post(`${API_URL}/login`, { correo, contrasena }).pipe(
      tap((res: any) => {
        localStorage.setItem('token', res.token);
        localStorage.setItem('usuario', JSON.stringify(res.usuario));
      })
    );
  }

  registro(data: any): Observable<any> {
    return this.http.post(`${API_URL}/registro`, data);
  }

  recuperarPassword(correo: string): Observable<any> {
    return this.http.post(`${API_URL}/recuperar-password`, { correo });
  }

  resetPassword(correo: string, nueva_contrasena: string, token_reset: string): Observable<any> {
    return this.http.post(`${API_URL}/reset-password`, { correo, nueva_contrasena, token_reset });
  }

  logout(): Observable<any> {
    return this.http.post(`${API_URL}/logout`, {}).pipe(
      tap(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('usuario');
      })
    );
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getUsuario(): any {
    const data = localStorage.getItem('usuario');
    return data ? JSON.parse(data) : null;
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getRol(): string {
    const usuario = this.getUsuario();
    return usuario ? usuario.rol : '';
  }

  getNombre(): string {
    const usuario = this.getUsuario();
    if (!usuario) return '';
    return usuario.nombre || usuario.nombre_comercial || usuario.correo || '';
  }

  getTallerId(): number | null {
    const usuario = this.getUsuario();
    return usuario ? usuario.taller_id : null;
  }

  getConductorId(): number | null {
    const usuario = this.getUsuario();
    return usuario ? usuario.conductor_id : null;
  }

  getTecnicoId(): number | null {
    const usuario = this.getUsuario();
    return usuario ? usuario.tecnico_id : null;
  }

  clearSession(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
  }
}
