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


# 1. Remove duplicate load_module lines from nginx.conf
code, r = run("sed -i '/^load_module modules\\/ngx_http_brotli/d' /etc/nginx/nginx.conf")
print(f"Removed duplicate load_module: {r}")

# 2. Check if brotli is already loaded via modules-enabled
code, r = run("ls /etc/nginx/modules-enabled/ | grep brotli")
print(f"Modules-enabled brotli: {r}")

# 3. Add brotli settings in http block if not present
code, r = run("grep -c 'brotli on' /etc/nginx/nginx.conf")
if r.strip() == "0":
    # Add brotli settings after gzip settings
    code, r = run(
        """sed -i '/gzip_comp_level/a\\    # Brotli compression\\n    brotli on;\\n    brotli_comp_level 4;\\n    brotli_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;' /etc/nginx/nginx.conf"""
    )
    print(f"Added brotli settings")

# 4. Test nginx
code, r = run("nginx -t 2>&1")
print(f"nginx test: {r}")

if "successful" not in r:
    # Show the problematic config
    code, r2 = run("cat /etc/nginx/nginx.conf")
    print(f"Full config:\n{r2[:2000]}")

# 5. Now update ai-website config for CGCPT static assets caching
code, r = run("cat /etc/nginx/sites-available/ai-website")
current = r

if "/CGCPT/assets/" not in current:
    # Add CGCPT assets caching before the CGCPT api location
    assets_block = """
        # CGCPT hashed assets - cache 1 year
        location /CGCPT/assets/ {
            alias /opt/CGCPT/root/CGCPT/assets/;
            expires 365d;
            add_header Cache-Control "public, immutable";
            add_header X-Content-Type-Options "nosniff";
            access_log off;
        }

"""
    new_config = current.replace(
        "location /CGCPT/api/", assets_block + "        location /CGCPT/api/"
    )

    # Write using SFTP to avoid shell escaping issues
    sftp = client.open_sftp()
    with sftp.open("/etc/nginx/sites-available/ai-website", "w") as f:
        f.write(new_config)
    sftp.close()
    print("Updated ai-website config with CGCPT assets caching")

# 6. Also add security headers to the CGCPT location
code, r = run("cat /etc/nginx/sites-available/ai-website")
current = r

if "X-Frame-Options" not in current:
    # Add security headers to CGCPT root location
    new_config = current.replace(
        "location /CGCPT/ {",
        'location /CGCPT/ {\n            add_header X-Frame-Options "SAMEORIGIN";\n            add_header X-XSS-Protection "1; mode=block";',
    )
    sftp = client.open_sftp()
    with sftp.open("/etc/nginx/sites-available/ai-website", "w") as f:
        f.write(new_config)
    sftp.close()
    print("Added security headers")

# 7. Final test and reload
code, r = run("nginx -t 2>&1")
print(f"Final nginx test: {r}")

if "successful" in r:
    code, r = run("systemctl reload nginx 2>&1")
    print("nginx reloaded successfully!")
else:
    print(f"ERROR: {r}")

client.close()
