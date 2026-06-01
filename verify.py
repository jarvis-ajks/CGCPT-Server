import paramiko
import time

HOST = "118.31.164.41"
USER = "root"
KEY_PATH = r"D:\Projects\CGCPT-Server\id_ed25519"

key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, pkey=key, timeout=15)

print("等待服务完全启动...")
time.sleep(5)

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

run_cmd(ssh, "curl -s http://localhost/CGCPT/api/health | python3 -m json.tool", "检查 API 健康状态")
run_cmd(ssh, "curl -s -X POST http://localhost/CGCPT/api/import/preview 2>&1 | head -5", "测试 import/preview 端点")
run_cmd(ssh, "ls /opt/CGCPT/root/CGCPT/assets/DataImport*", "确认 DataImport 资源")
run_cmd(ssh, "systemctl status cgcpt --no-pager | head -8", "检查服务运行状态")
run_cmd(ssh, "journalctl -u cgcpt --no-pager -n 15", "查看最近日志")

ssh.close()
print("\n✅ 验证完成!")
