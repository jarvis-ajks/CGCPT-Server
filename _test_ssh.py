import socket
import time

host = "118.31.164.41"
port = 22

print(f"Testing TCP connection to {host}:{port}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(30)
try:
    sock.connect((host, port))
    print("  TCP connected!")

    print("  Waiting for SSH banner (up to 30s)...")
    start = time.time()
    while time.time() - start < 30:
        try:
            data = sock.recv(4096)
            if data:
                banner = data.decode(errors="replace").strip()
                print(f"  Banner: {banner}")
                break
            else:
                print("  Connection closed")
                break
        except socket.timeout:
            elapsed = int(time.time() - start)
            print(f"  Still waiting... ({elapsed}s)")
    else:
        print("  No banner received within 30s")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")
finally:
    sock.close()
