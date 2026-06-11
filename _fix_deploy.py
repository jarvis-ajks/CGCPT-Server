import paramiko
import os

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
REMOTE_BASE = "/opt/CGCPT"
LOCAL_DIR = r"d:\Projects\CGCPT-Server"


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        HOST, username=USER, password=PASS, timeout=30, look_for_keys=False, allow_agent=False
    )
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


def upload_file(sftp, local_path, remote_path):
    remote_path = remote_path.replace("\\", "/")
    print(f"  Upload: {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)


def upload_dir(sftp, local_dir, remote_dir):
    remote_dir = remote_dir.replace("\\", "/")
    print(f"  Upload dir: {local_dir} -> {remote_dir}")
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)

    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = remote_dir + "/" + item
        if os.path.isdir(local_path):
            upload_dir(sftp, local_path, remote_path)
        else:
            upload_file(sftp, local_path, remote_path)


def main():
    print("=" * 60)
    print("CGCPT Fix & Redeploy Script")
    print("=" * 60)

    ssh = connect()
    sftp = ssh.open_sftp()

    print("\n[1] Uploading fixed api_server.py...")
    upload_file(sftp, os.path.join(LOCAL_DIR, "api_server.py"), REMOTE_BASE + "/api_server.py")

    print("\n[2] Fixing web/dist path on server...")
    run_cmd(ssh, "rm -rf /opt/CGCPT/web/dist")
    run_cmd(ssh, "cp -r '/opt/CGCPT/web\\dist' /opt/CGCPT/web/dist")
    run_cmd(ssh, "rm -rf '/opt/CGCPT/web\\dist'")
    run_cmd(ssh, "ls -la /opt/CGCPT/web/dist/")
    run_cmd(ssh, "ls -la /opt/CGCPT/web/dist/assets/ | head -5")

    sftp.close()

    print("\n[3] Verifying api_server import...")
    run_cmd(
        ssh,
        "cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c 'import api_server; print(\"Import OK\")'",
    )

    print("\n[4] Restarting service...")
    run_cmd(ssh, "systemctl restart cgcpt", timeout=30)
    run_cmd(ssh, "sleep 3 && systemctl status cgcpt --no-pager -l", timeout=30)

    print("\n[5] Verifying API...")
    run_cmd(ssh, "curl -s http://localhost:5001/CGCPT/api/stacking/models", timeout=30)

    ssh.close()
    print("\n" + "=" * 60)
    print("Fix & Redeploy complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
