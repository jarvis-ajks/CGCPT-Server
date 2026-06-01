import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41', username='root', password='Aa123456', timeout=30)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out.strip(), err.strip()

print('=== Final Verification ===\n')

tests = [
    ('Frontend Page', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/'),
    ('JS Bundle', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/assets/index-CfCqO3cC.js'),
    ('CSS Bundle', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/assets/index-BqpHRU_p.css'),
    ('Favicon', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/favicon.svg'),
    ('API Stats', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/stats'),
    ('API Prototypes', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/prototypes'),
    ('API Materials', 'curl -s -o /dev/null -w "%{http_code}" "http://118.31.164.41/CGCPT/api/materials?per_page=5"'),
    ('API Material Detail', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/materials/mp-2998'),
    ('API Search', 'curl -s -o /dev/null -w "%{http_code}" "http://118.31.164.41/CGCPT/api/search?q=BaTiO3"'),
    ('API Elements', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/elements'),
    ('API Classifications', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/classifications'),
    ('API Lattice Types', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/api/lattice-types'),
    ('SPA Route /materials', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/materials'),
    ('SPA Route /prototypes', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/prototypes'),
    ('SPA Route /generate', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/generate'),
    ('SPA Route /compare', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/compare'),
    ('SPA Route /favorites', 'curl -s -o /dev/null -w "%{http_code}" http://118.31.164.41/CGCPT/favorites'),
]

all_pass = True
for name, cmd in tests:
    out, err = run(cmd)
    status = out.strip()
    passed = status == '200'
    symbol = 'OK' if passed else 'FAIL'
    if not passed:
        all_pass = False
    print(f'  [{symbol}] {name}: {status}')

print()
print('=== Service Status ===')
out, _ = run('systemctl is-active cgcpt nginx')
print(f'  cgcpt + nginx: {out}')

print()
print('=== Memory Usage ===')
out, _ = run('ps aux --sort=-%mem | head -6')
for line in out.split('\n'):
    print(f'  {line}')

print()
print('=== Data Summary ===')
out, _ = run('curl -s http://118.31.164.41/CGCPT/api/stats')
if out:
    import json
    try:
        d = json.loads(out)
        print(f'  Total Materials: {d.get("total_materials", "N/A")}')
        print(f'  Verified Materials: {d.get("verified_materials", "N/A")}')
        print(f'  Unique Topologies: {d.get("unique_topologies", "N/A")}')
        print(f'  Unique Elements: {d.get("unique_elements", "N/A")}')
        print(f'  Unique Formulas: {d.get("unique_formulas", "N/A")}')
    except:
        print(f'  Raw: {out[:200]}')

print()
if all_pass:
    print('=== ALL TESTS PASSED ===')
    print('Access: http://118.31.164.41/CGCPT/')
else:
    print('=== SOME TESTS FAILED ===')

ssh.close()
