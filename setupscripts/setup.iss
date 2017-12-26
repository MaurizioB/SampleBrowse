#define MyAppName "SampleBrowse"
#define MyAppID "{742E8233-76A6-4D70-BF1C-07CDC07659AD}"
#define MyAppVersion GetFileVersion(AddBackslash(SourcePath) + "..\build\exe.win32-3.5\SampleBrowse.exe")
#define MyAppPublisher "jidesk"
#define MyAppURL "http://jidesk.net/"
#define MyAppExeName "SampleBrowse.exe"
#define MyDebugAppExeName "SampleBrowseDebug.exe"
[Code]
var
  deleteDb: bool;
  dbPath: string;
  deleteReg: bool;
  RegRemoveCheck: TNewCheckBox;
  DbRemoveCheck: TNewCheckBox;
  UninstallCheckPage: TNewNotebookPage;
  UninstallFinalPage: TNewNotebookPage;
  UninstallBackButton: TNewButton;
  UninstallNextButton: TNewButton;

procedure UpdateUninstallWizard;
begin
  if UninstallProgressForm.InnerNotebook.ActivePage = UninstallCheckPage then
  begin
    UninstallProgressForm.PageNameLabel.Caption := '{#MyAppName} uninstall wizard';
    UninstallProgressForm.PageDescriptionLabel.Caption :=
      'You are about to uninstall {#MyAppName} from this computer';
  end
    else
  if UninstallProgressForm.InnerNotebook.ActivePage = UninstallFinalPage then
  begin
    UninstallProgressForm.PageNameLabel.Caption := '{#MyAppName} uninstall wizard';
    UninstallProgressForm.PageDescriptionLabel.Caption :=
      'You are about to uninstall {#MyAppName} from this computer';
  end;

  UninstallBackButton.Visible :=
    (UninstallProgressForm.InnerNotebook.ActivePage <> UninstallCheckPage);

  if UninstallProgressForm.InnerNotebook.ActivePage <> UninstallFinalPage then
  begin
    UninstallNextButton.Caption := SetupMessage(msgButtonNext);
    UninstallNextButton.ModalResult := mrNone;
  end
    else
  begin
    UninstallNextButton.Caption := 'Uninstall';
    { Make the "Uninstall" button break the ShowModal loop }
    UninstallNextButton.ModalResult := mrOK;
  end;
end;  

procedure UninstallNextButtonClick(Sender: TObject);
begin
  if UninstallProgressForm.InnerNotebook.ActivePage = UninstallFinalPage then
  begin
    UninstallNextButton.Visible := False;
    UninstallBackButton.Visible := False;
  end
    else
  begin
    if UninstallProgressForm.InnerNotebook.ActivePage = UninstallCheckPage then
    begin
      UninstallProgressForm.InnerNotebook.ActivePage := UninstallFinalPage;
    end;
    UpdateUninstallWizard;
  end;
end;

procedure UninstallBackButtonClick(Sender: TObject);
begin
  if UninstallProgressForm.InnerNotebook.ActivePage = UninstallFinalPage then
  begin
    UninstallProgressForm.InnerNotebook.ActivePage := UninstallCheckPage;
  end;
  UpdateUninstallWizard;
end;

procedure InitializeUninstallProgressForm();
var
  PageText: TNewStaticText;
  PageNameLabel: string;
  PageDescriptionLabel: string;
  CancelButtonEnabled: Boolean;
  CancelButtonModalResult: Integer;
begin
  if not UninstallSilent then
  begin
    { Create the first page and make it active }
    UninstallCheckPage := TNewNotebookPage.Create(UninstallProgressForm);
    UninstallCheckPage.Notebook := UninstallProgressForm.InnerNotebook;
    UninstallCheckPage.Parent := UninstallProgressForm.InnerNotebook;
    UninstallCheckPage.Align := alClient;

    PageText := TNewStaticText.Create(UninstallProgressForm);
    PageText.Parent := UninstallCheckPage;
    PageText.Top := UninstallProgressForm.StatusLabel.Top;
    PageText.Left := UninstallProgressForm.StatusLabel.Left;
    PageText.Width := UninstallProgressForm.StatusLabel.Width;
//    PageText.Height := UninstallProgressForm.StatusLabel.Height;
    PageText.AutoSize := True;
    PageText.ShowAccelChar := False;
    PageText.Caption := 'Check the following options before proceeeding with uninstallation.';

    RegRemoveCheck := TNewCheckBox.Create(UninstallProgressForm);
    RegRemoveCheck.Parent := UninstallCheckPage;
    RegRemoveCheck.Top := PageText.Top + PageText.Height + 10;
    RegRemoveCheck.Left := PageText.Left;
    RegRemoveCheck.Width := PageText.Width;
    RegRemoveCheck.Caption := 'Remove all settings in registry';
    RegRemoveCheck.Enabled := false;

    DbRemoveCheck := TNewCheckBox.Create(UninstallProgressForm);
    DbRemoveCheck.Parent := UninstallCheckPage;
    DbRemoveCheck.Top := RegRemoveCheck.Top + RegRemoveCheck.Height + 10;
    DbRemoveCheck.Left := PageText.Left;
    DbRemoveCheck.Width := PageText.Width;
    DbRemoveCheck.Caption := 'Remove existing sample database';
    DbRemoveCheck.Enabled := false;

    if RegKeyExists(HKCU, 'Software\jidesk\SampleBrowse') then
      begin
        RegRemoveCheck.Enabled := true;
        if RegQueryStringValue(HKCU, 'Software\jidesk\SampleBrowse', 'dbPath', dbPath) then
          begin
            DbRemoveCheck.Enabled := true;
          end
          else
          begin
          if FileExists(ExpandConstant('{userappdata}\jidesk\SampleBrowse\sample.sqlite')) then
            begin
              dbPath := ExpandConstant('{userappdata}\jidesk\SampleBrowse\sample.sqlite');
              DbRemoveCheck.Enabled := true;
            end
          end
      end;

    UninstallProgressForm.InnerNotebook.ActivePage := UninstallCheckPage;

    PageNameLabel := UninstallProgressForm.PageNameLabel.Caption;
    PageDescriptionLabel := UninstallProgressForm.PageDescriptionLabel.Caption;

    { Create the second page }

    UninstallFinalPage := TNewNotebookPage.Create(UninstallProgressForm);
    UninstallFinalPage.Notebook := UninstallProgressForm.InnerNotebook;
    UninstallFinalPage.Parent := UninstallProgressForm.InnerNotebook;
    UninstallFinalPage.Align := alClient;

    PageText := TNewStaticText.Create(UninstallProgressForm);
    PageText.Parent := UninstallFinalPage;
    PageText.Top := UninstallProgressForm.StatusLabel.Top;
    PageText.Left := UninstallProgressForm.StatusLabel.Left;
    PageText.Width := UninstallProgressForm.StatusLabel.Width;
    PageText.Height := UninstallProgressForm.StatusLabel.Height;
    PageText.AutoSize := False;
    PageText.ShowAccelChar := False;
    PageText.Caption := 'Press Uninstall to complete the uninstallation.';

    UninstallNextButton := TNewButton.Create(UninstallProgressForm);
    UninstallNextButton.Parent := UninstallProgressForm;
    UninstallNextButton.Left :=
      UninstallProgressForm.CancelButton.Left -
      UninstallProgressForm.CancelButton.Width -
      ScaleX(10);
    UninstallNextButton.Top := UninstallProgressForm.CancelButton.Top;
    UninstallNextButton.Width := UninstallProgressForm.CancelButton.Width;
    UninstallNextButton.Height := UninstallProgressForm.CancelButton.Height;
    UninstallNextButton.OnClick := @UninstallNextButtonClick;

    UninstallBackButton := TNewButton.Create(UninstallProgressForm);
    UninstallBackButton.Parent := UninstallProgressForm;
    UninstallBackButton.Left :=
      UninstallNextButton.Left - UninstallNextButton.Width -
      ScaleX(10);
    UninstallBackButton.Top := UninstallProgressForm.CancelButton.Top;
    UninstallBackButton.Width := UninstallProgressForm.CancelButton.Width;
    UninstallBackButton.Height := UninstallProgressForm.CancelButton.Height;
    UninstallBackButton.Caption := SetupMessage(msgButtonBack);
    UninstallBackButton.OnClick := @UninstallBackButtonClick;
    UninstallBackButton.TabOrder := UninstallProgressForm.CancelButton.TabOrder;

    UninstallNextButton.TabOrder := UninstallBackButton.TabOrder + 1;

    UninstallProgressForm.CancelButton.TabOrder := UninstallNextButton.TabOrder + 1;

    { Run our wizard pages } 
    UpdateUninstallWizard;
    CancelButtonEnabled := UninstallProgressForm.CancelButton.Enabled
    UninstallProgressForm.CancelButton.Enabled := True;
    CancelButtonModalResult := UninstallProgressForm.CancelButton.ModalResult;
    UninstallProgressForm.CancelButton.ModalResult := mrCancel;

    if UninstallProgressForm.ShowModal = mrCancel then Abort;

    { Restore the standard page payout }
    UninstallProgressForm.CancelButton.Enabled := CancelButtonEnabled;
    UninstallProgressForm.CancelButton.ModalResult := CancelButtonModalResult;

    UninstallProgressForm.PageNameLabel.Caption := PageNameLabel;
    UninstallProgressForm.PageDescriptionLabel.Caption := PageDescriptionLabel;

    UninstallProgressForm.InnerNotebook.ActivePage :=
      UninstallProgressForm.InstallingPage;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegRemoveCheck.Checked then 
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\jidesk\SampleBrowse');
    begin
    end;
    if DbRemoveCheck.Checked then
    begin
      DeleteFile(dbPath);
    end;
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
    V := MsgBox(ExpandConstant('It seems like SampleBrowse is already installed. Uninstall is suggested before installing the new version' + #13#10#13#10 + 'Do you want to proceed anyway?'), mbInformation, MB_YESNO); //Custom Message if App installed
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
VersionInfoVersion=0.8
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

