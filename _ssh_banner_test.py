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


print("\nStep 2: Testing SSH banner with very long timeout (180s)...")
campus_run(f'timeout 180 nc -w 180 {CLOUD_HOST} 22 2>&1; echo "EXIT_CODE=$?"', timeout=200)

print("\nStep 3: Trying paramiko with raw socket and long banner wait...")
relay_script = (
    '''
import paramiko
import socket
import time
import sys

CLOUD_HOST = "'''
    + CLOUD_HOST
    + '''"
CLOUD_USER = "'''
    + CLOUD_USER
    + '''"
CLOUD_PASS = "'''
    + CLOUD_PASS
    + '''"
CLOUD_REMOTE = "'''
    + CLOUD_REMOTE
    + """"

print("Creating raw socket connection...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(180)
try:
    sock.connect((CLOUD_HOST, 22))
    print("  TCP connected!")
    
    print("  Waiting for SSH banner (up to 180s)...")
    banner_data = b""
    start = time.time()
    while time.time() - start < 180:
        try:
            chunk = sock.recv(4096)
            if chunk:
                banner_data += chunk
                print(f"  Received: {chunk[:200]}")
                if b"\\n" in banner_data:
                    break
            else:
                print("  Connection closed by server")
                break
        except socket.timeout:
            print(f"  Still waiting... ({int(time.time()-start)}s)")
            continue
    
    if not banner_data:
        print("  No banner received!")
        sys.exit(1)
    
    print(f"  Banner: {banner_data.decode('utf-8', errors='replace').strip()}")
    
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    sock.close()
"""
)

relay_path = "/archive/jarvisajks/ssh_banner_test.py"
with campus_sftp.open(relay_path, "w") as f:
    f.write(relay_script)

print("\nStep 4: Running banner test on campus server...")
campus_run(f"/archive/jarvisajks/cgcpt-stacking/venv/bin/python {relay_path} 2>&1", timeout=300)

campus_sftp.close()
campus.close()
print("\nDone!")
