import paramiko
import sys


def run_ssh(cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("118.31.164.41", port=22, username="root", password="ZS1029384756!", timeout=15)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    client.close()
    return out, err, exit_code


if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:])
    out, err, code = run_ssh(cmd)
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    sys.exit(code)
