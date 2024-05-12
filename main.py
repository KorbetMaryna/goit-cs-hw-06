import socket
import mimetypes
import logging

from urllib.parse import urlparse, unquote_plus
from threading import Thread
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BASE_DIR = Path(__file__).parent
URI_DB = f"mongodb://mongodb:27017"

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 3000

SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 5000

CHANK_SIZE = 1024

class MessaserHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        router = urlparse(self.path).path
        match router:
            case "/":
                self.send_html("index.html")
            case "/message":
                self.send_html("message.html")
            case _:
                file = BASE_DIR.joinpath(router[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)
    
    def do_POST(self):
        size = int(self.headers.get('Content-Length'))
        data = self.rfile.read(size).decode("utf-8")

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(data.encode("utf-8"), (SOCKET_HOST, SOCKET_PORT))
            client_socket.close()
        except socket.error:
            logging.error("Can't send message")

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())  

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mimetype = mimetypes.guess_type(filename)[0] or "text/plain"
        self.send_header("Content-type", mimetype)
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), MessaserHandler)
    try:
        logging.info(f"HTTP server started: http://{HTTP_HOST}:{HTTP_PORT}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("HTTP server stopped")
        httpd.server_close()    

def save_to_db(data):
    client = MongoClient(URI_DB, server_api=ServerApi('1'))
    db = client.socket_messages
    try:
        data = unquote_plus(data.decode())
        parse_data = dict([i.split("=") for i in data.split("&")])
        parse_data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.messages.insert_one(parse_data)
        print(parse_data)
    except Exception as e:
        logging.error(e)
    finally:
        client.close()

def run_socket_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Socket server started: http://{SOCKET_HOST}:{SOCKET_PORT}")

    try:
        while True:
            data, address = s.recvfrom(CHANK_SIZE)
            logging.info(f"Received from {address}: {data.decode()}")
            save_to_db(data)
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Socket server stopped")
        s.close()

if __name__ == "__main__": 
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")
    Thread(target=run_http_server, name="HTTP_Server").start()
    Thread(target=run_socket_server, name="SOCKET_Server").start()

