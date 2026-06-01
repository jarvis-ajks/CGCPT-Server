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

print(f"Connecting to campus server...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=15)
print("  Connected!")

def campus_run(cmd, timeout=900):
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("\nTrying SSH with old password Aa123456...")
out, err = campus_run(
    f'ssh -v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
    f'-o ConnectTimeout=30 -o PasswordAuthentication=yes '
    f'{CLOUD_USER}@{CLOUD_HOST} "echo test" 2>&1 | head -20',
    timeout=60
)
print(f"  out: {out[:500]}")

print("\nTrying with SSH_ASKPASS and old password...")
askpass_old = '/archive/jarvisajks/ssh_askpass_old.sh'
campus_sftp = campus.open_sftp()
with campus_sftp.open(askpass_old, 'w') as f:
    f.write('#!/bin/sh\necho "Aa123456"\n')
campus_run(f'chmod +x {askpass_old}')

out, err = campus_run(
    f'SSH_ASKPASS={askpass_old} SSH_ASKPASS_REQUIRE=force DISPLAY=:0 '
    f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
    f'-o ConnectTimeout=60 '
    f'{CLOUD_USER}@{CLOUD_HOST} "echo SSH_SUCCESS" 2>&1',
    timeout=120
)
print(f"  out: {out[:500]}")

print("\nChecking traceroute to cloud server...")
out, err = campus_run(f'traceroute -m 10 -w 2 {CLOUD_HOST} 2>&1', timeout=30)
print(f"  traceroute: {out[:500]}")

print("\nChecking if cloud server responds to ping...")
out, err = campus_run(f'ping -c 3 -W 5 {CLOUD_HOST} 2>&1', timeout=20)
print(f"  ping: {out[:300]}")

campus_sftp.close()
campus.close()
print("\nDone!")
