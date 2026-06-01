import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

# Install nginx brotli module
print("=== Installing nginx Brotli module ===")
code, r = run("apt-get install -y -qq libnginx-mod-http-brotli-filter libnginx-mod-http-brotli-static 2>&1 | tail -5")
print(r)

# Check if brotli modules are available
code, r = run("ls /etc/nginx/modules-available/ 2>/dev/null | grep brotli; ls /usr/lib/nginx/modules/ 2>/dev/null | grep brotli")
print(f"Brotli modules: {r}")

# Read current nginx config
code, r = run("cat /etc/nginx/sites-available/ai-website")
current_config = r

# Find the CGCPT static assets location block
# We need to add cache headers for hashed assets
print("\n=== Updating nginx config ===")

# Add brotli to http block in nginx.conf
code, r = run("cat /etc/nginx/nginx.conf")
nginx_conf = r

# Check if brotli is already in nginx.conf
if 'brotli' not in nginx_conf:
    # Add brotli module loading and configuration
    brotli_conf = """
# Brotli compression
load_module modules/ngx_http_brotli_filter_module.so;
load_module modules/ngx_http_brotli_static_module.so;
"""
    # Add load_module at the top (before events block)
    if 'load_module' not in nginx_conf:
        new_conf = nginx_conf.replace('events {', brotli_conf + '\nevents {')
    else:
        new_conf = nginx_conf
    
    # Add brotli settings in http block
    brotli_settings = """
    # Brotli compression
    brotli on;
    brotli_comp_level 4;
    brotli_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
"""
    if 'brotli on' not in new_conf:
        new_conf = new_conf.replace('    gzip_min_length', brotli_settings + '\n    gzip_min_length')
    
    # Write updated config
    code, r = run(f"echo '{new_conf}' > /etc/nginx/nginx.conf")
    print(f"Updated nginx.conf: {r}")

# Now update the CGCPT section in ai-website config
# Add long cache for hashed assets
cgcpt_assets_config = """
        # CGCPT hashed assets - cache for 1 year
        location /CGCPT/assets/ {
            alias /opt/CGCPT/root/CGCPT/assets/;
            expires 365d;
            add_header Cache-Control "public, immutable";
            add_header X-Content-Type-Options "nosniff";
            access_log off;
        }
"""

# Check if we already have the assets location
if '/CGCPT/assets/' not in current_config:
    # Add before the CGCPT api location
    new_config = current_config.replace(
        "location /CGCPT/api/",
        cgcpt_assets_config + "\n        location /CGCPT/api/"
    )
    code, r = run(f"""cat > /tmp/ai-website-new << 'NGINXEOF'
{new_config}
NGINXEOF
""")
    code, r = run("cp /etc/nginx/sites-available/ai-website /etc/nginx/sites-available/ai-website.bak")
    code, r = run("cp /tmp/ai-website-new /etc/nginx/sites-available/ai-website")
    print(f"Updated ai-website config")

# Test nginx
code, r = run("nginx -t 2>&1")
print(f"nginx test: {r}")

if 'successful' in r:
    code, r = run("systemctl reload nginx 2>&1")
    print(f"nginx reload: OK")
else:
    # Restore backup
    code, r = run("cp /etc/nginx/sites-available/ai-website.bak /etc/nginx/sites-available/ai-website")
    print(f"Restored backup, error was: {r}")

client.close()
