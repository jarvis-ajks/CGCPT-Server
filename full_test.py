import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip()[:5000])
    if err.strip():
        print("[stderr]", err.strip()[:2000])


print("=== Full API test suite ===")

print("1. Stats API")
run(
    'curl -s http://118.31.164.41/CGCPT/api/stats | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Materials: {d["total_materials"]}, Prototypes: {d["unique_topologies"]}, Elements: {d["unique_elements"]}")"'
)

print()
print("2. Prototypes API")
run(
    'curl -s http://118.31.164.41/CGCPT/api/prototypes | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Total prototypes: {d["total"]}")"'
)

print()
print("3. Materials API")
run(
    'curl -s "http://118.31.164.41/CGCPT/api/materials?per_page=2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Total materials: {d["total"]}, Page: {d["page"]}")"'
)

print()
print("4. Material Detail API")
run(
    'curl -s http://118.31.164.41/CGCPT/api/materials/mp-2998 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Formula: {d["formula"]}, SG: {d["space_group"]}, Verified: {d["verified"]}")"'
)

print()
print("5. Search API")
run(
    'curl -s "http://118.31.164.41/CGCPT/api/search?q=BaTiO3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Results: {d["total"]}")"'
)

print()
print("6. Elements API")
run(
    'curl -s http://118.31.164.41/CGCPT/api/elements | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Total elements: {d["total"]}")"'
)

print()
print("7. Classifications API")
run(
    'curl -s http://118.31.164.41/CGCPT/api/classifications | python3 -c "import sys,json; d=json.load(sys.stdin); print(f"Topologies: {len(d["by_topology"])}, Space groups: {len(d["by_space_group"])}")"'
)

print()
print("8. Static assets test")
run(
    'curl -s -o /dev/null -w "%{http_code} %{size_download}" http://118.31.164.41/CGCPT/assets/index-CfCqO3cC.js'
)
run(
    'curl -s -o /dev/null -w "%{http_code} %{size_download}" http://118.31.164.41/CGCPT/assets/index-BqpHRU_p.css'
)
run(
    'curl -s -o /dev/null -w "%{http_code} %{size_download}" http://118.31.164.41/CGCPT/favicon.svg'
)

print()
print("9. SPA routing test (should return index.html)")
run('curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/materials')
run('curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/prototypes')

print()
print("10. Memory check")
run("free -h")
run("ps aux --sort=-%mem | head -5")

ssh.close()
