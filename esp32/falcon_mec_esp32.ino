/* ============================================================================
   FALCON // NÚCLEO MEC — Firmware ESP32
   Monitoreo en sitio de una estructura CFE con telemetría REAL.

   Qué hace:
   - Crea un WiFi (modo Access Point por defecto) llamado "FALCON-MEC".
   - Sirve un panel de monitoreo ligero (HUD cian) en  http://192.168.4.1/
   - Expone la telemetría en  http://192.168.4.1/api/telemetry  (JSON, CORS abierto)
     para que el mapa Falcon (en una PC) pueda leer los datos reales de este punto.

   Sensores (ejemplos típicos — ajusta a tu hardware):
   - Tensión:    divisor resistivo / transformador de tensión -> ADC (GPIO34)
   - Corriente:  sensor de efecto Hall ACS712 o TC (CT) -> ADC (GPIO35)
   - Temperatura: DS18B20 o sensor analógico -> ADC (GPIO32)
   - Vibración:  acelerómetro (MPU6050 por I2C) o piezo -> ADC (GPIO33)

   Si no hay sensores conectados, usa valores simulados (marcados como SIMULADO)
   para que puedas probar el flujo completo antes de cablear.

   Requiere: placa "ESP32" en Arduino IDE (Núcleo de Espressif).
   ============================================================================ */
#include <WiFi.h>
#include <WebServer.h>

// ---------- Configuración ----------
#define MODO_AP   true                 // true = crea su propia red; false = se conecta a tu WiFi
const char* AP_SSID   = "FALCON-MEC";
const char* AP_PASS   = "cfe12345";    // mínimo 8 caracteres
const char* STA_SSID  = "TU_WIFI";     // sólo si MODO_AP=false
const char* STA_PASS  = "TU_PASSWORD";

const char* NOMBRE_ESTRUCTURA = "S.E. Hermosillo";   // nombre del activo monitoreado
const char* TIPO_ESTRUCTURA   = "Subestacion";

// Pines de sensores (ajusta a tu cableado)
const int PIN_TENSION = 34;
const int PIN_CORRIENTE = 35;
const int PIN_TEMP = 32;
const int PIN_VIB = 33;

#define HAY_SENSORES false             // pon true cuando ya tengas sensores físicos

WebServer server(80);

// ---------- Lectura de telemetría ----------
struct Telemetria { float v, i, freq, pf, thd, vib, temp, salud; };

float leerEscalado(int pin, float vmin, float vmax){
  // ADC del ESP32: 0..4095 -> escala al rango físico del sensor
  int raw = analogRead(pin);
  return vmin + (raw / 4095.0f) * (vmax - vmin);
}

Telemetria leerTelemetria(){
  Telemetria t;
  if (HAY_SENSORES) {
    t.v    = leerEscalado(PIN_TENSION, 0, 140);     // V (ajusta a tu divisor/TT)
    t.i    = leerEscalado(PIN_CORRIENTE, 0, 60);    // A (ajusta a tu CT/ACS712)
    t.temp = leerEscalado(PIN_TEMP, 0, 120);        // °C
    t.vib  = leerEscalado(PIN_VIB, 0, 12);          // mm/s
    t.freq = 60.0f;                                 // mide con cruce por cero si lo deseas
    t.pf   = 0.95f;                                 // calcula con desfase V/I
    t.thd  = 3.0f;                                  // calcula con FFT si tienes muestreo
  } else {
    // SIMULADO (para probar sin sensores)
    float r = random(0, 1000) / 1000.0f;
    t.temp = 42 + random(0, 80) / 10.0f;
    t.vib  = 0.8f + random(0, 160) / 100.0f;
    t.thd  = 2 + random(0, 250) / 100.0f;
    t.pf   = 0.91f + random(0, 70) / 1000.0f;
    t.salud= 86 + random(0, 120) / 10.0f;
    if (r > 0.9f) { t.temp = 60 + random(0,180)/10.0f; t.vib = 4 + random(0,400)/100.0f; t.thd = 6 + random(0,600)/100.0f; t.salud = 45 + random(0,300)/10.0f; }
    t.v = 120 + random(0, 120) / 10.0f;
    t.i = 10 + random(0, 450) / 10.0f;
    t.freq = 59.8f + random(0, 40) / 100.0f;
    return t;
  }
  // salud estimada a partir de los parámetros
  float s = 100;
  if (t.temp > 55) s -= (t.temp - 55) * 1.5f;
  if (t.vib  > 2.8) s -= (t.vib - 2.8) * 6;
  if (t.thd  > 5)   s -= (t.thd - 5) * 2;
  if (t.pf   < 0.9) s -= (0.9 - t.pf) * 100;
  t.salud = s < 0 ? 0 : (s > 100 ? 100 : s);
  return t;
}

String condicion(const Telemetria& t){
  if (t.salud >= 85 && t.temp < 55 && t.vib < 2.8 && t.thd < 5) return "buenas";
  if (t.salud >= 65 && t.temp < 65 && t.vib < 4.5 && t.thd < 8) return "regulares";
  if (t.salud >= 40) return "malas";
  return "pesimas";
}

String telemetriaJSON(){
  Telemetria t = leerTelemetria();
  String c = condicion(t);
  String s = "{";
  s += "\"nombre\":\"" + String(NOMBRE_ESTRUCTURA) + "\",";
  s += "\"tipo\":\"" + String(TIPO_ESTRUCTURA) + "\",";
  s += "\"v\":" + String(t.v,1) + ",";
  s += "\"i\":" + String(t.i,1) + ",";
  s += "\"freq\":" + String(t.freq,2) + ",";
  s += "\"pf\":" + String(t.pf,3) + ",";
  s += "\"thd\":" + String(t.thd,1) + ",";
  s += "\"vib\":" + String(t.vib,2) + ",";
  s += "\"temp\":" + String(t.temp,1) + ",";
  s += "\"salud\":" + String(t.salud,0) + ",";
  s += "\"cond\":\"" + c + "\",";
  s += "\"fuente\":\"" + String(HAY_SENSORES ? "sensores" : "simulado") + "\"";
  s += "}";
  return s;
}

// ---------- Panel web (HUD ligero) servido desde el ESP32 ----------
const char INDEX_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NÚCLEO MEC · ESP32</title><style>
:root{--hud:#22d3ee;--glow:#67e8f9;--bg:#040810;--mut:#7c8da0;--good:#10b981;--warn:#facc15;--bad:#f97316;--crit:#ef4444;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#cdeffb;font-family:Consolas,monospace}
.bar{padding:10px 14px;border-bottom:1px solid #0e7490;display:flex;gap:10px;align-items:center}
.bar b{color:var(--glow);letter-spacing:2px}.bar .n{color:#e5f6ff;font-weight:bold}.bar .t{color:var(--mut);font-size:12px}
.cond{margin-left:auto;font-weight:bold;padding:3px 10px;border-radius:5px;font-size:12px}
.wrap{padding:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:680px;margin:auto}
.card{background:rgba(7,20,32,.8);border:1px solid #0e7490;border-radius:8px;padding:10px 12px}
.card h4{margin:0 0 8px;color:var(--glow);font-size:11px;letter-spacing:1px}
.row{display:flex;justify-content:space-between;font-size:13px;margin:5px 0}.row .k{color:var(--mut)}.row .v{font-weight:bold}
canvas{width:100%;height:120px;display:block}.full{grid-column:1/3}
.mec{grid-column:1/3;background:rgba(7,20,32,.8);border:1px solid #0e7490;border-left:3px solid var(--hud);border-radius:6px;padding:10px 12px;font-size:13px;line-height:1.4}
.mec b{color:var(--glow)} .src{font-size:11px;color:var(--mut)}
</style></head><body>
<div class="bar"><b>◆ NÚCLEO MEC</b><span class="n" id="nm">—</span><span class="t" id="tp"></span><span class="cond" id="cd">—</span></div>
<div class="wrap">
 <div class="card full"><h4>OSCILOGRAMA · V / I</h4><canvas id="osc"></canvas></div>
 <div class="card"><h4>PARÁMETROS</h4>
   <div class="row"><span class="k">Tensión</span><span class="v" id="v">—</span></div>
   <div class="row"><span class="k">Corriente</span><span class="v" id="i">—</span></div>
   <div class="row"><span class="k">Frecuencia</span><span class="v" id="f">—</span></div>
   <div class="row"><span class="k">F. potencia</span><span class="v" id="pf">—</span></div>
 </div>
 <div class="card"><h4>CONDICIÓN</h4>
   <div class="row"><span class="k">THD</span><span class="v" id="thd">—</span></div>
   <div class="row"><span class="k">Vibración</span><span class="v" id="vib">—</span></div>
   <div class="row"><span class="k">Temperatura</span><span class="v" id="tmp">—</span></div>
   <div class="row"><span class="k">Salud</span><span class="v" id="sl">—</span></div>
 </div>
 <div class="mec"><b>MEC:</b> <span id="mec">Conectando…</span><div class="src" id="src"></div></div>
</div>
<script>
var ph=0, live=null;
var COL={buenas:'#10b981',regulares:'#facc15',malas:'#f97316',pesimas:'#ef4444'};
var TXT={buenas:'🟢 BUENAS',regulares:'🟡 REGULARES',malas:'🟠 MALAS',pesimas:'🔴 PÉSIMAS'};
function mec(d){var n=d.nombre;
 if(d.cond=='buenas')return 'Todo en orden con '+n+'. Tensión, frecuencia y factor de potencia dentro de norma; la salud se mantiene alta. No hace falta intervenir.';
 if(d.cond=='regulares')return n+' opera, pero la estoy vigilando de cerca: hay parámetros al límite. Conviene una revisión preventiva.';
 if(d.cond=='malas')return 'Ojo con '+n+': parámetros degradados. Recomiendo revisarla en el próximo turno.';
 return 'Alerta seria en '+n+': condiciones críticas. Hay que intervenir de inmediato.';}
function pull(){fetch('/api/telemetry').then(r=>r.json()).then(d=>{live=d;
 document.getElementById('nm').textContent=d.nombre;document.getElementById('tp').textContent='· '+d.tipo;
 var cd=document.getElementById('cd');cd.textContent=TXT[d.cond]+' · salud '+d.salud+'%';cd.style.background=COL[d.cond]+'22';cd.style.color=COL[d.cond];cd.style.border='1px solid '+COL[d.cond];
 document.getElementById('v').textContent=d.v+' V';document.getElementById('i').textContent=d.i+' A';
 document.getElementById('f').textContent=d.freq+' Hz';document.getElementById('pf').textContent=d.pf;
 document.getElementById('thd').textContent=d.thd+' %';document.getElementById('vib').textContent=d.vib+' mm/s';
 document.getElementById('tmp').textContent=d.temp+' °C';document.getElementById('sl').textContent=d.salud+' %';
 document.getElementById('mec').textContent=mec(d);document.getElementById('src').textContent='Fuente: '+d.fuente.toUpperCase();
}).catch(()=>{});}
function draw(){requestAnimationFrame(draw);ph+=0.06;if(!live)return;
 var c=document.getElementById('osc');var dpr=devicePixelRatio||1;var r=c.getBoundingClientRect();
 if(c.width!=r.width*dpr){c.width=r.width*dpr;c.height=r.height*dpr;}var x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);
 var w=r.width,h=r.height;x.clearRect(0,0,w,h);x.strokeStyle='rgba(34,211,238,.1)';for(var gy=0;gy<=h;gy+=h/4){x.beginPath();x.moveTo(0,gy);x.lineTo(w,gy);x.stroke();}
 var mid=h/2,va=h*.34,ia=h*.30*Math.min(1.1,Math.max(.25,live.i/45)),pf=Math.acos(Math.min(1,live.pf)),td=live.thd/100;
 x.lineWidth=2;x.strokeStyle='#22d3ee';x.beginPath();for(var px=0;px<=w;px++){var a=px/w*3*6.283+ph;var y=mid-Math.sin(a)*va;px?x.lineTo(px,y):x.moveTo(px,y);}x.stroke();
 x.strokeStyle='#facc15';x.beginPath();for(var px2=0;px2<=w;px2++){var a2=px2/w*3*6.283+ph-pf;var ff=Math.sin(a2)+td*Math.sin(3*a2);var y2=mid-ff*ia;px2?x.lineTo(px2,y2):x.moveTo(px2,y2);}x.stroke();}
pull();setInterval(pull,1000);draw();
</script></body></html>
)HTML";

void handleRoot(){ server.send_P(200, "text/html", INDEX_HTML); }
void handleTelemetry(){
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", telemetriaJSON());
}

void setup(){
  Serial.begin(115200);
  analogReadResolution(12);
  if (MODO_AP) {
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("AP listo. Conéctate a la red \""); Serial.print(AP_SSID);
    Serial.print("\" y abre http://"); Serial.println(WiFi.softAPIP());
  } else {
    WiFi.begin(STA_SSID, STA_PASS);
    Serial.print("Conectando a WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
    Serial.print("\nListo. Abre http://"); Serial.println(WiFi.localIP());
  }
  server.on("/", handleRoot);
  server.on("/api/telemetry", handleTelemetry);
  server.begin();
}

void loop(){ server.handleClient(); }
