"""
Monitoreo MEC — diagnóstico de activos eléctricos de CFE (SOLO edición MEC/CFE).

Integra el sistema "MEC Industrial Analytics Pro" (repo Prime119/ProyectoMEC). Al seleccionar
una subestación, torre, línea o estructura de CFE en el mapa 3D (módulo Falcon), se interpreta
su telemetría en tiempo real y se diagnostica su condición.

Este módulo implementa el CONTRATO de datos y el CLASIFICADOR DE CONDICIÓN (lógica pura y
testeable), reutilizando los umbrales y normas de ProyectoMEC:
  - Tensión nominal [110-140 V]
  - Frecuencia nominal [55-65 Hz]
  - THD: <5% OK, 5-8% aviso, >8% viola IEEE 519
  - Factor de potencia: >=0.92 OK, 0.85-0.92 aviso, <0.85 penalizable por CFE
  - Vibración (ISO 10816): <2.8 mm/s Zona A, 2.8-7.1 Zona B, >=7.1 Zona C/D (peligroso)
  - Temperatura: <50°C OK, 50-65°C monitoreo, >=65°C crítico

La conexión real con la consola (serial/COM o simulación) y la UI PyQt viven en ProyectoMEC;
aquí exponemos el diagnóstico para que MEC (el asistente) lo explique por voz/texto.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Condicion(Enum):
    BUENAS = "buenas"        # sin avisos ni errores, salud alta
    REGULARES = "regulares"  # algún aviso / salud media
    MALAS = "malas"          # salud baja / varios avisos
    PESIMAS = "pesimas"      # algún error crítico / salud muy baja


# Orden CSV que emite ProyectoMEC (emisor_simulado.py)
_PAYLOAD_ORDER = (
    "tension_v", "corriente_a", "vibracion_mms", "temperatura_c", "frecuencia_hz",
    "factor_potencia", "thd_pct", "potencia_activa_w", "potencia_reactiva_var",
    "potencia_aparente_va", "salud_pct",
)


@dataclass
class AssetReading:
    """Lectura de telemetría de un activo (subestación, motor, línea, torre…)."""
    tension_v: float = 127.2
    corriente_a: float = 18.5
    frecuencia_hz: float = 60.0
    factor_potencia: float = 0.88
    temperatura_c: float = 45.0
    vibracion_mms: float = 1.8
    thd_pct: float = 4.5
    potencia_activa_w: float = 2068.0
    potencia_reactiva_var: float = 1100.0
    potencia_aparente_va: float = 2353.0
    salud_pct: float = 95.0

    @classmethod
    def from_payload(cls, payload: str) -> "AssetReading":
        """Crea una lectura desde la línea CSV de 11 valores que emite ProyectoMEC."""
        parts = [p.strip() for p in payload.strip().split(",")]
        if len(parts) < len(_PAYLOAD_ORDER):
            raise ValueError(f"Payload incompleto: se esperaban {len(_PAYLOAD_ORDER)} valores.")
        values = {k: float(parts[i]) for i, k in enumerate(_PAYLOAD_ORDER)}
        return cls(**values)


@dataclass
class Diagnostico:
    condicion: Condicion
    salud_pct: float
    errores: list[str]
    advertencias: list[str]
    ok: list[str]

    @property
    def resumen(self) -> str:
        if self.errores:
            return f"{len(self.errores)} error(es) crítico(s)"
        if self.advertencias:
            return f"{len(self.advertencias)} advertencia(s)"
        return "sin observaciones"


def diagnosticar(r: AssetReading) -> Diagnostico:
    """Clasifica la condición del activo según los umbrales/normas de ProyectoMEC."""
    errores: list[str] = []
    advertencias: list[str] = []
    ok: list[str] = []

    # Tensión nominal
    if 110 <= r.tension_v <= 140:
        ok.append(f"Tensión {r.tension_v:.1f} V en rango [110-140 V]")
    else:
        errores.append(f"Tensión {r.tension_v:.1f} V FUERA de rango [110-140 V]")

    # Frecuencia nominal
    if r.frecuencia_hz > 0 and 55 <= r.frecuencia_hz <= 65:
        ok.append(f"Frecuencia {r.frecuencia_hz:.1f} Hz en rango [55-65 Hz]")
    elif r.frecuencia_hz > 0:
        errores.append(f"Frecuencia {r.frecuencia_hz:.1f} Hz FUERA de rango [55-65 Hz]")

    # THD (IEEE 519)
    if r.thd_pct < 5:
        ok.append(f"THD {r.thd_pct:.1f}% < 5% (IEEE 519 cumplido)")
    elif r.thd_pct < 8:
        advertencias.append(f"THD {r.thd_pct:.1f}% entre 5-8% (límite aceptable)")
    else:
        errores.append(f"THD {r.thd_pct:.1f}% > 8% (viola IEEE 519)")

    # Factor de potencia (CFE)
    if r.factor_potencia >= 0.92:
        ok.append(f"PF {r.factor_potencia:.3f} ≥ 0.92 (excelente)")
    elif r.factor_potencia >= 0.85:
        advertencias.append(f"PF {r.factor_potencia:.3f} entre 0.85-0.92 (mejorable)")
    else:
        errores.append(f"PF {r.factor_potencia:.3f} < 0.85 (penalizable por CFE)")

    # Vibración (ISO 10816)
    if r.vibracion_mms < 2.8:
        ok.append(f"Vibración {r.vibracion_mms:.2f} mm/s (ISO 10816 Zona A)")
    elif r.vibracion_mms < 7.1:
        advertencias.append(f"Vibración {r.vibracion_mms:.2f} mm/s (ISO 10816 Zona B)")
    else:
        errores.append(f"Vibración {r.vibracion_mms:.2f} mm/s (ISO 10816 Zona C/D, peligroso)")

    # Temperatura
    if r.temperatura_c < 50:
        ok.append(f"Temperatura {r.temperatura_c:.1f}°C nominal")
    elif r.temperatura_c < 65:
        advertencias.append(f"Temperatura {r.temperatura_c:.1f}°C en zona de monitoreo [50-65°C]")
    else:
        errores.append(f"Temperatura {r.temperatura_c:.1f}°C > 65°C (crítico)")

    condicion = _clasificar(r.salud_pct, errores, advertencias)
    return Diagnostico(condicion, r.salud_pct, errores, advertencias, ok)


def _clasificar(salud_pct: float, errores: list[str], advertencias: list[str]) -> Condicion:
    if errores or salud_pct < 40:
        return Condicion.PESIMAS
    if salud_pct < 60 or len(advertencias) >= 3:
        return Condicion.MALAS
    if advertencias or salud_pct < 85:
        return Condicion.REGULARES
    return Condicion.BUENAS


def explicar(d: Diagnostico, *, activo: str = "el activo") -> str:
    """Texto breve, estilo ingeniero MEC, para responder por voz/chat."""
    cabecera = {
        Condicion.BUENAS: f"🟢 {activo}: condición BUENA",
        Condicion.REGULARES: f"🟡 {activo}: condición REGULAR",
        Condicion.MALAS: f"🟠 {activo}: condición MALA",
        Condicion.PESIMAS: f"🔴 {activo}: condición PÉSIMA",
    }[d.condicion]
    lineas = [f"{cabecera} — salud {d.salud_pct:.0f}% ({d.resumen})."]
    if d.errores:
        lineas.append("Errores: " + "; ".join(d.errores))
    if d.advertencias:
        lineas.append("Avisos: " + "; ".join(d.advertencias))
    return "\n".join(lineas)
