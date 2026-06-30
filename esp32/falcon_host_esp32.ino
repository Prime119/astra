/* ============================================================================
   FALCON // HOST en ESP32
   Aloja el programa Falcon COMPLETO dentro del ESP32 (memoria flash LittleFS)
   y lo sirve por WiFi. Te conectas con tu celular/PC, abres la dirección y el
   navegador renderiza todo Falcon (mapa, hologramas, Núcleo MEC).

   El ESP32 es el "servidor"; el dispositivo que se conecta es quien dibuja.

   ---------------------------------------------------------------------------
   CÓMO INSTALAR LOS ARCHIVOS DENTRO DEL ESP32 (una sola vez):
   1. En tu sketch, crea una carpeta llamada  data/  junto a este .ino
   2. Copia DENTRO de data/ los archivos de la carpeta falcon/:
        data/index.html
        data/holo-lib.js
        data/sw.js
        data/estructuras-cfe-osm.csv   (opcional)
   3. Instala la herramienta "ESP32 LittleFS Data Upload" (o usa PlatformIO).
   4. Herramientas → "ESP32 Sketch Data Upload"  -> sube la carpeta data/ a la flash.
   5. Sube este sketch normalmente (botón Subir).
   ---------------------------------------------------------------------------

   NOTA: usa una partición con suficiente espacio para LittleFS:
   Herramientas → Partition Scheme → "No OTA (2MB APP/2MB SPIFFS)" o similar.
   ============================================================================ */
#include <WiFi.h>
#include <WebServer.h>
#include <LittleFS.h>

#define MODO_AP   true
const char* AP_SSID  = "FALCON";
const char* AP_PASS  = "cfe12345";       // mínimo 8 caracteres
const char* STA_SSID = "TU_WIFI";        // si MODO_AP=false (recomendado: red con internet para los mapas)
const char* STA_PASS = "TU_PASSWORD";

WebServer server(80);

String contentType(const String& path){
  if (path.endsWith(".html")) return "text/html";
  if (path.endsWith(".js"))   return "application/javascript";
  if (path.endsWith(".css"))  return "text/css";
  if (path.endsWith(".json")) return "application/json";
  if (path.endsWith(".csv"))  return "text/csv";
  if (path.endsWith(".png"))  return "image/png";
  if (path.endsWith(".jpg") || path.endsWith(".jpeg")) return "image/jpeg";
  if (path.endsWith(".svg"))  return "image/svg+xml";
  if (path.endsWith(".glb"))  return "model/gltf-binary";
  return "text/plain";
}

bool serveFile(String path){
  if (path.endsWith("/")) path += "index.html";
  if (LittleFS.exists(path)) {
    File f = LittleFS.open(path, "r");
    server.streamFile(f, contentType(path));
    f.close();
    return true;
  }
  return false;
}

void handleAny(){
  if (!serveFile(server.uri())) {
    // SPA fallback: si no existe la ruta, sirve index.html
    if (!serveFile("/index.html")) server.send(404, "text/plain", "No encontrado");
  }
}

void setup(){
  Serial.begin(115200);
  if (!LittleFS.begin(true)) { Serial.println("ERROR: no se pudo montar LittleFS"); }

  if (MODO_AP) {
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("AP \""); Serial.print(AP_SSID);
    Serial.print("\" listo. Abre http://"); Serial.println(WiFi.softAPIP());
  } else {
    WiFi.begin(STA_SSID, STA_PASS);
    Serial.print("Conectando");
    while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
    Serial.print("\nListo. Abre http://"); Serial.println(WiFi.localIP());
  }

  server.onNotFound(handleAny);
  server.on("/", [](){ handleAny(); });
  server.begin();
  Serial.println("Falcon servido desde el ESP32.");
}

void loop(){ server.handleClient(); }
