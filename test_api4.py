import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=60)
    return o.read().decode().strip(), e.read().decode().strip()


out, err = run("cp /opt/CGCPT/stacking_analyzer.py /opt/CGCPT/backend/stacking_analyzer.py")
print("COPY:", out, err[:100])

out, err = run("cp /opt/CGCPT/api_server.py /opt/CGCPT/backend/api_server.py")
print("COPY API:", out, err[:100])

out, err = run("mkdir -p /opt/CGCPT/backend/uploads /opt/CGCPT/backend/models")
print("MKDIR:", out, err[:100])

out, err = run("systemctl restart cgcpt")
print("RESTART:", out, err[:100])

import time

time.sleep(4)

out, err = run("curl -s -X POST http://127.0.0.1:5001/api/stacking/scan")
print("SCAN:", out[:500])

out, err = run("curl -s http://127.0.0.1:5001/api/stacking/models")
print("MODELS:", out[:300])

ssh.close()
