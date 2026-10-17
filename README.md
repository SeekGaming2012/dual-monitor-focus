# Dual Monitor Focus

A small Windows 11 tray app that moves keyboard focus to the monitor you are looking at, so you can
type without clicking. It uses your webcam to estimate which way your **head** is turned (not your
eyes), and after you have looked at a monitor for about half a second it focuses the topmost window
on that monitor.

- Two monitors, any ordinary webcam
- Runs in the background with a tray icon: Pause/Resume, Recalibrate, Quit
- Short calibration: look at the left monitor, then the right
- No flicker: it only switches after a sustained look (default 500 ms)
- **Private by design:** everything runs on your PC. Camera frames are analysed in memory and thrown
  away; no image is ever saved or sent anywhere. The app makes no network connections.

See [INSTALL.md](INSTALL.md) for setup.

## Using it

1. Start **Dual Monitor Focus** (desktop shortcut, or `pythonw main.py`).
2. The first time, a calibration prompt appears on each monitor. Look at the dot on the **left**
   monitor and hold still, then do the same on the **right**.
3. A tray icon appears (check the `^` overflow area if you don't see it). Look at a monitor for about
   half a second and focus moves to its topmost window.

### Tray menu

| Item | What it does |
|---|---|
| Status | Shows what the app is doing (tracking, paused, camera unavailable, too dark...) |
| Pause / Resume tracking | Pausing **releases the camera** (the webcam LED goes off). Double-clicking the icon does the same |
| Recalibrate... | Repeats the left/right calibration. Use it if you move your chair, camera or monitors |
| Start with Windows | Ticked = the app starts automatically when you sign in (per-user, no admin rights needed) |
| Quit | Stops the app and frees the camera |

### Tray icon colors

- **Green**: tracking
- **Grey**: paused or calibrating
- **Amber**: a problem (camera unavailable, too dark to see your face, fewer than two monitors)

## How it behaves

- **Looking away does nothing.** If you look down at the keyboard, at your phone, or turn away, focus
  stays where it is. It switches only on a sustained look at the *other* monitor.
- **It waits while you type.** A switch is held back while any key or mouse button is down, and for
  about 0.35 s afterwards, so keystrokes and drags aren't redirected mid-action. If you look back at
  the first monitor in the meantime, the pending switch is cancelled.
- **Which window gets focus:** the topmost normal window on the monitor you looked at. Minimized
  windows, windows on other virtual desktops, tool windows, the taskbar and the desktop are skipped.
- **Dark room or no face:** nothing switches until your face is visible again.
- **Sleep/wake or a camera hiccup:** the camera is reopened automatically.

## Settings

Edit `%APPDATA%\dual-monitor-focus\settings.json` (created on first run) and restart the app:

```json
{
  "dwell_s": 0.5,
  "ignore_target_processes": [],
  "suspend_when_foreground": []
}
```

| Key | Meaning |
|---|---|
| `dwell_s` | How long you must look at a monitor before focus moves, in seconds. Try 0.4 for snappier, 0.6 for steadier |
| `ignore_target_processes` | Programs that should never be chosen as the window to focus, e.g. `["overlay.exe"]` |
| `suspend_when_foreground` | While one of these programs is in front, no switching happens, e.g. `["game.exe"]` |

## Files it creates

All in `%APPDATA%\dual-monitor-focus\`:

- `calibration.json`: your left/right head angles. Numbers only, no images
- `settings.json`: the settings above
- `app.log`: a short event log (for example `LEFT: Discord.exe -> alt-tap`). It contains program names
  but no window titles and no images. It rotates at about 200 KB. Delete it any time

## Known limitations

- **It tracks head direction, not gaze.** Moving only your eyes won't register.
- **Windows may refuse to focus an administrator (elevated) window** from a normal app. The log then
  shows `FAILED` for that switch. Running the tray app as administrator avoids this but is not
  recommended.
- **Calibration depends on your seating position.** If switching becomes inaccurate after you move,
  choose Recalibrate.
- It is built for **two monitors**. With more, the leftmost and rightmost are used.
- Focus switching uses a brief synthetic Alt key press (the standard way for a background app to be
  allowed to take focus). In a few programs this can briefly highlight a menu bar.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Tray status says *camera unavailable* | Another app is using the webcam (Zoom, Teams, browser, the Camera app), or the webcam's privacy shutter is closed. Close the other app; the app retries every 2 seconds. Check *Settings > Privacy & security > Camera* |
| Nothing happens when I look at a monitor | Check the tray icon is green. Recalibrate. Make sure your face is lit from the front and visible |
| Switches to the wrong monitor | Recalibrate, with your head clearly turned toward each monitor. Left and right must differ by at least 10 degrees |
| Switches too eagerly or too slowly | Change `dwell_s` in `settings.json` |
| Second launch says "already running" | Only one copy runs at a time. Find the icon in the tray |
| Wrong webcam is used | Run `scripts\step0_list_cameras.py` to list cameras. The app uses camera 0 for the first calibration, then the `"camera"` value stored in `calibration.json`, so to change it quit the app and edit that number. Virtual cameras (Iriun, OBS) can take index 0. (Choosing a camera from the tray menu is not built yet.) |

## Project layout

```
main.py                 entry point (tray app)
src/
  headpose.py           webcam frame -> head yaw/pitch/roll (MediaPipe Face Landmarker)
  classify.py           smoothing + LEFT/RIGHT/UNKNOWN from calibrated yaw
  dwell.py              "looked long enough" filter
  inputguard.py         waits while you are typing or dragging
  monitors.py           finds monitors (Win32)
  windows.py            finds the topmost window on a monitor
  focus.py              brings a window to the foreground
  worker.py             background loop tying it all together
  calibration.py        left/right calibration prompts
  tray.py               tray icon and menu
  autostart.py          "Start with Windows" (per-user Run registry entry)
  config.py, settings.py, camera.py
scripts/                step-by-step test programs (step0 ... step9)
tests/                  unit tests for the dwell filter, input guard and autostart
models/                 face_landmarker.task (downloaded during install)
```

The `scripts/step*.py` programs are the build-up of the app, each runnable on its own. They are
handy for diagnosing problems, for example `step3_headpose.py` shows live head angles and
`step7_windows.py` shows which window the app would pick on each monitor.

## Running the tests

```
.\.venv\Scripts\python.exe -m pytest tests
```
