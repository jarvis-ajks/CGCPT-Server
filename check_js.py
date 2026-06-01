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
        print(out.strip()[:5000])
    if err.strip():
        print('[stderr]', err.strip()[:2000])

print('=== Search for localhost in JS ===')
run('grep -o ".localhost." /opt/CGCPT/frontend/assets/*.js | head -20')

print()
print('=== Search for API URL patterns in JS ===')
run('grep -oP ".{0,30}CGCPT/api.{0,30}" /opt/CGCPT/frontend/assets/*.js | head -10')

print()
print('=== Search for any hardcoded URLs ===')
run('grep -oP "http[s]?://[^\"\\x27\\s]+" /opt/CGCPT/frontend/assets/*.js | head -20')

print()
print('=== Check the api client code in built JS ===')
run('grep -oP ".{0,50}BASE.{0,50}" /opt/CGCPT/frontend/assets/*.js | head -10')

print()
print('=== Check what localhost context is ===')
run('grep -oP ".{0,60}localhost.{0,60}" /opt/CGCPT/frontend/assets/*.js | head -10')

ssh.close()
