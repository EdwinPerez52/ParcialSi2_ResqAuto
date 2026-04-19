import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class NotificacionService {

  constructor(private http: HttpClient) {}

  listar(pagina = 1, limite = 20): Observable<any> {
    return this.http.get(`${API_URL}/notificaciones?pagina=${pagina}&limite=${limite}`);
  }

  contarNoLeidas(): Observable<any> {
    return this.http.get(`${API_URL}/notificaciones/no-leidas`);
  }

  marcarLeida(id: number): Observable<any> {
    return this.http.patch(`${API_URL}/notificaciones/${id}/leer`, {});
  }

  marcarTodasLeidas(): Observable<any> {
    return this.http.patch(`${API_URL}/notificaciones/leer-todas`, {});
  }
}
