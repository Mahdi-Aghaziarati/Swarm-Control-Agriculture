import socket
import threading

SERVER_IP = "10.52.14.61"
PORT = 5000

def receive_loop(s):
    while True:
        data = s.recv(1024)
        if not data:
            print("\n server is disconnected!!", flush=True)
            break
        print("\nپاسخ:", data.decode("utf-8"), flush=True)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(5)
    s.connect((SERVER_IP, PORT))
    s.settimeout(None)

    threading.Thread(target=receive_loop, args=(s,), daemon=True).start()

    while True:
        msg = input(" (exit : ")
        if msg == "exit":
            break
        s.sendall(msg.encode("utf-8"))
