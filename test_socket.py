import socketio

sio = socketio.Client()


@sio.event
def connect():
    print("Connected!")


@sio.event
def disconnect():
    print("Disconnected")


try:
    sio.connect("http://127.0.0.1:5000")
    sio.wait()
except Exception as e:
    print(e)