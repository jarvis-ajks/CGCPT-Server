import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

tests = []

# 1. Frontend HTML
code, r = run("curl -s http://localhost/CGCPT/ | head -5")
ok = '<html' in r.lower()
tests.append(("Frontend HTML", ok, r[:100]))

# 2. Frontend assets (JS)
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js")
ok = r == '200'
tests.append(("React vendor JS", ok, f"HTTP {r}"))

# 3. Three.js chunk
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/assets/vendor-three-Kl_qsPTx.js")
ok = r == '200'
tests.append(("Three.js chunk", ok, f"HTTP {r}"))

# 4. CSS
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/assets/index-DqPzHtd4.css")
ok = r == '200'
tests.append(("CSS bundle", ok, f"HTTP {r}"))

# 5. API stats
code, r = run("curl -s http://localhost/CGCPT/api/stats")
try:
    d = json.loads(r)
    ok = d.get('total_materials', 0) > 0
    tests.append(("API /stats", ok, f"materials={d.get('total_materials')}, topologies={d.get('unique_topologies')}"))
except:
    tests.append(("API /stats", False, r[:100]))

# 6. API prototypes
code, r = run("curl -s http://localhost/CGCPT/api/prototypes | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"total\",0))'")
ok = int(r) > 0 if r.isdigit() else False
tests.append(("API /prototypes", ok, f"total={r}"))

# 7. Stacking models
code, r = run("curl -s http://localhost/CGCPT/api/stacking/models")
try:
    d = json.loads(r)
    models = d.get('models', [])
    ok = len(models) > 0
    tests.append(("API /stacking/models", ok, f"{len(models)} models"))
except:
    tests.append(("API /stacking/models", False, r[:100]))

# 8. Prediction test (all 9 test CIFs)
correct = 0
total = 0
code, r = run("ls /opt/CGCPT/test_cifs/")
test_files = [f for f in r.strip().split('\n') if f.strip()]
for tf in test_files:
    cif_path = f"/opt/CGCPT/test_cifs/{tf}"
    code, r2 = run(f"python3 -c \"import json,urllib.request; data=json.dumps({{'model_id':'gb_97393','cif_text':open('{cif_path}').read()}}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={{'Content-Type':'application/json'}}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print(d.get('predicted_topology','?'), d.get('confidence',0))\"")
    parts = r2.strip().split()
    if len(parts) >= 2:
        pred = parts[0]
        conf = parts[1]
        expected = tf.replace('test_', '').rsplit('_', 1)[0].replace('_', '-')
        is_correct = pred == expected
        if is_correct:
            correct += 1
        total += 1
        print(f"  {tf}: pred={pred}, expected={expected}, conf={conf}, {'OK' if is_correct else 'WRONG'}")

tests.append(("Prediction accuracy", correct == total, f"{correct}/{total} correct"))

# 9. Memory check
code, r = run("free -h | head -3")
lines = r.strip().split('\n')
mem_line = lines[1] if len(lines) > 1 else ''
tests.append(("Memory usage", True, mem_line.strip()))

# 10. Service status
code, r = run("systemctl is-active cgcpt")
tests.append(("Service status", r.strip() == 'active', r.strip()))

# 11. API via nginx proxy
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/api/stats")
tests.append(("Nginx proxy", r.strip() == '200', f"HTTP {r.strip()}"))

# Summary
print("\n" + "="*60)
print("VERIFICATION RESULTS")
print("="*60)
all_pass = True
for name, ok, detail in tests:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {name}: {detail}")

print(f"\n{'ALL TESTS PASSED!' if all_pass else 'SOME TESTS FAILED!'}")

client.close()
