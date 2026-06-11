import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456")

stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1/CGCPT/api/stacking/models")
data = json.loads(stdout.read().decode())
models = data.get("models", [])
print(f"Models: {len(models)} available")
for m in models[:5]:
    print(f"  {m['model_id']}: acc={m['test_accuracy']}, samples={m['n_samples']}")

ssh.close()
