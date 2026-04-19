import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class TallerService {

  constructor(private http: HttpClient) {}

  // Especialidades
  listarEspecialidades(): Observable<any> {
    return this.http.get(`${API_URL}/especialidades`);
  }

  obtenerEspecialidadesTaller(tallerId: number): Observable<any> {
    return this.http.get(`${API_URL}/taller/${tallerId}/especialidades`);
  }

  asignarEspecialidades(tallerId: number, especialidadIds: number[]): Observable<any> {
    return this.http.post(`${API_URL}/taller/${tallerId}/especialidades`, {
      especialidad_ids: especialidadIds
    });
  }

  // Técnicos
  listarTecnicos(tallerId: number): Observable<any> {
    return this.http.get(`${API_URL}/taller/${tallerId}/tecnicos`);
  }

  agregarTecnico(tallerId: number, data: any): Observable<any> {
    return this.http.post(`${API_URL}/taller/${tallerId}/tecnicos`, data);
  }

  actualizarTecnico(tallerId: number, tecnicoId: number, data: any): Observable<any> {
    return this.http.put(`${API_URL}/taller/${tallerId}/tecnicos/${tecnicoId}`, data);
  }

  eliminarTecnico(tallerId: number, tecnicoId: number): Observable<any> {
    return this.http.delete(`${API_URL}/taller/${tallerId}/tecnicos/${tecnicoId}`);
  }

  // Disponibilidad
  cambiarDisponibilidad(tecnicoId: number, estadisponible: boolean): Observable<any> {
    return this.http.patch(`${API_URL}/tecnicos/${tecnicoId}/disponibilidad`, { estadisponible });
  }
}
