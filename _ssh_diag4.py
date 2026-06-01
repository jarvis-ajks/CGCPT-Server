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

print("\nChecking if SSH is actually running on port 22...")
out, _ = campus_run(f'timeout 5 bash -c "echo \\"\\" | nc -w 3 {CLOUD_HOST} 22" 2>&1', timeout=8)
print(f"  Port 22 banner: {out[:200] if out else 'NO BANNER'}")

out, _ = campus_run(f'timeout 5 bash -c "echo \\"\\" | nc -w 3 {CLOUD_HOST} 80" 2>&1', timeout=8)
print(f"  Port 80 banner: {out[:200] if out else 'NO BANNER'}")

print("\nTrying SSH with explicit protocol version...")
out, _ = campus_run(
    f'echo "SSH-2.0-OpenSSH_9.2" | timeout 10 nc {CLOUD_HOST} 22 2>&1',
    timeout=15
)
print(f"  Response after sending client banner: {out[:200] if out else 'NO RESPONSE'}")

print("\nChecking if there's an HTTP proxy on port 22...")
out, _ = campus_run(
    f'echo -e "GET / HTTP/1.0\\r\\n\\r\\n" | timeout 5 nc {CLOUD_HOST} 22 2>&1',
    timeout=8
)
print(f"  HTTP response on port 22: {out[:200] if out else 'NO RESPONSE'}")

campus.close()
print("\nDone!")
