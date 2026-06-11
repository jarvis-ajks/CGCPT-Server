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


# The issue might be that the server has another server block that catches the request first
# Check which server block is handling the request
code, r = run("nginx -T 2>/dev/null | grep -c 'server {'")
print(f"Server blocks: {r}")

# Check if there's a default server that might be catching
code, r = run("nginx -T 2>/dev/null | grep -B2 'server_name.*_' | head -10")
print(f"Server names with _:\n{r}")

# The warning about "conflicting server name _" means there are TWO server blocks with server_name _
# This means the FIRST one in the config wins, which might not be the ai-website one
# Let's check the order
code, r = run("ls -la /etc/nginx/sites-enabled/")
print(f"\nSites enabled:\n{r}")

# Check the other site config
code, r = run("cat /etc/nginx/sites-enabled/cgcpt 2>/dev/null | head -5")
print(f"\ncgcpt site: {r}")

# Remove the conflicting cgcpt site (we use ai-website now)
code, r = run("rm -f /etc/nginx/sites-enabled/cgcpt 2>/dev/null")
code, r = run("nginx -t 2>&1")
print(f"\nAfter removing cgcpt site: {r}")

if "successful" in r:
    code, r = run("systemctl reload nginx 2>&1")

    # Test again
    code, r = run("curl -sI http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js | head -15")
    print(f"\nAsset headers:\n{r}")

client.close()
