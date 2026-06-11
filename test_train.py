import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=120)
    return o.read().decode().strip(), e.read().decode().strip()


import json

out, err = run(
    'curl -s -X POST http://127.0.0.1:5001/api/stacking/train -H "Content-Type: application/json" -d \'{"test_ratio": 0.2}\''
)
print("TRAIN:", out[:1000])

ssh.close()
