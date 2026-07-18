
from flask import Flask, render_template
from flask_socketio import SocketIO


def create_app() -> tuple[Flask, SocketIO]:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    return app, socketio


app, socketio = create_app()


if __name__ == "__main__":
    socketio.run(
    app,
    host="127.0.0.1",
    port=5000,
    allow_unsafe_werkzeug=True
)