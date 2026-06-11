import paramiko
import os
import stat

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
REMOTE_BASE = "/opt/CGCPT"

LOCAL_DIR = r"d:\Projects\CGCPT-Server"

UPLOADS = [
    ("stacking_analyzer.py", "stacking_analyzer.py"),
    ("layer_generator.py", "layer_generator.py"),
    ("api_server.py", "api_server.py"),
    ("search_mp.py", "search_mp.py"),
    ("verify_topology.py", "verify_topology.py"),
    ("run_search_topo.py", "run_search_topo.py"),
    ("db_config.py", "db_config.py"),
]

DIR_UPLOADS = [
    ("decision_tree", "decision_tree"),
    (os.path.join("web", "dist"), os.path.join("web", "dist")),
]


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
    print(f"  Upload: {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)


def upload_dir(sftp, local_dir, remote_dir):
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
    print("CGCPT Deployment Script")
    print("=" * 60)

    ssh = connect()
    sftp = ssh.open_sftp()

    print("\n[1/6] Uploading single files...")
    for local_name, remote_name in UPLOADS:
        local_path = os.path.join(LOCAL_DIR, local_name)
        remote_path = REMOTE_BASE + "/" + remote_name
        upload_file(sftp, local_path, remote_path)

    print("\n[2/6] Uploading directories...")
    for local_name, remote_name in DIR_UPLOADS:
        local_path = os.path.join(LOCAL_DIR, local_name)
        remote_path = REMOTE_BASE + "/" + remote_name
        upload_dir(sftp, local_path, remote_path)

    sftp.close()
    print("\n[3/6] All files uploaded successfully!")

    print("\n[4/6] Installing scikit-learn...")
    run_cmd(ssh, "pip3 install scikit-learn", timeout=120)

    print("\n[5/6] Verifying training functionality...")
    train_cmd = "cd /opt/CGCPT && python3 -c \"from stacking_analyzer import train_decision_tree; r = train_decision_tree(max_sequences=200, cv_folds=3); print('Accuracy:', r.get('best_params', {}).get('test_accuracy', 'N/A'))\""
    run_cmd(ssh, train_cmd, timeout=600)

    print("\n[6/6] Restarting service...")
    run_cmd(ssh, "systemctl restart cgcpt", timeout=30)
    run_cmd(ssh, "sleep 3 && systemctl status cgcpt --no-pager -l", timeout=30)

    print("\n[7/6] Verifying API...")
    run_cmd(ssh, "curl -s http://localhost:5001/CGCPT/api/stacking/models", timeout=30)

    ssh.close()
    print("\n" + "=" * 60)
    print("Deployment complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
