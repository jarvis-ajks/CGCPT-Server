import paramiko
import sys

HOST = '10.21.22.100'
USER = 'jarvisajks'
PASS = 'Jarvis666'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=600):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out.strip(), err.strip()

VENV = '/archive/jarvisajks/cgcpt-stacking/venv'
PIP = f'{VENV}/bin/pip'

mirrors = [
    '-i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn',
    '-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com',
    '-i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com',
    '--index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org',
]

pkgs = 'numpy scikit-learn joblib pymatgen'

for i, mirror_args in enumerate(mirrors):
    print(f"\n尝试镜像 {i+1}/{len(mirrors)}: {mirror_args[:50]}...")
    cmd = f'{PIP} install {mirror_args} {pkgs} 2>&1 | tail -8'
    out, err = run(cmd, timeout=600)
    print(out)

    out2, _ = run(f'{VENV}/bin/python -c "import numpy; print(\'numpy OK:\', numpy.__version__)" 2>&1')
    if 'OK' in out2:
        print(f"  numpy安装成功! {out2}")
        break
    else:
        print(f"  仍然失败")

print("\n最终验证...")
out, _ = run(f'cd /archive/jarvisajks/cgcpt-stacking && {VENV}/bin/python -c "import stacking_analyzer; print(\'pymatgen=\', stacking_analyzer.HAS_PYMATGEN, \'sklearn=\', stacking_analyzer.HAS_SKLEARN)" 2>&1')
print(f"  {out}")

ssh.close()
print("完成!")
