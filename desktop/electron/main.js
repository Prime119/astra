const { app, BrowserWindow, Tray, Menu, ipcMain, session, nativeImage } = require('electron')
const path = require('path')
const fs = require('fs')
const { spawn } = require('child_process')

// === HABILITAR SPEECH RECOGNITION EN ELECTRON ===
app.commandLine.appendSwitch('enable-speech-dispatcher')
app.commandLine.appendSwitch('enable-features', 'WebSpeechAPI')
app.commandLine.appendSwitch('enable-web-speech-api')

// Suprimir errores de pipe rotos
process.on('uncaughtException', (err) => {
  if (err.code === 'EPIPE' || err.message.includes('EPIPE')) return
  console.error('Error:', err.message)
})

let mainWindow
let tray = null
let pythonProcess
let setupProcess
let isQuitting = false

// === PATHS ===
const ASTRA_ROOT = path.join(__dirname, '../..')
const CONFIG_DIR = path.join(ASTRA_ROOT, 'config')
const MODELS_DIR = path.join(ASTRA_ROOT, 'models')
const NEEDS_SETUP_FILE = path.join(CONFIG_DIR, '.needs_setup')
const INSTALLER_STATE_FILE = path.join(CONFIG_DIR, '.installer_state.json')

// === SINGLE INSTANCE LOCK ===
// Solo una instancia de Astra puede correr a la vez
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    // Si intentan abrir otra instancia, mostrar la ventana existente
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

// === FIRST-RUN DETECTION ===
function needsFirstRun() {
  if (fs.existsSync(NEEDS_SETUP_FILE)) return true

  if (!fs.existsSync(INSTALLER_STATE_FILE)) {
    if (fs.existsSync(MODELS_DIR)) {
      const files = fs.readdirSync(MODELS_DIR).filter(f => f.endsWith('.gguf'))
      if (files.length > 0) return false
    }
    return true
  }

  try {
    const state = JSON.parse(fs.readFileSync(INSTALLER_STATE_FILE, 'utf8'))
    return !state.first_run_complete
  } catch (e) {
    return true
  }
}

function getPythonPath() {
  const embeddedPython = path.join(ASTRA_ROOT, 'python', 'python.exe')
  if (fs.existsSync(embeddedPython)) return embeddedPython
  return process.platform === 'win32' ? 'python' : 'python3'
}

// === FIRST-RUN SETUP ===
function runFirstTimeSetup() {
  return new Promise((resolve) => {
    console.log('[Astra] First-run — launching model selector...')
    const pythonPath = getPythonPath()
    const setupScript = path.join(ASTRA_ROOT, 'installer', 'first_run.py')

    if (!fs.existsSync(setupScript)) {
      console.log('[Astra] Setup script not found, skipping.')
      resolve(false)
      return
    }

    setupProcess = spawn(pythonPath, [setupScript], {
      cwd: ASTRA_ROOT,
      env: { ...process.env, ASTRA_MODE: 'desktop' },
      stdio: ['pipe', 'pipe', 'pipe']
    })

    setupProcess.stdout.on('data', (data) => {
      const msg = data.toString().trim()
      if (msg) console.log(`[Setup] ${msg}`)
    })
    setupProcess.stderr.on('data', (data) => {
      const msg = data.toString().trim()
      if (msg) console.error(`[Setup] ${msg}`)
    })
    setupProcess.on('close', (code) => {
      try { if (fs.existsSync(NEEDS_SETUP_FILE)) fs.unlinkSync(NEEDS_SETUP_FILE) } catch (e) {}
      setupProcess = null
      resolve(code === 0)
    })
    setupProcess.on('error', (err) => {
      console.error(`[Astra] Setup error: ${err.message}`)
      setupProcess = null
      resolve(false)
    })
  })
}

// === SYSTEM TRAY ===
function createTray() {
  // Intentar cargar icono, usar uno por defecto si no existe
  let iconPath = path.join(__dirname, '../public/icon.png')
  if (!fs.existsSync(iconPath)) {
    // Crear un icono mínimo en memoria (16x16 azul)
    iconPath = null
  }

  let trayIcon
  if (iconPath) {
    trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  } else {
    // Icono fallback: un cuadrado azul 16x16
    trayIcon = nativeImage.createEmpty()
  }

  tray = new Tray(trayIcon)
  tray.setToolTip('Astra — IA Personal (corriendo en segundo plano)')

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Abrir Astra',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        } else {
          createWindow()
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Gestionar Modelos',
      click: () => {
        const pythonPath = getPythonPath()
        spawn(pythonPath, ['-m', 'installer.first_run', '--manage'], {
          cwd: ASTRA_ROOT,
          env: { ...process.env, ASTRA_MODE: 'desktop' },
          stdio: 'inherit'
        })
      }
    },
    { type: 'separator' },
    {
      label: 'Salir completamente',
      click: () => {
        isQuitting = true
        if (pythonProcess) {
          pythonProcess.kill()
          pythonProcess = null
        }
        app.quit()
      }
    }
  ])

  tray.setContextMenu(contextMenu)

  // Doble clic en el tray → mostrar ventana
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus()
    } else {
      createWindow()
    }
  })
}

// === WINDOW CREATION ===
function createWindow() {
  if (mainWindow) {
    mainWindow.show()
    mainWindow.focus()
    return
  }

  Menu.setApplicationMenu(null)

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 600,
    minHeight: 500,
    frame: true,
    transparent: false,
    backgroundColor: '#030608',
    icon: path.join(__dirname, '../public/icon.png'),
    alwaysOnTop: false,
    resizable: true,
    movable: true,
    title: 'ASTRA',
    show: false, // No mostrar hasta que cargue
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })

  mainWindow.maximize()

  // Permisos de micrófono y cámara
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowed = ['media', 'mediaKeySystem', 'geolocation', 'notifications', 'midi', 'pointerLock', 'fullscreen']
    callback(allowed.includes(permission))
  })

  // Cargar la interfaz web
  mainWindow.loadURL('http://localhost:3000', {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
  })

  // Mostrar cuando esté listo
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  // MINIMIZAR AL TRAY en vez de cerrar (segundo plano)
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow.hide()
      // Notificar al usuario la primera vez
      if (tray) {
        tray.displayBalloon({
          title: 'Astra sigue activa',
          content: 'Astra está corriendo en segundo plano. Haz doble clic en el icono del tray para abrir.',
          noSound: true
        })
      }
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// === SPLASH WINDOW ===
function createSplashWindow() {
  const splash = new BrowserWindow({
    width: 500,
    height: 350,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  })

  const splashHTML = `
    <html>
    <body style="margin:0; display:flex; align-items:center; justify-content:center; 
                 height:100vh; background: rgba(10,14,20,0.95); border-radius:16px;
                 border: 1px solid #1e2a38; font-family: 'Segoe UI', sans-serif;">
      <div style="text-align:center; color:#e0e8f0;">
        <h1 style="color:#00d4ff; font-size:32px; margin-bottom:8px;">ASTRA</h1>
        <p style="color:#7a8a9a; font-size:14px;">Configurando modelos de IA...</p>
        <div style="margin-top:24px; width:200px; height:4px; background:#1e2a38; 
                    border-radius:2px; margin:24px auto 0;">
          <div style="width:60%; height:100%; background:#00d4ff; border-radius:2px;
                      animation: pulse 1.5s ease-in-out infinite;"></div>
        </div>
        <p style="color:#4a5a6a; font-size:11px; margin-top:16px;">Esto solo ocurre la primera vez</p>
      </div>
    </body>
    <style>@keyframes pulse { 0%,100%{width:30%} 50%{width:80%} }</style>
    </html>`

  splash.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHTML))
  return splash
}

// === PYTHON BACKEND ===
function startPythonBackend() {
  const pythonPath = getPythonPath()
  const scriptPath = path.join(ASTRA_ROOT, 'web', 'servidor.py')

  pythonProcess = spawn(pythonPath, [scriptPath], {
    cwd: ASTRA_ROOT,
    env: { ...process.env, ASTRA_MODE: 'desktop' },
    stdio: ['pipe', 'pipe', 'pipe']
  })

  pythonProcess.stdout.on('data', (data) => {
    try { process.stdout.write(`[Python] ${data.toString().trim()}\n`) } catch(e) {}
  })
  pythonProcess.stderr.on('data', (data) => {
    try { process.stderr.write(`[Python] ${data.toString().trim()}\n`) } catch(e) {}
  })
  pythonProcess.on('error', (err) => {
    console.error('Error al iniciar Python:', err.message)
  })
  pythonProcess.on('close', (code) => {
    console.log(`[Python] Backend terminó con código ${code}`)
    pythonProcess = null
  })
}

// Wait for backend
function waitForBackend(timeoutMs = 15000) {
  return new Promise((resolve) => {
    const start = Date.now()
    const http = require('http')
    const check = () => {
      if (Date.now() - start > timeoutMs) { resolve(false); return }
      const req = http.get('http://localhost:3000/api/status', (res) => {
        resolve(res.statusCode === 200)
      })
      req.on('error', () => setTimeout(check, 500))
      req.setTimeout(2000, () => { req.destroy(); setTimeout(check, 500) })
    }
    setTimeout(check, 1000)
  })
}

// === IPC HANDLERS ===
ipcMain.on('window-minimize', () => mainWindow?.minimize())
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize()
  else mainWindow?.maximize()
})
ipcMain.on('window-close', () => mainWindow?.close())

ipcMain.on('open-simulation', (event, simUrl) => {
  const simWindow = new BrowserWindow({
    width: 600, height: 500, minWidth: 400, minHeight: 350,
    frame: true, title: 'ASTRA — Simulación 3D',
    backgroundColor: '#030608', resizable: true,
    parent: mainWindow,
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  })
  simWindow.loadURL(simUrl || 'http://localhost:3000')
})

ipcMain.handle('get-model-status', async () => {
  try {
    const http = require('http')
    return new Promise((resolve) => {
      http.get('http://localhost:3000/api/status', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => {
          try { resolve(JSON.parse(data)) } catch (e) { resolve({ error: 'parse error' }) }
        })
      }).on('error', () => resolve({ error: 'not available' }))
    })
  } catch (e) { return { error: e.message } }
})

ipcMain.on('open-model-manager', () => {
  const pythonPath = getPythonPath()
  spawn(pythonPath, ['-m', 'installer.first_run', '--manage'], {
    cwd: ASTRA_ROOT, env: { ...process.env, ASTRA_MODE: 'desktop' }, stdio: 'inherit'
  })
})

// === APP LIFECYCLE ===
app.whenReady().then(async () => {
  // Crear system tray PRIMERO (siempre en segundo plano)
  createTray()

  // First-run setup si es necesario
  if (needsFirstRun()) {
    console.log('[Astra] First-run setup needed')
    const splash = createSplashWindow()
    try {
      await runFirstTimeSetup()
    } catch (e) {
      console.error(`[Astra] Setup error: ${e.message}`)
    }
    if (splash && !splash.isDestroyed()) splash.close()
  }

  // Iniciar backend Python
  startPythonBackend()

  // Esperar backend
  console.log('[Astra] Waiting for backend...')
  await waitForBackend(15000)

  // Abrir ventana principal
  createWindow()
})

// NO cerrar la app cuando se cierran las ventanas — sigue en tray
app.on('window-all-closed', () => {
  // No hacer nada — Astra sigue en segundo plano (system tray)
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', () => {
  isQuitting = true
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
  if (setupProcess) { setupProcess.kill(); setupProcess = null }
})
