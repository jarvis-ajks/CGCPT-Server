$host_ip = "118.31.164.41"
$user = "root"
$pass = "ZS1029384756!"

$commands = @(
    'echo "=== COMMAND 1: cat /etc/nginx/sites-available/ai-website ==="',
    'cat /etc/nginx/sites-available/ai-website',
    'echo "=== COMMAND 2: cat /etc/nginx/nginx.conf ==="',
    'cat /etc/nginx/nginx.conf',
    'echo "=== COMMAND 3: ls -la /etc/nginx/sites-enabled/ ==="',
    'ls -la /etc/nginx/sites-enabled/',
    'echo "=== COMMAND 4: grep -rn server_name /etc/nginx/ ==="',
    'grep -rn "server_name" /etc/nginx/',
    'echo "=== COMMAND 5: curl -sI http://localhost/CGCPT/ ==="',
    'curl -sI http://localhost/CGCPT/ 2>&1',
    'echo "=== COMMAND 6: curl -sI http://localhost/CGCPT/assets/ ==="',
    'curl -sI http://localhost/CGCPT/assets/ 2>&1',
    'echo "=== COMMAND 7: nginx -T 2>&1 | head -200 ==="',
    'nginx -T 2>&1 | head -200',
    'echo "=== COMMAND 8: curl -sI http://127.0.0.1/CGCPT/ -H Host:localhost ==="',
    'curl -sI http://127.0.0.1/CGCPT/ -H "Host: localhost" 2>&1'
)

$fullCommand = $commands -join "`n"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "C:\Windows\System32\OpenSSH\ssh.exe"
$psi.Arguments = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $user@$host_ip"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$process.Start() | Out-Null

Start-Sleep -Milliseconds 2000

$process.StandardInput.WriteLine($pass)
Start-Sleep -Milliseconds 3000

foreach ($cmd in $commands) {
    $process.StandardInput.WriteLine($cmd)
    Start-Sleep -Milliseconds 500
}

$process.StandardInput.WriteLine("exit")
Start-Sleep -Milliseconds 2000

$output = $process.StandardOutput.ReadToEnd()
$errorOutput = $process.StandardError.ReadToEnd()

Write-Output "=== STDOUT ==="
Write-Output $output
Write-Output "=== STDERR ==="
Write-Output $errorOutput

$process.WaitForExit()
Write-Output "Exit code: $($process.ExitCode)"
