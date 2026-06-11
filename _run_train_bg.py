import paramiko
import os
import time

HOST = "118.31.164.41"
USER = "root"
KEY = r"D:\Projects\CGCPT-Server\id_ed25519"


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, key_filename=KEY, timeout=30)
    return ssh


def run_cmd(ssh, cmd, timeout=30):
    print(f"\n>>> {cmd[:150]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    return out, err


def main():
    ssh = connect()
    print("[OK] Connected")

    print("\n=== Starting training in background ===")
    run_cmd(
        ssh,
        "nohup /opt/CGCPT/venv/bin/python3 /opt/CGCPT/_run_train.py > /opt/CGCPT/_train_output.log 2>&1 & echo $!",
    )

    print("\n=== Waiting for training to complete (polling) ===")
    for i in range(60):
        time.sleep(10)
        out, _ = run_cmd(ssh, "ps aux | grep _run_train.py | grep -v grep", timeout=15)
        if "_run_train" not in out:
            print("Training process finished!")
            break
        print(f"Still running... ({(i+1)*10}s elapsed)")

    print("\n=== Training output ===")
    run_cmd(ssh, "cat /opt/CGCPT/_train_output.log", timeout=30)

    print("\n=== Verify API ===")
    run_cmd(ssh, "curl -s http://localhost/CGCPT/api/health | python3 -m json.tool")
    run_cmd(ssh, "curl -s http://localhost:5001/api/health | python3 -m json.tool")

    ssh.close()
    print("\n=== All done ===")


if __name__ == "__main__":
    main()
