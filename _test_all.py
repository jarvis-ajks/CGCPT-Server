import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "118.31.164.41",
    username="root",
    password="ZS1029384756!",
    timeout=30,
    look_for_keys=False,
    allow_agent=False,
)


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


# Test with test_cifs
code, r = run("ls /opt/CGCPT/test_cifs/")
test_files = [f for f in r.strip().split("\n") if f.strip()]
print(f"Test CIFs: {test_files}")

for tf in test_files[:9]:
    cif_path = f"/opt/CGCPT/test_cifs/{tf}"
    code, r = run(
        f"python3 -c \"import json,urllib.request; data=json.dumps({{'model_id':'gb_97393','cif_text':open('{cif_path}').read()}}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={{'Content-Type':'application/json'}}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print(d.get('predicted_topology','?'), d.get('confidence',0), d.get('success',False))\""
    )
    # Extract expected topology from filename
    expected = tf.replace("test_", "").rsplit("_", 1)[0].replace("_", "-")
    print(f"  {tf}: predicted={r.strip()}, expected~{expected}")

# Also test via nginx proxy
print("\n=== Test via nginx proxy ===")
code, r = run(
    f"python3 -c \"import json,urllib.request; data=json.dumps({{'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/{test_files[0]}').read()}}).encode(); req=urllib.request.Request('http://localhost/CGCPT/api/stacking/predict',data=data,headers={{'Content-Type':'application/json'}}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print('success:', d.get('success'), 'topology:', d.get('predicted_topology'), 'confidence:', d.get('confidence'))\""
)
print(f"  Via nginx: {r.strip()}")

# Final memory check
code, r = run("free -h | head -3")
print(f"\nFinal memory:\n{r}")

# Check service
code, r = run("ps aux | grep gunicorn | grep -v grep | head -3")
print(f"\nGunicorn processes:\n{r}")

client.close()
print("\nAll tests complete!")
