import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=120)
    return o.read().decode().strip(), e.read().decode().strip()


out, err = run("curl -s -X POST http://127.0.0.1:5001/api/stacking/scan")
import json

data = json.loads(out)
print("Total samples:", data.get("n_samples"))
topos = set()
for s in data.get("samples", []):
    topos.add(s["topology"])
print("Unique topologies:", len(topos))
for t in sorted(topos):
    count = sum(1 for s in data["samples"] if s["topology"] == t)
    print(f"  {t}: {count}")

ssh.close()
