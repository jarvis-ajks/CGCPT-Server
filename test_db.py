import paramiko
ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41',username='root',password='Aa123456',timeout=30)
def run(cmd):
    _,o,e=ssh.exec_command(cmd,timeout=30)
    return o.read().decode().strip(), e.read().decode().strip()

out, _ = run('ls -la /opt/CGCPT/backend/database/ | head -30')
print('DB DIRS:', out)

out, _ = run('ls /opt/CGCPT/backend/database/Raw_Proto_*/  2>/dev/null | head -5')
print('RAW:', out[:300])

out, _ = run('ls /opt/CGCPT/backend/database/Verified_Proto_*/  2>/dev/null | head -5')
print('VERIFIED:', out[:300])

out, _ = run('ls /opt/CGCPT/backend/database/Proto_*.json 2>/dev/null')
print('PROTO JSON:', out)

ssh.close()
