import paramiko

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30, look_for_keys=False, allow_agent=False)
    return ssh


def run_cmd(ssh, cmd, timeout=300):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    print(f"[EXIT CODE] {exit_code}")
    return out, err, exit_code


def main():
    ssh = connect()

    print("=== Check web/dist path ===")
    run_cmd(ssh, "ls -la /opt/CGCPT/web/")
    run_cmd(ssh, "ls -la '/opt/CGCPT/web\\dist' 2>/dev/null || echo 'web\\dist not found'")
    run_cmd(ssh, "ls -la /opt/CGCPT/web/dist/ 2>/dev/null || echo 'web/dist not found'")

    print("\n=== Check gunicorn error ===")
    run_cmd(ssh, "cd /opt/CGCPT && /opt/CGCPT/venv/bin/gunicorn -c gunicorn.conf.py api_server:app 2>&1 &; sleep 3; kill %1 2>/dev/null")
    run_cmd(ssh, "journalctl -u cgcpt -n 50 --no-pager")

    print("\n=== Check gunicorn.conf.py ===")
    run_cmd(ssh, "cat /opt/CGCPT/gunicorn.conf.py")

    print("\n=== Check api_server import ===")
    run_cmd(ssh, "cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c 'import api_server' 2>&1")

    ssh.close()


if __name__ == "__main__":
    main()
