import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

def receive_loop(conn):
    while True:
        data = conn.recv(1024)
        if not data:
            print("\ disconnected .", flush=True)
            break
        print("\ recived:", data.decode("utf-8"), flush=True)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"  waiting on port {PORT} ...", flush=True)

    conn, addr = server.accept()
    with conn:
        print(" connected:", addr, flush=True)
        threading.Thread(target=receive_loop, args=(conn,), daemon=True).start()

        while True:
            msg = input( " recive (exit for ): ")
            if msg == "exit":
                break
            conn.sendall(msg.encode("utf-8"))