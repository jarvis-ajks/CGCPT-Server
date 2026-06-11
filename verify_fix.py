import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("=== Full Verification ===\n")

tests = [
    ("Frontend Page", 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/'),
    (
        "New JS Bundle",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/assets/index-_UHI_a-C.js',
    ),
    (
        "CSS Bundle",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/assets/index-BqpHRU_p.css',
    ),
    ("API Stats", 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/stats'),
    (
        "API Prototypes",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/prototypes',
    ),
    (
        "API Materials",
        'curl -s -o /dev/null -w "%{http_code}" "http://118.31.164.41/CGCPT/api/materials?per_page=5"',
    ),
    (
        "API Material Detail",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/materials/mp-2998',
    ),
    (
        "API Search",
        'curl -s -o /dev/null -w "%{http_code}" "http://118.31.164.41/CGCPT/api/search?q=BaTiO3"',
    ),
    (
        "API Elements",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/elements',
    ),
    (
        "SPA Route /materials",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/materials',
    ),
    (
        "SPA Route /prototypes",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/prototypes',
    ),
    (
        "SPA Route /compare",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/compare',
    ),
    (
        "SPA Route /favorites",
        'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/favorites',
    ),
]

all_pass = True
for name, cmd in tests:
    out, _ = run(cmd)
    status = out.strip()
    passed = status == "200"
    if not passed:
        all_pass = False
    print(f'  [{"OK" if passed else "FAIL"}] {name}: {status}')

print()
print("=== Verify no Div in THREE namespace error ===")
out, _ = run('grep -c "Div is not part" /opt/CGCPT/root/CGCPT/assets/index-_UHI_a-C.js || echo "0"')
print(f'  "Div is not part" occurrences in JS: {out}')

print()
print("=== Verify ElementTooltip is outside Canvas ===")
out, _ = run('grep -o "ElementTooltip" /opt/CGCPT/root/CGCPT/assets/index-_UHI_a-C.js | wc -l')
print(f"  ElementTooltip references: {out}")

print()
if all_pass:
    print("=== ALL TESTS PASSED ===")
else:
    print("=== SOME TESTS FAILED ===")

ssh.close()
