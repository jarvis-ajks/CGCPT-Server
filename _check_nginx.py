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

run("curl -sv http://localhost/CGCPT/api/health 2>&1 | head -30")
run("cat /etc/nginx/sites-enabled/cgcpt* 2>/dev/null || cat /etc/nginx/conf.d/cgcpt* 2>/dev/null || echo 'No cgcpt nginx config found'")
run("ls /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null")

ssh.close()
