import paramiko
import os
import time
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

sftp = client.open_sftp()


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


def upload_dir(local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        for f in files:
            local_path = os.path.join(root, f)
            rel = os.path.relpath(local_path, local_dir)
            remote_path = f"{remote_dir}/{rel.replace(os.sep, '/')}"
            try:
                sftp.stat(os.path.dirname(remote_path))
            except FileNotFoundError:
                parts = remote_path.split("/")
                path = ""
                for p in parts[:-1]:
                    path += "/" + p if path else "/" + p
                    try:
                        sftp.stat(path)
                    except FileNotFoundError:
                        sftp.mkdir(path)
            sftp.put(local_path, remote_path)


# Deploy frontend
print("=== Deploying frontend ===")
run("rm -rf /opt/CGCPT/root/CGCPT/assets")
upload_dir(r"d:\Projects\CGCPT-Server\web\dist", "/opt/CGCPT/root/CGCPT")
print("Frontend deployed!")

# Verify
print("\n=== Final Verification ===")

tests = []

# 1. Frontend
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/")
tests.append(("Frontend", r == "200", f"HTTP {r}"))

# 2. API
code, r = run(
    "curl -s http://localhost/CGCPT/api/stats | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"total_materials\",0))'"
)
tests.append(("API /stats", r.strip() == "2460", f"{r.strip()} materials"))

# 3. Health
code, r = run("curl -s http://localhost:5001/api/health")
try:
    h = json.loads(r)
    tests.append(
        (
            "Health check",
            h.get("status") == "ok",
            f"uptime={h.get('uptime_seconds')}s, mem={h.get('memory',{}).get('percent',0)}%",
        )
    )
except:
    tests.append(("Health check", False, r[:100]))

# 4. Cache headers
code, r = run("curl -sI http://localhost/CGCPT/api/stats | grep -i cache-control")
tests.append(("Cache headers", "max-age" in r, r.strip()))

# 5. Static asset cache
code, r = run(
    "curl -sI http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js | grep -i cache-control"
)
tests.append(("Asset cache", "immutable" in r or "365" in r, r.strip()))

# 6. Brotli
code, r = run(
    "curl -sI -H 'Accept-Encoding: br,gzip' http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js | grep -i content-encoding"
)
tests.append(("Brotli/gzip", "br" in r or "gzip" in r, r.strip()))

# 7. Security headers
code, r = run("curl -sI http://localhost/CGCPT/ | grep -i 'x-frame\\|x-content'")
tests.append(
    ("Security headers", "X-Frame" in r or "X-Content" in r, r.strip() if r.strip() else "none")
)

# 8. Prediction
code, r = run(
    "python3 -c \"import json,urllib.request; data=json.dumps({'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/test_XO3_M7_XO3_M7_XO3_XO3_1.cif').read()}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={'Content-Type':'application/json'}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print(d.get('predicted_topology','?'), d.get('confidence',0))\""
)
parts = r.strip().split()
tests.append(("Prediction", len(parts) >= 2 and parts[0] == "XO3-M7-XO3-M7-XO3-XO3", r.strip()))

# 9. fail2ban
code, r = run("systemctl is-active fail2ban")
tests.append(("fail2ban", r.strip() == "active", r.strip()))

# 10. Memory
code, r = run("free -h | head -2")
lines = r.strip().split("\n")
tests.append(("Memory", True, lines[1].strip() if len(lines) > 1 else r[:100]))

# 11. Service
code, r = run("systemctl is-active cgcpt")
tests.append(("CGCPT service", r.strip() == "active", r.strip()))

# Summary
print("\n" + "=" * 60)
print("FINAL VERIFICATION RESULTS")
print("=" * 60)
all_pass = True
for name, ok, detail in tests:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {name}: {detail}")

print(f"\n{'ALL TESTS PASSED!' if all_pass else 'SOME TESTS FAILED!'}")

# Performance comparison
print("\n=== Performance Comparison ===")
code, r = run(
    "curl -s -o /dev/null -w '%{time_total}s %{size_download}B' http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js"
)
print(f"React vendor JS: {r}")

code, r = run(
    "curl -s -o /dev/null -w '%{time_total}s %{size_download}B' -H 'Accept-Encoding: br,gzip' http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js"
)
print(f"React vendor JS (compressed): {r}")

code, r = run(
    "curl -s -o /dev/null -w '%{time_total}s %{size_download}B' -H 'Accept-Encoding: br,gzip' http://localhost/CGCPT/assets/vendor-three-Kl_qsPTx.js"
)
print(f"Three.js chunk (compressed): {r}")

sftp.close()
client.close()
