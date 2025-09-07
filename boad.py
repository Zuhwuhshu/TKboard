import tkinter as tk
from tkinter import filedialog, simpledialog, Toplevel, StringVar, OptionMenu, Button
import pygame
import sounddevice as sd, wave, os
from styles import STYLES   # ✅ import styles
from pynput import keyboard as kb   # ✅ global hotkeys

RECORDINGS_DIR = "recordings"

class SoundButton(tk.Button):
    def __init__(self, master, sound_path, key=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sound_path = sound_path
        self.key = key  # store assigned key
        self.config(command=self.play_sound)

    def play_sound(self, event=None):  # event param lets keys trigger it
        pygame.mixer.music.load(self.sound_path)
        pygame.mixer.music.play()

class SoundboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎵 Soundboard with Recorder")
        self.geometry("450x500")
        self.configure(**STYLES["window"])  # ✅ apply window style
        pygame.mixer.init()

        os.makedirs(RECORDINGS_DIR, exist_ok=True)

        self.sounds = []   # list of SoundButton
        self.key_map = {}  # key -> SoundButton mapping

        self.create_widgets()
        self.load_existing_sounds()

        # ✅ Start global key listener
        listener = kb.Listener(on_press=self.on_key_press)
        listener.start()

    def on_key_press(self, key):
        """Handle global key presses."""
        try:
            if hasattr(key, "char") and key.char in self.key_map:
                self.key_map[key.char].play_sound()
        except Exception as e:
            print("Key press error:", e)

    def create_widgets(self):
        # Title
        title = tk.Label(self, text="Soundboard", **STYLES["title"])
        title.pack(pady=10)

        # Frame for sound buttons
        self.button_frame = tk.Frame(self, bg=STYLES["window"]["bg"])
        self.button_frame.pack(pady=10)

        # Add / Record / Delete / Reassign buttons
        self.add_button = tk.Button(self, text="➕ Add Sound", command=self.add_sound, **STYLES["add_button"])
        self.add_button.pack(pady=5)

        self.record_button = tk.Button(self, text="🎙️ Record Sound", command=self.record_sound, **STYLES["record_button"])
        self.record_button.pack(pady=5)

        self.delete_button = tk.Button(self, text="🗑️ Delete Sound", command=self.delete_sound, **STYLES["delete_button"])
        self.delete_button.pack(pady=5)

        self.reassign_button = tk.Button(self, text="🔑 Re-Assign Key", command=self.reassign_key, **STYLES["add_button"])
        self.reassign_button.pack(pady=5)

    def add_sound(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg")]
        )
        if file_path:
            self.create_sound_button(file_path, ask_key=True)

    def record_sound(self):
        name = simpledialog.askstring("Recording", "Enter a name for your sound:")
        if not name:
            return

        # ask duration
        try:
            duration = int(simpledialog.askstring("Recording Length", "Enter recording duration (seconds):"))
        except (TypeError, ValueError):
            return

        file_path = os.path.join(RECORDINGS_DIR, f"{name}.wav")
        samplerate, channels = 44100, 1

        # popup
        popup = Toplevel(self)
        popup.title("Recording")
        popup.geometry("300x220")
        popup.configure(**STYLES["window"])

        label = tk.Label(popup, text="Recording starts in...", bg=STYLES["window"]["bg"], fg="white", font=("Arial", 14))
        label.pack(pady=10)

        countdown_label = tk.Label(popup, text="3", fg="red", bg=STYLES["window"]["bg"], font=("Arial", 32))
        countdown_label.pack(pady=10)

        remaining_label = tk.Label(popup, text="", fg="lime", bg=STYLES["window"]["bg"], font=("Arial", 28))
        remaining_label.pack(pady=10)

        cancel_flag = {"stop": False}

        def cancel():
            cancel_flag["stop"] = True
            popup.destroy()

        Button(popup, text="Cancel", command=cancel, **STYLES["delete_button"]).pack(pady=5)

        def start_recording():
            if cancel_flag["stop"]:
                return
            label.config(text="🎙️ Recording...")
            countdown_label.config(text="")
            remaining_label.config(text=str(duration))

            audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')

            def update_remaining(i):
                if cancel_flag["stop"]:
                    sd.stop()
                    return
                if i > 0:
                    remaining_label.config(text=str(i))
                    self.after(1000, update_remaining, i - 1)
                else:
                    sd.wait()
                    popup.destroy()
                    if cancel_flag["stop"]:
                        return
                    # save file
                    with wave.open(file_path, 'wb') as wf:
                        wf.setnchannels(channels)
                        wf.setsampwidth(2)
                        wf.setframerate(samplerate)
                        wf.writeframes(audio.tobytes())
                    self.create_sound_button(file_path, ask_key=True)

            update_remaining(duration)

        def countdown(i):
            if cancel_flag["stop"]:
                return
            if i > 0:
                countdown_label.config(text=str(i))
                self.after(1000, countdown, i - 1)
            else:
                start_recording()

        countdown(3)

    def ask_for_key(self):
        """Popup: wait for the user to press a key, return it if unique."""
        popup = Toplevel(self)
        popup.title("Assign Key")
        popup.geometry("300x120")
        popup.configure(**STYLES["window"])

        label = tk.Label(popup, text="Press a key to assign this sound:",
                         bg=STYLES["window"]["bg"], fg="white")
        label.pack(pady=20)

        assigned_key = {"value": None}

        def on_press(key):
            try:
                if hasattr(key, "char") and key.char:
                    k = key.char
                elif hasattr(key, "name"):
                    k = key.name
                else:
                    k = None

                if k and k in self.key_map:  # 🔁 duplicate check
                    label.config(text=f"⚠️ '{k}' already used, press another")
                    return

                assigned_key["value"] = k
            except Exception:
                assigned_key["value"] = None
            finally:
                if assigned_key["value"]:
                    listener.stop()
                    popup.destroy()

        listener = kb.Listener(on_press=on_press)
        listener.start()
        self.wait_window(popup)
        return assigned_key["value"]

    def create_sound_button(self, file_path, ask_key=False):
        assigned_key = self.ask_for_key() if ask_key else None

        btn = SoundButton(
            self.button_frame,
            sound_path=file_path,
            key=assigned_key,
            text=f"{os.path.basename(file_path)} ({assigned_key})" if assigned_key else os.path.basename(file_path),
            **STYLES["sound_button"]
        )
        btn.pack(pady=4)
        self.sounds.append(btn)

        if assigned_key:
            self.key_map[assigned_key] = btn

    def load_existing_sounds(self):
        for file_name in os.listdir(RECORDINGS_DIR):
            if file_name.endswith(".wav"):
                # don’t ask for key on load
                self.create_sound_button(os.path.join(RECORDINGS_DIR, file_name), ask_key=False)

    def delete_sound(self):
        if not self.sounds:
            print("No sounds to delete.")
            return

        popup = Toplevel(self)
        popup.title("Delete Sound")
        popup.geometry("300x150")
        popup.configure(**STYLES["window"])

        tk.Label(popup, text="Select a sound to delete:", bg=STYLES["window"]["bg"], fg="white").pack(pady=10)

        names = [btn["text"] for btn in self.sounds]
        selected = StringVar(popup)
        selected.set(names[0])

        dropdown = OptionMenu(popup, selected, *names)
        dropdown.pack(pady=5)

        def confirm_delete():
            name = selected.get()
            for btn in self.sounds:
                if btn["text"] == name:
                    file_path = btn.sound_path
                    if btn.key in self.key_map:
                        del self.key_map[btn.key]
                    btn.destroy()
                    self.sounds.remove(btn)
                    # only delete file if inside recordings/
                    if file_path.startswith(RECORDINGS_DIR) and os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Deleted {file_path}")
                    else:
                        print(f"Removed button for {file_path} (file not deleted).")
                    break
            popup.destroy()

        Button(popup, text="Delete", command=confirm_delete, **STYLES["delete_button"]).pack(pady=10)

    def reassign_key(self):
        if not self.sounds:
            print("No sounds to reassign.")
            return

        popup = Toplevel(self)
        popup.title("Re-Assign Key")
        popup.geometry("300x150")
        popup.configure(**STYLES["window"])

        tk.Label(popup, text="Select a sound to re-assign:", bg=STYLES["window"]["bg"], fg="white").pack(pady=10)

        names = [btn["text"] for btn in self.sounds]
        selected = StringVar(popup)
        selected.set(names[0])

        dropdown = OptionMenu(popup, selected, *names)
        dropdown.pack(pady=5)

        def confirm_reassign():
            name = selected.get()
            for btn in self.sounds:
                if btn["text"] == name:
                    new_key = self.ask_for_key()
                    if btn.key in self.key_map:
                        del self.key_map[btn.key]
                    btn.key = new_key
                    btn.config(text=f"{os.path.basename(btn.sound_path)} ({new_key})")
                    self.key_map[new_key] = btn
                    break
            popup.destroy()

        Button(popup, text="Re-Assign", command=confirm_reassign, **STYLES["add_button"]).pack(pady=10)

if __name__ == "__main__":
    app = SoundboardApp()
    app.mainloop()
