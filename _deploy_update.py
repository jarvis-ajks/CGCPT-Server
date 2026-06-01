import paramiko
import os
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

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

print("=== Deploying updated frontend ===")
run("rm -rf /opt/CGCPT/root/CGCPT/assets")
run("mkdir -p /opt/CGCPT/root/CGCPT/assets")

web_dist = r"d:\Projects\CGCPT-Server\web\dist"
upload_dir(web_dist, "/opt/CGCPT/root/CGCPT")
print("Frontend uploaded!")

print("\n=== Deploying updated backend ===")
backend_files = ["stacking_analyzer.py", "api_server.py"]
for f in backend_files:
    local_path = os.path.join(r"d:\Projects\CGCPT-Server", f)
    if os.path.exists(local_path):
        sftp.put(local_path, f"/opt/CGCPT/{f}")
        print(f"  Uploaded: {f}")

print("\n=== Restarting service ===")
code, r = run("systemctl restart cgcpt")
print(f"Restart: {r}")
time.sleep(3)

code, r = run("systemctl status cgcpt --no-pager | head -8")
print(f"Status:\n{r}")

print("\n=== Testing ===")
time.sleep(2)

code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/")
print(f"Frontend: HTTP {r}")

code, r = run("curl -s http://localhost/CGCPT/api/stats | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"materials={d[chr(116)+chr(111)+chr(116)+chr(97)+chr(108)+chr(95)+chr(109)+chr(97)+chr(116)+chr(101)+chr(114)+chr(105)+chr(97)+chr(108)+chr(115)]}\")'")
print(f"API: {r}")

code, r = run("curl -s http://localhost/CGCPT/api/stacking/models | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(f\"  {m[chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(95)+chr(105)+chr(100)]}: acc={m[chr(116)+chr(101)+chr(115)+chr(116)+chr(95)+chr(97)+chr(99)+chr(99)+chr(117)+chr(114)+chr(97)+chr(99)+chr(121)]}\") for m in d.get(chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(115),[])]'")
print(f"Models:\n{r}")

# Test prediction
code, r = run("python3 -c \"import json,urllib.request; data=json.dumps({'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/test_XO3_M7_XO3_M7_XO3_XO3_1.cif').read()}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={'Content-Type':'application/json'}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print(f'prediction: {d.get(chr(112)+chr(114)+chr(101)+chr(100)+chr(105)+chr(99)+chr(116)+chr(101)+chr(100)+chr(95)+chr(116)+chr(111)+chr(112)+chr(111)+chr(108)+chr(111)+chr(103)+chr(121))}, confidence: {d.get(chr(99)+chr(111)+chr(110)+chr(102)+chr(105)+chr(100)+chr(101)+chr(110)+chr(99)+chr(101))}')\"")
print(f"Prediction: {r}")

code, r = run("free -h | head -3")
print(f"\nMemory:\n{r}")

sftp.close()
client.close()
print("\nDeployment complete!")
