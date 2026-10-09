import tkinter as tk

def show_message():
    message.config(text="Hello from my Python .exe!")

window = tk.Tk()
window.title("First Python .exe")
window.geometry("400x250")

title = tk.Label(
    window,
    text="My First Python .exe",
    font=("Arial", 20)
)
title.pack(pady=30)

button = tk.Button(
    window,
    text="Click Me",
    command=show_message
)
button.pack()

message = tk.Label(window, text="")
message.pack(pady=20)

window.mainloop()