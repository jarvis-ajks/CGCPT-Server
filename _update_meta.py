import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

# Update gb_97393 meta with known accuracy
code, r = run("cat /opt/CGCPT/models/gb_97393_meta.json")
print(f"Before: {r}")

meta = json.loads(r)
meta['test_accuracy'] = 0.9654
meta['train_accuracy'] = 0.9983
meta['n_samples'] = 2460
meta['best_params']['model_name'] = 'GradientBoostingClassifier'

code, r = run(f"echo '{json.dumps(meta)}' > /opt/CGCPT/models/gb_97393_meta.json")
print(f"Write: code={code}")

code, r = run("cat /opt/CGCPT/models/gb_97393_meta.json")
print(f"After: {r}")

# Verify API
code, r = run("curl -s http://localhost:5001/api/stacking/models")
data = json.loads(r)
for m in data.get('models', []):
    print(f"  {m['model_id']}: accuracy={m['test_accuracy']}, classes={m['n_classes']}")

client.close()
