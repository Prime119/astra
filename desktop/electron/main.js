const { app, BrowserWindow, ipcMain, Menu, session } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

// === HABILITAR SPEECH RECOGNITION EN ELECTRON ===
// Electron no soporta Web Speech API por defecto — estos flags lo habilitan
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
  // Usar partition para forzar usar la Speech API
  mainWindow.loadURL('http://localhost:3000', {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    if (pythonProcess) pythonProcess.kill()
  })
}

// Iniciar el backend Python
function startPythonBackend() {
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'
  const scriptPath = path.join(__dirname, '../../web/servidor.py')
  
  pythonProcess = spawn(pythonPath, [scriptPath], {
    cwd: path.join(__dirname, '../..'),
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
}

// IPC: controles de ventana
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

app.whenReady().then(() => {
  startPythonBackend()
  // Esperar 2 segundos para que Python arranque
  setTimeout(createWindow, 2000)
})

app.on('window-all-closed', () => {
  // NO matar Python — sigue aprendiendo en segundo plano
  // Python se mantiene activo para tareas programadas y auto-investigación
  if (process.platform !== 'darwin') app.quit()
  // El proceso Python sigue vivo en background
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
