import paramiko

HOST = "118.31.164.41"
USER = "root"
KEY = r"D:\Projects\CGCPT-Server\id_ed25519"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, key_filename=KEY, timeout=30)

def run(cmd):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out: print(out)
    if err: print(f"[STDERR] {err}")

run("cat /etc/nginx/sites-enabled/default")
run("cat /etc/nginx/sites-enabled/ai-website")

ssh.close()
