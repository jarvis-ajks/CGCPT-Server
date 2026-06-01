import paramiko
import json
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

def timed_run(cmd):
    start = time.time()
    code, r = run(cmd)
    elapsed = time.time() - start
    return code, r, elapsed

print("=== 1. Memory Analysis ===")
code, r = run("free -h && echo '---' && ps aux --sort=-%mem | head -10")
print(r)

print("\n=== 2. API Response Times ===")
endpoints = [
    ("GET /api/stats", "curl -s -o /dev/null -w '%{time_total}s' http://localhost:5001/api/stats"),
    ("GET /api/prototypes", "curl -s -o /dev/null -w '%{time_total}s' http://localhost:5001/api/prototypes"),
    ("GET /api/materials", "curl -s -o /dev/null -w '%{time_total}s' 'http://localhost:5001/api/materials?per_page=20'"),
    ("GET /api/elements", "curl -s -o /dev/null -w '%{time_total}s' http://localhost:5001/api/elements"),
    ("GET /api/lattice-types", "curl -s -o /dev/null -w '%{time_total}s' http://localhost:5001/api/lattice-types"),
    ("GET /api/stacking/models", "curl -s -o /dev/null -w '%{time_total}s' http://localhost:5001/api/stacking/models"),
]
for name, cmd in endpoints:
    code, r, t = timed_run(cmd)
    print(f"  {name}: {r} (total: {t:.2f}s)")

print("\n=== 3. First Prediction (cold) vs Subsequent (warm) ===")
code, r = run("systemctl restart cgcpt")
time.sleep(3)

code, r, t = timed_run("python3 -c \"import json,urllib.request; data=json.dumps({'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/test_XO3_M7_XO3_M7_XO3_XO3_1.cif').read()}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={'Content-Type':'application/json'}); urllib.request.urlopen(req,timeout=120).read()\"")
print(f"  Cold prediction: {t:.2f}s")

code, r, t = timed_run("python3 -c \"import json,urllib.request; data=json.dumps({'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/test_XO3_M7_XO3_M7_XO3_XO3_1.cif').read()}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={'Content-Type':'application/json'}); urllib.request.urlopen(req,timeout=60).read()\"")
print(f"  Warm prediction: {t:.2f}s")

print("\n=== 4. Frontend Asset Sizes ===")
code, r = run("ls -lhS /opt/CGCPT/root/CGCPT/assets/ | head -15")
print(r)

print("\n=== 5. nginx Config ===")
code, r = run("cat /etc/nginx/sites-available/ai-website | grep -E 'gzip|cache|buffer|proxy_read|client_max' | head -15")
print(r)

print("\n=== 6. Disk Usage ===")
code, r = run("df -h / && echo '---' && du -sh /opt/CGCPT/* | sort -rh | head -10")
print(r)

print("\n=== 7. Python Process Memory ===")
code, r = run("ps aux | grep gunicorn | grep -v grep | awk '{printf \"PID=%s RSS=%sMB CPU=%s%% CMD=%s\\n\", $2, int($6/1024), $3, $11}'")
print(r)

print("\n=== 8. System Limits ===")
code, r = run("ulimit -a 2>/dev/null | grep -E 'open files|max memory|stack size'")
print(r)

client.close()
