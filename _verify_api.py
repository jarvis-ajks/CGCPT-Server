import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace').strip(), stderr.read().decode('utf-8', errors='replace').strip()

# Get the full formatted API response
print('=== 验证API: improvement_history (通过nginx) ===')
out, err = run('curl -s http://127.0.0.1/CGCPT/api/stacking/improvement_history | python3 -m json.tool')
print(out)

ssh.close()
