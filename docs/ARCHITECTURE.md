# Arquitectura de Astra

Astra fusiona los patrones comunes de 16 IAs de ficción en un solo diseño coherente.
La idea central, repetida en casi todos los documentos de referencia, es:

> **El cerebro (LLM) piensa, pero NUNCA toca el hardware.** Propone acciones; un auditor
> independiente las revisa; y solo un ejecutor determinista las realiza, con confirmación
> humana para lo crítico.

## Flujo de una petición

```
  🎙️ Voz / texto
        │
        ▼
  [Capa 7] Atención por cámara  ── ¿me está hablando a mí?
        │
        ▼
  [Capa 6] Personalidad + contexto
        │
        ▼
  [Capa 2] Cerebro LLM  ── PROPONE una respuesta/acción
        │
        ▼
  [Capa 1] AUDITOR  ── revisa contra el núcleo ético (poder de veto)
        │
   ┌────┴─────┐
   │          │
 BLOCK     CONFIRM ── pide confirmación humana
   │          │
   │          ▼
   │     [Capa 3] EJECUTOR determinista (sandbox)
   │          │
   ▼          ▼
 explica   [Capa 4] MEMORIA registra (en el perfil)
            │
            ▼
        🔊 Voz (TTS) / interfaz de usuario
```

## Capa 0 — Núcleo ético inmutable
`config/ethics_core.md`, cargado en solo lectura con verificación de hash (Zero-Trust).
Es la "constitución" que ni el usuario ni Astra pueden cambiar en ejecución.

## Base inmutable vs. perfil escribible

```
Astra/
├── astra-base/      🔒 programa + modelos (solo lectura)
└── astra-perfil/    ✏️ memoria, aprendizajes, config (lo único que se modifica)
```

- Borrar el perfil = Astra "nueva".
- Llevar el perfil a otra Astra = continuidad.
- La base intacta = otro usuario puede tener su propio perfil sin afectar el original.

## Modos
- **Portátil**: todo en la SSD, no deja rastro en la PC.
- **Residente**: copiado a la PC, en segundo plano (tipo Siri/JARVIS), requiere permisos.

## Stack objetivo
- **Cerebro**: Ollama / llama.cpp con Qwen2.5 (general) y Qwen2.5-Coder (código). Boost
  opcional a la nube cuando hay internet.
- **Voz**: faster-whisper (STT) + Piper (TTS, voz femenina en español).
- **Memoria**: SQLite (corto plazo) + base vectorial / RAG (episódica).
- **Visión / 3D**: MediaPipe (rostro, mirada, manos). Interfaz por definir.
- **App**: interfaz gráfica de escritorio (no consola), empaquetada y portátil.
