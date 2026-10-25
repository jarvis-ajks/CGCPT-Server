"""Test SSH connection with retry and different methods."""
import paramiko
import socket
import time

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"

# First test raw socket
print("Testing raw socket connection...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
try:
    s.connect((HOST, 22))
    banner = s.recv(1024)
    print(f"SSH Banner: {banner}")
    s.close()
except Exception as e:
    print(f"Socket error: {e}")

# Try paramiko with different settings
for attempt in range(3):
    print(f"\nParamiko attempt {attempt + 1}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            HOST,
            port=22,
            username=USER,
            password=PASS,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
            allow_agent=False,
            look_for_keys=False,
        )
        print("Connected!")
        stdin, stdout, stderr = ssh.exec_command("echo OK && uname -a", timeout=30)
        print(stdout.read().decode())
        ssh.close()
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
