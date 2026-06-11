import paramiko

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


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


# 1. Install fail2ban
print("=== Installing fail2ban ===")
code, r = run("apt-get install -y -qq fail2ban 2>&1 | tail -3")
print(r)

# 2. Configure fail2ban for SSH
print("\n=== Configuring fail2ban ===")
fail2ban_local = """[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 3600
"""

sftp = client.open_sftp()
with sftp.open("/etc/fail2ban/jail.local", "w") as f:
    f.write(fail2ban_local)
sftp.close()
print("Created /etc/fail2ban/jail.local")

# 3. Start fail2ban
code, r = run("systemctl enable fail2ban && systemctl restart fail2ban 2>&1")
print(f"fail2ban: {r}")

code, r = run("fail2ban-client status sshd 2>&1")
print(f"fail2ban status: {r}")

# 4. SSH hardening
print("\n=== SSH hardening ===")
ssh_hardening = """
# Disable root login with password after key is set up
# PermitRootLogin prohibit-password
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
"""
# Don't disable password auth yet since user needs it
# Just add rate limiting
code, r = run(
    "grep -q 'MaxAuthTries 3' /etc/ssh/sshd_config || echo 'MaxAuthTries 3' >> /etc/ssh/sshd_config"
)
code, r = run(
    "grep -q 'LoginGraceTime 30' /etc/ssh/sshd_config || echo 'LoginGraceTime 30' >> /etc/ssh/sshd_config"
)
print("SSH config updated")

code, r = run("systemctl reload sshd 2>&1")
print(f"sshd reload: {r}")

# 5. Install psutil for health check
print("\n=== Installing psutil ===")
code, r = run(
    "/opt/CGCPT/venv/bin/pip install psutil -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com 2>&1 | tail -3"
)
print(r)

# 6. Deploy updated api_server.py
print("\n=== Deploying updated backend ===")
sftp.put(r"d:\Projects\CGCPT-Server\api_server.py", "/opt/CGCPT/api_server.py")
sftp.put(r"d:\Projects\CGCPT-Server\stacking_analyzer.py", "/opt/CGCPT/stacking_analyzer.py")
print("Backend files uploaded")

# 7. Restart CGCPT service
import time

code, r = run("systemctl restart cgcpt 2>&1")
print(f"CGCPT restart: {r}")
time.sleep(3)

code, r = run("systemctl status cgcpt --no-pager | head -8")
print(f"CGCPT status:\n{r}")

# 8. Test health endpoint
code, r = run("curl -s http://localhost:5001/api/health")
print(f"\nHealth check: {r}")

# 9. Check memory
code, r = run("free -h | head -3")
print(f"\nMemory:\n{r}")

sftp.close()
client.close()
print("\nSecurity hardening complete!")
