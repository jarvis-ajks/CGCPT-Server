import paramiko
import sys

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"


def ssh_exec(cmd, timeout=30):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=timeout)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    client.close()
    return out, err


def run_step(step_name, cmd):
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")
    print(f"CMD: {cmd}")
    print("-" * 60)
    out, err = ssh_exec(cmd)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[STDERR] {err}")
    if not out.strip() and not err.strip():
        print("(no output)")
    return out, err


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "investigate"

    if mode == "investigate":
        print("=" * 60)
        print("  STEP 1: MALWARE INVESTIGATION")
        print("=" * 60)

        run_step("1. Check /dev/shm/", "ls -la /dev/shm/")
        run_step(
            "2. Read malicious script w.sh",
            "cat /dev/shm/w.sh 2>/dev/null || echo 'File not found'",
        )
        run_step(
            "3. Check file types in /dev/shm/",
            "file /dev/shm/* 2>/dev/null || echo 'No files in /dev/shm/'",
        )
        run_step(
            "4. Check running processes from /dev/shm",
            "ps aux | grep -E '/dev/shm|w\\.sh|astats|netai|kstats' | grep -v grep",
        )
        run_step("5. Check high CPU processes", "ps aux --sort=-%cpu | head -10")
        run_step("6. Check network connections", "ss -tlnp | head -20")
        run_step("7. Check crontab for root", "crontab -l 2>/dev/null || echo 'No crontab'")
        run_step("8. Check /etc/crontab", "cat /etc/crontab")
        run_step(
            "9. Check cron.d", "ls -la /etc/cron.d/ && echo '---' && cat /etc/cron.d/* 2>/dev/null"
        )
        run_step(
            "10. Check authorized_keys",
            "cat /root/.ssh/authorized_keys 2>/dev/null || echo 'No authorized_keys'",
        )
        run_step(
            "11. Check suspicious systemd services",
            "systemctl list-units --type=service --state=running | grep -v -E 'ssh|nginx|mysql|fail2ban|cgcpt|systemd|dbus|cron|rsyslog|snap|udev|user@'",
        )
        run_step(
            "12. Check /tmp for suspicious files", "ls -la /tmp/ | grep -v -E 'systemd|ssh|snap'"
        )

    elif mode == "cleanup":
        print("=" * 60)
        print("  STEP 2: MALWARE CLEANUP")
        print("=" * 60)

        run_step(
            "1. Identify malicious PIDs",
            "ps aux | grep -E '/dev/shm|w\\.sh|astats|netai|kstats' | grep -v grep | awk '{print $2}'",
        )
        out, _ = ssh_exec(
            "ps aux | grep -E '/dev/shm|w\\.sh|astats|netai|kstats' | grep -v grep | awk '{print $2}'"
        )
        pids = [p.strip() for p in out.strip().split("\n") if p.strip()]
        if pids:
            kill_cmd = f"kill -9 {' '.join(pids)}"
            run_step(f"1b. Kill malicious processes (PIDs: {pids})", kill_cmd)
        else:
            print("\n[INFO] No malicious processes found to kill.")

        run_step(
            "2. Remove known malicious files",
            "rm -f /dev/shm/w.sh /dev/shm/astats /dev/shm/netai /dev/shm/kstats 2>/dev/null; echo 'Done'",
        )
        run_step(
            "3. Remove ALL files from /dev/shm/",
            "find /dev/shm/ -type f -delete 2>/dev/null; echo 'Done'",
        )
        run_step(
            "4. Clean malicious crontab entries",
            "crontab -l 2>/dev/null | grep -v 'w.sh' | grep -v 'astats' | grep -v 'netai' | grep -v 'kstats' | crontab -; echo 'Crontab cleaned'",
        )
        run_step("4b. Verify crontab", "crontab -l 2>/dev/null || echo 'No crontab'")
        run_step(
            "5. Check /tmp for suspicious executables",
            "find /tmp/ -type f -executable 2>/dev/null | head -20",
        )
        out2, _ = ssh_exec("find /tmp/ -type f -executable 2>/dev/null | head -20")
        suspicious_tmp = [
            f.strip()
            for f in out2.strip().split("\n")
            if f.strip() and "systemd" not in f.strip() and "ssh" not in f.strip()
        ]
        if suspicious_tmp:
            rm_tmp_cmd = f"rm -f {' '.join(suspicious_tmp)}"
            run_step(f"5b. Remove suspicious /tmp files: {suspicious_tmp}", rm_tmp_cmd)
        else:
            print("\n[INFO] No suspicious executables in /tmp.")
        run_step("6. Check persistence - .ssh directory", "ls -la /root/.ssh/")

    elif mode == "verify":
        print("=" * 60)
        print("  STEP 3: VERIFICATION")
        print("=" * 60)

        run_step(
            "1. Check for remaining /dev/shm processes",
            "ps aux | grep -E '/dev/shm|w\\.sh' | grep -v grep",
        )
        run_step("2. Check /dev/shm/ contents", "ls -la /dev/shm/")
        run_step("3. Check crontab", "crontab -l 2>/dev/null || echo 'No crontab'")
        run_step("4. Check CPU usage", "ps aux --sort=-%cpu | head -5")
