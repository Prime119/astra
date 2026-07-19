const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

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

  // En desarrollo, cargar Vite dev server
  const isDev = !app.isPackaged
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    // mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
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
    env: { ...process.env, ASTRA_MODE: 'desktop' }
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data.toString().trim()}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Error] ${data.toString().trim()}`)
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
