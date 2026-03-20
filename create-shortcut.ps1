$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$env:USERPROFILE\Desktop\WhisperWriter.lnk")
$s.TargetPath = "wscript.exe"
$s.Arguments = "`"$scriptDir\WhisperWriter.vbs`""
$s.WorkingDirectory = $scriptDir
$s.Description = "WhisperWriter - Voice to Text (GPU)"
$s.Save()
Write-Host "Shortcut created on Desktop!"
