# FrontierInterfaceHackathon2026

## Track Challenge: Storytelling with Biosensing in TouchDesigner

Turn emotional, physiological, and motion data into interactive visualizations. Participants will use biosignals such as heart rate, electrodermal activity (EDA), and accelerometer data to drive visual outputs in real time or from pre-recorded streams. The focus is on creating meaningful mappings between internal states and visual expression, enabling applications in interactive media, well-being, and performance.

## Project Metrics

Here is a short summary of the metrics that we will be working with during the project:

### 1. Cardiovascular & Blood Flow (Optical Sensors)
These metrics use light to measure how blood moves through your vascular system.

- **PPg red & ppg ir**: Use red and infrared light to measure deep tissue blood volume and oxygenation. *Practical Example*: Calculating blood oxygen levels (SpO2) using a medical finger clip oximeter.
- **ppg grn**: Uses green light for surface-level blood flow measurement, which is highly resistant to motion artifacts. *Practical Example*: A sports watch maintaining a heart rate reading while your arms swing aggressively during a sprint.
- **hr**: The calculated Heart Rate in beats per minute (BPM) derived from the PPG sensors. *Practical Example*: Your pulse elevating from 60 to 140 BPM when exercising.

### 2. Electrodermal Activity (Stress & Arousal)
These metrics track the electrical conductivity of your skin, which changes based on microscopic sweat gland activity controlled by your fight-or-flight nervous system.

- **eda**: The continuous, overall baseline electrical conductivity of your skin. *Practical Example*: The baseline skin measurement taken during a polygraph (lie detector) test.
- **scr:amp (Amplitude)**: The intensity or height of a sudden sweat spike. *Practical Example*: The exact magnitude of your physiological reaction to a jump scare in a horror movie.
- **scrfreq (Frequency)**: How many of these sweat spikes happen per minute. *Practical Example*: Registering 15 sweat spikes per minute during a high-stress math exam compared to 2 per minute while relaxing.
- **scr:ris (Rise Time)**: How long it takes for a sweat spike to reach its peak amplitude. *Practical Example*: The delayed 2-second physiological realization and sweat response after stubbing your toe.

### 3. Kinematics & Orientation (Motion Sensors)
These metrics track exactly how the device is moving through physical space across three axes (X, Y, and Z).

- **accXYZ (Accelerometer)**: Tracks straight-line acceleration and the pull of gravity. *Practical Example*: A smartphone detecting gravity to automatically rotate a video to landscape mode.
- **GYRO XYZ (Gyroscope)**: Tracks angular rotation and tilt. *Practical Example*: Tilting your device like a physical steering wheel to turn a car in a mobile racing game.
- **MagXYZ (Magnetometer)**: Tracks magnetic fields to determine directional orientation. *Practical Example*: The digital compass arrow pointing North in a navigation app.

### 4. Thermodynamics
- **temp1**: Measures localized skin temperature at the sensor's contact point. *Practical Example*: Logging your body temperature continuously overnight to detect a 0.5°C fever onset.