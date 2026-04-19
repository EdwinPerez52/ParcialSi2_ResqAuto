import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class VehiculoService {

  constructor(private http: HttpClient) {}

  listar(): Observable<any> {
    return this.http.get(`${API_URL}/vehiculos`);
  }

  registrar(data: any): Observable<any> {
    return this.http.post(`${API_URL}/vehiculos`, data);
  }

  actualizar(placa: string, data: any): Observable<any> {
    return this.http.put(`${API_URL}/vehiculos/${placa}`, data);
  }

  eliminar(placa: string): Observable<any> {
    return this.http.delete(`${API_URL}/vehiculos/${placa}`);
  }
}
