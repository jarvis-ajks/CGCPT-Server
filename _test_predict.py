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


# Test with gb_97393 model (the best one)
model_id = "gb_97393"

# First, test with a real CIF from the database
code, r = run("ls /opt/CGCPT/test_cifs/ 2>/dev/null | head -5")
print(f"Test CIFs: {r}")

# Try to find a real CIF
code, r = run("find /opt/CGCPT/database -name '*.cif' -type f | head -1")
print(f"Sample CIF: {r}")

if r:
    cif_path = r.strip()
    # Read the CIF content
    code, cif_content = run(f"cat {cif_path}")
    print(f"CIF length: {len(cif_content)}")

    # Predict using this real CIF
    payload = json.dumps({"model_id": model_id, "cif_text": cif_content})
    # Use a temp file approach to avoid shell escaping issues
    code, r = run(
        f"python3 -c \"import json,urllib.request; data=json.dumps({{'model_id':'{model_id}','cif_text':open('{cif_path}').read()}}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={{'Content-Type':'application/json'}}); resp=urllib.request.urlopen(req,timeout=60); print(resp.read().decode()[:500])\""
    )
    print(f"Prediction: {r[:500]}")

# Also test the analyze endpoint
code, r = run(
    f"python3 -c \"import json,urllib.request; data=json.dumps({{'cif_text':open('{cif_path}').read()}}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/analyze',data=data,headers={{'Content-Type':'application/json'}}); resp=urllib.request.urlopen(req,timeout=60); print(resp.read().decode()[:500])\""
)
print(f"Analyze: {r[:500]}")

# Check memory after loading pymatgen
code, r = run("free -h | head -3")
print(f"\nMemory after ML load:\n{r}")

client.close()
