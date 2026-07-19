const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

// Suprimir errores de pipe rotos (son inofensivos)
process.on('uncaughtException', (err) => {
  if (err.code === 'EPIPE' || err.message.includes('EPIPE')) return // ignorar
  console.error('Error:', err.message)
})

let mainWindow
let pythonProcess

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    frame: false, // Sin barra de título (custom titlebar)
    transparent: false,
    backgroundColor: '#030608',
    icon: path.join(__dirname, '../public/icon.png'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  })

  // Cargar la interfaz web del backend Python (localhost:3000)
  const isDev = !app.isPackaged
  mainWindow.loadURL('http://localhost:3000')
  
  if (isDev) {
    // mainWindow.webContents.openDevTools()
  }

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

app.whenReady().then(() => {
  startPythonBackend()
  // Esperar 2 segundos para que Python arranque
  setTimeout(createWindow, 2000)
})

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
