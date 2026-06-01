import paramiko
import os
import time

CAMPUS_HOST = '10.21.22.100'
CAMPUS_USER = 'jarvisajks'
CAMPUS_PASS = 'Jarvis666'
CLOUD_HOST = '118.31.164.41'
CLOUD_USER = 'root'
CLOUD_PASS = 'ZS1029384756!'

print("Connecting to campus server...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=15)
print("  Connected!")

def campus_run(cmd, timeout=300):
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("\nScanning common SSH ports on cloud server...")
ports_to_check = [22, 80, 443, 2222, 8022, 8443, 10022, 2200, 22222, 3022, 4022, 5022, 60022, 9000, 9090]
for port in ports_to_check:
    out, _ = campus_run(
        f'timeout 2 bash -c "echo > /dev/tcp/{CLOUD_HOST}/{port}" 2>&1 && echo "OPEN" || echo "CLOSED"',
        timeout=5
    )
    if 'OPEN' in out:
        print(f"  Port {port}: OPEN")
        out2, _ = campus_run(
            f'timeout 5 bash -c "echo \\"\\" | nc -w 3 {CLOUD_HOST} {port}" 2>&1 | head -1',
            timeout=8
        )
        if out2:
            print(f"    Banner: {out2[:200]}")
    else:
        print(f"  Port {port}: closed")

campus.close()
print("\nDone!")
