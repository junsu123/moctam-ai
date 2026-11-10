"""TikTok (8096) và Shopee (8095) giả lập: TikTok bắt đăng nhập/captcha; Shopee cho tìm, nhưng trang shop bắt đăng nhập."""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
def mk(kind):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            p = self.path.split("?")[0]
            if kind == "tt":
                body = "<h1>Log in to TikTok</h1><div>Verify to continue: drag the slider (captcha)</div>"
            elif p.startswith("/search_user"):
                body = '<h1>Shop</h1><div><a href="/shop/777">Ngũ Cốc Mẹ Su Official</a></div><div><a href="/shop/778">Trà Thảo Mộc Shop</a></div>'
            else:
                body = "<h1>Shopee</h1><div>Vui lòng đăng nhập để tiếp tục</div>"
            self.send_response(200); self.send_header("content-type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>".encode())
    return H
for port, k in ((8096, "tt"), (8095, "sp")):
    threading.Thread(target=HTTPServer(("127.0.0.1", port), mk(k)).serve_forever, daemon=True).start()
threading.Event().wait()
