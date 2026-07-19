const { app, BrowserWindow, ipcMain, Menu, session } = require('electron')
const path = require('path')
const fs = require('fs')
const { spawn, execSync } = require('child_process')

// === HABILITAR SPEECH RECOGNITION EN ELECTRON ===
app.commandLine.appendSwitch('enable-speech-dispatcher')
app.commandLine.appendSwitch('enable-features', 'WebSpeechAPI')
app.commandLine.appendSwitch('enable-web-speech-api')

// Suprimir errores de pipe rotos (son inofensivos)
process.on('uncaughtException', (err) => {
  if (err.code === 'EPIPE' || err.message.includes('EPIPE')) return
  console.error('Error:', err.message)
})

let mainWindow
let pythonProcess
let setupProcess

// === PATHS ===
const ASTRA_ROOT = path.join(__dirname, '../..')
const CONFIG_DIR = path.join(ASTRA_ROOT, 'config')
const MODELS_DIR = path.join(ASTRA_ROOT, 'models')
const NEEDS_SETUP_FILE = path.join(CONFIG_DIR, '.needs_setup')
const INSTALLER_STATE_FILE = path.join(CONFIG_DIR, '.installer_state.json')

// === FIRST-RUN DETECTION ===
function needsFirstRun() {
  // Check 1: Explicit marker file from installer
  if (fs.existsSync(NEEDS_SETUP_FILE)) {
    return true
  }

  // Check 2: No installer state (never ran setup)
  if (!fs.existsSync(INSTALLER_STATE_FILE)) {
    // Check if there are any models downloaded
    if (fs.existsSync(MODELS_DIR)) {
      const files = fs.readdirSync(MODELS_DIR).filter(f => f.endsWith('.gguf'))
      if (files.length > 0) {
        return false // Has models, not first run
      }
    }
    return true
  }

  // Check 3: Installer state exists but first_run not complete
  try {
    const state = JSON.parse(fs.readFileSync(INSTALLER_STATE_FILE, 'utf8'))
    return !state.first_run_complete
  } catch (e) {
    return true
  }
}

function getPythonPath() {
  // Check for embedded Python first (installed version)
  const embeddedPython = path.join(ASTRA_ROOT, 'python', 'python.exe')
  if (fs.existsSync(embeddedPython)) {
    return embeddedPython
  }
  // Fallback to system Python
  return process.platform === 'win32' ? 'python' : 'python3'
}

// === FIRST-RUN SETUP ===
function runFirstTimeSetup() {
  return new Promise((resolve, reject) => {
    console.log('[Astra] First-run detected — launching model selector...')

    const pythonPath = getPythonPath()
    const setupScript = path.join(ASTRA_ROOT, 'installer', 'first_run.py')

    // Check if setup script exists
    if (!fs.existsSync(setupScript)) {
      console.log('[Astra] Setup script not found, skipping first-run.')
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
      console.log(`[Astra] Setup finished with code ${code}`)
      // Remove the needs_setup marker
      try {
        if (fs.existsSync(NEEDS_SETUP_FILE)) {
          fs.unlinkSync(NEEDS_SETUP_FILE)
        }
      } catch (e) { /* ignore */ }
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


// === WINDOW CREATION ===
function createWindow() {
  // Quitar menú de Electron (File, Edit, View, Window)
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
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })

  // Maximizar al abrir (pantalla completa en PC)
  mainWindow.maximize()

  // Permisos de micrófono y cámara
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowed = ['media', 'mediaKeySystem', 'geolocation', 'notifications', 'midi', 'pointerLock', 'fullscreen']
    if (allowed.includes(permission)) {
      callback(true)
    } else {
      callback(false)
    }
  })

  // Cargar la interfaz web del backend Python (localhost:3000)
  mainWindow.loadURL('http://localhost:3000', {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    if (pythonProcess) pythonProcess.kill()
  })
}

// === SPLASH/LOADING WINDOW (shown during setup) ===
function createSplashWindow() {
  const splash = new BrowserWindow({
    width: 500,
    height: 350,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })

  // Simple HTML splash screen
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
        <p style="color:#4a5a6a; font-size:11px; margin-top:16px;">
          Esto solo ocurre la primera vez
        </p>
      </div>
    </body>
    <style>
      @keyframes pulse { 0%,100%{width:30%} 50%{width:80%} }
    </style>
    </html>
  `

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

// Wait for backend to be ready (poll localhost:3000)
function waitForBackend(timeoutMs = 15000) {
  return new Promise((resolve) => {
    const start = Date.now()
    const http = require('http')

    const check = () => {
      if (Date.now() - start > timeoutMs) {
        console.log('[Astra] Backend timeout — opening window anyway')
        resolve(false)
        return
      }

      const req = http.get('http://localhost:3000/api/status', (res) => {
        if (res.statusCode === 200) {
          resolve(true)
        } else {
          setTimeout(check, 500)
        }
      })
      req.on('error', () => setTimeout(check, 500))
      req.setTimeout(2000, () => { req.destroy(); setTimeout(check, 500) })
    }

    setTimeout(check, 1000) // Wait 1s before first check
  })
}

// === IPC HANDLERS ===
ipcMain.on('window-minimize', () => mainWindow?.minimize())
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize()
  else mainWindow?.maximize()
})
ipcMain.on('window-close', () => mainWindow?.close())

// IPC: abrir simulación en ventana separada
ipcMain.on('open-simulation', (event, simUrl) => {
  const simWindow = new BrowserWindow({
    width: 600,
    height: 500,
    minWidth: 400,
    minHeight: 350,
    frame: true,
    title: 'ASTRA — Simulación 3D',
    backgroundColor: '#030608',
    resizable: true,
    movable: true,
    parent: mainWindow,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })
  simWindow.loadURL(simUrl || 'http://localhost:3000')
})

// IPC: Get model info
ipcMain.handle('get-model-status', async () => {
  try {
    const http = require('http')
    return new Promise((resolve) => {
      http.get('http://localhost:3000/api/status', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => {
          try { resolve(JSON.parse(data)) }
          catch (e) { resolve({ error: 'parse error' }) }
        })
      }).on('error', () => resolve({ error: 'not available' }))
    })
  } catch (e) {
    return { error: e.message }
  }
})

// IPC: Run model manager UI
ipcMain.on('open-model-manager', () => {
  const pythonPath = getPythonPath()
  spawn(pythonPath, ['-m', 'installer.first_run', '--manage'], {
    cwd: ASTRA_ROOT,
    env: { ...process.env, ASTRA_MODE: 'desktop' },
    stdio: 'inherit'
  })
})


// === APP LIFECYCLE ===
app.whenReady().then(async () => {
  // Check if first-run setup is needed
  if (needsFirstRun()) {
    console.log('[Astra] First-run setup needed')

    // Show splash while setup runs
    const splash = createSplashWindow()

    try {
      const setupOk = await runFirstTimeSetup()
      console.log(`[Astra] Setup result: ${setupOk ? 'OK' : 'partial/failed'}`)
    } catch (e) {
      console.error(`[Astra] Setup error: ${e.message}`)
    }

    // Close splash
    if (splash && !splash.isDestroyed()) {
      splash.close()
    }
  }

  // Start Python backend
  startPythonBackend()

  // Wait for backend to be ready
  console.log('[Astra] Waiting for backend...')
  const backendReady = await waitForBackend(15000)

  if (backendReady) {
    console.log('[Astra] Backend ready — opening window')
  } else {
    console.log('[Astra] Backend may not be ready — opening window anyway')
  }

  createWindow()
})

app.on('window-all-closed', () => {
  // Kill Python backend when all windows close
  if (pythonProcess) {
    console.log('[Astra] Stopping Python backend...')
    pythonProcess.kill()
    pythonProcess = null
  }
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', () => {
  // Cleanup on quit
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  if (setupProcess) {
    setupProcess.kill()
    setupProcess = null
  }
})
