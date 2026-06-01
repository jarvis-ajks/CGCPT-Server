param(
    [string]$Command
)

$password = "ZS1029384756!"
$sshPath = "C:\Windows\System32\OpenSSH\ssh.exe"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $sshPath
$psi.Arguments = "-o StrictHostKeyChecking=no root@118.31.164.41 `"$Command`""
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)

Start-Sleep -Milliseconds 2000
$proc.StandardInput.WriteLine($password)
$proc.StandardInput.Flush()

$output = $proc.StandardOutput.ReadToEnd()
$errorOut = $proc.StandardError.ReadToEnd()
$proc.WaitForExit(30000)

Write-Host $output
if ($errorOut) { Write-Host $errorOut }
exit $proc.ExitCode
