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
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()


# More aggressive MySQL optimization
mysql_opt = """[mysqld]
innodb_buffer_pool_size = 64M
innodb_log_buffer_size = 2M
innodb_log_file_size = 16M
max_connections = 20
table_open_cache = 400
table_open_cache_instances = 1
thread_cache_size = 2
key_buffer_size = 8M
read_buffer_size = 64K
read_rnd_buffer_size = 128K
sort_buffer_size = 128K
join_buffer_size = 128K
tmp_table_size = 8M
max_heap_table_size = 8M
performance_schema = OFF
innodb_flush_method = O_DIRECT
innodb_flush_log_at_trx_commit = 2
"""

sftp = client.open_sftp()
with sftp.open("/etc/mysql/mysql.conf.d/low-memory.cnf", "w") as f:
    f.write(mysql_opt)
sftp.close()

code, r = run("systemctl restart mysql 2>&1")
print(f"MySQL restart: {r}")

import time

time.sleep(5)

code, r = run(
    "ps aux | grep mysql | grep -v grep | awk '{sum+=int($6/1024)} END {print sum\"MB total\"}'"
)
print(f"MySQL memory: {r}")

code, r = run("free -h | head -3")
print(f"System memory:\n{r}")

# Also check if ai-website Java app can be optimized
code, r = run('ps aux | grep java | grep -v grep | awk \'{print "Java RSS=" int($6/1024) "MB"}\'')
print(f"\n{r}")

client.close()
