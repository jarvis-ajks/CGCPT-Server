$plink = "d:\Projects\CGCPT-Server\plink.exe"
$host_ip = "118.31.164.41"
$user = "root"
$pass = "ZS1029384756!"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $plink
$psi.Arguments = "-ssh -l $user -pw $pass $host_ip `"echo CONNECTION_OK`""
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$process.Start() | Out-Null

Start-Sleep -Milliseconds 3000

$process.StandardInput.WriteLine("y")
Start-Sleep -Milliseconds 3000

$output = $process.StandardOutput.ReadToEnd()
$errorOutput = $process.StandardError.ReadToEnd()

Write-Output "=== STDOUT ==="
Write-Output $output
Write-Output "=== STDERR ==="
Write-Output $errorOutput

$process.WaitForExit()
Write-Output "Exit code: $($process.ExitCode)"
