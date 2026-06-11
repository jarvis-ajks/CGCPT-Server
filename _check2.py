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
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


code, r = run("cat /etc/nginx/sites-available/ai-website")
print(f"ai-website config:\n{r[:500]}\n")

code, r = run("curl -s http://localhost:5001/api/stats | head -200")
print(f"Direct API (5001): {r[:200]}\n")

code, r = run("curl -s http://localhost/api/stats | head -200")
print(f"Nginx API (80): {r[:200]}\n")

code, r = run("curl -s http://localhost/ | head -5")
print(f"Nginx root (80): {r[:200]}\n")

client.close()
