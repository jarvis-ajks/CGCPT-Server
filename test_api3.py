import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=60)
    return o.read().decode().strip(), e.read().decode().strip()


out, err = run("cat /etc/systemd/system/cgcpt.service")
print("SERVICE:", out)

out, err = run("head -50 /opt/CGCPT/api_server.py | grep -n stacking")
print("STACKING LINES:", out)

out, err = run('grep -n "def stacking" /opt/CGCPT/api_server.py')
print("STACKING FUNCS:", out)

out, err = run("curl -s http://127.0.0.1:5001/api/stats | head -200")
print("STATS:", out[:200])

ssh.close()
