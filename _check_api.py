import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace').strip(), stderr.read().decode('utf-8', errors='replace').strip()

# Try different API paths
paths = [
    'curl -s http://localhost:5001/CGCPT/api/stacking/improvement_history',
    'curl -s http://localhost:5001/api/stacking/improvement_history',
    'curl -s http://127.0.0.1/CGCPT/api/stacking/improvement_history',
]

for p in paths:
    out, err = run(p)
    print(f'Path: {p}')
    print(f'  Response: {out[:500]}')
    print()

# Check what routes are available
out, err = run('grep -n "improvement_history" /opt/CGCPT/api_server.py')
print(f'improvement_history in api_server.py:\n{out}')

out, err = run('grep -n "@app.route" /opt/CGCPT/api_server.py')
print(f'\nAll routes in api_server.py:\n{out}')

# Check if the route exists in self_improver
out, err = run('grep -n "improvement_history" /opt/CGCPT/self_improver.py')
print(f'\nimprovement_history in self_improver.py:\n{out[:500]}')

# Try the models API to verify the server is working
out, err = run('curl -s http://localhost:5001/api/stacking/models')
print(f'\nmodels API response (first 300 chars):\n{out[:300]}')

ssh.close()
