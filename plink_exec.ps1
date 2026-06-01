param([string]$Cmd)

$plinkPath = "d:\Projects\CGCPT-Server\plink.exe"
$hostKey = "118.31.164.41"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $plinkPath
$psi.Arguments = "-pw ZS1029384756! root@$hostKey `"$Cmd`""
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)

$sw = $proc.StandardInput
$sr = $proc.StandardOutput
$se = $proc.StandardError

Start-Sleep -Milliseconds 2000

$sw.WriteLine("y")
$sw.Flush()

Start-Sleep -Milliseconds 1000

$output = $sr.ReadToEnd()
$err = $se.ReadToEnd()
$proc.WaitForExit(30000)

Write-Host "=== STDOUT ==="
Write-Host $output
Write-Host "=== STDERR ==="
Write-Host $err
Write-Host "=== EXIT CODE: $($proc.ExitCode) ==="
