import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

# Find all server blocks with their server_name
code, r = run("nginx -T 2>/dev/null | grep -n 'server {' | head -10")
print(f"Server blocks:\n{r}")

code, r = run("nginx -T 2>/dev/null | grep -n 'server_name' | head -10")
print(f"\nServer names:\n{r}")

# The issue is likely that there's a default server block in /etc/nginx/sites-enabled/default
# or in the main nginx.conf that's catching requests before ai-website
code, r = run("ls /etc/nginx/sites-enabled/")
print(f"\nSites: {r}")

# Check if there's a default config
code, r = run("cat /etc/nginx/sites-enabled/default 2>/dev/null | head -20")
print(f"\nDefault site:\n{r[:500]}")

# The real issue: add_header not showing up means the request IS going to the right location
# but nginx might be serving from a different root or the add_header is being ignored
# Let me check if the file is actually being served from the right location
code, r = run("curl -sI http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js | grep -i 'content-length\\|etag\\|last-modified'")
print(f"\nFile info: {r}")

# Check if the file exists at the right path
code, r = run("ls -la /opt/CGCPT/root/CGCPT/assets/vendor-react-076Dd0Bx.js 2>/dev/null")
print(f"\nFile check: {r}")

# The real problem might be that add_header doesn't work with try_files or alias
# when the response is a static file served by the static module
# Let me try a different approach - use more_set_headers instead
# Actually, the issue is that add_header in a nested location doesn't inherit
# from parent, and the parent server block might have its own add_header

# Let me check if there's an add_header in the server block
code, r = run("grep -n 'add_header' /etc/nginx/sites-available/ai-website | head -10")
print(f"\nadd_header directives:\n{r}")

client.close()
