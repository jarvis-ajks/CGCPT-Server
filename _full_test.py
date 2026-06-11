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


# Remove conflicting cgcpt site config (we use ai-website instead)
code, r = run("rm -f /etc/nginx/sites-enabled/cgcpt")
print(f"Removed cgcpt site: {r}")

code, r = run("nginx -t 2>&1")
print(f"nginx test: {r}")

code, r = run("systemctl reload nginx 2>&1")
print(f"nginx reload: {r}")

print("\n=== Full test ===")

# Test frontend
code, r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/")
print(f"Frontend: HTTP {r}")

# Test API via nginx
code, r = run("curl -s http://localhost/CGCPT/api/stats")
try:
    data = json.loads(r)
    print(
        f"API via nginx: total_materials={data.get('total_materials')}, unique_topologies={data.get('unique_topologies')}"
    )
except:
    print(f"API via nginx: FAILED - {r[:200]}")

# Test API direct
code, r = run("curl -s http://localhost:5001/api/stats")
try:
    data = json.loads(r)
    print(f"API direct: total_materials={data.get('total_materials')}")
except:
    print(f"API direct: FAILED")

# Test stacking models
code, r = run("curl -s http://localhost/CGCPT/api/stacking/models")
try:
    data = json.loads(r)
    print(f"Stacking models: {data}")
except:
    print(f"Stacking models: {r[:200]}")

# Test prediction with a simple CIF
test_cif = """data_test
_cell_length_a 4.2
_cell_length_b 4.2
_cell_length_c 4.2
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_symmetry_space_group_name_H-M 'Pm-3m'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Ba1 Ba 0.0 0.0 0.0
Ti1 Ti 0.5 0.5 0.5
O1 O 0.5 0.5 0.0
O2 O 0.5 0.0 0.5
O3 O 0.0 0.5 0.5
"""

import urllib.request
import urllib.parse

# Find available model
code, r = run("ls /opt/CGCPT/models/*.pkl")
print(f"\nAvailable models: {r}")

# Get model list via API
code, r = run("curl -s http://localhost:5001/api/stacking/models")
try:
    data = json.loads(r)
    models = data.get("models", [])
    if models:
        model_id = models[0].get("model_id", "")
        print(f"Using model: {model_id}")

        # Test prediction
        payload = json.dumps({"model_id": model_id, "cif_text": test_cif})
        code, r2 = run(
            f"curl -s -X POST http://localhost:5001/api/stacking/predict -H 'Content-Type: application/json' -d '{payload}'"
        )
        try:
            pred = json.loads(r2)
            print(
                f"Prediction result: success={pred.get('success')}, topology={pred.get('predicted_topology')}, confidence={pred.get('confidence')}"
            )
        except:
            print(f"Prediction raw: {r2[:300]}")
    else:
        print("No models available")
except Exception as e:
    print(f"Model list error: {e}")

# Memory check
code, r = run("free -h | head -3")
print(f"\nMemory:\n{r}")

# Service check
code, r = run("systemctl status cgcpt --no-pager | head -8")
print(f"Service:\n{r}")

client.close()
print("\n=== All tests complete! ===")
