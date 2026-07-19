<template>
  <div class="astra-app">
    <!-- Custom Titlebar -->
    <div class="titlebar">
      <div class="titlebar-title">
        <span class="logo">ASTRA</span>
        <span class="status" :class="{online: connected}">{{ connected ? 'En línea' : 'Conectando...' }}</span>
      </div>
      <div class="titlebar-controls">
        <button @click="minimize" class="tb-btn">─</button>
        <button @click="maximize" class="tb-btn">□</button>
        <button @click="closeWin" class="tb-btn close">✕</button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- 3D Orb (Babylon.js canvas) -->
      <canvas ref="babylonCanvas" class="orb-canvas"></canvas>

      <!-- Chat overlay -->
      <div class="chat-panel">
        <div class="messages" ref="messagesEl">
          <div v-for="(msg, i) in messages" :key="i" 
               class="message" :class="msg.type">
            {{ msg.text }}
          </div>
        </div>
      </div>

      <!-- Input bar -->
      <div class="input-bar">
        <button class="action-btn" :class="{active: micActive}" @click="toggleMic">🎙️</button>
        <button class="action-btn" :class="{active: convMode}" @click="toggleConv">💬</button>
        <input v-model="inputText" @keydown.enter="send" 
               placeholder="Escribe algo o activa el modo conversación..." 
               class="chat-input"/>
        <button class="send-btn" @click="send">ENVIAR</button>
        <button class="action-btn" :class="{active: camActive}" @click="toggleCam">📷</button>
        <button class="action-btn" :class="{active: vozActive}" @click="toggleVoz">{{ vozActive ? '🔊' : '🔇' }}</button>
      </div>

      <!-- Info bar -->
      <div class="info-bar">
        <span v-if="emotion">{{ emotionEmoji }} {{ emotion }}</span>
        <span>{{ time }}</span>
        <span>CPU {{ cpu }}%</span>
        <span>RAM {{ ram }}</span>
      </div>
    </div>

    <!-- Camera preview -->
    <video ref="camVideo" v-show="camActive" class="cam-preview" autoplay muted></video>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue'
import { gsap } from 'gsap'
import { initBabylonScene } from './components/DysonOrb.js'

export default {
  setup() {
    const babylonCanvas = ref(null)
    const messagesEl = ref(null)
    const camVideo = ref(null)
    const inputText = ref('')
    const messages = ref([])
    const connected = ref(false)
    const micActive = ref(false)
    const convMode = ref(false)
    const camActive = ref(false)
    const vozActive = ref(true)
    const emotion = ref('')
    const emotionEmoji = ref('😐')
    const time = ref('')
    const cpu = ref(0)
    const ram = ref('')

    let babylonScene = null
    let audioQueue = []
    let isPlaying = false

    // Backend URL
    const API = 'http://localhost:3000'

    onMounted(async () => {
      // Inicializar Babylon.js
      babylonScene = initBabylonScene(babylonCanvas.value)
      
      // Verificar conexión con backend
      checkConnection()
      setInterval(checkConnection, 10000)

      // Saludo inicial
      const h = new Date().getHours()
      let saludo = h >= 5 && h < 12 ? 'Buenos días, sistemas en línea.' :
                   h >= 12 && h < 19 ? 'Buenas tardes, todo operativo.' :
                   'Buenas noches, aquí estoy.'
      addMessage(saludo, 'astra')
      speak(saludo)
    })

    async function checkConnection() {
      try {
        const r = await fetch(`${API}/api/status`)
        const d = await r.json()
        connected.value = d.astra?.brain_local_online || false
        if (d.sistema) {
          time.value = d.sistema.hora
          cpu.value = d.sistema.cpu_uso
          ram.value = `${d.sistema.ram_usada_gb}/${d.sistema.ram_total_gb}GB`
        }
        if (d.astra?.emotions) {
          emotion.value = d.astra.emotions.descripcion
          const emojis = {neutral:'😐',feliz:'😊',emocionada:'🤩',divertida:'😄',curiosa:'🤔',
            apasionada:'🔥',triste:'😢',frustrada:'😤',enojada:'😠',preocupada:'😟'}
          emotionEmoji.value = emojis[d.astra.emotions.emocion] || '😐'
        }
      } catch(e) { connected.value = false }
    }

    function addMessage(text, type) {
      messages.value.push({ text, type })
      nextTick(() => {
        const el = messagesEl.value
        if (el) {
          el.scrollTop = el.scrollHeight
          // Animar entrada con GSAP
          const lastMsg = el.lastElementChild
          if (lastMsg) {
            gsap.from(lastMsg, { opacity: 0, y: 20, duration: 0.3, ease: 'power2.out' })
          }
        }
      })
    }

    async function send() {
      const text = inputText.value.trim()
      if (!text) return
      inputText.value = ''
      addMessage(text, 'user')
      
      // Orbe: pensar
      if (babylonScene) babylonScene.setState('thinking')

      try {
        const r = await fetch(`${API}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ texto: text })
        })
        const d = await r.json()
        
        // Orbe: hablar
        if (babylonScene) babylonScene.setState('speaking')
        addMessage(d.respuesta, 'astra')
        speak(d.respuesta, d.audio)

        // Simulación si hay
        if (d.simulacion) {
          // TODO: abrir panel de simulación Babylon.js
        }

        setTimeout(() => {
          if (babylonScene) babylonScene.setState('idle')
        }, 6000)
      } catch(e) {
        if (babylonScene) babylonScene.setState('idle')
        addMessage('Error de conexión con el cerebro.', 'system')
      }
    }

    function speak(text, audioUrl) {
      if (!vozActive.value) return
      audioQueue.push({ text, url: audioUrl })
      processAudioQueue()
    }

    function processAudioQueue() {
      if (isPlaying || audioQueue.length === 0) return
      isPlaying = true
      const item = audioQueue.shift()
      
      if (item.url) {
        const audio = new Audio(item.url.startsWith('http') ? item.url : `${API}${item.url}`)
        audio.playbackRate = 1.1
        audio.onended = () => { isPlaying = false; if(babylonScene) babylonScene.setState('idle'); processAudioQueue() }
        audio.onerror = () => { isPlaying = false; processAudioQueue() }
        audio.play().catch(() => { isPlaying = false; processAudioQueue() })
      } else {
        // Fallback browser TTS
        if (window.speechSynthesis) {
          const u = new SpeechSynthesisUtterance(item.text)
          u.lang = 'es-MX'; u.rate = 1.1; u.pitch = 1.15
          u.onend = () => { isPlaying = false; processAudioQueue() }
          speechSynthesis.speak(u)
        } else { isPlaying = false; processAudioQueue() }
      }
    }

    function toggleMic() { micActive.value = !micActive.value }
    function toggleConv() { convMode.value = !convMode.value }
    function toggleCam() {
      camActive.value = !camActive.value
      if (camActive.value) {
        navigator.mediaDevices.getUserMedia({ video: true }).then(s => {
          camVideo.value.srcObject = s
        }).catch(() => { camActive.value = false })
      } else {
        const s = camVideo.value?.srcObject
        if (s) s.getTracks().forEach(t => t.stop())
      }
    }
    function toggleVoz() { vozActive.value = !vozActive.value }

    // Electron window controls
    function minimize() { if(window.require) window.require('electron').ipcRenderer.send('window-minimize') }
    function maximize() { if(window.require) window.require('electron').ipcRenderer.send('window-maximize') }
    function closeWin() { if(window.require) window.require('electron').ipcRenderer.send('window-close') }

    return {
      babylonCanvas, messagesEl, camVideo, inputText, messages, connected,
      micActive, convMode, camActive, vozActive, emotion, emotionEmoji,
      time, cpu, ram, send, toggleMic, toggleConv, toggleCam, toggleVoz,
      minimize, maximize, closeWin
    }
  }
}
</script>

<style>
.astra-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #030608;
  color: #e4ecf5;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

/* Titlebar */
.titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(3,6,8,0.95);
  -webkit-app-region: drag;
  border-bottom: 1px solid rgba(79,195,247,0.06);
}
.titlebar-title { display: flex; align-items: center; gap: 12px; }
.logo { color: #4fc3f7; font-size: 14px; font-weight: 700; letter-spacing: 4px; text-shadow: 0 0 10px rgba(79,195,247,0.3); }
.status { font-size: 10px; color: #8a9bb0; }
.status.online { color: #4fc3f7; }
.status.online::before { content: '●'; margin-right: 4px; }
.titlebar-controls { display: flex; gap: 4px; -webkit-app-region: no-drag; }
.tb-btn { background: rgba(255,255,255,0.05); border: none; color: #8a9bb0; width: 32px; height: 24px; border-radius: 4px; cursor: pointer; font-size: 11px; }
.tb-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.tb-btn.close:hover { background: #e53935; color: #fff; }

/* Main Content */
.main-content { flex: 1; position: relative; overflow: hidden; }

/* Babylon Canvas */
.orb-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }

/* Chat Panel */
.chat-panel { position: relative; z-index: 5; height: calc(100% - 110px); display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 20px 30px; display: flex; flex-direction: column; gap: 10px; }
.messages::-webkit-scrollbar { width: 3px; }
.messages::-webkit-scrollbar-thumb { background: rgba(79,195,247,0.15); border-radius: 3px; }
.message { max-width: 65%; padding: 12px 18px; border-radius: 16px; font-size: 13.5px; line-height: 1.6; }
.message.user { align-self: flex-end; background: rgba(79,195,247,0.06); border: 1px solid rgba(79,195,247,0.12); border-bottom-right-radius: 3px; }
.message.astra { align-self: flex-start; background: rgba(10,20,35,0.85); border: 1px solid rgba(79,195,247,0.08); border-bottom-left-radius: 3px; backdrop-filter: blur(8px); }
.message.system { align-self: center; font-size: 10px; opacity: 0.4; font-style: italic; }

/* Input Bar */
.input-bar { position: absolute; bottom: 35px; left: 0; right: 0; padding: 12px 24px; display: flex; gap: 8px; align-items: center; z-index: 10; background: rgba(3,6,8,0.8); backdrop-filter: blur(12px); border-top: 1px solid rgba(79,195,247,0.06); }
.chat-input { flex: 1; background: rgba(10,18,28,0.7); border: 1px solid rgba(79,195,247,0.08); color: #e4ecf5; padding: 11px 16px; border-radius: 12px; font-size: 13px; outline: none; transition: 0.2s; }
.chat-input:focus { border-color: rgba(79,195,247,0.25); box-shadow: 0 0 0 2px rgba(79,195,247,0.04); }
.action-btn { background: rgba(10,18,28,0.6); border: 1px solid rgba(79,195,247,0.1); color: #4fc3f7; width: 38px; height: 38px; border-radius: 10px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
.action-btn:hover { border-color: rgba(79,195,247,0.3); background: rgba(79,195,247,0.04); }
.action-btn.active { background: rgba(79,195,247,0.1); border-color: #4fc3f7; box-shadow: 0 0 8px rgba(79,195,247,0.15); }
.send-btn { background: linear-gradient(135deg, #4fc3f7, #0288d1); color: #fff; border: none; padding: 10px 18px; border-radius: 10px; font-weight: 600; cursor: pointer; font-size: 11.5px; letter-spacing: 0.5px; box-shadow: 0 2px 12px rgba(79,195,247,0.2); }
.send-btn:hover { filter: brightness(1.1); box-shadow: 0 4px 20px rgba(79,195,247,0.3); }

/* Info Bar */
.info-bar { position: absolute; bottom: 0; left: 0; right: 0; padding: 6px 24px; display: flex; gap: 12px; font-size: 9.5px; color: #6a7b8a; justify-content: center; z-index: 10; }
.info-bar span { padding: 2px 8px; background: rgba(10,18,28,0.4); border-radius: 3px; }

/* Camera */
.cam-preview { position: fixed; top: 45px; left: 16px; width: 140px; height: 105px; border-radius: 8px; border: 1px solid rgba(79,195,247,0.15); opacity: 0.8; z-index: 20; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
</style>
