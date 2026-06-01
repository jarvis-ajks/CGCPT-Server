import paramiko
import os
import time
import tarfile
import tempfile

LOCAL_BASE = r'd:\Projects\CGCPT-Server'
CAMPUS_HOST = '10.21.22.100'
CAMPUS_USER = 'jarvisajks'
CAMPUS_PASS = 'Jarvis666'
CLOUD_HOST = '118.31.164.41'
CLOUD_USER = 'root'
CLOUD_PASS = 'ZS1029384756!'
CLOUD_REMOTE = '/opt/CGCPT'

print(f"Step 1: Connecting to campus server {CAMPUS_HOST}...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=15)
print("  Connected!")
campus_sftp = campus.open_sftp()

def campus_run(cmd, timeout=900):
    print(f'  $ {cmd}')
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:100]:
            print(f'    {line}')
    if err:
        for line in err.split('\n')[:30]:
            print(f'    [stderr] {line}')
    return out, err

print("\nStep 2: Diagnosing SSH connectivity to cloud server...")
print("  Testing SSH banner with nc...")
campus_run(f'echo "" | timeout 10 nc {CLOUD_HOST} 22 2>&1 || echo "NC_FAILED"', timeout=15)

print("\n  Testing SSH banner with timeout 60...")
campus_run(f'timeout 60 bash -c "echo \\"\\\\" | nc {CLOUD_HOST} 22" 2>&1 || echo "NC_TIMEOUT"', timeout=70)

print("\n  Checking if SSH is on alternate ports...")
campus_run(f'timeout 3 bash -c "echo > /dev/tcp/{CLOUD_HOST}/2222" 2>&1 && echo "Port 2222 OPEN" || echo "Port 2222 CLOSED"', timeout=5)
campus_run(f'timeout 3 bash -c "echo > /dev/tcp/{CLOUD_HOST}/8022" 2>&1 && echo "Port 8022 OPEN" || echo "Port 8022 CLOSED"', timeout=5)

print("\n  Testing SSH with long connection timeout...")
campus_run(
    f'ssh -v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
    f'-o ConnectTimeout=60 -o ConnectionAttempts=3 '
    f'{CLOUD_USER}@{CLOUD_HOST} "echo SSH_SUCCESS" 2>&1 | head -50',
    timeout=200
)

campus_sftp.close()
campus.close()
print("\nDiagnostics complete!")
