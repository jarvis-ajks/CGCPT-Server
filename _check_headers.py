import paramiko

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
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


# Full headers check
code, r = run("curl -sI http://localhost/CGCPT/assets/vendor-react-076Dd0Bx.js")
print(f"Asset full headers:\n{r}")

print("---")

code, r = run("curl -sI http://localhost/CGCPT/")
print(f"Page full headers:\n{r}")

client.close()
