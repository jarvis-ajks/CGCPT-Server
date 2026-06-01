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

print('=== Debug: what does nginx see? ===')
run('namei -l /opt/CGCPT/root/CGCPT/assets/index-CfCqO3cC.js')
run('cat /opt/CGCPT/root/CGCPT/assets/index-CfCqO3cC.js | wc -c')

print()
print('=== Check nginx error log ===')
run('tail -20 /var/log/nginx/error.log')

print()
print('=== Check the full nginx config ===')
run('cat /etc/nginx/sites-available/ai-website | head -60')

print()
print('=== Check if AIclub location is intercepting ===')
run('grep -n "location" /etc/nginx/sites-available/ai-website | head -30')

ssh.close()
