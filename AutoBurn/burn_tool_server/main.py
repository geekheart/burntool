from .auto_flash import auto_flash
from email.message import Message
from pathlib import Path
import click
from . import log
import logging
from email.parser import BytesParser
from email.policy import default
import http.server
import socketserver

CONFIG_BIN_PATH = Path(__file__).parent.parent/"bin"
CONFIG_BIN_NAME = CONFIG_BIN_PATH/"received_firmware.fwpkg"

com_port = 3  # Default COM port, can be changed via command line


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload':
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"status": "fail", "reason": "Not found"}')
            return
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b'{"status": "fail", "reason": "Invalid content type"}')
            return
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # 解析多部分表单数据
        parser = BytesParser(policy=default)
        message: Message[str, str] = parser.parsebytes(
            b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)

        if not message.is_multipart():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b'{"status": "fail", "reason": "Invalid form data"}')
            return
        com = "3"
        firmware_data = None
        baud = "115200"
        for part in message.iter_parts():
            content_disposition = part.get("Content-Disposition", "")
            if "form-data" in content_disposition:
                name = part.get_param("name", header="Content-Disposition")
                if name == "file" and part.get_filename() == "firmware.bin":
                    firmware_data = part.get_payload(decode=True)
                    CONFIG_BIN_NAME.parent.mkdir(parents=True, exist_ok=True)
                    with CONFIG_BIN_NAME.open("wb") as f:
                        f.write(firmware_data)
                elif name == "com":
                    com = part.get_payload(decode=False)
                    print(com, type(com))
                elif name == "baud":
                    baud = part.get_payload(decode=False)
                    print(baud, type(baud))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "success", "size": %d}' %
                         len(firmware_data))
        auto_flash(f"COM{com}", CONFIG_BIN_NAME, int(baud))


@click.command()
@click.option('--verbose', '-v', is_flag=True, help="打开调试的log")
@click.option('--port', '-p', default=1997, type=int, help='开启服务的端口号')
def server(verbose, port) -> None:
    if verbose:
        log.logging_setup(level=log.logging.DEBUG)
    else:
        log.logging_setup(level=log.logging.INFO)

    handler = SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"Serving on port {port}")
        httpd.serve_forever()


if __name__ == "__main__":
    server()
