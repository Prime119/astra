; ============================================================
; ASTRA — Inno Setup Installer Script
; ============================================================
; Genera un instalador .exe ligero (~300MB) que incluye:
;   - Electron (app desktop)
;   - Python embebido (3.11.x, sin instalación global)
;   - llama-server.exe (inferencia local)
;   - Código fuente de Astra
;
; Los modelos NO se incluyen — se descargan en primera ejecución
; según el hardware del usuario.
;
; Compilar con: Inno Setup Compiler 6.x
;   iscc.exe astra_installer.iss
; ============================================================

#define MyAppName "Astra"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Prime119"
#define MyAppURL "https://github.com/Prime119/astra"
#define MyAppExeName "Astra.exe"


[Setup]
AppId={{A5F7D3B2-8E4C-4F1A-B9D6-7C2E1A0F3B5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Salida del instalador
OutputDir=..\dist
OutputBaseFilename=Astra-Setup-v{#MyAppVersion}
; Icono del instalador (comentar si no tienes icon.ico)
; SetupIconFile=..\desktop\public\icon.ico
; Compresión máxima para mantenerlo ligero
Compression=lzma2/ultra64
SolidCompression=yes
; Requiere Windows 10+
MinVersion=10.0
; Tamaño del disco requerido (installer + espacio para modelos)
ExtraDiskSpaceRequired=2147483648
; Privilegios (no necesita admin para instalar en carpeta de usuario)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Wizard
WizardStyle=modern
WizardSizePercent=120,120
; Desinstalar
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar Astra con Windows (segundo plano)"; GroupDescription: "Opciones adicionales:"

[Files]
; === ELECTRON APP (empaquetada) ===
Source: "..\dist\electron\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; === PYTHON EMBEBIDO ===
Source: "..\dist\python-embedded\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; === LLAMA.CPP SERVER ===
Source: "..\dist\llama-cpp\llama-server.exe"; DestDir: "{app}\llama-cpp"; Flags: ignoreversion
Source: "..\dist\llama-cpp\*.dll"; DestDir: "{app}\llama-cpp"; Flags: ignoreversion skipifsourcedoesntexist

; === CÓDIGO FUENTE DE ASTRA (Python) ===
Source: "..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\web\*"; DestDir: "{app}\web"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\installer\*"; DestDir: "{app}\installer"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.iss,build_installer.py"

; === ARCHIVOS RAÍZ ===
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\astra.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\astra_desktop.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\astra_web.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; === LAUNCHER ===
Source: "..\dist\Astra-Launcher.bat"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist


[Dirs]
; Directorio para modelos (se descargan después)
Name: "{app}\models"; Permissions: users-full

[Icons]
; Menú inicio
Name: "{group}\{#MyAppName}"; Filename: "{app}\Astra-Launcher.bat"; IconFilename: "{app}\llama-cpp\llama-server.exe"
Name: "{group}\Gestionar Modelos"; Filename: "{app}\python\python.exe"; Parameters: "-m installer.first_run --manage"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
; Escritorio
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Astra-Launcher.bat"; Tasks: desktopicon

[Registry]
; Auto-start con Windows (opcional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Astra"; ValueData: """{app}\Astra-Launcher.bat"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Instalar dependencias Python después de la instalación
Filename: "{app}\python\python.exe"; Parameters: "-m pip install --no-warn-script-location -r ""{app}\requirements.txt"""; WorkingDir: "{app}"; StatusMsg: "Instalando dependencias de Python..."; Flags: runhidden waituntilterminated
; Ejecutar setup de primera vez
Filename: "{app}\python\python.exe"; Parameters: "-m installer.first_run"; WorkingDir: "{app}"; StatusMsg: "Configurando Astra (selección de modelos)..."; Flags: nowait
; Lanzar Astra después de instalar
Filename: "{app}\Astra-Launcher.bat"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpiar archivos generados
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\config\.installer_state.json"
Type: filesandordirs; Name: "{app}\config\setup_result.json"
Type: filesandordirs; Name: "{app}\web\static\audio"

[Code]
// === PASCAL SCRIPT — Lógica personalizada del instalador ===

var
  DiskSpacePage: TOutputMsgWizardPage;

// Verificar espacio en disco antes de instalar
function InitializeSetup(): Boolean;
var
  FreeMB: Cardinal;
begin
  Result := True;
  // Verificar al menos 500MB libres para el installer base
  // Los modelos necesitan más (se descarga después)
  FreeMB := GetSpaceOnDisk(ExpandConstant('{sd}'), True) div 1048576;
  if FreeMB < 500 then
  begin
    MsgBox('Se necesitan al menos 500 MB de espacio libre para instalar Astra.' + #13#10 +
           'Espacio disponible: ' + IntToStr(FreeMB) + ' MB' + #13#10 + #13#10 +
           'Además, necesitarás entre 1-5 GB adicionales para los modelos de IA.',
           mbError, MB_OK);
    Result := False;
  end;
end;

// Mensaje personalizado al finalizar
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Crear archivo marcador para que Electron detecte primera ejecución
    SaveStringToFile(ExpandConstant('{app}\config\.needs_setup'), 'true', False);
  end;
end;

// Información extra en la página de bienvenida
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := '';
  Result := Result + 'Astra se instalará con:' + NewLine;
  Result := Result + Space + '• Motor de IA local (llama.cpp)' + NewLine;
  Result := Result + Space + '• Interfaz de escritorio (Electron)' + NewLine;
  Result := Result + Space + '• Python embebido (sin afectar tu sistema)' + NewLine;
  Result := Result + NewLine;
  Result := Result + 'Tamaño del instalador: ~300 MB' + NewLine;
  Result := Result + NewLine;
  Result := Result + 'NOTA: Al iniciar por primera vez, Astra te mostrará' + NewLine;
  Result := Result + 'un selector de modelos de IA para descargar (1-5 GB).' + NewLine;
  Result := Result + 'Los modelos se ejecutan 100% local, sin internet.' + NewLine;

  if MemoTasksInfo <> '' then
  begin
    Result := Result + NewLine + MemoTasksInfo;
  end;
end;
