import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class BitacoraService {

  constructor(private http: HttpClient) {}

  listar(pagina: number = 1, limite: number = 20, usuarioId?: number, tabla?: string): Observable<any> {
    let params = new HttpParams()
      .set('pagina', pagina.toString())
      .set('limite', limite.toString());

    if (usuarioId) {
      params = params.set('usuario_id', usuarioId.toString());
    }
    if (tabla) {
      params = params.set('tabla', tabla);
    }

    return this.http.get(`${API_URL}/bitacora`, { params });
  }
}
