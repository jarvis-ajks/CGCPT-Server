param([string]$Cmd)

$sshPath = "C:\Windows\System32\OpenSSH\ssh.exe"
$plinkPath = "d:\Projects\CGCPT-Server\plink.exe"

$regPath = "HKCU:\Software\SimonTatham\PuTTY\SshHostKeys"
if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}

$keyFingerprint = "ssh-ed25519 255 SHA256:s/ZbF9PcdPRDU/zd3bY6Tab/hkZnsRs34Opg0rkb7pI"
$hostKey = "118.31.164.41"

$existingKeys = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
if (-not ($existingKeys."ssh-ed25519@$($hostKey)") ) {
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo.FileName = $sshPath
    $proc.StartInfo.Arguments = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o NumberOfPasswordPrompts=1 root@$hostKey `"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys`""
    $proc.StartInfo.UseShellExecute = $false
    $proc.StartInfo.RedirectStandardInput = $true
    $proc.StartInfo.RedirectStandardOutput = $true
    $proc.StartInfo.RedirectStandardError = $true
    $proc.StartInfo.CreateNoWindow = $true
    $proc.Start()
    
    Start-Sleep -Seconds 3
    
    $proc.StandardInput.WriteLine("ZS1029384756!")
    $proc.StandardInput.Flush()
    
    Start-Sleep -Milliseconds 500
    
    $pubKey = Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" -Raw
    $proc.StandardInput.Write($pubKey)
    $proc.StandardInput.Close()
    
    $output = $proc.StandardOutput.ReadToEnd()
    $err = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit(30000)
    
    Write-Host "Key push stdout: $output"
    Write-Host "Key push stderr: $err"
    Write-Host "Key push exit: $($proc.ExitCode)"
}

& $sshPath -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 root@$hostKey $Cmd 2>&1
