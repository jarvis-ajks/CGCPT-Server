import paramiko
import time

HOST = "118.31.164.41"
USER = "root"
KEY_PATH = r"D:\Projects\CGCPT-Server\id_ed25519"

key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, pkey=key, timeout=15)

def run_cmd(ssh, cmd, desc=""):
    print(f"\n{'='*60}")
    print(f"▶ {desc}")
    print(f"{'='*60}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    print(f"[退出码] {rc}")
    return out, err, rc

run_cmd(ssh, "curl -s http://localhost:5001/api/health | python3 -m json.tool", "直接测试5001端口 API健康")
run_cmd(ssh, "curl -s -X POST http://localhost:5001/api/import/preview 2>&1 | head -5", "直接测试5001 import/preview")
run_cmd(ssh, "cat /etc/nginx/sites-enabled/cgcpt.conf 2>/dev/null || cat /etc/nginx/conf.d/cgcpt.conf 2>/dev/null || echo 'NOT FOUND'", "查看nginx配置")
run_cmd(ssh, "ls /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null", "列出nginx配置文件")

ssh.close()
