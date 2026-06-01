import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


class Handler(SimpleHTTPRequestHandler):
    def _proxy_to_backend(self):
        u = urlsplit(self.path)
        upstream_path = u.path
        if upstream_path.startswith("/CGCPT/api/"):
            upstream_path = "/api/" + upstream_path[len("/CGCPT/api/"):]
        upstream_url = urlunsplit(("http", "127.0.0.1:5000", upstream_path, u.query, ""))

        body = None
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b""

        headers = {}
        for k, v in self.headers.items():
            lk = k.lower()
            if lk in ("host", "connection", "content-length", "accept-encoding"):
                continue
            headers[k] = v

        req = urllib.request.Request(upstream_url, data=body, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    lk = k.lower()
                    if lk in ("transfer-encoding", "connection", "content-encoding", "content-length"):
                        continue
                    self.send_header(k, v)
                data = resp.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            ct = e.headers.get("Content-Type")
            if ct:
                self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def translate_path(self, path):
        if path == "/CGCPT" or path.startswith("/CGCPT/"):
            path = path[len("/CGCPT"):] or "/"
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith("/CGCPT/api/"):
            return self._proxy_to_backend()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/CGCPT/api/"):
            return self._proxy_to_backend()
        return self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/CGCPT/api/"):
            return self._proxy_to_backend()
        return self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/CGCPT/api/"):
            return self._proxy_to_backend()
        return self.send_error(404)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            index = os.path.join(path, "index.html")
            if os.path.exists(index):
                self.path = "/CGCPT/index.html"
        else:
            if not os.path.exists(path) and (self.path == "/CGCPT" or self.path.startswith("/CGCPT/")):
                self.path = "/CGCPT/index.html"
        return super().send_head()


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), "web", "dist"))
    host = "127.0.0.1"
    port = 4173
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.serve_forever()
