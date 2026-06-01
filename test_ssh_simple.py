
import paramiko
import sys

print('开始测试 SSH 连接...')
print(f'Python 版本: {sys.version}')

try:
    print('正在导入 paramiko...')
    import paramiko
    print('✓ paramiko 导入成功')
    
    print('正在创建 SSHClient...')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print('✓ SSHClient 创建成功')
    
    print('正在连接...')
    client.connect(
        '118.31.164.41',
        port=22,
        username='root',
        key_filename='D:\\Projects\\CGCPT-Server\\id_ed25519',
        timeout=15
    )
    print('✓ 连接成功')
    
    print('正在执行简单命令...')
    stdin, stdout, stderr = client.exec_command('echo "Hello from server" && whoami && pwd')
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print('输出:')
    print(out)
    if err:
        print('错误:')
        print(err)
    
    client.close()
    print('✓ 连接关闭')
    
except Exception as e:
    print(f'错误: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
