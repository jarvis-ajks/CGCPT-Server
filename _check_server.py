import socket
host = "118.31.164.41"
for port in [22, 80, 443, 5000, 3306, 8080]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((host, port))
        status = "OPEN" if result == 0 else "CLOSED/FILTERED"
        print(f"Port {port}: {status}")
        s.close()
    except Exception as e:
        print(f"Port {port}: ERROR - {e}")

# Try ping
import subprocess
try:
    result = subprocess.run(["ping", "-n", "3", host], capture_output=True, text=True, timeout=15)
    print(f"\nPing result:\n{result.stdout[-200:]}")
except Exception as e:
    print(f"Ping error: {e}")
