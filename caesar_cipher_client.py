import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json

class CaeserCypherClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Caesar Cypher Client")
        self.root.geometry("700x600")
        
        self.client_socket = None
        self.connected = False
        self.in_chat = False
        
        self.setup_gui()

    def setup_gui(self):

        conn_frame = tk.Frame(self.root)
        conn_frame.pack(pady=10)
        
        tk.Label(conn_frame, text="Server IP:").grid(row=0, column=0, padx=5)
        self.ip_entry = tk.Entry(conn_frame, width=15)
        
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5)
        self.port_entry = tk.Entry(conn_frame, width=10)
        self.port_entry.grid(row=0, column=3, padx=5)
        
        tk.Label(conn_frame, text="Name:").grid(row=1, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(conn_frame, width=20)
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.grid(row=1, column=3, padx=5, pady=5)
        
        self.disconnect_btn = tk.Button(conn_frame, text="Disconnect", 
                                        command=self.disconnect, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=4, padx=5)
        
        message_frame = tk.LabelFrame(self.root, text="Message", padx=10, pady=10)
        message_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.message_label = tk.Label(message_frame, text="Waiting to connect...", 
                                      wraplength=600, justify=tk.LEFT, font=('Arial', 12))
        self.message_label.pack(pady=10)

        answer_frame = tk.Frame(message_frame)
        answer_frame.pack(pady=10)
        
        tk.Label(answer_frame, text="Answer:",font=('Arial', 10)).pack(anchor=tk.W, pady=2,side=tk.LEFT)
        self.answer_entry = tk.Entry(answer_frame, width=30)
        self.answer_entry.pack(side=tk.RIGHT, pady=2)
        
        self.submit_btn = tk.Button(message_frame, text="Submit", 
                                    command=self.submit_answer, state=tk.DISABLED)
        self.submit_btn.pack(pady=10)
        
        score_frame = tk.LabelFrame(self.root, text="Scoreboard", padx=10, pady=10)
        score_frame.pack(padx=10, pady=5, fill=tk.BOTH)
        
        self.scoreboard_text = scrolledtext.ScrolledText(score_frame, height=6, width=80)
        self.scoreboard_text.pack()
        
        tk.Label(self.root, text="Activity Log:").pack()
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Listbox(log_frame, height=20, width=90, 
                                yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.log_text.yview)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)

    def connect_to_server(self):
        server_ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        name = self.name_entry.get().strip()
        
        if not server_ip or not port_str or not name:
            messagebox.showerror("Error", "Please fill in all fields")
            return
            
        try:
            port = int(port_str)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, port))
            
            message = {
                'type': 'connect',
                'name': name
            }
            
            self.client_socket.send((json.dumps(message) + "\n").encode())
            data = self.client_socket.recv(1024).decode()
            response = json.loads(data)
            
            if response['type'] == 'error':
                messagebox.showerror("Connection Failed", response['message'])
                if self.client_socket:
                    self.client_socket.close()
                self.connected = False
                return
                
            self.connected = True
            self.log(f"Connected to server as '{name}'")
            self.message_label.config(text="Waiting for game to start...")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.name_entry.config(state=tk.DISABLED)
            
  
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except (socket.error, OSError) as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            self.connected = False
            if self.client_socket:
                self.client_socket.close()

    def receive_messages(self):
        buffer = ""
        while self.connected:
            try:
                data = self.client_socket.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        message = json.loads(line)
                        self.handle_message(message)
            except (socket.error, OSError) as e:
                if self.connected:
                    self.log(f"Connection error: {e}")
                    self.disconnect()

    def handle_message(self, message):

        msg_type = message['type']
        if msg_type == 'scoreboard':
            self.update_scoreboard(message['scoreboard'])
            
        elif msg_type == 'game_start':
            self.handle_game_start()
            
        elif msg_type == 'message':
            self.display_message(message)
            
        elif msg_type == 'message_result':
            self.show_result(message)
            
        elif msg_type == 'game_end':
            self.show_game_end(message)
            
        elif msg_type == 'client_disconnected':
            self.log(f"Player '{message['name']}' disconnected")
        
        elif msg_type == 'server_shutdown':
            self.handle_server_shutdown(message)

    def handle_server_shutdown(self, message):
        self.log("Server has been shut down")
        if self.connected:
            self.disconnect()
 
    def handle_game_start(self):
        self.in_game = True
        self.log("Game is starting!")
        self.message_label.config(text="Get ready for the first message...")

    def display_message(self, message):
        message_num = message['message_num']
        message_text = message['message']
        
        self.message_label.config(text=f"Message {message_num}: {message_text}")
        
        self.submit_btn.config(state=tk.NORMAL)
        
        self.log(f"Message {message_num} received")

    def submit_answer(self):
        answer = self.answer_entry.get().strip()
        
        if not answer:
            messagebox.showwarning("Warning", "Please enter an answer")
            return
            
        self.submit_btn.config(state=tk.DISABLED)
        
        message = {
            'type': 'answer',
            'answer': answer
        }
        try:
            
            self.client_socket.send((json.dumps(message) + "\n").encode())
            self.log(f"Submitted answer: {answer}")
        except (socket.error, OSError) as e:
            self.log(f"Failed to send answer: {e}")
            self.disconnect()

    def show_result(self, message):
        message_num = message['message_num']
        correct_answer = message['correct_answer']
        results = message['results']
        
        client_name = self.name_entry.get()
        result = results[client_name]
        
        if result['correct']:
            if result['first']:
                self.log(f"You answered message {message_num}: CORRECT! You were first! " +
                        f"(+{result['points']} points)")
            else:
                self.log(f"You answered message {message_num}: CORRECT! (+{result['points']} point)")
        else:
            self.log(f"You answered message {message_num}: WRONG. Correct answer was: {correct_answer}")

    def show_game_end(self, message):
        self.in_game = False
        rankings = message['rankings']
        
        result = "GAME OVER!\n\nFinal Rankings:\n"
        for rank_info in rankings:
            result += f"{rank_info['rank']}. {rank_info['name']} - {rank_info['score']} points\n"
            
        self.message_label.config(text=result)
        self.log("Game ended!")
        
        messagebox.showinfo("Game Over", result)
        
        if self.connected:
            self.log("Disconnecting from server...")
            self.disconnect()
    
    def update_scoreboard(self, rankings):
        self.scoreboard_text.delete(1.0, tk.END)
        self.scoreboard_text.insert(tk.END, "Current Scores:\n")
        self.scoreboard_text.insert(tk.END, "-" * 40 + "\n")
        
        for rank_info in rankings:
            self.scoreboard_text.insert(tk.END, 
                f"{rank_info['rank']}. {rank_info['name']} - {rank_info['score']} points\n")

    def disconnect(self):
        if self.connected:
            self.connected = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                    self.log("Disconnected from server")
                except (socket.error, OSError):
                    pass
            self.handle_disconnection() 

    def handle_disconnection(self):
        self.connected = False
        self.in_game = False
        
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.ip_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.name_entry.config(state=tk.NORMAL)
        
        self.answer_entry.config(state=tk.NORMAL)
        self.submit_btn.config(state=tk.DISABLED)

        self.scoreboard_text.delete(1.0, tk.END)
        self.scoreboard_text.insert(tk.END, "Current Scores:\n")
        self.scoreboard_text.insert(tk.END, "-" * 40 + "\n")
        self.message_label.config(text="Waiting to connect...") 
 
    def on_closing(self):
        if self.connected:
            self.disconnect()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    client = CaeserCypherClient()
    client.run()
