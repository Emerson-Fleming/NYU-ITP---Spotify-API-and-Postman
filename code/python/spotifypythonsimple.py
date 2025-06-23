import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, redirect
import requests
from io import BytesIO
from PIL import Image, ImageTk
import qrcode
from tkinter import Grid, Tk, Label, Toplevel
import threading
import queue
import atexit
import sys

app = Flask(__name__)

CURRENT_TOKEN_INFO = None
TOKEN_LOCK = threading.Lock()

CURRENT_SONG_QUEUE = queue.Queue()

ROOT = None

DISPLAY_WINDOW = None
ALBUM_LABEL = None
QR_LABEL = None
CURRENT_ALBUM_PIL_IMAGE = None
CURRENT_QR_PIL_IMAGE = None

POLLING_ACTIVE = threading.Event()
POLLING_THREAD = None

# change client id and secret to your own; not secure
CLIENT_ID = ""
CLIENT_SECRET = ""


@app.route("/")
def login():
    print("Flask: / (login) route hit. Redirecting to Spotify auth.")
    sys.stdout.flush()
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)


@app.route("/redirect")
def redirect_page():
    print("Flask: /redirect route hit. Attempting to get token.")
    sys.stdout.flush()
    code = request.args.get("code")
    spotify_oauth = create_spotify_oauth()
    try:
        token_info = spotify_oauth.get_access_token(code)
        print("Flask: Successfully obtained Spotify access token.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Flask: ERROR getting Spotify access token: {e}")
        sys.stdout.flush()
        return "<h1>Error during Spotify authentication. Please try again.</h1>"

    global CURRENT_TOKEN_INFO
    with TOKEN_LOCK:
        CURRENT_TOKEN_INFO = token_info
        print("Flask: Initial Spotify token stored globally.")
        sys.stdout.flush()
    global POLLING_THREAD
    if POLLING_THREAD is None or not POLLING_THREAD.is_alive():
        POLLING_ACTIVE.set()
        POLLING_THREAD = threading.Thread(target=run_spotify_polling, daemon=True)
        POLLING_THREAD.start()
        print("Flask: Spotify polling thread initiated and started.")
        sys.stdout.flush()
    else:
        print("Flask: Polling thread already running.")
        sys.stdout.flush()
    return "<h1>Spotify authentication successful!</h1><p>The album cover and QR code will appear in a separate window.</p>"


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirect_page", _external=True),
        scope="user-read-currently-playing user-read-playback-state",
    )


def create_spotify_oauth_for_polling_thread():
    with app.app_context():
        return create_spotify_oauth()


def get_valid_token():
    global CURRENT_TOKEN_INFO
    with TOKEN_LOCK:
        if CURRENT_TOKEN_INFO is None:

            sys.stdout.flush()
            return None
        now = int(time.time())

        is_expired = CURRENT_TOKEN_INFO["expires_at"] - now < 60
        if is_expired:
            try:
                print(
                    "Polling: Token is expired or near expiration. Attempting refresh."
                )
                sys.stdout.flush()
                spotify_oauth = create_spotify_oauth_for_polling_thread()
                refreshed_token = spotify_oauth.refresh_access_token(
                    CURRENT_TOKEN_INFO["refresh_token"]
                )
                CURRENT_TOKEN_INFO = refreshed_token
                print("Polling: Spotify token refreshed successfully.")
                sys.stdout.flush()
            except Exception as e:
                print(f"Polling: ERROR Failed to refresh Spotify token: {e}")
                sys.stdout.flush()
                CURRENT_TOKEN_INFO = None
                return None
        return CURRENT_TOKEN_INFO["access_token"]


def fetch_currently_playing():
    access_token = get_valid_token()
    if not access_token:

        sys.stdout.flush()
        return None
    sp = spotipy.Spotify(auth=access_token)
    try:
        current_playback = sp.current_playback()
        if not current_playback or not current_playback.get("item"):

            sys.stdout.flush()
            return None
        album_cover_url = current_playback["item"]["album"]["images"][0]["url"]
        song_url = current_playback["item"]["external_urls"]["spotify"]

        sys.stdout.flush()
        return {"image_url": album_cover_url, "song_url": song_url}
    except spotipy.exceptions.SpotifyException as se:
        print(f"Polling: Spotify API error fetching playback: {se}")
        sys.stdout.flush()
        if se.http_status == 401:
            with TOKEN_LOCK:
                _current_token_info = None
            print("Polling: Token invalidated due to 401. Re-authentication needed.")
            sys.stdout.flush()
        return None
    except Exception as e:
        print(f"Polling: Unexpected error fetching current playback: {e}")
        sys.stdout.flush()
        return None


def run_spotify_polling():
    print("Polling thread: Started.")
    sys.stdout.flush()
    while POLLING_ACTIVE.is_set():
        song_data = fetch_currently_playing()
        if song_data:

            sys.stdout.flush()
            CURRENT_SONG_QUEUE.put(song_data)
        time.sleep(1)
    print("Polling thread: Stopped.")
    sys.stdout.flush()


def display_image_and_qr(image_url, song_url):
    global ROOT, DISPLAY_WINDOW, ALBUM_LABEL, QR_LABEL, CURRENT_ALBUM_PIL_IMAGE, CURRENT_QR_PIL_IMAGE
    if not ROOT:
        print("Tkinter: Root window not initialized. Cannot display.")
        sys.stdout.flush()
        return
    try:

        print("Tkinter: Fetching album cover image...")
        sys.stdout.flush()
        response = requests.get(image_url)
        new_album_pil_image = Image.open(BytesIO(response.content)).convert("RGB")
        print("Tkinter: Album cover fetched.")
        sys.stdout.flush()

        print("Tkinter: Generating QR code...")
        sys.stdout.flush()
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(song_url)
        qr.make(fit=True)
        new_qr_pil_image = qr.make_image(fill="black", back_color="white").convert(
            "RGB"
        )
        print("Tkinter: QR code generated.")
        sys.stdout.flush()

        CURRENT_ALBUM_PIL_IMAGE = new_album_pil_image
        CURRENT_QR_PIL_IMAGE = new_qr_pil_image

        def resize_images():
            if not DISPLAY_WINDOW or not DISPLAY_WINDOW.winfo_exists():
                return

            target_width_per_image = DISPLAY_WINDOW.winfo_width() // 2
            target_height = DISPLAY_WINDOW.winfo_height()
            if target_width_per_image <= 0 or target_height <= 0:
                return
            min_dim = min(target_width_per_image, target_height)
            if min_dim <= 0:
                return

            if CURRENT_ALBUM_PIL_IMAGE:
                resized_album = CURRENT_ALBUM_PIL_IMAGE.copy()
                if resized_album.width > min_dim or resized_album.height > min_dim:
                    resized_album.thumbnail(
                        (min_dim, min_dim), Image.Resampling.LANCZOS
                    )
                album_tk = ImageTk.PhotoImage(resized_album)
                ALBUM_LABEL.config(image=album_tk)
                ALBUM_LABEL.image = album_tk

            if CURRENT_QR_PIL_IMAGE:
                resized_qr = CURRENT_QR_PIL_IMAGE.copy()
                if resized_qr.width > min_dim or resized_qr.height > min_dim:
                    resized_qr.thumbnail((min_dim, min_dim), Image.Resampling.LANCZOS)
                qr_tk = ImageTk.PhotoImage(resized_qr)
                QR_LABEL.config(image=qr_tk)
                QR_LABEL.image = qr_tk

        if DISPLAY_WINDOW is None or not DISPLAY_WINDOW.winfo_exists():
            DISPLAY_WINDOW = Toplevel(ROOT)
            DISPLAY_WINDOW.title("Spotify Album and QR Code")
            DISPLAY_WINDOW.geometry("600x300")
            print("Tkinter: Created new Toplevel window.")
            sys.stdout.flush()

            Grid.columnconfigure(DISPLAY_WINDOW, 0, weight=1)
            Grid.columnconfigure(DISPLAY_WINDOW, 1, weight=1)
            Grid.rowconfigure(DISPLAY_WINDOW, 0, weight=1)

            ALBUM_LABEL = Label(DISPLAY_WINDOW)
            ALBUM_LABEL.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            QR_LABEL = Label(DISPLAY_WINDOW)
            QR_LABEL.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

            DISPLAY_WINDOW.bind("<Configure>", resize_images)
            print(
                "Tkinter: Toplevel window and labels initialized, resize binding set."
            )
            sys.stdout.flush()
        else:
            print("Tkinter: Updating existing Toplevel window.")
            sys.stdout.flush()

        DISPLAY_WINDOW.update_idletasks()
        resize_images()
        print("Tkinter: Image and QR code updated in window.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Tkinter: ERROR displaying image or QR code: {e}")
        sys.stdout.flush()


def check_queue_and_display_image():
    try:
        song_data = CURRENT_SONG_QUEUE.get_nowait()
        print("Tkinter: Retrieved song data from queue. Calling display_image_and_qr.")
        sys.stdout.flush()
        display_image_and_qr(song_data["image_url"], song_data["song_url"])
    except queue.Empty:
        pass
    except Exception as e:
        print(f"Tkinter: ERROR checking queue or calling display: {e}")
        sys.stdout.flush()
    finally:

        if ROOT:
            ROOT.after(100, check_queue_and_display_image)


if __name__ == "__main__":
    ROOT = Tk()
    ROOT.withdraw()
    ROOT.title("Spotify QR App")
    print("Main: Tkinter root initialized and hidden.")
    sys.stdout.flush()

    def run_flask_app():
        from werkzeug.serving import run_simple

        run_simple(
            "0.0.0.0",
            5000,
            app,
            use_reloader=False,
            use_debugger=True,
            ssl_context="adhoc",
        )

    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    print(
        "Main: Flask app thread started on port 5000. Access at https://localhost:5000/"
    )
    sys.stdout.flush()

    atexit.register(lambda: POLLING_ACTIVE.clear())
    print("Main: Atexit handler registered for polling thread shutdown.")
    sys.stdout.flush()

    ROOT.after(100, check_queue_and_display_image)
    print("Main: Tkinter queue checking scheduled.")
    sys.stdout.flush()
    ROOT.mainloop()
    print("Main: Tkinter mainloop exited.")
    sys.stdout.flush()