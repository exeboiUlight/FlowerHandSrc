from tkinter import *
from tkinter import ttk, messagebox, scrolledtext, filedialog
import socket
import threading
import json
import os
from datetime import datetime
import sys
import pyaudio
from PIL import ImageTk
import wave

COLORS = {
    "bg": "#2d2d2d",  # Основной фон
    "fg": "#e0e0e0",  # Основной текст
    "widget_bg": "#3d3d3d",  # Фон виджетов
    "widget_fg": "#ffffff",  # Текст виджетов
    "entry_bg": "#4d4d4d",  # Фон полей ввода
    "entry_fg": "#ffffff",  # Текст полей ввода
    "button_bg": "#4d4d4d",  # Фон кнопок
    "button_fg": "#ffffff",  # Текст кнопок
    "button_active": "#5d5d5d",  # Активная кнопка
    "listbox_bg": "#3d3d3d",  # Фон списка
    "listbox_fg": "#ffffff",  # Текст списка
    "scrollbar_bg": "#3d3d3d",  # Фон скроллбара
    "scrollbar_trough": "#2d2d2d",  # Дорожка скроллбара
    "text_bg": "#3d3d3d",  # Фон текстового поля
    "text_fg": "#ffffff",  # Текст текстового поля
    "select_bg": "#5d5d5d",  # Фон выделения
    "select_fg": "#ffffff",  # Текст выделения
    "border": "#1d1d1d",  # Цвет границ
    "highlight": "#6d6d6d",  # Цвет выделения
    "error": "#ff6b6b",  # Цвет ошибок
    "success": "#6bff6b",  # Цвет успеха
    "info": "#6b6bff"  # Цвет информации
}

class Server:
    def __init__(self, host='0.0.0.0', port=10000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.banned_users = set()
        self.admin_users = {"admin"}
        self.running = False
    
    def ban_user(self, username):
        """Забанить пользователя и отключить его"""
        for client_socket, client_username in list(self.clients.items()):
            if client_username == username:
                try:
                    client_socket.send("Вы были забанены на этом сервере".encode('utf-8'))
                    client_socket.close()
                except:
                    pass
                self.remove_client(client_socket)
                self.banned_users.add(username)
                return True
        return False

    def send_private_message(self, sender, recipient, message):
        """Отправить личное сообщение конкретному пользователю"""
        for client_socket, client_username in list(self.clients.items()):
            if client_username == recipient:
                try:
                    full_msg = f"[PM from {sender}] {message}"
                    client_socket.send(full_msg.encode('utf-8'))
                    return True
                except Exception as e:
                    print(f"Ошибка отправки PM: {e}")
                    self.remove_client(client_socket)
        return False
    
    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"Сервер запущен на {self.host}:{self.port}")

    def accept_connection(self):
        if not self.running:
            return None
        client_socket, addr = self.socket.accept()
        return client_socket, addr

    def receive_message(self, client_socket):
        try:
            data = client_socket.recv(1024).decode('utf-8')
            return data if data else None
        except:
            return None

    def broadcast_message(self, message, exclude=None):
        for client_socket in list(self.clients.keys()):
            if client_socket != exclude:
                try:
                    client_socket.send(message.encode('utf-8'))
                except:
                    self.remove_client(client_socket)

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            username = self.clients[client_socket]
            del self.clients[client_socket]
            print(f"Клиент {username} отключен")

    def stop(self):
        self.running = False
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.socket.close()
        print("Сервер остановлен")

class Client:
    def __init__(self, host='127.0.0.1', port=10000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_message(self, message):
        self.socket.send(message.encode('utf-8'))

    def receive_message(self):
        try:
            data = self.socket.recv(1024).decode('utf-8')
            return data if data else None
        except:
            return None

    def disconnect(self):
        self.socket.close()

class VoiceChat:
    def __init__(self, socket, is_server=False):
        self.socket = socket
        self.is_active = False
        self.is_server = is_server
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.thread = None

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024

    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self.stream = self.audio.open(format=self.FORMAT,
                                      channels=self.CHANNELS,
                                      rate=self.RATE,
                                      input=True,
                                      frames_per_buffer=self.CHUNK)
        self.thread = threading.Thread(target=self._capture_and_send, daemon=True)
        self.thread.start()

        self.recv_thread = threading.Thread(target=self._receive_audio, daemon=True)
        self.recv_thread.start()

    def stop(self):
        self.is_active = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

    def _capture_and_send(self):
        while self.is_active:
            try:
                data = self.stream.read(self.CHUNK)
                self.socket.sendall(data)
            except:
                break

    def _receive_audio(self):
        output_stream = self.audio.open(format=self.FORMAT,
                                        channels=self.CHANNELS,
                                        rate=self.RATE,
                                        output=True)
        while self.is_active:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                output_stream.write(data)
            except:
                break
        output_stream.stop_stream()
        output_stream.close()

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FlowerHand")
        self.root.geometry("800x600")
        self.root.configure(bg=COLORS["bg"])
        
        self.setup_theme()
        
        self.nickname = self.load_nickname() or ("User" + str(int(datetime.now().timestamp()))[-4:])
        self.username = self.nickname

        self.chat_history = []
        self.history_file = "chat_history.json"
        self.clients = {}
        
        self.api_names = {
            "26.22.97.228": "UlightClub",
            "127.0.0.1": "Локальный сервер"
        }
        
        self.load_history()
        self.setup_mode_selection()

    def setup_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', 
                       background=COLORS["bg"],
                       foreground=COLORS["fg"],
                       fieldbackground=COLORS["entry_bg"],
                       selectbackground=COLORS["select_bg"],
                       selectforeground=COLORS["select_fg"],
                       insertcolor=COLORS["fg"],
                       troughcolor=COLORS["scrollbar_trough"],
                       highlightcolor=COLORS["highlight"])
        
        style.configure('TButton',
                       background=COLORS["button_bg"],
                       foreground=COLORS["button_fg"],
                       bordercolor=COLORS["border"],
                       lightcolor=COLORS["button_bg"],
                       darkcolor=COLORS["button_bg"])
        
        style.map('TButton',
                 background=[('active', COLORS["button_active"]),
                            ('disabled', COLORS["widget_bg"])])
        
        style.configure('TEntry',
                       fieldbackground=COLORS["entry_bg"],
                       foreground=COLORS["entry_fg"])
        
        style.configure('TCombobox',
                       fieldbackground=COLORS["entry_bg"],
                       background=COLORS["entry_bg"],
                       foreground=COLORS["entry_fg"])
        
        style.configure('Vertical.TScrollbar',
                       background=COLORS["scrollbar_bg"],
                       troughcolor=COLORS["scrollbar_trough"],
                       bordercolor=COLORS["border"],
                       arrowcolor=COLORS["fg"])
        
        style.configure('Horizontal.TScrollbar',
                       background=COLORS["scrollbar_bg"],
                       troughcolor=COLORS["scrollbar_trough"],
                       bordercolor=COLORS["border"],
                       arrowcolor=COLORS["fg"])
        
        self.root.option_add('*Background', COLORS["bg"])
        self.root.option_add('*Foreground', COLORS["fg"])
        self.root.option_add('*Entry*Background', COLORS["entry_bg"])
        self.root.option_add('*Entry*Foreground', COLORS["entry_fg"])
        self.root.option_add('*Button*Background', COLORS["button_bg"])
        self.root.option_add('*Button*Foreground', COLORS["button_fg"])
        self.root.option_add('*Listbox*Background', COLORS["listbox_bg"])
        self.root.option_add('*Listbox*Foreground', COLORS["listbox_fg"])
        self.root.option_add('*Text*Background', COLORS["text_bg"])
        self.root.option_add('*Text*Foreground', COLORS["text_fg"])
        self.root.option_add('*Scrollbar*Background', COLORS["scrollbar_bg"])
        self.root.option_add('*Scrollbar*TroughColor', COLORS["scrollbar_trough"])
        self.root.option_add('*Scrollbar*HighlightColor', COLORS["highlight"])
        self.root.option_add('*Select*Background', COLORS["select_bg"])
        self.root.option_add('*Select*Foreground', COLORS["select_fg"])

    def load_nickname(self):
        if os.path.exists("nickname.json"):
            try:
                with open("nickname.json", 'r') as f:
                    data = json.load(f)
                    return data.get("nickname", "")
            except:
                return ""
        return ""

    def save_nickname(self, nickname):
        with open("nickname.json", 'w') as f:
            json.dump({"nickname": nickname}, f)

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.chat_history = json.load(f)
            except:
                self.chat_history = []

    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.chat_history, f, indent=2)

    def ban_selected_user(self):
        if not hasattr(self, 'server') or not self.server:
            return
        
        selection = self.clients_listbox.curselection()
        if not selection:
            messagebox.showwarning("Ошибка", "Выберите пользователя из списка")
            return
        
        username = self.clients_listbox.get(selection[0])
        if username == self.username:
            messagebox.showwarning("Ошибка", "Нельзя забанить себя")
            return
        
        if self.server.ban_user(username):
            self.log_message(f">>> Пользователь {username} был забанен")
        else:
            messagebox.showerror("Ошибка", f"Не удалось забанить пользователя {username}")

    def setup_mode_selection(self):
        self.clear_window()
        
        main_frame = Frame(self.root, bg=COLORS["bg"])
        main_frame.pack(expand=True, fill=BOTH, padx=20, pady=20)
        
        Label(main_frame, text="Выберите режим работы", font=('Arial', 14), bg=COLORS["bg"], fg=COLORS["fg"]).pack(pady=20)
        
        user_frame = Frame(main_frame, bg=COLORS["bg"])
        user_frame.pack(pady=10)
        
        Label(user_frame, text="Ваш никнейм:", bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=LEFT)
        self.username_entry = Entry(user_frame, width=20, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"], insertbackground=COLORS["fg"])
        self.username_entry.pack(side=LEFT, padx=5)
        self.username_entry.insert(0, self.username)
        
        btn_frame = Frame(main_frame, bg=COLORS["bg"])
        btn_frame.pack(pady=20)
        
        Button(btn_frame, text="Сервер", command=self.setup_server, width=15,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=10)
        
        Button(btn_frame, text="Клиент", command=self.setup_client, width=15,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=10)
        
        Button(main_frame, text="Просмотреть историю", command=self.show_history,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(pady=20)

    def setup_server(self):
        self.username = self.username_entry.get().strip() or self.username
        self.save_nickname(self.username)
        self.clear_window()
        self.root.title(f"FlowerHand - Server Mode ({self.username})")
        
        self.server = Server()
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        
        info_frame = Frame(self.root, bg=COLORS["bg"])
        info_frame.pack(fill=X, padx=10, pady=5)
        Label(info_frame, text=f"Сервер запущен | Ник: {self.username}", font=('Arial', 12),
              bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=LEFT)
        
        clients_frame = Frame(self.root, bg=COLORS["bg"])
        clients_frame.pack(fill=X, padx=10, pady=5)
        Label(clients_frame, text="Подключенные клиенты:", bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=LEFT)
        
        self.clients_listbox = Listbox(clients_frame, height=4, bg=COLORS["listbox_bg"], fg=COLORS["listbox_fg"],
                                      selectbackground=COLORS["select_bg"], selectforeground=COLORS["select_fg"])
        self.clients_listbox.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=WORD, width=80, height=20,
                                                bg=COLORS["text_bg"], fg=COLORS["text_fg"],
                                                insertbackground=COLORS["fg"],
                                                selectbackground=COLORS["select_bg"],
                                                selectforeground=COLORS["select_fg"])
        self.log_area.pack(expand=True, fill=BOTH, padx=10, pady=5)
        self.log_message(f">>> Сервер запущен. Никнейм: {self.username}")
        self.log_area.config(state=DISABLED)
        
        msg_frame = Frame(self.root, bg=COLORS["bg"])
        msg_frame.pack(fill=X, padx=10, pady=5)
        self.server_msg_entry = Text(msg_frame, height=3, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
                                   insertbackground=COLORS["fg"],
                                   selectbackground=COLORS["select_bg"],
                                   selectforeground=COLORS["select_fg"])
        self.server_msg_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.server_msg_entry.bind("<Return>", lambda e: self.broadcast_message())
        
        Button(msg_frame, text="Отправить всем", command=self.broadcast_message,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT)
        
        ctrl_frame = Frame(self.root, bg=COLORS["bg"])
        ctrl_frame.pack(pady=5)
        
        Button(ctrl_frame, text="Остановить сервер", command=self.stop_server,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Button(ctrl_frame, text="История", command=self.show_history,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Button(clients_frame, text="Забанить", command=self.ban_selected_user,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.stop_server)

    def run_server(self):
        self.server.start()
        while True:
            try:
                client_socket, addr = self.server.accept_connection()
                if client_socket:
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,),
                        daemon=True
                    ).start()
            except Exception as e:
                self.log_message(f"Ошибка сервера: {str(e)}")
                break

    def send_private_message(self, sender, recipient, message):
        """Отправить личное сообщение конкретному пользователю"""
        for client_socket, client_username in list(self.clients.items()):
            if client_username == recipient:
                try:
                    # Формат сообщения для клиента
                    full_msg = f"[PM from {sender}] {message}"
                    client_socket.send(full_msg.encode('utf-8'))
                    return True
                except Exception as e:
                    print(f"Ошибка отправки PM: {e}")
                    self.remove_client(client_socket)
        return False

    def handle_client(self, client_socket):
        while True:
            try:
                self.clients = self.server.clients

                message = self.server.receive_message(client_socket)
                if not message:
                    break
                    
                if message.startswith("USERNAME:"):
                    username = message.split(":", 1)[1].strip()
                    self.server.clients[client_socket] = username
                    self.update_clients_list()
                    self.log_message(f">>> {username} присоединился к чату")
                
                if message.startswith("FILE|"):
                    # Распарсим заголовок
                    parts = message.split('|')
                    if len(parts) == 3:
                        filename = parts[1]
                        filesize = int(parts[2])
                        # Получаем файл
                        file_data = b''
                        remaining = filesize
                        while remaining > 0:
                            chunk = client_socket.recv(min(4096, remaining))
                            if not chunk:
                                break
                            file_data += chunk
                            remaining -= len(chunk)
                        save_path = os.path.join('received_files', filename)
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, 'wb') as f:
                            f.write(file_data)
                        self.log_message(f"Получен файл: {filename}")

                elif message.startswith("/pm"):
                    try:
                        parts = message.split(maxsplit=2)
                        if len(parts) >= 3:
                            _, recipient, pm_message = parts
                            if recipient in self.clients.values():
                                self.send_private_message(username, recipient, pm_message)
                                self.log_message(f"ЛС {recipient} от {username}: {pm_message}")
                            else:
                                self.log_message(f"Пользователь {recipient} не найден")
                        else:
                            self.log_message("Некорректный формат ЛС")
                    except Exception as e:
                        self.log_message(f"Ошибка при отправке ЛС: {str(e)}")

                else:
                    username = self.server.clients.get(client_socket, "Unknown")
                    timestamp = datetime.now().timestamp()
                    self.chat_history.append({
                        'timestamp': timestamp,
                        'username': username,
                        'message': message,
                        'type': 'received'
                    })
                    self.save_history()
                    self.log_message(f"{username}: {message}")
                    self.server.broadcast_message(f"{username}: {message}", exclude=client_socket)
                    
            except Exception as e:
                break
                
        username = self.server.clients.get(client_socket, "Unknown")
        self.log_message(f">>> {username} покинул чат")
        self.server.remove_client(client_socket)
        self.update_clients_list()
        client_socket.close()

    def update_clients_list(self):
        self.clients_listbox.delete(0, END)
        for username in self.server.clients.values():
            self.clients_listbox.insert(END, username)

    def broadcast_message(self):
        message = self.server_msg_entry.get("1.0", "end-1c").strip()
        if not message:
            return
        
        timestamp = datetime.now().timestamp()
        self.chat_history.append({
            'timestamp': timestamp,
            'username': self.username,
            'message': message,
            'type': 'broadcast'
        })
        self.save_history()
        
        self.log_message(f"Вы (всем): {message}")
        self.server_msg_entry.delete("1.0", END)
        self.server.broadcast_message(f"{self.username}: {message}")

    def setup_client(self):
        self.username = self.username_entry.get().strip() or self.username
        self.save_nickname(self.username)
        self.clear_window()
        self.root.title(f"FlowerHand - Client Mode ({self.username})")
        
        conn_frame = Frame(self.root, bg=COLORS["bg"])
        conn_frame.pack(fill=X, padx=10, pady=5)
        Label(conn_frame, text="Адрес сервера:", bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=LEFT)
        
        self.server_combobox = ttk.Combobox(conn_frame, width=20)
        self.server_combobox['values'] = list(self.api_names.values()) + ["Другой..."]
        self.server_combobox.pack(side=LEFT, padx=5)
        self.server_combobox.set("UlightClub")
        
        self.custom_ip_entry = Entry(conn_frame, width=15, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
                                   insertbackground=COLORS["fg"])
        self.custom_ip_entry.pack(side=LEFT, padx=5)
        self.custom_ip_entry.insert(0, "192.168.0.107")
        self.custom_ip_entry.pack_forget()
        
        def on_server_select(event):
            if self.server_combobox.get() == "Другой...":
                self.custom_ip_entry.pack(side=LEFT, padx=5)
            else:
                self.custom_ip_entry.pack_forget()
        
        self.server_combobox.bind("<<ComboboxSelected>>", on_server_select)
        
        Button(conn_frame, text="Подключиться", command=self.connect_to_server,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Label(conn_frame, text=f"Ник: {self.username}", bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=RIGHT)
        
        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=WORD, width=80, height=20,
                                                 bg=COLORS["text_bg"], fg=COLORS["text_fg"],
                                                 insertbackground=COLORS["fg"],
                                                 selectbackground=COLORS["select_bg"],
                                                 selectforeground=COLORS["select_fg"])
        self.chat_area.pack(expand=True, fill=BOTH, padx=10, pady=5)
        self.chat_area.config(state=DISABLED)
        
        msg_frame = Frame(self.root, bg=COLORS["bg"])
        msg_frame.pack(fill=X, padx=10, pady=5)
        self.message_entry = Text(msg_frame, height=3, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
                                insertbackground=COLORS["fg"],
                                selectbackground=COLORS["select_bg"],
                                selectforeground=COLORS["select_fg"])
        self.message_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        Button(msg_frame, text="Отправить", command=self.send_message,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT)
        
        ctrl_frame = Frame(self.root, bg=COLORS["bg"])
        ctrl_frame.pack(pady=5)
        
        Button(ctrl_frame, text="Отключиться", command=self.disconnect_client,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Button(ctrl_frame, text="История", command=self.show_history,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)

        self.send_file_button = Button(msg_frame, text="Отправить файл", command=self.send_file,
                               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
                               activebackground=COLORS["button_active"],
                               activeforeground=COLORS["button_fg"])
        self.send_file_button.pack(side=LEFT, padx=5)
        
        self.client = None
        self.connected = False
        self.server_ip = None
        self.server_display_name = None
        self.voice_chat_active = False

    def show_image(self, image_path):
        top = Toplevel(self.root)
        top.title(f"Просмотр изображения: {os.path.basename(image_path)}")
        img = Image.open(image_path)
        img.thumbnail((800, 600))
        photo = ImageTk.PhotoImage(img)
        label = Label(top, image=photo)
        label.image = photo
        label.pack()

        def save_image():
            save_path = filedialog.asksaveasfilename(
                initialfile=os.path.basename(image_path),
                defaultextension=os.path.splitext(image_path)[1],
                filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Все файлы", "*.*")]
            )
            if save_path:
                try:
                    img.save(save_path)
                    messagebox.showinfo("Успех", "Файл успешно сохранен")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")

        btn_save = Button(top, text="Скачать", command=save_image)
        btn_save.pack(pady=5)

    def play_audio(self, audio_path):
        def _play():
            wf = wave.open(audio_path, 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(1024)
            while data:
                stream.write(data)
                data = wf.readframes(1024)
            stream.stop_stream()
            stream.close()
            p.terminate()

        def save_audio():
            save_path = filedialog.asksaveasfilename(
                initialfile=os.path.basename(audio_path),
                defaultextension=os.path.splitext(audio_path)[1],
                filetypes=[("Audio", "*.mp3 *.wav *.ogg"), ("Все файлы", "*.*")]
            )
            if save_path:
                try:
                    with open(audio_path, 'rb') as src, open(save_path, 'wb') as dst:
                        dst.write(src.read())
                    messagebox.showinfo("Успех", "Файл успешно сохранен")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")

        threading.Thread(target=_play, daemon=True).start()

        # Создаем окно с кнопкой "Скачать"
        top = Toplevel(self.root)
        top.title("Воспроизведение аудио")
        btn_save = Button(top, text="Скачать", command=save_audio)
        btn_save.pack(pady=5)

    def send_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        # Определяем тип файла
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            file_type = 'image'
        else:
            file_type = 'other'
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            # Отправляем заголовок с типом и размером
            header = f"FILE|{file_type}|{filename}|{len(file_data)}"
            self.client.send_message(header)
            self.client.socket.sendall(file_data)
            self.update_chat(f"Вы отправили файл: {filename}\n")
            # Запись в историю
            timestamp = datetime.now().timestamp()
            self.chat_history.append({
                'timestamp': timestamp,
                'username': self.username,
                'message': f"Отправлен файл: {filename}",
                'type': 'file',
                'file_type': file_type,
                'file_name': filename,
                'file_path': file_path
            })
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {str(e)}")

    def toggle_voice_chat(self):
        if not self.connected or not self.client:
            messagebox.showwarning("Ошибка", "Сначала подключитесь к серверу")
            return

        if not hasattr(self, 'voice_chat') or not self.voice_chat or not self.voice_chat.is_active:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.server_ip, 10001))
                self.voice_chat = VoiceChat(sock)
                self.voice_chat.start()
                self.voice_button.config(text="Голосовой чат (Выкл)")
                self.voice_chat_active = True
                self.update_chat(">>> Голосовой чат включен. Говорите...\n")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось запустить голосовой чат: {str(e)}")
        else:
            # Останавливаем голосовой чат
            self.voice_chat.stop()
            self.voice_chat = None
            self.voice_button.config(text="Голосовой чат (Вкл)")
            self.voice_chat_active = False
            self.update_chat(">>> Голосовой чат выключен\n")

    def connect_to_server(self):
        selected_server = self.server_combobox.get()
        
        if selected_server == "Другой...":
            host = self.custom_ip_entry.get().strip()
            display_name = host
        else:
            host = next((ip for ip, name in self.api_names.items() if name == selected_server), selected_server)
            display_name = selected_server
        
        if not host:
            messagebox.showerror("Ошибка", "Введите адрес сервера")
            return
        
        try:
            self.client = Client(host, 10000)
            self.client.connect()
            self.client.send_message(f"USERNAME:{self.username}")
            
            self.connected = True
            self.server_ip = host
            self.server_display_name = display_name
            self.update_chat(f">>> Подключено к серверу '{display_name}' как {self.username}\n")
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к {display_name}: {str(e)}")

    def send_message(self):
        if not self.connected or not self.client:
            messagebox.showwarning("Ошибка", "Нет подключения к серверу")
            return

        message = self.message_entry.get("1.0", "end-1c").strip()
        if not message:
            return

        if message.startswith("/pm"):
            parts = message.split(maxsplit=2)
            if len(parts) >= 3:
                _, recipient, pm_message = parts
                self.client.send_message(f"/pm {recipient} {pm_message}")
                self.update_chat(f"[Вы -> {recipient}]{pm_message}\n")
            else:
                messagebox.showwarning("Ошибка", "Неверный формат ЛС. Используйте: /pm получатель сообщение")
        else:
            self.client.send_message(message)
            self.update_chat(f"[Вы]{message}\n")
        
        self.message_entry.delete("1.0", END)

    def run_voice_server(self):
        voice_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        voice_server_socket.bind((self.server.host, 10001))
        voice_server_socket.listen(5)
        print("Voice server запущен на порту 10001")
        while True:
            conn, addr = voice_server_socket.accept()
            print(f"Подключение голосового клиента: {addr}")
            threading.Thread(target=self.handle_voice_client, args=(conn,), daemon=True).start()

    def handle_voice_client(self, conn):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                for client_conn in self.server.clients:
                    if client_conn != conn:
                        try:
                            client_conn.sendall(data)
                        except:
                            pass
        finally:
            conn.close()

    def receive_messages(self):
        while self.connected and self.client:
            try:
                response = self.client.receive_message()
                if not response:
                    break

                if response.startswith("[PM from "):
                    end_bracket = response.find("]")
                    sender = response[9:end_bracket]
                    pm_message = response[end_bracket+2:]
                    timestamp = datetime.now().timestamp()
                    self.chat_history.append({
                        'timestamp': timestamp,
                        'username': sender,
                        'message': pm_message,
                        'type': 'private_received',
                        'server': self.server_display_name
                    })
                    self.save_history()
                    self.update_chat(f"[PM from {sender}] {pm_message}\n")
                else:
                    if ":" in response:
                        username, msg = response.split(":", 1)
                        username = username.strip()
                        msg = msg.strip()
                    else:
                        username = "Сервер"
                        msg = response

                    timestamp = datetime.now().timestamp()
                    self.chat_history.append({
                        'timestamp': timestamp,
                        'username': username,
                        'message': msg,
                        'type': 'received',
                        'server': self.server_display_name
                    })
                    self.save_history()
                    self.update_chat(f"{username}: {msg}\n")
            except ConnectionError as e:
                self.update_chat(f"❗ Соединение с сервером потеряно: {str(e)}\n")
                self.connected = False
                break
            except Exception as e:
                self.update_chat(f"❗ Ошибка получения: {str(e)}\n")
                self.connected = False
                break

    def disconnect_client(self):
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
        self.connected = False
        self.update_chat(f">>> Отключено от сервера '{self.server_display_name}'\n")

    def show_history(self):
        history_win = Toplevel(self.root)
        history_win.title("История переписки")
        history_win.geometry("600x400")
        history_win.configure(bg=COLORS["bg"])
        
        history_text = scrolledtext.ScrolledText(history_win, wrap=WORD, width=70, height=20,
                                               bg=COLORS["text_bg"], fg=COLORS["text_fg"],
                                               insertbackground=COLORS["fg"],
                                               selectbackground=COLORS["select_bg"],
                                               selectforeground=COLORS["select_fg"])
        history_text.pack(expand=True, fill=BOTH, padx=10, pady=10)
        
        if not self.chat_history:
            history_text.insert(END, "История переписки пуста\n")
        else:
            for message in self.chat_history:
                timestamp = datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                history_text.insert(END, f"[{timestamp}] {message['username']}: {message['message']}\n")
        
        history_text.config(state=DISABLED)
        
        btn_frame = Frame(history_win, bg=COLORS["bg"])
        btn_frame.pack(pady=10)
        
        Button(btn_frame, text="Экспорт в файл", command=self.export_history,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Button(btn_frame, text="Очистить историю", command=self.clear_history,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)
        
        Button(btn_frame, text="Закрыть", command=history_win.destroy,
               bg=COLORS["button_bg"], fg=COLORS["button_fg"],
               activebackground=COLORS["button_active"],
               activeforeground=COLORS["button_fg"]).pack(side=LEFT, padx=5)

    def export_history(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Сохранить историю как"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    for message in self.chat_history:
                        timestamp = datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        f.write(f"[{timestamp}] {message['username']}: {message['message']}\n")
                messagebox.showinfo("Успех", "История успешно экспортирована")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать историю: {str(e)}")

    def clear_history(self):
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите очистить историю переписки?"):
            self.chat_history = []
            self.save_history()
            messagebox.showinfo("Успех", "История переписки очищена")

    def stop_server(self):
        if messagebox.askokcancel("Выход", "Остановить сервер и выйти?"):
            if hasattr(self, 'server') and self.server:
                self.server.stop()
            self.save_history()
            self.root.destroy()
            sys.exit(0)

    def log_message(self, message):
        self.log_area.config(state=NORMAL)
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)
        self.log_area.config(state=DISABLED)

    def update_chat(self, message):
        self.chat_area.config(state=NORMAL)
        self.chat_area.insert(END, message)
        self.chat_area.see(END)
        self.chat_area.config(state=DISABLED)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = Tk()
    root.iconbitmap(default="icon.ico")
    app = ChatApp(root)
    root.mainloop()
