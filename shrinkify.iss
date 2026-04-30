[Setup]
AppName=Shrinkify
AppVersion=1.0.4
DefaultDirName={autopf}\Shrinkify
DefaultGroupName=Shrinkify
OutputBaseFilename=Shrinkify-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\Shrinkify.exe"; DestDir: "{app}"
Source: "icon.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\Shrinkify"; Filename: "{app}\Shrinkify.exe"
Name: "{commondesktop}\Shrinkify"; Filename: "{app}\Shrinkify.exe"

[Run]
Filename: "{app}\Shrinkify.exe"; Description: "Launch Shrinkify"; Flags: nowait postinstall
