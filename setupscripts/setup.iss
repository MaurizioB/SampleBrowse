#define MyAppName "SampleBrowse"
#define MyAppID "{742E8233-76A6-4D70-BF1C-07CDC07659AD}"
#define MyAppVersion GetFileVersion(AddBackslash(SourcePath) + "..\build\exe.win32-3.5\SampleBrowse.exe")
#define MyAppPublisher "jidesk"
#define MyAppURL "http://jidesk.net/"
#define MyAppExeName "SampleBrowse.exe"
#define MyDebugAppExeName "SampleBrowseDebug.exe"
[Code]
var
  deleteDb: integer;
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usAppMutexCheck then
    if FileExists(ExpandConstant('{userappdata}\jidesk\SampleBrowse\sample.sqlite')) then 
      begin
        deleteDb := MsgBox('Samples database found, do you want to remove it as well?', mbConfirmation, MB_YESNO);
      end      
  else;
  if (CurUninstallStep = usPostUninstall) and (deleteDb = IDYES) then begin
    DeleteFile(ExpandConstant('{userappdata}\jidesk\SampleBrowse\sample.sqlite'))
  end;

end;
function GetUninstallString: string;
var
  sUnInstPath: string;
  sUnInstallString: String;
begin
  Result := '';
  sUnInstPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppID}_is1';
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade: Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function InitializeSetup: Boolean;
var
  V: Integer;
  iResultCode: Integer;
  sUnInstallString: string;
begin
  Result := True; // in case when no previous version is found
  if RegValueExists(HKLM,'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppID}}_is1', 'UninstallString') then  //Your App GUID/ID
  begin
    V := MsgBox(ExpandConstant('It seems like SampleBrowse is already installed. Uninstall is required before installing the new version. Proceed?'), mbInformation, MB_YESNO); //Custom Message if App installed
    if V = IDYES then
    begin
      sUnInstallString := GetUninstallString();
      sUnInstallString :=  RemoveQuotes(sUnInstallString);
      Exec(ExpandConstant(sUnInstallString), '', '', SW_SHOW, ewWaitUntilTerminated, iResultCode);
      Result := True; //if you want to proceed after uninstall
      //Exit; //if you want to quit after uninstall
    end
    else
      Result := False; //proceed anyway
  end;
end;
[Setup]
SourceDir=..\
AppId={{#MyAppID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename={#MyAppName}Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
VersionInfoVersion=0.3
InfoBeforeFile="setupscripts\infobefore.txt"

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
Name: "{app}\__pycache__"; Permissions: users-modify

[Files]
;remember to change the soundfile.cpython pyc version number, if needed
Source: "build\exe.win32-3.5\SampleBrowse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\exe.win32-3.5\*"; DestDir: "{app}"; Excludes: "PyQt5\Qt\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\exe.win32-3.5\PyQt5\Qt\plugins\audio\*"; DestDir: "{app}\PyQt5\Qt\plugins\audio"; Flags: ignoreversion recursesubdirs createallsubdirs
;These are needed since python tries to create an optimized cache of scripts.
Source: "setupscripts\emptyfile"; DestDir: "{app}"; DestName: "lextab.py"; Permissions: users-modify; Flags: ignoreversion
Source: "setupscripts\emptyfile"; DestDir: "{app}"; DestName: "yacctab.py"; Permissions: users-modify; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} (debug mode)"; Filename: "{app}\{#MyDebugAppExeName}"
Name: "{group}\Project website"; Filename: "https://github.com/MaurizioB/Bigglesworth"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__\soundfile.cpython-35.pyc"
Type: files; Name: "{app}\lextab.py";
Type: files; Name: "{app}\yacctab.py";

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

