import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import time

class CaesarServer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Caesar Cypher Server")
        self.root.geometry("800x600")
        
        self.server_socket = None
        self.clients = {} 
        self.messages = []
        self.encrypt_messages = []
        self.current_message = 0
        self.answers_received = {} 
        self.game_started = False
        self.is_listening = False
        self.port = None
        self.processing_answers = False
        self.game_ending = False
        
        self.gui_setup()
    
    def gui_setup(self):

        port_frame = tk.Frame(self.root)
        port_frame.pack(pady=10)
        
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(port_frame, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = tk.Button(port_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(port_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=5)
        
        tk.Label(file_frame, text="Message File:").pack(side=tk.LEFT)
        self.file_entry = tk.Entry(file_frame, width=40)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(file_frame, text="Load Messages", command=self.load_messages).pack(side=tk.LEFT, padx=5)
        
        
        shift_frame = tk.Frame(self.root)
        shift_frame.pack(pady=5)

        tk.Label(shift_frame, text="Shift:").pack(side=tk.LEFT)
        self.shift_entry = tk.Entry(shift_frame, width=10)
        self.shift_entry.pack(side=tk.LEFT, padx=5)

        time_frame = tk.Frame(self.root)
        time_frame.pack(pady=5)

        tk.Label(time_frame, text="Time Limit (seconds):").pack(side=tk.LEFT)
        self.time_entry = tk.Entry(time_frame, width=10)
        self.time_entry.pack(side=tk.RIGHT, padx=5)

        self.start_game_btn = tk.Button(self.root, text="Start Game", 
                                        command=self.start_game, state=tk.DISABLED)
        self.start_game_btn.pack(pady=10)

        score_frame = tk.LabelFrame(self.root, text="Scoreboard", padx=10, pady=10)
        score_frame.pack(padx=10, pady=5, fill=tk.BOTH)
        
        self.scoreboard_text = scrolledtext.ScrolledText(score_frame, height=6, width=80, state=tk.DISABLED)
        self.scoreboard_text.pack()

        tk.Label(self.root, text="Server Log:").pack()
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

    def load_messages(self):
        filename = self.file_entry.get()
        if not filename:
            messagebox.showerror("Error", "Please select a message file")
            return
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.log("Successfully opened the file")
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return  
         
        shift_str = self.shift_entry.get()
        if not shift_str:
            messagebox.showwarning("Warning", "Please enter a shift value")
            return
        if not shift_str.isdigit():
            messagebox.showwarning("Warning", "Please enter a valid number for the shift")
            return
        if int(shift_str) <= 0:
            messagebox.showwarning("Warning", "Please enter a positive shift value")
            return
        if not self.time_entry.get().isdigit() or int(self.time_entry.get()) <= 0:
            messagebox.showwarning("Warning", "Please enter a valid positive number for time limit")
            return
        self.messages = []
        i = 0
        while i < len(lines):
            message = {
                'message': lines[i].strip(),
                'encrypted': self.encrypt_message(lines[i].strip(), int(shift_str)),
                'time_limit': int(self.time_entry.get())
            }
            self.messages.append(message)
            i=i+1

        self.log(f"Loaded {len(self.messages)} messages from file")
        
        if self.is_listening and len(self.clients) >= 2:
            self.start_game_btn.config(state=tk.NORMAL)

    def encrypt_message(self, message, shift):
        encrypted = ""
        for char in message:
            if char.isalpha():
                base = ord('A') if char.isupper() else ord('a')
                encrypted += chr((ord(char) - base + shift) % 26 + base)
            else:
                encrypted += char
        return encrypted
                 
    def start_server(self):
        try:
            port = int(self.port_entry.get())
            self.port = port
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('', port))
            self.server_socket.listen(5)
            
            self.is_listening = True
            self.log(f"Server started on port {port}")
            
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            
            threading.Thread(target=self.accept_connections, daemon=True).start()
            
        except (socket.error, ValueError)as e :
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.is_listening = False
            if self.server_socket:
                self.server_socket.close()

    def stop_server(self):
        if messagebox.askokcancel("Stop Server", "The server is going to stop. Continue?"):
            self.is_listening = False
            
            shutdown_msg = {'type': 'server_shutdown', 'message': 'Server is shutting down'}
            
            for client_socket in list(self.clients.keys()):
                if self.clients[client_socket].get('connected', True):
                    try:
                        client_socket.send((json.dumps(shutdown_msg)+ "\n").encode())
                    except (socket.error, OSError):
                        pass

            time.sleep(0.5)
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except (socket.error, OSError):
                    pass
            
            if self.server_socket:
                try:
                    self.server_socket.close()
                except (socket.error, OSError):
                    pass
            
            self.clients.clear()
            self.game_started = False
            self.current_message = 0
            self.answers_received = {}
            
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.NORMAL)
            self.start_game_btn.config(state=tk.DISABLED)
            self.scoreboard_text.config(state=tk.NORMAL)
            self.scoreboard_text.delete(1.0, tk.END)
            self.scoreboard_text.insert(tk.END, "Current Scores:\n")
            self.scoreboard_text.insert(tk.END, "-" * 40 + "\n")
            self.scoreboard_text.config(state=tk.DISABLED)
            self.log("Server stopped")

    def accept_connections(self):
        while self.is_listening:
            try:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, 
                            args=(client_socket, address), daemon=True).start()
            except (socket.error, OSError):
                break

    def start_game(self):
        if len(self.clients) < 2:
            messagebox.showwarning("Warning", "Need at least 2 players to start")
            return
            
        if not self.messages:
            messagebox.showwarning("Warning", "Please load messages first")
            return
        
        self.game_started = True
        self.current_message = 0
        self.answers_received = {}
        for client in self.clients.values():
            client['score'] = 0
            
        self.log("Game started.")
        self.start_game_btn.config(state=tk.DISABLED)
        
        response = {
            'type': 'game_start',
            'num_messages': self.messages.__len__()
        }
        self.broadcast(response)
        self.send_next_message()
        
    def handle_client(self, client_socket, address):
        try:
            data = client_socket.recv(1024).decode()
            message = json.loads(data)
            
            if message['type'] == 'connect':
                client_name = message['name']
                
                if self.game_started:
                    response = {
                        'type': 'error',
                        'message': 'Game has already started'
                    }
                    client_socket.send((json.dumps(response)+ "\n").encode())
                    client_socket.close()
                    return
                
                name_taken = False
                for c in self.clients.values():
                    if c['name'] == client_name:
                        name_taken = True
                        break

                if name_taken:
                    response = {
                        'type': 'error',
                        'message': f"Name '{client_name}' is already taken."
                    }
                    client_socket.send((json.dumps(response)+ "\n").encode())
                    client_socket.close()
                    return
                
                self.clients[client_socket] = {
                    'name': client_name, 
                    'score': 0,
                    'connected': True}
                self.log(f"Client '{client_name}' connected from {address[0]}")
                
                response = {
                    'type': 'connected',
                    'message': 'Connected successfully'
                }
                client_socket.send((json.dumps(response)+ "\n").encode())

                self.broadcast_scoreboard()
                
                if len(self.clients) >= 2 and len(self.messages) > 0 and not self.game_started:
                    self.start_game_btn.config(state=tk.NORMAL)
                
                while True:
                    try:
                        data = client_socket.recv(1024).decode()
                        if not data:
                            break
                        message = json.loads(data)
                        
                        if message['type'] == 'answer':
                            self.handle_answer(client_socket, message['answer'])
                    except (socket.error, OSError):
                        break
                        
        except (socket.error, ValueError) as e:
            self.log(f"Client handler error: {e}")
        finally:
            if client_socket in self.clients:
                self.disconnect_client(client_socket)

    def handle_answer(self, client_socket, answer):
        if client_socket not in self.clients:
            return
            
        client_name = self.clients[client_socket]['name']
        
        if self.current_message not in self.answers_received:
            self.answers_received[self.current_message] = {}
            
        self.answers_received[self.current_message][client_name] = answer
        
        self.log(f"Received answer from {client_name}: {answer}")
        

        active_clients = []
        for c in self.clients.values():
            if c['connected']:
                active_clients.append(c)
    

        if len(self.answers_received[self.current_message]) >= len(active_clients):
            self.process_answers()

    def process_answers(self):
        if self.processing_answers:
            return
        self.processing_answers = True

        message_index = self.current_message % len(self.messages)
        message = self.messages[message_index]
        correct_answer = message['message']
        
        first_correct = None
        results = {}
        for client_name, answer in self.answers_received[self.current_message].items():
            is_correct = (answer == correct_answer)
            
            if is_correct:
                client_socket = None
                for sock, info in self.clients.items():
                    if info['name'] == client_name and info.get('connected', True):
                        client_socket = sock
                        break
                        
                if client_socket:
                    if first_correct is None:
                        first_correct = client_name
                        active_count = 0
                        for c in self.clients.values():
                            if c['connected']:
                                active_count += 1
                        bonus = active_count - 1
                        self.clients[client_socket]['score'] += 1 + bonus
                        results[client_name] = {
                            'correct': True,
                            'first': True,
                            'points': 1 + bonus
                        }
                    else:
                        self.clients[client_socket]['score'] += 1
                        results[client_name] = {
                            'correct': True,
                            'first': False,
                            'points': 1
                        }
            else:
                results[client_name] = {
                    'correct': False,
                    'first': False,
                    'points': 0
                }
        
        response = {
            'type': 'message_result',
            'message_num': self.current_message + 1,
            'correct_answer': correct_answer,
            'results': results
        }
        
        self.broadcast(response)
        self.broadcast_scoreboard()
        
        self.current_message += 1
        
        should_end = False
        num_messages = int(self.messages.__len__())
        active_clients = []
        for c in self.clients.values():
            if c['connected']:
                active_clients.append(c)

        if self.current_message >= num_messages:
            self.log("Game ended: all messages finished")
            should_end = True
        elif len(active_clients) < 2:
            self.log("Game ended due to insufficient players")
            should_end = True
        
        if should_end:
            self.end_game()
        else:
            self.root.after(2000, self.send_next_message)  
        self.processing_answers = False         
    
    def send_next_message(self):
        num_messages = int(self.messages.__len__())
        
        if self.current_message >= num_messages:
            return
        message_index = self.current_message % len(self.messages)
        message = self.messages[message_index]

        response = {
            'type': 'message',
            'message_num': self.current_message + 1,
            'message': message['encrypted'],
            'time_limit': message['time_limit']
        }
        
        self.broadcast(response)
        self.log(f"Sent message {self.current_message + 1}")

    def broadcast_scoreboard(self):
        scoreboard = []
        for client_info in self.clients.values():
            scoreboard.append({
                'name': client_info['name'],
                'score': client_info['score']})
            
        scoreboard.sort(key=lambda x: x['score'], reverse=True)
        rankings = []
        current_rank = 1
        i = 0
        while i < len(scoreboard):
            score = scoreboard[i]['score']
            tied_players = [scoreboard[i]['name']]
            
            j = i + 1
            while j < len(scoreboard) and scoreboard[j]['score'] == score:
                tied_players.append(scoreboard[j]['name'])
                j += 1
                
            for player in tied_players:
                rankings.append({
                    'name': player,
                    'score': score,
                    'rank': current_rank
                })
                
            current_rank += len(tied_players)
            i = j
        
        response = {
            'type': 'scoreboard',
            'scoreboard': rankings
        }
        self.update_scoreboard(rankings)
        self.broadcast(response)

    def update_scoreboard(self, rankings):
        self.scoreboard_text.config(state=tk.NORMAL)
        self.scoreboard_text.delete(1.0, tk.END)
        self.scoreboard_text.insert(tk.END, "Current Scores:\n")
        self.scoreboard_text.insert(tk.END, "-" * 40 + "\n")
        
        for rank_info in rankings:
            self.scoreboard_text.insert(tk.END, 
                f"{rank_info['rank']}. {rank_info['name']} - {rank_info['score']} points\n")
        self.scoreboard_text.config(state=tk.DISABLED)
            
    def end_game(self):
        if self.game_ending:
            return
        
        self.game_ending = True
        
        scoreboard = []
        for client_info in self.clients.values():
            scoreboard.append({
                'name': client_info['name'],
                'score': client_info['score']
            })
            
        scoreboard.sort(key=lambda x: x['score'], reverse=True)
        
        rankings = []
        current_rank = 1
        i = 0
        while i < len(scoreboard):
            score = scoreboard[i]['score']
            tied_players = [scoreboard[i]['name']]
            
            j = i + 1
            while j < len(scoreboard) and scoreboard[j]['score'] == score:
                tied_players.append(scoreboard[j]['name'])
                j += 1
                
            for player in tied_players:
                rankings.append({
                    'name': player,
                    'score': score,
                    'rank': current_rank
                })
                
            current_rank += len(tied_players)
            i = j
        
        response = {
            'type': 'game_end',
            'rankings': rankings
        }
       
    
        for client_socket in list(self.clients.keys()):
            try:
                if(self.clients[client_socket]['connected']):
                    client_socket.send((json.dumps(response)+ "\n").encode())
            except:
                pass
        time.sleep(0.5)
        
        clients_to_close = list(self.clients.keys())
        self.clients.clear()
        
        for client_socket in clients_to_close:
            try:
                client_socket.close()
            except (socket.error, OSError):
                pass

        self.game_started = False
        self.current_message = 0
        self.answers_received = {}
        self.game_ending = False
        self.scoreboard_text.config(state=tk.NORMAL)
        self.scoreboard_text.delete(1.0, tk.END)
        self.scoreboard_text.insert(tk.END, "Current Scores:\n")
        self.scoreboard_text.insert(tk.END, "-" * 40 + "\n")
        self.scoreboard_text.config(state=tk.DISABLED)
        self.log("All client connections terminated")
        self.log("Server is still listening for new clients")
        
    def broadcast(self, message):
        for client_socket, info in list(self.clients.items()):
            if not info.get('connected', True):
                continue 

            try:
                
                client_socket.send((json.dumps(message) + "\n").encode())
                
            except (socket.error, OSError):
                pass 
            
    def disconnect_client(self, client_socket):
        if client_socket in self.clients:
            client_name = self.clients[client_socket]['name']
            self.clients[client_socket]['connected'] = False
            self.log(f"Client '{client_name}' disconnected")
            
            try:
                client_socket.close()
            except (socket.error, OSError):
                pass
                
            disconnect_msg = {
                'type': 'client_disconnected',
                'name': client_name
            }
            self.broadcast(disconnect_msg)
            
            active_clients = []
            for c in self.clients.values():
                if c['connected']:
                    active_clients.append(c)

            if self.game_started and len(active_clients) == 1:
                last_player_name = active_clients[0]['name']
                if self.current_message in self.answers_received and last_player_name in self.answers_received[self.current_message]:
                    if not self.processing_answers:
                        self.process_answers() 
                   
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.is_listening = False
            shutdown_msg = { 'type': 'server_shutdown', 'message': 'Server is shutting down' }

            for client_socket in list(self.clients.keys()):
                if self.clients[client_socket].get('connected', True):
                    try:
                        client_socket.send((json.dumps(shutdown_msg)+ "\n").encode())
                    except (socket.error, OSError):
                        pass
            time.sleep(0.5)
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except (socket.error, OSError):
                    pass
            
            if self.server_socket:
                try:
                    self.server_socket.close()
                except (socket.error, OSError):
                    pass
            self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    server = CaesarServer()
    server.run()
            

            