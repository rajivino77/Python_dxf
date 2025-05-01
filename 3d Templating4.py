import tkinter as tk
from tkinter import ttk, messagebox, Menu, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from inputs import get_gamepad
import math
import serial
from scipy.interpolate import splprep, splev
import ezdxf
import os
import threading

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

root = tk.Tk()
root.title("3d Templating")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")
canvas2 = tk.Canvas(
        root,
        height = screen_height,
        width = screen_width,
        bg = "#ffffff",
        bd = 0
    )
canvas2.grid()
paned = tk.PanedWindow(canvas2, orient=tk.HORIZONTAL)
paned.grid()
left_frame = tk.Frame(paned, width=screen_width/2, height=screen_height/2)
paned.add(left_frame)
right_frame = tk.Frame(paned,  width=screen_width/2, height=screen_width/2)
paned.add(right_frame)
frame = ttk.Frame(right_frame)
frame.grid(pady = 50, padx = 10)
fig = Figure(figsize=(8, 8), dpi=100)
ax = fig.add_subplot()
ax.set_title("3d Templating")
ax.set_xlabel("X-axis")
ax.set_ylabel("Y-axis")
dropdown_var = tk.StringVar()

canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.draw()
canvas.get_tk_widget().grid()
com_var = tk.StringVar(value = "COM4")
xyz_points = []
plane_points = []
drawing_points = []
points = []
captured, email_body = "", ""
doc = ezdxf.new()
msp = doc.modelspace()
last_data = None
ser = None

def clear_serial_buffer():
    global ser
    ser.reset_input_buffer()
    
def clear():
    global captured
    ax.clear()
    ax.set_title("3d Templating")
    ax.set_xlabel("X-axis")
    ax.set_ylabel("Y-axis")
    canvas.draw()
    xyz_points.clear()
    points.clear()
    display.insert(tk.END, "Points Cleared\n")
    display.see(tk.END) 
    msp.delete_all_entities()
    
def ser_connection(event = None):
    global com_var
    SERIAL_PORT = com_var.get().strip()
    BAUD_RATE = 9600
    global ser
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
     
def key_pressed():
    while True:
        events = get_gamepad()  
        for event in events:
            if event.code == "BTN_TL" and event.state == 1:
                read_xyz()
            elif event.code == "ABS_HAT0Y" and event.state == 1: #down arrow
                create_line()
            elif event.code == "ABS_HAT0Y" and event.state == -1: #up arrow
                create_spline()
            elif event.code == "ABS_HAT0X" and event.state == 1: #right arrow
                create_hole(1.5)
            elif event.code == "ABS_HAT0X" and event.state == -1: #left arrow
                create_hole(5) 
            elif event.code == "BTN_EAST" and event.state == 1: #circle key
                export_to_dxf()
            elif event.code == "BTN_SOUTH" and event.state == 1: #circle key
                clear()
                  
def read_xyz():
    clear_serial_buffer()
    global captured
    global button_read
    global last_data
    try:
        data = ser.readline().decode("utf-8").strip()
        if data and data != last_data:
            x, y, z = map(float, data.split(","))
            if(x <= 1000 and y<=1000 and z <= 1000):
                xyz_points.append((x, y, z))
                last_data = data
                captured = f"Captured: X={x}, Y={y}, Z={z}\n"
                display.insert(tk.END, captured)
                display.see(tk.END) 
                button_read.config(bg="green")
                root.after(500, lambda: button_read.config(bg="SystemButtonFace"))
            else:
                return        
    except ValueError:
        button_read.config(bg="red")
        root.after(500, lambda: button_read.config(bg="SystemButtonFace"))            
        return

def select_plane(points, plane):
    if plane == 'XY Plane':
        return [(x, y) for x, y, _ in points]
    elif plane == 'YZ Plane':
        return [(y, z) for _, y, z in points]
    elif plane == 'XZ Plane':
        return [(x, z) for x, _, z in points]
    else:
        messagebox.showerror("Error", "Invalid plane.")
        
def create_hole(radius):
    global dropdown_var
    plane = dropdown_var.get().strip()
    xyz_points.clear()
    global email_body
    points.clear()
    read_xyz()
    points1 = []
    points1 = select_plane(xyz_points, plane)
    ax.set_title("3d Templating")
    ax.set_xlabel("X-axis")
    ax.set_ylabel("Y-axis")
    for pt in points1:
        points.append(pt) 
    email_body += "\n".join(f" {item}\n" for item in points) 
    try:
        msp.add_circle(points[-1],radius)
        circle = plt.Circle(points[-1], radius, color='blue', fill=False)
        ax.add_patch(circle)
        ax.plot()
        canvas.draw()
        display.insert(tk.END, "Hole Created\n")
        display.see(tk.END) 
        xyz_points.clear()
        points.clear()
    except:
        return
    
def create_spline():
    global dropdown_var
    global captured
    global email_body
    plane = dropdown_var.get().strip()
    points1 = []
    points1 = select_plane(xyz_points, plane)
    ax.set_title("3d Templating")
    ax.set_xlabel("X-axis")
    ax.set_ylabel("Y-axis")
    for pt in points1:
        points.append(pt)
    msp.add_spline(points)
    email_body += "\n".join(f" {item}\n" for item in points) 
    x_vals, y_vals = zip(*points)
    if len(points) > 3:
        tck, _ = splprep([x_vals, y_vals], s=0)
        u_new = np.linspace(0, 1, 100)
        spline_x, spline_y = splev(u_new, tck)
        ax.plot(spline_x, spline_y, 'b')
        canvas.draw()
        display.insert(tk.END, "Drawing Spline\n")
        display.see(tk.END)         
        last_point = points[-1]
        xyz_points.clear()
        points.clear()
        points.append(last_point)
    else:
        messagebox.showerror("Error", "Not enough points to create a spline")
        return
    
def create_line():
    global dropdown_var
    global captured
    global email_body
    plane = dropdown_var.get().strip()
    points1 = []
    points1 = select_plane(xyz_points, plane)
    ax.set_title("3d Templating")
    ax.set_xlabel("X-axis")
    ax.set_ylabel("Y-axis")
    try:
        for pt in points1:
            points.append(pt)
        for i in range(len(points)-1):
            msp.add_line(points[i],points[i+1])
        x_vals, y_vals = zip(*points)
        email_body += "\n".join(f" {item}\n" for item in points) 

        if len(points) >= 2:
            ax.plot(x_vals, y_vals, 'bo-')
            canvas.draw()
            last_point = points[-1]
            xyz_points.clear()
            points.clear()
            points.append(last_point)
            display.insert(tk.END, "Drawing Line\n")
            display.see(tk.END) 
        else:
            messagebox.showerror("Error", "Not enough points to create a line")
            return
    except:
        return
    
def calculate_radius():
    global dropdown_var
    plane = dropdown_var.get().strip()
    points1 = select_plane(xyz_points, plane)
    for pt in points1:
        points.append(pt) 
    (x1, y1), (x2, y2), (x3, y3) = points[-1], points[-2], points[-3]
    a = math.hypot(x3 - x2, y3 - y2)
    b = math.hypot(x3 - x1, y3 - y1)
    c = math.hypot(x2 - x1, y2 - y1)
    area = 0.5 * abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))
    if area != 0:
        radius = (a * b * c) / (4 * area)
        messagebox.showinfo("Radius Info", f"Radius of the arc is {radius:.2f}")
        captured = f"Radius of the arc is {radius:.2f}\n"
        display.insert(tk.END, captured)
        display.see(tk.END) 
    else:
        messagebox.showerror("Error","The points are colinear — no circle/arc can be formed.")    
    xyz_points.clear()
    points.clear()
    
def copy_text():
    display.event_generate("<<Copy>>")

def paste_text():
    display.event_generate("<<Paste>>")

def cut_text():
    display.event_generate("<<Cut>>")

def show_context_menu(event):
    global context_menu
    context_menu.post(event.x_root, event.y_root)

def export_to_dxf():
    global email_body
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "output.dxf")
    doc.saveas(file_name)
    display.insert(tk.END, "Email sent\n")  
    display.see(tk.END)  
    send_email_with_attachment("rupeshinsalem@gmail.com","wywe tazp nqly xmzx","rupeshinsalem@gmail.com","3D Scanner Image File",email_body,file_name)
    
def send_email_with_attachment(sender_email, sender_password, recipient_email, subject, body, file_path):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with open(file_path, 'rb') as attachment:
            mime_base = MIMEBase('application', 'octet-stream')
            mime_base.set_payload(attachment.read())
            encoders.encode_base64(mime_base)
            mime_base.add_header(
                'Content-Disposition',
                f'attachment; filename={file_path.split("/")[-1]}'
            )
            msg.attach(mime_base)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, sender_password)  # Log in to the SMTP server
            server.send_message(msg)  
    except Exception as e:
        print(f" {e}")
        
def on_closing():
    if ser.is_open:
        ser.close()
    root.destroy()  
    
def main():
    global display
    global display_all
    global entry_plane
    global dropdown_var
    global context_menu
    global button_read
    global com_var
    
    ttk.Label(left_frame, text="Choose The Plane", font=("Arial", 18)).grid(pady =10)
    dropdown = ttk.Combobox(left_frame, textvariable = dropdown_var, font = ("Arial", 14))
    dropdown['values'] = ("XY Plane", "YZ Plane", "XZ Plane")  
    dropdown.current(0)  
    dropdown.grid(pady = 10)
    ttk.Label(left_frame, text="Choose the COM Port", font=("Arial", 18)).grid(pady =10)
    dropdown1 = ttk.Combobox(left_frame, textvariable = com_var, font = ("Arial", 14))
    dropdown1['values'] = ("COM4", "COM5", "COM6")  
    dropdown1.current(0)  
    dropdown1.grid(pady = 10)
    dropdown1.bind("<<ComboboxSelected>>", ser_connection)
    button_read = tk.Button(left_frame, text = "Read point",  font = ("Arial", 14), command = read_xyz)
    button_read.grid()  
    button_line = tk.Button(left_frame, text = "Create Line", command = create_line, font = ("Arial", 14))
    button_line.grid() 
    button_spl = tk.Button(left_frame, text = "Create Spline", command = create_spline, font = ("Arial", 14))
    button_spl.grid()  
    button_hole3 = tk.Button(left_frame, text = "Create 3 diameter Hole", command = lambda : create_hole(1.5), font = ("Arial", 14))
    button_hole3.grid()   
    button_hole10 = tk.Button(left_frame, text = "Create 10 diameter Hole", command = lambda : create_hole(5), font = ("Arial", 14))
    button_hole10.grid()  
    button_angle = tk.Button(left_frame, text = "Calculate Radius", command = calculate_radius, font = ("Arial", 14))
    button_angle.grid()
    button_dxf = tk.Button(left_frame, text = "Create DXF & Send Email", command = export_to_dxf, font = ("Arial", 14))
    button_dxf.grid()
    button_clear = tk.Button(left_frame, text = "Clear Points", command = clear, font = ("Arial", 14))
    button_clear.grid()
    display = scrolledtext.ScrolledText(left_frame, width=60, height=10)
    display.grid(row=60, column=0, padx=10, pady=10, sticky="nsew")
    scrollbar = tk.Scrollbar(left_frame, command=display.yview)
    scrollbar.grid(row=60, column=1, sticky="ns")
    display.config(yscrollcommand=scrollbar.set)
    context_menu = Menu(left_frame, tearoff=0)
    context_menu.add_command(label="Cut", command=cut_text)
    context_menu.add_command(label="Copy", command=copy_text)
    context_menu.add_command(label="Paste", command=paste_text)
    display.bind("<Button-3>", show_context_menu)  
    ser_connection()
    threading.Thread(target=key_pressed, daemon=True).start()  
    root.protocol("WM_DELETE_WINDOW", on_closing) 
    root.mainloop()

if __name__ == "__main__":
    main()
   
