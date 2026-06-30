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
