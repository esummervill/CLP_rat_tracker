# CLP Rat Tracker

**Conditioned Place Preference (CPP) Experiment Tracker**

A simple, cross-platform tool for tracking which side of a bin a rat prefers. Designed for behavioral neuroscience labs running CPP experiments with standard video recordings (MP4, MTS).

Built on the tracking concepts from [CaT-z Software](https://github.com/CaT-zTools/CaT-z_Software), adapted for standard 2D video analysis.

---

## What It Does

- Loads your experiment video (MP4, MTS, AVI, MOV)
- You draw a line on the video to define the two sides of the bin
- Automatically tracks the rat's position frame-by-frame
- Calculates **time on each side**, **preference index**, and **number of crossings**
- Exports results to CSV for analysis in Excel, R, SPSS, etc.

---

## Installation

### Step 1: Install Python

**Windows:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download and run the installer
3. **IMPORTANT:** Check the box that says **"Add Python to PATH"** during installation
4. Click "Install Now"

**Mac:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download and run the installer
3. Follow the prompts

### Step 2: Get the Software

**Option A - Download ZIP (easiest):**
1. Go to the [repository page](https://github.com/LeoBlakeley/CLP_rat_tracker)
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file to a folder (e.g., Desktop or Documents)

**Option B - Clone with Git:**
```
git clone https://github.com/LeoBlakeley/CLP_rat_tracker.git
```

### Step 3: Run the App (dependencies install automatically)

**Windows:** Double-click **`run_windows.bat`** -- it will install everything for you on first launch.

**Mac:** Double-click **`run_mac.command`** -- it will install everything for you on first launch. (You may need to right-click > Open the first time.)

That's it! The launcher scripts automatically create an isolated environment and install all required packages the first time you run them. No manual commands needed.

### Manual Installation (if the launcher scripts don't work)

Open a terminal/command prompt, navigate to the CLP_rat_tracker folder, and run:

```
pip install -r requirements.txt
```

Or install the project as a package:

```
pip install .
```

---

## How to Use

### Starting the App

**Windows:** Double-click `run_windows.bat`

**Mac:** Double-click `run_mac.command` (you may need to right-click > Open the first time)

**Or from a terminal:**
```
python main.py
```

### Step-by-Step

1. **Load Video** - Click "Open Video File" and select your MP4 or MTS recording

2. **Draw the Dividing Line** - Click two points on the video to draw the line that separates Side A from Side B. The sides are labeled with colors (blue = Side A, red = Side B). You can rename them (e.g., "Drug Side" / "Saline Side")

3. **Adjust Settings** (optional)
   - **Sensitivity**: Higher = detects more movement (increase if the rat is not being detected; decrease if background noise is being picked up)
   - **Min size**: Minimum blob size in pixels (increase if small noise blobs are being tracked instead of the rat)

4. **Start Tracking** - Click "Start Tracking" and wait for it to process. You'll see the rat being tracked in real-time with a colored dot

5. **View Results** - When complete, you'll see:
   - Time spent on each side (seconds and percentage)
   - Preference Index (-1.0 to +1.0)
   - Number of crossings between sides

6. **Export Data** - Click "Export CSV" for frame-by-frame data, or "Export Summary" for a single-row summary

---

## Understanding the Results

| Metric | Meaning |
|--------|---------|
| **Side A / Side B Time** | Total seconds the rat spent on each side |
| **Side A / Side B %** | Percentage of tracked time on each side |
| **Preference Index** | Ranges from -1.0 (100% Side A) to +1.0 (100% Side B). 0.0 = no preference |
| **Crossings** | Number of times the rat crossed from one side to the other |

### CSV Export Columns (detailed)

| Column | Description |
|--------|-------------|
| Frame | Frame number |
| Time (s) | Timestamp in seconds |
| X, Y | Rat position in pixels |
| Side | Which side the rat was on |
| Cumulative (s) | Running total of time on each side |

---

## Troubleshooting

**"Python is not found"**
- Make sure Python is installed and added to your PATH. Reinstall Python and check "Add Python to PATH".

**Video won't load**
- Make sure the file is a valid MP4, MTS, AVI, or MOV file.
- Some MTS files from older cameras may need converting. Use [HandBrake](https://handbrake.fr/) (free) to convert to MP4.

**Rat is not being detected**
- Increase the Sensitivity slider
- Decrease the Min Size value
- Make sure there is good contrast between the rat and the bin floor
- The background subtraction works best with a static camera

**Too much noise / detecting wrong things**
- Decrease the Sensitivity slider
- Increase the Min Size value
- Make sure the camera is stationary (not handheld)

---

## Supported Video Formats

- MP4 (.mp4)
- MTS (.mts, .MTS) - AVCHD format from many lab cameras
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- WMV (.wmv)

---

## Citation

This software is based on tracking approaches from:

> Gerós, A., Magalhães, A. & Aguiar, P. "Improved 3D tracking and automated classification of rodents' behavioral activity using depth-sensing cameras." *Behav Res* (2020). doi: 10.3758/s13428-020-01381-9

Original software: [CaT-z Software](https://github.com/CaT-zTools/CaT-z_Software)

---

## License

MIT License - Free to use and modify for research purposes.
