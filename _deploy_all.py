import paramiko
import os
import time
import stat

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
REMOTE_FRONTEND_DIR = "/opt/CGCPT/root/CGCPT/"
REMOTE_BACKEND_FILE = "/opt/CGCPT/api_server.py"
LOCAL_FRONTEND_DIR = r"d:\Projects\CGCPT-Server\web\dist"
LOCAL_BACKEND_FILE = r"d:\Projects\CGCPT-Server\api_server.py"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def run_cmd(ssh, cmd, timeout=30):
    log(f"执行命令: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if out.strip():
        log(f"STDOUT:\n{out.strip()}")
    if err.strip():
        log(f"STDERR:\n{err.strip()}")
    log(f"退出码: {exit_code}")
    return out, err, exit_code


def upload_dir_recursive(sftp, local_dir, remote_dir):
    log(f"上传目录: {local_dir} -> {remote_dir}")
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)

    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = remote_dir + "/" + item
        if os.path.isdir(local_path):
            upload_dir_recursive(sftp, local_path, remote_path)
        else:
            log(f"  上传文件: {item}")
            sftp.put(local_path, remote_path)


def main():
    log("=" * 60)
    log("CGCPT 部署脚本启动")
    log("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    log(f"连接服务器 {HOST}...")
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    log("SSH 连接成功")

    sftp = ssh.open_sftp()
    log("SFTP 通道已建立")

    # ========== Part 1: 部署前端 ==========
    log("\n" + "=" * 60)
    log("Part 1: 部署前端")
    log("=" * 60)

    log("清除旧前端文件...")
    run_cmd(ssh, f"rm -rf {REMOTE_FRONTEND_DIR}assets/ {REMOTE_FRONTEND_DIR}index.html")

    log("上传前端文件...")
    upload_dir_recursive(sftp, LOCAL_FRONTEND_DIR, REMOTE_FRONTEND_DIR)

    log("验证前端文件...")
    run_cmd(ssh, f"ls -la {REMOTE_FRONTEND_DIR}")
    run_cmd(ssh, f"ls -la {REMOTE_FRONTEND_DIR}assets/ | head -10")

    # ========== Part 2: 部署后端 ==========
    log("\n" + "=" * 60)
    log("Part 2: 部署后端")
    log("=" * 60)

    log(f"上传 api_server.py -> {REMOTE_BACKEND_FILE}")
    sftp.put(LOCAL_BACKEND_FILE, REMOTE_BACKEND_FILE)
    log("api_server.py 上传完成")

    log("重启 cgcpt 服务...")
    run_cmd(ssh, "systemctl restart cgcpt", timeout=30)

    log("等待服务启动...")
    time.sleep(3)

    log("检查服务状态...")
    run_cmd(ssh, "systemctl status cgcpt --no-pager -l", timeout=15)

    # ========== Part 3: 验证 ==========
    log("\n" + "=" * 60)
    log("Part 3: 验证部署")
    log("=" * 60)

    log("--- 3.1 检查前端 HTTP 头 ---")
    run_cmd(ssh, "curl -sI http://localhost/CGCPT/")

    log("--- 3.2 检查 API 健康状态 ---")
    run_cmd(ssh, "curl -s http://localhost/CGCPT/api/health | python3 -m json.tool")

    log("--- 3.3 检查 API stats 缓存 (第一次) ---")
    run_cmd(ssh, "time curl -s http://localhost/CGCPT/api/stats > /dev/null")

    log("--- 3.3 检查 API stats 缓存 (第二次, 应更快) ---")
    run_cmd(ssh, "time curl -s http://localhost/CGCPT/api/stats > /dev/null")

    log("--- 3.4 检查 assets 目录 ---")
    run_cmd(ssh, "ls -la /opt/CGCPT/root/CGCPT/assets/ | head -5")

    # ========== 清理 ==========
    sftp.close()
    ssh.close()
    log("\n" + "=" * 60)
    log("部署完成! 连接已关闭")
    log("=" * 60)


if __name__ == "__main__":
    main()
