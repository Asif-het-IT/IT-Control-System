import sys
import os

# Project root path add karo (one level up)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs import speed_test_job

import tkinter as tk
from queue import Queue
from jobs import speed_test_job  # make sure 8_Internet_Speed_Test.py is renamed as speed_test_job.py or import correctly
import threading

root = tk.Tk()
root.title("Internet Speed Test")
txt = tk.Text(root, width=80, height=20)
txt.pack()

log_queue = Queue()

def update_textbox():
    while not log_queue.empty():
        msg = log_queue.get()
        txt.insert(tk.END, msg + "\n")
        txt.see(tk.END)
    root.after(500, update_textbox)

def start_speedtest():
    threading.Thread(target=speed_test_job.run_job, kwargs={"gui_enqueue": log_queue.put}).start()

btn = tk.Button(root, text="Run Speedtest", command=start_speedtest)
btn.pack()

update_textbox()
root.mainloop()
