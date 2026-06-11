import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "118.31.164.41",
    username="root",
    password="ZS1029384756!",
    timeout=30,
    look_for_keys=False,
    allow_agent=False,
)

sftp = client.open_sftp()

local_script = r"d:\Projects\CGCPT-Server\_gen_meta_script.py"
remote_script = "/opt/CGCPT/_gen_meta_script.py"

sftp.put(local_script, remote_script)
sftp.close()


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


code, r = run("/opt/CGCPT/venv/bin/python3 /opt/CGCPT/_gen_meta_script.py")
print(f"Generate meta:\n{r}")

code, r = run("ls -la /opt/CGCPT/models/*_meta.json")
print(f"\nMeta files:\n{r}")

code, r = run("curl -s http://localhost:5001/api/stacking/models")
print(f"\nModels API:\n{r[:800]}")

client.close()
