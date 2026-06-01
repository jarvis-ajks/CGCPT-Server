import paramiko
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

# Deploy backend files
print("=== Deploying backend ===")
sftp.put(r'd:\Projects\CGCPT-Server\api_server.py', '/opt/CGCPT/api_server.py')
print("  api_server.py uploaded")
sftp.put(r'd:\Projects\CGCPT-Server\stacking_analyzer.py', '/opt/CGCPT/stacking_analyzer.py')
print("  stacking_analyzer.py uploaded")

# Fix SSH reload (Ubuntu uses 'ssh' not 'sshd')
code, r = run("systemctl reload ssh 2>&1 || systemctl reload sshd 2>&1")
print(f"SSH reload: {r}")

# Restart CGCPT
code, r = run("systemctl restart cgcpt 2>&1")
print(f"CGCPT restart: {r}")
time.sleep(4)

# Test health
code, r = run("curl -s http://localhost:5001/api/health")
print(f"\nHealth: {r}")

# Test API
code, r = run("curl -s http://localhost/CGCPT/api/stats | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"OK: {d.get(chr(116)+chr(111)+chr(116)+chr(97)+chr(108)+chr(95)+chr(109)+chr(97)+chr(116)+chr(101)+chr(114)+chr(105)+chr(97)+chr(108)+chr(115))} materials\")'")
print(f"API: {r}")

# Test prediction
code, r = run("python3 -c \"import json,urllib.request; data=json.dumps({'model_id':'gb_97393','cif_text':open('/opt/CGCPT/test_cifs/test_XO3_M7_XO3_M7_XO3_XO3_1.cif').read()}).encode(); req=urllib.request.Request('http://localhost:5001/api/stacking/predict',data=data,headers={'Content-Type':'application/json'}); resp=urllib.request.urlopen(req,timeout=60); d=json.loads(resp.read().decode()); print(f'pred={d.get(chr(112)+chr(114)+chr(101)+chr(100)+chr(105)+chr(99)+chr(116)+chr(101)+chr(100)+chr(95)+chr(116)+chr(111)+chr(112)+chr(111)+chr(108)+chr(111)+chr(103)+chr(121))} conf={d.get(chr(99)+chr(111)+chr(110)+chr(102)+chr(105)+chr(100)+chr(101)+chr(110)+chr(99)+chr(101))}')\"")
print(f"Prediction: {r}")

# Memory
code, r = run("free -h | head -3")
print(f"\nMemory:\n{r}")

# fail2ban status
code, r = run("fail2ban-client status sshd 2>&1 | head -8")
print(f"fail2ban:\n{r}")

sftp.close()
client.close()
