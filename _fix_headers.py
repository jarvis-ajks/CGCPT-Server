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

# Read current config
code, r = run("cat /etc/nginx/sites-available/ai-website")
config = r

# Fix assets cache: 30d -> 365d
config = config.replace("expires 30d;", "expires 365d;")

# Add security headers to CGCPT root location
config = config.replace(
    "location ^~ /CGCPT/ {\n        root /opt/CGCPT/root;\n        index index.html;\n        try_files $uri $uri/ /CGCPT/index.html;",
    "location ^~ /CGCPT/ {\n        root /opt/CGCPT/root;\n        index index.html;\n        try_files $uri $uri/ /CGCPT/index.html;\n        add_header X-Frame-Options \"SAMEORIGIN\";\n        add_header X-Content-Type-Options \"nosniff\";"
)

# Add security headers to assets too
config = config.replace(
    "location ^~ /CGCPT/assets/ {\n        root /opt/CGCPT/root;\n        expires 365d;\n        add_header Cache-Control \"public, immutable\";",
    "location ^~ /CGCPT/assets/ {\n        root /opt/CGCPT/root;\n        expires 365d;\n        add_header Cache-Control \"public, immutable\";\n        add_header X-Content-Type-Options \"nosniff\";\n        access_log off;"
)

# Write updated config
sftp = client.open_sftp()
with sftp.open('/etc/nginx/sites-available/ai-website', 'w') as f:
    f.write(config)
sftp.close()

# Test and reload
code, r = run("nginx -t 2>&1")
print(f"nginx test: {r}")

if 'successful' in r:
    code, r = run("systemctl reload nginx 2>&1")
    print("nginx reloaded!")

    # Verify
    code, r = run("curl -sI http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js | grep -i 'cache-control\\|x-content'")
    print(f"Asset headers: {r.strip()}")

    code, r = run("curl -sI http://localhost/CGCPT/ | grep -i 'x-frame\\|x-content'")
    print(f"Page headers: {r.strip()}")
else:
    print(f"ERROR: {r}")

client.close()
