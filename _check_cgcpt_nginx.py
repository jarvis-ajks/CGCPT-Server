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


# Check the current CGCPT section in ai-website
code, r = run("grep -n 'CGCPT' /etc/nginx/sites-available/ai-website")
print(f"CGCPT lines:\n{r}")

# Show the full CGCPT section
code, r = run("sed -n '/location.*CGCPT/,/}/p' /etc/nginx/sites-available/ai-website | head -40")
print(f"\nCGCPT section:\n{r}")

# The issue is that the /CGCPT/assets/ location might not be matching
# because the main /CGCPT/ location catches everything first
# Let me check what location blocks exist
code, r = run("grep 'location' /etc/nginx/sites-available/ai-website | grep -i cgcpt")
print(f"\nCGCPT locations:\n{r}")

client.close()
