import paramiko
import time

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


print("=== Fixing frontend deployment ===")

code, r = run("mkdir -p /opt/CGCPT/root/CGCPT/assets")
print(f"mkdir: {r}")

code, r = run("cp /opt/CGCPT/web/dist/index.html /opt/CGCPT/root/CGCPT/index.html")
print(f"copy index.html: {r}")

code, r = run("cp /opt/CGCPT/web/dist/favicon.svg /opt/CGCPT/root/CGCPT/favicon.svg")
print(f"copy favicon: {r}")

code, r = run("cp /opt/CGCPT/web/dist/icons.svg /opt/CGCPT/root/CGCPT/icons.svg")
print(f"copy icons: {r}")

code, r = run("cp -r /opt/CGCPT/web/dist/assets/* /opt/CGCPT/root/CGCPT/assets/")
print(f"copy assets: {r}")

code, r = run("ls -la /opt/CGCPT/root/CGCPT/")
print(f"CGCPT dir:\n{r}")

code, r = run("ls -la /opt/CGCPT/root/CGCPT/assets/ | head -10")
print(f"assets dir:\n{r}")

print("\n=== Update nginx config for SSE support ===")
code, r = run(
    """sed -i 's/proxy_read_timeout 120s;/proxy_read_timeout 300s;\\n        proxy_buffering off;/' /etc/nginx/sites-available/ai-website"""
)
print(f"sed: {r}")

code, r = run("nginx -t 2>&1")
print(f"nginx test: {r}")

code, r = run("systemctl reload nginx 2>&1")
print(f"nginx reload: {r}")

print("\n=== Test CGCPT access ===")
time.sleep(2)

code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/")
print(f"CGCPT page status: {r}")

code, r = run("curl -s http://localhost/CGCPT/ | head -5")
print(f"CGCPT page:\n{r}")

code, r = run("curl -s http://localhost/CGCPT/api/stats | head -200")
print(f"CGCPT API:\n{r[:300]}")

print("\n=== Test direct API ===")
code, r = run("curl -s http://localhost:5001/api/stats | head -200")
print(f"Direct API:\n{r[:200]}")

print("\n=== Memory usage ===")
code, r = run("free -h | head -3")
print(r)

print("\n=== Service status ===")
code, r = run("systemctl status cgcpt --no-pager | head -8")
print(r)

client.close()
print("\nDone!")
