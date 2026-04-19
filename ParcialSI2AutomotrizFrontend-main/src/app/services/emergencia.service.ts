import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class EmergenciaService {

  constructor(private http: HttpClient) {}

  solicitar(data: { latitud: number; longitud: number; descripcion: string; vehiculo_placa: string }): Observable<any> {
    return this.http.post(`${API_URL}/emergencias/solicitar`, data);
  }

  listar(estado?: string, pagina = 1, limite = 20): Observable<any> {
    let url = `${API_URL}/emergencias?pagina=${pagina}&limite=${limite}`;
    if (estado) url += `&estado=${estado}`;
    return this.http.get(url);
  }

  detalle(incidenteId: number): Observable<any> {
    return this.http.get(`${API_URL}/emergencias/${incidenteId}`);
  }

  aceptar(incidenteId: number, tecnicoId: number): Observable<any> {
    return this.http.post(`${API_URL}/emergencias/${incidenteId}/aceptar`, { tecnico_id: tecnicoId });
  }

  rechazar(incidenteId: number, motivo?: string): Observable<any> {
    return this.http.post(`${API_URL}/emergencias/${incidenteId}/rechazar`, { motivo });
  }

  actualizarEstado(incidenteId: number, estado: string, nota?: string): Observable<any> {
    return this.http.patch(`${API_URL}/emergencias/${incidenteId}/estado`, { estado, nota });
  }

  cancelar(incidenteId: number, motivo?: string): Observable<any> {
    return this.http.post(`${API_URL}/emergencias/${incidenteId}/cancelar`, { motivo });
  }

  reasignar(incidenteId: number): Observable<any> {
    return this.http.post(`${API_URL}/emergencias/${incidenteId}/reasignar`, {});
  }
}
