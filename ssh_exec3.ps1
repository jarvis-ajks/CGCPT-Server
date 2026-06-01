param([string]$Cmd)

$sshPath = "C:\Windows\System32\OpenSSH\ssh.exe"
$hostKey = "118.31.164.41"

$keyPath = "$env:USERPROFILE\.ssh\id_rsa_cgcpt"
if (-not (Test-Path $keyPath)) {
    & "C:\Windows\System32\OpenSSH\ssh-keygen.exe" -t rsa -b 4096 -f $keyPath -N '""' -q 2>&1
}

$pubKey = Get-Content "$keyPath.pub" -Raw

$tempScript = [System.IO.Path]::GetTempFileName() + ".expect.ps1"
$scriptContent = @"
`$psi = New-Object System.Diagnostics.ProcessStartInfo
`$psi.FileName = '$sshPath'
`$psi.Arguments = '-o StrictHostKeyChecking=no root@118.31.164.41 \"mkdir -p ~/.ssh && echo `'`$pubKey`' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys\"'
`$psi.UseShellExecute = `$false
`$psi.RedirectStandardInput = `$true
`$psi.RedirectStandardOutput = `$true
`$psi.RedirectStandardError = `$true
`$psi.CreateNoWindow = `$true

`$proc = [System.Diagnostics.Process]::Start(`$psi)

`$sw = `$proc.StandardInput
`$sr = `$proc.StandardOutput
`$se = `$proc.StandardError

Start-Sleep -Seconds 3
`$sw.WriteLine('ZS1029384756!')
`$sw.Flush()

`$output = `$sr.ReadToEnd()
`$err = `$se.ReadToEnd()
`$proc.WaitForExit(30000)

Write-Host `$output
Write-Host `$err
"@
Set-Content -Path $tempScript -Value $scriptContent

& $tempScript 2>&1

Start-Sleep -Seconds 2

& $sshPath -o StrictHostKeyChecking=no -i $keyPath root@118.31.164.41 $Cmd 2>&1
