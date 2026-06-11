import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=60)
    return o.read().decode().strip(), e.read().decode().strip()


out, err = run(
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "import stacking_analyzer; print(stacking_analyzer.HAS_SKLEARN)"'
)
print("HAS_SKLEARN:", out, err)

out, err = run("curl -s -X POST http://127.0.0.1:5001/api/stacking/scan")
print("SCAN:", out[:500])

out, err = run("curl -s http://127.0.0.1:5001/api/stacking/models")
print("MODELS:", out[:300])

ssh.close()
