import paramiko
import os
import time
import tarfile
import tempfile

LOCAL_BASE = r"d:\Projects\CGCPT-Server"
CAMPUS_HOST = "10.21.22.100"
CAMPUS_USER = "jarvisajks"
CAMPUS_PASS = "Jarvis666"
CLOUD_HOST = "118.31.164.41"
CLOUD_USER = "root"
CLOUD_PASS = "ZS1029384756!"
CLOUD_REMOTE = "/opt/CGCPT"

print(f"Step 1: Connecting to campus server {CAMPUS_HOST}...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=15)
print("  Connected!")
campus_sftp = campus.open_sftp()


def campus_run(cmd, timeout=900):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        for line in out.split("\n")[:100]:
            print(f"    {line}")
    if err:
        for line in err.split("\n")[:30]:
            print(f"    [stderr] {line}")
    return out, err


print("\nStep 2: Testing SSH on alternate ports...")
for port in [2222, 8022]:
    print(f"\n  Testing port {port}...")
    out, _ = campus_run(
        f'timeout 10 bash -c "echo \\"\\" | nc {CLOUD_HOST} {port}" 2>&1', timeout=15
    )
    print(f'  Banner on port {port}: {out[:200] if out else "No banner"}')

print("\nStep 3: Trying SSH on port 2222...")
campus_run(
    f"ssh -v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    f'-o ConnectTimeout=10 -p 2222 {CLOUD_USER}@{CLOUD_HOST} "echo SSH_PORT_2222_SUCCESS" 2>&1 | head -30',
    timeout=30,
)

print("\nStep 4: Trying SSH on port 8022...")
campus_run(
    f"ssh -v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    f'-o ConnectTimeout=10 -p 8022 {CLOUD_USER}@{CLOUD_HOST} "echo SSH_PORT_8022_SUCCESS" 2>&1 | head -30',
    timeout=30,
)

campus_sftp.close()
campus.close()
print("\nDiagnostics complete!")
