import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

cmds = [
    ('sites-enabled', 'ls -la /etc/nginx/sites-enabled/'),
    ('nginx-test', 'nginx -t 2>&1'),
    ('nginx-reload', 'systemctl reload nginx 2>&1'),
    ('http-status', 'curl -s -o /dev/null -w "%{http_code}" http://localhost/'),
    ('front-page', 'curl -s http://localhost/ | head -3'),
    ('api-test', 'curl -s http://localhost/api/stats | python3 -m json.tool | head -10'),
    ('cgcpt-status', 'systemctl status cgcpt --no-pager -l | head -10'),
    ('memory', 'free -h | head -3'),
]

for name, cmd in cmds:
    code, result = run(cmd)
    print(f'=== {name} (exit={code}) ===')
    print(result[:500])
    print()

client.close()
