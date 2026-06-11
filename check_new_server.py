import paramiko
import json
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Try connecting to the server
print("Connecting to 118.31.164.41 as jarvisajks...")
try:
    ssh.connect("118.31.164.41", username="jarvisajks", password="Jarvis666", timeout=30)
    print("Connected!")
except Exception as e:
    print(f"Failed: {e}")
    print("\nTrying as root...")
    try:
        ssh.connect("118.31.164.41", username="root", password="Jarvis666", timeout=30)
        print("Connected as root!")
    except Exception as e2:
        print(f"Root also failed: {e2}")
        sys.exit(1)


def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("\n=== Who am I ===")
out, _ = run("whoami && id")
print(out)

print("\n=== Home ===")
out, _ = run("ls -la ~")
print(out)

print("\n=== Find CIF files ===")
out, _ = run('find /home -name "*.cif" -type f 2>/dev/null | head -30')
print(out if out else "No CIF in /home")

out, _ = run('find /opt -name "*.cif" -type f 2>/dev/null | head -30')
print(out if out else "No CIF in /opt")

out, _ = run('find /root -name "*.cif" -type f 2>/dev/null | head -30')
print(out if out else "No CIF in /root")

print("\n=== Find database dirs ===")
out, _ = run('find / -maxdepth 4 -type d -name "*Proto*" 2>/dev/null | head -20')
print(out if out else "No Proto dirs")

out, _ = run('find / -maxdepth 4 -type d -name "database" 2>/dev/null | head -20')
print(out if out else "No database dirs")

print("\n=== Python ===")
out, _ = run("python3 --version 2>&1")
print(out)

print("\n=== pip packages ===")
out, _ = run(
    'pip3 list 2>/dev/null | grep -iE "sklearn|scikit|pymatgen|numpy|joblib" || echo "pip3 not available"'
)
print(out)

ssh.close()
print("\nDone!")
