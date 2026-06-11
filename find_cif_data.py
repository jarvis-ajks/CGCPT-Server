import paramiko
import sys

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)


def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("=== 查找CIF数据 ===\n")

out, _ = run('find /archive/jarvisajks -name "*.cif" -type f 2>/dev/null | head -30')
print(f"Home目录CIF文件:\n{out if out else '无'}\n")

out, _ = run("find /archive/jarvisajks -maxdepth 4 -type d 2>/dev/null")
print(f"Home目录结构:\n{out if out else '无'}\n")

out, _ = run('find / -maxdepth 5 -name "*.cif" -type f 2>/dev/null | head -30')
print(f"全系统CIF文件:\n{out if out else '无'}\n")

out, _ = run(
    'find / -maxdepth 4 -type d \\( -name "*XO*" -o -name "*Proto*" -o -name "*cif*" -o -name "*CIF*" -o -name "*stacking*" -o -name "*database*" -o -name "*train*" -o -name "*data*" \\) 2>/dev/null | grep -v proc | grep -v sys | head -30'
)
print(f"数据相关目录:\n{out if out else '无'}\n")

out, _ = run("ls -la /archive/jarvisajks/cgcpt-stacking/data/")
print(f"cgcpt-stacking/data/:\n{out}\n")

ssh.close()
