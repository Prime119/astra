# FALCON // Núcleo MEC en ESP32

Firmware para monitorear **una estructura CFE en sitio** con un ESP32, con telemetría **real** de sensores. Sirve un panel HUD ligero y una API JSON que el mapa Falcon (en PC) puede leer.

## Qué hace
- Crea un WiFi propio **`FALCON-MEC`** (modo Access Point) o se conecta a tu WiFi.
- Sirve el panel en **`http://192.168.4.1/`** (en modo AP).
- Expone la telemetría en **`http://192.168.4.1/api/telemetry`** (JSON, CORS abierto).

## Cómo cargarlo (Arduino IDE)
1. Instala el **núcleo ESP32**: Archivo → Preferencias → URLs de gestor de tarjetas:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   Luego Herramientas → Placa → Gestor de tarjetas → instala **esp32**.
2. Selecciona tu placa (p. ej. *ESP32 Dev Module*) y el puerto COM.
3. Abre `falcon_mec_esp32.ino`, ajusta `NOMBRE_ESTRUCTURA` y, si quieres, el WiFi.
4. **Subir**. Abre el Monitor Serie (115200) para ver la IP.

## Probar sin sensores
Por defecto `HAY_SENSORES = false`: el ESP32 entrega datos **simulados** (marcados como tal) para que pruebes todo el flujo. Conéctate al WiFi `FALCON-MEC` (clave `cfe12345`) y abre `http://192.168.4.1/`.

## Conectar sensores reales (cuando los tengas)
Pon `HAY_SENSORES = true` y ajusta el escalado de cada pin a tu hardware:
| Magnitud | Sensor típico | Pin (ADC) |
|---|---|---|
| Tensión | Transformador de tensión / divisor | GPIO34 |
| Corriente | ACS712 (Hall) o TC + burden | GPIO35 |
| Temperatura | DS18B20 o LM35 | GPIO32 |
| Vibración | MPU6050 (I2C) o piezo | GPIO33 |

> Para THD/FP reales necesitas muestrear la onda y hacer FFT/cruce por cero; el sketch deja esos valores listos para que los calcules cuando integres el muestreo.

## Conectarlo al mapa Falcon (datos reales por estructura)
En el inventario CSV que cargas en Falcon (botón 📂 INVENTARIO), agrega una columna **`Device`** con la URL del ESP32 de ese punto. Ejemplo:

```
Nombre;Tipo;Estado;Voltaje;Operador;Lat;Lon;Device
S.E. Hermosillo;Subestación;Sonora;115000;CFE;29.07;-110.97;http://192.168.4.1/api/telemetry
```

Cuando abras el Núcleo MEC de esa estructura en el mapa, Falcon leerá la telemetría **real del ESP32** en vez de la simulada. Si el dispositivo no responde, vuelve a simulado automáticamente.

## Seguridad
- Cambia `AP_PASS` por una contraseña fuerte.
- Para uso en CFE, colócalo en una red autorizada y, si se requiere, agrega autenticación al endpoint.


---

# Opción 2: Alojar TODO Falcon dentro del ESP32 (`falcon_host_esp32.ino`)

Guarda el programa Falcon completo en la memoria del ESP32 y lo sirve por WiFi. Te conectas con tu celular/PC, abres la dirección y **el navegador renderiza Falcon completo** (mapa, hologramas, Núcleo MEC). El ESP32 es el servidor; el dispositivo que se conecta es quien dibuja (el ESP32 no puede renderizar 3D por sí solo).

### Pasos
1. Junto a `falcon_host_esp32.ino` crea una carpeta **`data/`**.
2. Copia dentro de `data/` los archivos de `falcon/`: `index.html`, `holo-lib.js`, `sw.js` y (opcional) `estructuras-cfe-osm.csv`.
3. Instala el plugin **"ESP32 LittleFS Data Upload"** (o usa PlatformIO).
4. Herramientas → **Partition Scheme** → elige uno con SPIFFS/LittleFS amplio (p. ej. *No OTA (2MB APP/2MB SPIFFS)*).
5. Herramientas → **ESP32 Sketch Data Upload** (sube la carpeta `data/`).
6. **Subir** el sketch.
7. Conéctate al WiFi `FALCON` y abre `http://192.168.4.1/`.

### Sobre los mapas (importante y honesto)
- Los **mosaicos del mapa** y los datos de OSM necesitan **internet** en el dispositivo que se conecta. Por eso, para uso real, conviene `MODO_AP=false` y poner el ESP32 en una **red con internet** (modo STA).
- Para uso **100% sin internet**, primero usa el botón **⬇ OFFLINE** (descarga la zona en el dispositivo) o, a futuro, una **microSD** con los mosaicos guardados (paso avanzado).
