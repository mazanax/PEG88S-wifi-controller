import io
import os
import socket
import threading
import time
from tkinter import Tk, Canvas, NW

from PIL import Image as PImage, ImageTk

from camera import Camera

IP = "192.168.4.153"
CAMERA_PORT = 8080
CONTROL_PORT = 8090

root = None
canvas = None
pictures = [None, None]
current_picture = 0
picture_on_canvas = None
last_image_taken = None

running = True
need_jump = False
speed = 0
rotation = 0


def on_press(key):
    global running, need_jump, speed, rotation

    if key.keycode == 65:  # space
        need_jump = True
    elif key.keycode == 9:  # escape
        on_close()
    elif key.char == "w":
        speed = 50
    elif key.char == "s":
        speed = -50
    elif key.char == "W":
        speed = 100
    elif key.char == "S":
        speed = -100
    elif key.char == "a" or key.char == "A":
        rotation = -40
    elif key.char == "d" or key.char == "D":
        rotation = 40


def on_release(key):
    global speed, rotation

    if key.keycode in [25, 39]:
        speed = 0
    if key.keycode in [38, 40]:
        rotation = 0


def on_close():
    global running
    running = False

    if root is not None:
        root.destroy()


def send_udp(sock):
    global running, need_jump, speed, rotation

    while running:
        if need_jump and speed == 0:
            b = bytes.fromhex(Camera.jump())
            need_jump = False
        elif speed != 0 or rotation != 0:
            b = bytes.fromhex(Camera.move(speed, rotation))
            need_jump = False
        else:
            b = bytes.fromhex(Camera.ping())

        try:
            sock.sendto(b, (IP, CONTROL_PORT))
        except OSError:
            pass
        time.sleep(.15)


def read_udp(control_sock):
    global running, canvas, pictures, current_picture, picture_on_canvas, last_image_taken

    images = []

    while running:
        try:
            control_sock.sendto(bytes.fromhex(Camera.start()), (IP, CONTROL_PORT))

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(bytes.fromhex(Camera.start()), (IP, CAMERA_PORT))

            image_buffer = b""
            current_image = b""
            started = False
            while sock is not None and running:
                try:
                    sock.settimeout(2)
                    data, addr = sock.recvfrom(1472)

                    if b'\xff\xd8' in data:
                        current_image = data[0]
                        image_buffer += data[8:]
                        started = True
                        images.append(data)
                        continue

                    if b'\xff\xd9' in data:
                        image_buffer += data[8:]
                        images.append(data)

                        now = time.time()
                        if last_image_taken is None or now - last_image_taken > 0.1 and canvas is not None:
                            last_image_taken = now

                            try:
                                image_file = PImage.open(io.BytesIO(image_buffer))
                                pictures[current_picture] = ImageTk.PhotoImage(image_file)
                                canvas.itemconfigure(picture_on_canvas, image=pictures[current_picture])
                                current_picture = (current_picture + 1) % 2
                            except Exception:
                                pass

                        image_buffer = b""
                        current_image = b""
                        continue

                    if started and current_image == data[0]:
                        image_buffer += data[8:]
                        images.append(data)
                except socket.timeout:
                    sock.sendto(bytes.fromhex(Camera.stop()), (IP, CAMERA_PORT))
                    sock.sendto(bytes.fromhex(Camera.stop()), (IP, CONTROL_PORT))

                    sock.close()
                    time.sleep(.1)
                    break
        except OSError as e:
            pass


def main():
    global root, canvas, pictures, current_picture, picture_on_canvas, running

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sender = threading.Thread(target=send_udp, args=(sock,))
    sender.start()

    receiver = threading.Thread(target=read_udp, args=(sock,))
    receiver.start()

    os.system('xset r off')
    root = Tk()
    root.resizable(0, 0)

    icon = PImage.open("res/icon.png").resize((64, 64))
    root.wm_iconphoto(False, ImageTk.PhotoImage(icon))

    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    w = w // 2
    h = h // 2
    root.title("WiFi Car Control")
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.geometry("1280x720+{}+{}".format(w - 640, h - 360))
    root.bind("<KeyPress>", on_press)
    root.bind("<KeyRelease>", on_release)

    canvas = Canvas(root, width=1280, height=720)
    canvas.pack()
    image_file = PImage.open("res/no_image.jpg").resize((1280, 720))
    pictures[current_picture] = ImageTk.PhotoImage(image_file)
    picture_on_canvas = canvas.create_image((0, 0), image=pictures[current_picture], anchor=NW)
    current_picture = (current_picture + 1) % 2

    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_close()

    sock.sendto(bytes.fromhex(Camera.stop()), (IP, CONTROL_PORT))
    sock.close()
    os.system('xset r on')


if __name__ == '__main__':
    main()
