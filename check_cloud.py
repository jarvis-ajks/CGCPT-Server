import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41', username='root', password='Aa123456', timeout=30)

def run(cmd):
    print(f'$ {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out.strip()[:3000])
    if err.strip():
        print('[stderr]', err.strip()[:1000])

print('=== 1. Check all running services ===')
run('systemctl list-units --type=service --state=running | grep -E "cgcpt|nginx|gunicorn"')

print()
print('=== 2. Check gunicorn is running on cloud ===')
run('ps aux | grep gunicorn')

print()
print('=== 3. Check nginx config for CGCPT ===')
run('grep -A 20 "CGCPT" /etc/nginx/sites-available/ai-website')

print()
print('=== 4. Test frontend page from cloud ===')
run('curl -s http://118.31.164.41/CGCPT/ | head -c 600')

print()
print('=== 5. Test API from cloud ===')
run('curl -s http://118.31.164.41/CGCPT/api/stats | head -c 300')

print()
print('=== 6. Test a material detail API ===')
run('curl -s http://118.31.164.41/CGCPT/api/materials/mp-2998 | head -c 500')

print()
print('=== 7. Check frontend JS file references ===')
run('cat /opt/CGCPT/frontend/index.html')
run('ls -la /opt/CGCPT/frontend/assets/')

print()
print('=== 8. Check JS content for API base URL ===')
run('grep -o "CGCPT/api" /opt/CGCPT/frontend/assets/*.js | head -5')
run('grep -o "localhost" /opt/CGCPT/frontend/assets/*.js | head -5')
run('grep -o "127.0.0.1" /opt/CGCPT/frontend/assets/*.js | head -5')
run('grep -o "5000\\|5001\\|5173\\|5175" /opt/CGCPT/frontend/assets/*.js | head -5')

print()
print('=== 9. Check if port 5001 is listening ===')
run('ss -tlnp | grep 5001')

print()
print('=== 10. Check disk usage ===')
run('du -sh /opt/CGCPT/')

ssh.close()
