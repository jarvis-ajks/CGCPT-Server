import socket
import time

host = '118.31.164.41'
for port in [22, 80, 443, 2222, 8022, 8443]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port))
        print(f'Port {port}: OPEN')
        if port in [80, 443, 8443]:
            sock.send(b'GET /CGCPT/ HTTP/1.0\r\nHost: 118.31.164.41\r\n\r\n')
            data = sock.recv(4096)
            resp = data[:200].decode(errors='replace')
            print(f'  HTTP: {resp}')
        elif port == 22:
            sock.send(b'SSH-2.0-Test\r\n')
            data = sock.recv(4096)
            resp = data[:200].decode(errors='replace')
            print(f'  SSH: {resp}')
    except socket.timeout:
        print(f'Port {port}: TIMEOUT')
    except ConnectionRefusedError:
        print(f'Port {port}: REFUSED')
    except Exception as e:
        print(f'Port {port}: {type(e).__name__}: {e}')
    finally:
        sock.close()
