import socket
host = "118.31.164.41"
for port in [22, 2222, 8022, 443, 80, 5000]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((host, port))
        status = "OPEN" if result == 0 else "CLOSED"
        print(f"Port {port}: {status}")
        s.close()
    except Exception as e:
        print(f"Port {port}: ERROR - {e}")
