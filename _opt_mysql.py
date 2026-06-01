import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('118.31.164.41', username='root', password='ZS1029384756!', timeout=30, look_for_keys=False, allow_agent=False)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, (out + err).strip()

# Check current MySQL config
print("=== Current MySQL memory usage ===")
code, r = run("ps aux | grep mysql | grep -v grep | awk '{print \"RSS=\" int($6/1024) \"MB\"}'")
print(r)

# Check MySQL config
print("\n=== MySQL config ===")
code, r = run("cat /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null | grep -v '^#' | grep -v '^$' | head -30")
print(r)

# Check MySQL variables
print("\n=== Key MySQL variables ===")
code, r = run("mysql -e \"SHOW VARIABLES LIKE 'innodb_buffer_pool_size'; SHOW VARIABLES LIKE 'max_connections'; SHOW VARIABLES LIKE 'table_open_cache'; SHOW VARIABLES LIKE 'thread_cache_size';\" 2>/dev/null")
print(r)

# Optimize MySQL for low memory (2GB server)
print("\n=== Optimizing MySQL ===")
mysql_opt = """
[mysqld]
# Low memory optimization for 2GB server
innodb_buffer_pool_size = 128M
innodb_log_buffer_size = 4M
max_connections = 30
table_open_cache = 64
thread_cache_size = 4
key_buffer_size = 16M
read_buffer_size = 128K
read_rnd_buffer_size = 256K
sort_buffer_size = 256K
join_buffer_size = 256K
tmp_table_size = 16M
max_heap_table_size = 16M
performance_schema = OFF
"""

sftp = client.open_sftp()
with sftp.open('/etc/mysql/mysql.conf.d/low-memory.cnf', 'w') as f:
    f.write(mysql_opt)
sftp.close()
print("Created /etc/mysql/mysql.conf.d/low-memory.cnf")

# Restart MySQL
code, r = run("systemctl restart mysql 2>&1")
print(f"MySQL restart: {r}")

import time
time.sleep(3)

# Check new memory
code, r = run("ps aux | grep mysql | grep -v grep | awk '{print \"RSS=\" int($6/1024) \"MB\"}'")
print(f"New MySQL memory: {r}")

# Overall memory
code, r = run("free -h | head -3")
print(f"\nOverall memory:\n{r}")

client.close()
