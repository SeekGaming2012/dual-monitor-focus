# Installation Manual

Dual Monitor Focus runs from source with Python. The steps below take about 10 minutes, mostly
download time. All commands are for **PowerShell** on Windows 11.

## 1. Requirements

| Need | Details |
|---|---|
| Windows 11 | Windows 10 should also work, but is untested |
| Two monitors | Side by side, arranged left/right in *Settings > System > Display* |
| A webcam | Any ordinary webcam; it should see your face from your normal seat |
| Python 3.12 | Developed and tested on 3.12. 3.11 should work but is untested. Avoid very new versions until MediaPipe supports them |
| Internet (once) | To download Python packages and the face model. The app itself never goes online |
| About 1 GB free disk | For the Python environment and packages |

Check Python:

```powershell
python --version
```

If this prints `Python 3.12.x` (or 3.11.x), continue. Otherwise install it from
<https://www.python.org/downloads/windows/> and tick **Add python.exe to PATH** in the installer.

## 2. Get the project

Put the project folder somewhere permanent, for example
`C:\Users\<you>\claude-projects\dual-monitor-setup`. The desktop shortcut points into this folder, so
don't move it afterwards without re-creating the shortcut.

```powershell
cd C:\Users\<you>\claude-projects\dual-monitor-setup
```

## 3. Create the Python environment and install packages

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This installs OpenCV, MediaPipe, NumPy, pystray and Pillow (plus pytest for the tests).

## 4. Download the face model

The head-pose model is a single 3.7 MB file from Google's MediaPipe model storage. This is the only
file the app needs from the internet besides the packages.

```powershell
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" `
  -OutFile models\face_landmarker.task
```

## 5. Verify the install

```powershell
.\.venv\Scripts\python.exe scripts\step1_check_env.py
```

You should see the OpenCV, MediaPipe and NumPy versions and `model ... OK`.

Check that your webcam works. You should see yourself and an fps counter; press Esc to close:

```powershell
.\.venv\Scripts\python.exe scripts\step2_preview.py
```

If you see an error, or a black picture, see *Webcam problems* below. If you have several cameras
(including virtual ones such as Iriun or OBS), list them and pass the right index with `--camera N`:

```powershell
.\.venv\Scripts\python.exe scripts\step0_list_cameras.py
```

Optionally run the unit tests (should report all passed):

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## 6. First run and calibration

```powershell
Start-Process .\.venv\Scripts\pythonw.exe main.py
```

(Use `.\.venv\Scripts\python.exe main.py` instead if you want a console window to see error messages.)

With no saved calibration, the app calibrates first:

1. A full-screen prompt appears on the **left** monitor. Look at the dot, keep your head turned
   toward it, and hold still until the bar fills (about 4 seconds).
2. The prompt moves to the **right** monitor. Do the same.
3. The tray icon appears. Done.

Turn your head clearly toward each monitor; the two directions must differ by at least 10 degrees.
Press **Esc** during calibration to abort.

Try it: look at the other monitor for half a second and focus should follow. If it does not, see
the README's troubleshooting table.

## 7. Create a desktop shortcut (optional)

This creates a shortcut that starts the app without a console window, with the tray icon image:

```powershell
$proj = (Get-Location).Path
.\.venv\Scripts\python.exe -I -c "import sys; sys.path.insert(0,'src'); from tray import make_icon; make_icon('active').save('app.ico', sizes=[(16,16),(32,32),(48,48),(64,64)])"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Dual Monitor Focus.lnk'))
$s.TargetPath = Join-Path $proj '.venv\Scripts\pythonw.exe'
$s.Arguments = '"' + (Join-Path $proj 'main.py') + '"'
$s.WorkingDirectory = $proj
$s.IconLocation = Join-Path $proj 'app.ico'
$s.Description = 'Move keyboard focus to the monitor you look at'
$s.Save()
```

Keep `app.ico` in the project folder, or the shortcut loses its icon.

## 8. Start automatically with Windows (optional)

Right-click the tray icon and tick **Start with Windows**. Untick it to turn it off again.

This adds one entry to your per-user startup list (`HKEY_CURRENT_USER\...\Run`, value
`DualMonitorFocus`), which needs no administrator rights. It runs `pythonw.exe main.py` from this
project folder, so if you move the folder, open the app from its new location and tick the box again.
If you switch the app off in *Settings > Apps > Startup*, Windows respects that and the menu item
shows unticked; ticking it again turns it back on.

At login the app starts straight into tracking using your saved calibration. If the webcam isn't
ready yet, it retries every 2 seconds.

## Updating

Replace the project files (keep your `.venv`, `models` and `app.ico`), then, if
`requirements.txt` changed, run step 3's `pip install -r requirements.txt` again. Quit the running
app from the tray first and start it again afterwards, because a running copy keeps using the old
code. Your calibration and settings are kept in `%APPDATA%` and survive updates.

## Uninstalling

1. Right-click the tray icon, untick **Start with Windows** if it is ticked, then choose **Quit**.
2. Delete the desktop shortcut.
3. Delete the project folder (this removes the Python environment and the downloaded model).
4. Delete `%APPDATA%\dual-monitor-focus` to remove calibration, settings and the log.

The only registry entry the app ever creates is the optional startup value above, which step 1
removes. No services are installed.

## Webcam problems

| Symptom | Fix |
|---|---|
| `Could not open camera 0` | Another app is using the webcam, or the privacy shutter is closed. Close Zoom/Teams/the Camera app/browser tabs using the camera. Check *Settings > Privacy & security > Camera* ("Let desktop apps access your camera" must be on). Unplugging and replugging the camera, or disabling and re-enabling it in Device Manager, also clears a stuck camera |
| The picture is black | Shutter closed, wrong device, or a virtual camera with nothing connected. Run `step0_list_cameras.py` and try `--camera 1`, `2`, ... |
| Face not detected | Add front light, face the camera, keep your whole face in view. Glasses are fine; strong backlighting is not |
| `pip` fails to install MediaPipe | Check `python --version`. Use 64-bit Python 3.12 (the tested version) |

## Privacy summary

- Camera frames are processed in memory and discarded immediately; nothing is written to disk.
- The app opens no network connections. Internet is needed only during installation.
- Stored data: your calibration angles, your settings and a short text event log, all in
  `%APPDATA%\dual-monitor-focus`.
- Pausing or quitting releases the camera, so the webcam LED turns off.
