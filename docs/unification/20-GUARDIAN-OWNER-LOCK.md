# 20 — Guardián: Candado de Dueño + Anti-Robo / Anti-Manipulación

> Protección para que **solo el dueño** pueda modificar el sistema, una copia robada sea
> **inútil**, y si alguien altera el código sin autorización, el sistema **se bloquee**.
> Alinea con el "Latido Biométrico" (F.R.I.D.A.Y.), "Archivo Cero" (E.D.I.T.H.) y Zero-Trust (Cortana).

---

## ⚖️ La verdad técnica (sin humo)

| Lo que se pidió | ¿Posible? | Cómo se logra de verdad |
|---|---|---|
| Tu rostro como llave; solo tú modificas | ✅ Sí | Dueño enrolado; operaciones sensibles exigen rostro (Fase 5/7) |
| Copia robada inútil | ✅ Sí | El rostro/llaves viven **solo en tu dispositivo**, nunca en el repo |
| Si alteran el código, "se rompe" / no funciona | ✅ Sí | **Tamper-lock**: verificación de integridad firmada al arrancar |
| Dar acceso a otra persona (registrar su rostro) | ✅ Sí | Solo el dueño presente puede enrolar administradores |
| "Que no se pueda editar en ningún programa (VS Code…)" | ❌ No directo | El SO permite a cualquier editor escribir. **Equivalente real:** cifrado + tamper-lock → editarlo lo **rompe** |
| "Oculto aunque abran la programación" | ⚠️ Parcial | Ofuscar + compilar a binario (Nuitka/PyInstaller). **Ningún software es 100% irrompible.** |

> **Conclusión honesta:** podemos hacer que **robar o modificar el sistema sea inútil y se
> autobloquee sin ti** (tu meta). Pero "imposible de ver/romper al 100%" no existe en ningún
> software. Lo crítico —tu rostro y tus llaves **fuera del repositorio**— sí queda blindado.

---

## 🧱 Capas de protección

### 1. Manifiesto de integridad (implementado ✅)
`src/astra/core/guardian.py` calcula un **hash SHA-256** de cada archivo protegido:
- `src/astra/**/*.py`, `config/ethics_core.md`, `config/astra.config.json`, `config/editions/*.json`.
- Un **digest global** resume todo el código.

### 2. Sello del dueño (implementado ✅)
- El dueño "sella" el estado bueno conocido: `python -m astra --seal`.
- El **sello vive en el perfil local** (`astra-perfil-*/guardian.seal`), **NUNCA en el repo**.
- Modo desarrollo: **sin sello, no hay restricción** (para poder programar).

### 3. Tamper-lock al arrancar (implementado ✅)
En cada arranque, el Guardián verifica:
- Sin sellar → opera normal (desarrollo).
- Sellado y el código coincide → opera.
- Sellado y el código **NO** coincide → **se bloquea**… salvo que el **dueño esté presente**.

```
Arranque ──> Guardian.verify()
   ├─ sin sellar ............... opera (dev)
   ├─ sellado + íntegro ........ opera
   └─ sellado + ALTERADO
        ├─ dueño presente ...... permite (y el dueño puede re-sellar)
        └─ sin dueño ........... 🛑 BLOQUEADO (no funciona)
```

### 4. Presencia del dueño = rostro (futuro 🟡)
`Guardian.owner_present()`:
- **Hoy** (sin cámara): marcador de sesión de dueño (`ASTRA_OWNER=1`).
- **Futuro (Fase 5/7):** **reconocimiento facial en vivo** con cámara. La plantilla del rostro del
  dueño se enrola y se guarda **cifrada en el perfil local** (`owner.lock`), nunca en el repo.
- **Administradores adicionales** (`admins.lock`): el dueño, **estando presente**, puede autorizar el
  rostro de otra persona para darle acceso.

### 5. Anti-robo real (diseño, futuro 🟡)
- **Cifrado del sistema/perfil**: el código sensible/datos se guardan cifrados; la llave deriva del
  enrolamiento del dueño. Una copia robada **no descifra** sin el dueño → inútil.
- **Build protegido**: compilar a binario (Nuitka/PyInstaller) + ofuscación → el tamper-lock corre al
  iniciar; si manipulan el binario, **no arranca**.
- **Clean Slate / Archivo Cero**: ante intrusión persistente, aislar/borrar secretos locales
  (ya contemplado por la constitución, reglas 6 y 11).

---

## 🕹️ Comandos
```bash
python -m astra --verify   # ver estado de integridad (tamper-lock)
python -m astra --seal     # (DUEÑO) sellar el estado actual como bueno conocido
python -m astra --status   # incluye el bloque "guardian": {sealed, owner_present, integrity_ok…}
```

> Tras cambios **legítimos** del dueño, se vuelve a `--seal` para actualizar el sello.

---

## ✅ Verificado (sin cámara)
- Sin sellar → opera (modo desarrollo).
- Sellar → crea el sello local.
- Modificar un archivo protegido tras sellar → **bloqueo** ("Sistema bloqueado…").
- Con dueño presente (`ASTRA_OWNER=1`) → permite (y puede re-sellar).

## 🟡 Pendiente (necesita cámara / build)
- Reconocimiento facial del dueño como `owner_present()` real.
- Enrolamiento del rostro del dueño + administradores autorizados.
- Cifrado del perfil/código y build binario ofuscado.

> **Privacidad:** todo lo del dueño (rostro, llaves, sello) vive **solo en el dispositivo**, cifrado,
> **fuera del repositorio**. Clonar el código de GitHub no da acceso a nada de esto.
