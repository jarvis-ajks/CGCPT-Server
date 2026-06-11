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
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")


run("nginx -t")
run("systemctl reload nginx")
run("sleep 1 && curl -sv http://localhost/CGCPT/api/health 2>&1")
run("curl -s http://localhost:5001/api/health | python3 -m json.tool")

ssh.close()
