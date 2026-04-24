# EmotiBit: A Complete Guide

## Table of Contents
- [What is EmotiBit?](#what-is-emotibit)
- [Key Features](#key-features)
- [Hardware Overview](#hardware-overview)
- [Getting Started](#getting-started)
  - [What's in the Box](#whats-in-the-box)
  - [Assembly](#assembly)
  - [WiFi Configuration](#wifi-configuration)
  - [Installing Software](#installing-software)
  - [Installing Firmware](#installing-firmware)
  - [Bootup & LED Indicators](#bootup--led-indicators)
- [Recording Data](#recording-data)
  - [Using the EmotiBit Oscilloscope](#using-the-emotibit-oscilloscope)
  - [Streaming Protocols (OSC, UDP, LSL)](#streaming-protocols-osc-udp-lsl)
- [Data Output & Format](#data-output--format)
  - [Raw Data Format](#raw-data-format)
  - [Parsed Data Format](#parsed-data-format)
  - [File Types](#file-types)
- [EmotiBit Data Types (TypeTags)](#emotibit-data-types-typetags)
  - [Biometric TypeTags](#biometric-typetags)
  - [Sampling Rates](#sampling-rates)
- [Mapping EmotiBit Data to Our Project Metrics](#mapping-emotibit-data-to-our-project-metrics)
- [Visualization & Next Steps](#visualization--next-steps)
- [Useful Links](#useful-links)

---

## What is EmotiBit?

**EmotiBit** is an open-source, wearable biosensor designed to capture high-quality emotional, physiological, and movement data in real time. It is a small, lightweight module that stacks onto an Adafruit Feather development board and can be worn on various parts of the body (wrist, arm, head, etc.) using adjustable straps.

EmotiBit captures **16+ biometric signals** simultaneously, including:
- **Heart activity** (PPG — photoplethysmography using red, infrared, and green light)
- **Electrodermal activity** (skin conductance / stress response)
- **Motion & orientation** (accelerometer, gyroscope, magnetometer — 9-axis IMU)
- **Skin temperature** (contact thermistor or medical-grade thermopile)
- **Humidity** (perspiration sensing, on older models)

All data is **100% user-owned**, recorded with precise timestamps, and stored locally on an SD card. EmotiBit is designed for researchers, developers, educators, artists, and anyone interested in biometric sensing.

---

## Key Features

| Feature | Details |
|---------|---------|
| **Open-Source** | Hardware, firmware, and software are all open-source |
| **Wireless Streaming** | Real-time data streaming over WiFi (2.4GHz) |
| **Multi-Modal** | 16+ simultaneous biometric data channels |
| **Cross-Platform Software** | Visualizer/Oscilloscope available for Windows, macOS, and Linux |
| **Data Ownership** | All data stored locally on SD card — no cloud dependency |
| **Streaming Protocols** | OSC, UDP, LSL, and BrainFlow SDK support |
| **Modular** | Stacks onto Adafruit Feather (ESP32 Huzzah or M0 WiFi) |
| **Wearable** | Lightweight, adjustable straps for wearing anywhere on the body |
| **Timestamped** | Precise timestamps with time-sync calibration |

---

## Hardware Overview

EmotiBit is a **FeatherWing** (an add-on board for Adafruit Feather microcontrollers). The system consists of:

1. **EmotiBit Board** — The sensor module itself (available in **MD** and **EMO** variants)
2. **Adafruit Feather** — The microcontroller (either **Feather ESP32 Huzzah** or **Feather M0 WiFi**)
3. **MicroSD Card** — For local data storage
4. **LiPo Battery** — 400mAh lithium ion battery for portable use
5. **EDA Electrodes** — Ag/AgCl electrodes for electrodermal activity sensing
6. **Emoti-stretch Straps** — Adjustable straps for body placement

### LEDs on EmotiBit

| LED | Meaning |
|-----|---------|
| 🔴 **RED** | Blinks at ~1Hz when **recording** |
| 🔵 **BLUE** | Solid on when **connected** to EmotiBit Oscilloscope |
| 🟡 **YELLOW** | Solid on when **battery is low** |

### Buttons & Switches

| Control | Action |
|---------|--------|
| **EmotiBit Button** (short press) | Toggle WiFi modes |
| **EmotiBit Button** (long press, 5 sec) | Enter **Sleep mode** |
| **Reset Button** | Restart the microcontroller |
| **Hibernate Switch** (V4+) | Kill power to Feather and EmotiBit for long-term storage |

---

## Getting Started

### What's in the Box

**EmotiBit unit:**
- 1× EmotiBit with finger loop Emoti-stretch strap
- 1× Emoti-genic barrier (hygienic layer / sweat protection)
- 2× EDA electrodes (Ag/AgCl) pre-attached
- 2× EmotiBit stickers

**Essentials Kit (sold separately or in bundle):**
- Adafruit Feather (M0 WiFi or ESP32 Huzzah)
- 400mAh LiPo battery
- High-speed microSD card + card reader
- Micro USB cable
- 3× Emoti-stretch straps (various sizes)
- Plastic spudger

### Assembly

1. **Prepare the SD card:**
   - Insert the SD card into the card reader and plug it into your computer
   - Download the config file from [emotibit.com/files/config](https://www.emotibit.com/files/config)

2. **Add WiFi credentials** (see next section)

3. **Insert the SD card** into the EmotiBit

4. **Set the Hibernate switch** to the active (not HIB) position

5. **Plug the battery** into the Feather — ensure the connector is firmly seated

6. **Stack the Feather onto EmotiBit:**
   - 12-pin connector → 12-pin socket
   - 16-pin connector → 16-pin socket

### WiFi Configuration

Open the downloaded `config.txt` file in a text editor and replace the placeholders with your WiFi credentials:

```json
{
  "WifiCredentials": [
    {
      "ssid": "YOUR_WIFI_NAME_GOES_HERE",
      "password": "YOUR_WIFI_PASSWORD_GOES_HERE"
    }
  ]
}
```

You can add **multiple WiFi networks** by adding more entries to the `WifiCredentials` array:

```json
{
  "WifiCredentials": [
    {
      "ssid": "home_wifi",
      "password": "password1"
    },
    {
      "ssid": "lab_wifi",
      "password": "password2"
    }
  ]
}
```

Save the file to the SD card and eject it.

> **Note:** EmotiBit only supports the **2.4GHz WiFi band**. Enterprise WiFi (login/password after connecting) has experimental support only on ESP32 Feathers.

### Installing Software

1. Download the latest EmotiBit Software from: [github.com/EmotiBit/ofxEmotiBit/releases/latest](https://github.com/EmotiBit/ofxEmotiBit/releases/latest)

2. **Windows:** Extract the `.zip` → run the `.msi` installer → follow on-screen instructions
3. **macOS:** Extract the `.zip` → applications are inside the extracted folder
4. **Linux:** Follow instructions on the release page

The software bundle includes:
- **EmotiBit Oscilloscope** — Real-time data visualization & recording
- **EmotiBit DataParser** — Convert raw data files into individual CSV channels
- **EmotiBit FirmwareInstaller** — Flash firmware onto the Feather

5. **Install USB drivers** (CP210x) included in the software bundle.

### Installing Firmware

1. Open the **EmotiBit FirmwareInstaller**
2. Connect the Feather to your computer via USB (not stacked with EmotiBit)
3. Follow the on-screen instructions to flash the latest stock firmware

> ⚠️ **Do NOT unplug or reset the Feather while firmware upload is in progress — this could brick your device.**

### Bootup & LED Indicators

When EmotiBit boots up, LEDs indicate progress:

| Stage | LED State | Meaning / Action |
|-------|-----------|------------------|
| 1 | Feather RED LED ON | Feather is powering up |
| 2 | Feather RED LED turns ON then OFF | Check if SD card is correctly inserted |
| 3 | EmotiBit RED LED ON | Check config file exists on SD card and is correctly formatted |
| 4 | EmotiBit BLUE LED solid ON | Verify WiFi credentials in config file |
| 5 | EmotiBit BLUE LED **BLINKING** | ✅ **Connected to WiFi!** Open EmotiBit Oscilloscope to start streaming |

---

## Recording Data

### Using the EmotiBit Oscilloscope

1. **Open EmotiBit Oscilloscope** on your computer
2. **Grant network permissions** when prompted (firewall/security dialogs)
3. **Select your EmotiBit** from the device list
4. Data begins **streaming in real-time** immediately
5. Click the **Record Button** to start saving data to the SD card
6. Click the Record Button again to **stop recording**

**Recording indicators:**
- **On EmotiBit:** RED LED blinks during active recording
- **On Oscilloscope:** Record button turns red, filename shows below it

**Power Modes:**

| Mode | Description |
|------|-------------|
| **Normal** | Full functionality — record + stream |
| **Low Power** | Records but cannot stream real-time data |
| **WiFi Off** | WiFi disabled for longer battery life (toggle with short button press) |
| **Sleep** | All tasks halted (activate with long button press, 5 sec) |

### Streaming Protocols (OSC, UDP, LSL)

EmotiBit Oscilloscope can relay data to external applications via:

| Protocol | Settings File | Available Since |
|----------|---------------|-----------------|
| **OSC** (Open Sound Control) | `oscOutputSettings.xml` | v1.2.0+ |
| **UDP** | `udpOutputSettings.xml` | v1.7.1+ |
| **LSL** (Lab Streaming Layer) | `lslOutputSettings.json` | v1.11.1+ |

Enable any protocol from the **Output List** dropdown in the Oscilloscope. This is particularly useful for integrating EmotiBit with tools like **TouchDesigner**, **Max/MSP**, **Python**, or any LSL-compatible application.

**Example OSC patch** (relaying PPG Green to an OSC stream):
```xml
<patch>
  <input>PG</input>
  <output>/EmotiBit/0/PPG:GRN</output>
</patch>
```

---

## Data Output & Format

### File Types

Each recording session generates the following files on the SD card:

| File Type | Format | Description |
|-----------|--------|-------------|
| **Raw Data** | `.csv` | Single interleaved file containing ALL sensor streams |
| **Info File** | `_info.json` | Metadata: sampling rates, sensor settings, units, hardware/firmware version |
| **Parsed Data** | `_<TypeTag>.csv` | Individual CSV files per data channel (generated by DataParser) |

**Naming convention:** Files are named with the recording start timestamp.
- Example raw file: `2024-09-18_22-59-45-827135.csv`
- Example info file: `2024-09-18_22-59-45-827135_info.json`
- Example parsed file: `2024-09-18_22-59-45-827135_AX.csv` (Accelerometer X)

### Raw Data Format

The raw CSV file stores data in the following format:

```
EMOTIBIT_TIMESTAMP, PACKET#, NUM_DATAPOINTS, TYPETAG, VERSION, RELIABILITY, PAYLOAD
```

| Field | Description |
|-------|-------------|
| `EMOTIBIT_TIMESTAMP` | Milliseconds since EmotiBit bootup |
| `PACKET#` | Sequentially increasing packet count |
| `NUM_DATAPOINTS` | Number of data points in the payload |
| `TYPETAG` | Type of data being sent (see TypeTags below) |
| `VERSION` | Packet protocol version |
| `RELIABILITY` | Data reliability score out of 100 |
| `PAYLOAD` | Comma-separated data points |

**Sample raw data:**
```csv
531473,17298,3,PI,1,100,112870,112866,112867
531473,17299,3,PR,1,100,26870,26855,26857
531473,17300,3,PG,1,100,3720,3704,3717
531459,17301,2,EA,1,100,0.030269,0.030269
531452,17303,1,T1,1,100,33.037
531473,17305,3,AX,1,100,-0.436,-0.434,-0.433
531473,17308,3,GX,1,100,-0.275,-0.244,-0.275
531473,17311,3,MX,1,100,37,38,37
```

### Parsed Data Format

After running the **EmotiBit DataParser**, you get individual CSV files per data channel:

```
LocalTimestamp, EmotiBitTimestamp, PacketNumber, DataLength, TypeTag, ProtocolVersion, DataReliability, Data
```

**Example parsed file (Accelerometer X — `_AX.csv`):**
```csv
LocalTimestamp,EmotiBitTimestamp,PacketNumber,DataLength,TypeTag,ProtocolVersion,DataReliability,AX
1726714786.598369,531473.000,17305,3,AX,1,100,-0.436
1726714786.598369,531473.000,17305,3,AX,1,100,-0.434
1726714786.598369,531473.000,17305,3,AX,1,100,-0.433
1726714786.638383,531513.000,17322,3,AX,1,100,-0.434
```

**How to parse:**
1. Open the **EmotiBit DataParser**
2. Click **Load file** and select the raw `.csv` file
3. The parser generates individual files in the same directory
4. The parser quits automatically on completion

---

## EmotiBit Data Types (TypeTags)

### Biometric TypeTags

| TypeTag | Signal | Description | Units |
|:-------:|--------|-------------|-------|
| **EA** | EDA | Electrodermal Activity (skin conductance) | microsiemens (µS) |
| **EL** | EDL | Electrodermal Level (tonic baseline) | microsiemens (µS) |
| **ER** | EDR | Electrodermal Response (phasic) | microsiemens (µS) |
| **SA** | SCR Amplitude | Skin Conductance Response — peak intensity | microsiemens (µS) |
| **SF** | SCR Frequency | Skin Conductance Response — events per minute | count/min |
| **SR** | SCR Rise Time | Skin Conductance Response — time to peak | seconds |
| **PI** | PPG Infrared | Photoplethysmography — infrared wavelength | raw units |
| **PR** | PPG Red | Photoplethysmography — red wavelength | raw units |
| **PG** | PPG Green | Photoplethysmography — green wavelength | raw units |
| **HR** | Heart Rate | Derived heart rate | BPM |
| **BI** | Inter-Beat Interval | Time between heartbeats | milliseconds |
| **AX** | Accelerometer X | Linear acceleration — X axis | g |
| **AY** | Accelerometer Y | Linear acceleration — Y axis | g |
| **AZ** | Accelerometer Z | Linear acceleration — Z axis | g |
| **GX** | Gyroscope X | Angular rotation — X axis | degrees/second |
| **GY** | Gyroscope Y | Angular rotation — Y axis | degrees/second |
| **GZ** | Gyroscope Z | Angular rotation — Z axis | degrees/second |
| **MX** | Magnetometer X | Magnetic field — X axis | microhenries |
| **MY** | Magnetometer Y | Magnetic field — Y axis | microhenries |
| **MZ** | Magnetometer Z | Magnetic field — Z axis | microhenries |
| **T0** | Temperature 0 | Temperature (V1-V3 only) | °C |
| **T1** | Temperature 1 | Skin temperature | °C |
| **TH** | Thermopile | Medical-grade thermopile (EmotiBit MD only) | °C |
| **H0** | Humidity | Humidity / perspiration (V1-V3 only) | % |

### Sampling Rates

| Sensor Category | TypeTags | Sensor IC | Sampling Rate |
|----------------|----------|-----------|---------------|
| **Motion (9-axis IMU)** | `AX` `AY` `AZ` `GX` `GY` `GZ` `MX` `MY` `MZ` | BMI160 + BMM150 | **25 Hz** |
| **PPG (Optical)** | `PI` `PG` `PR` | MAX30101 | **25 Hz** (100Hz variant available) |
| **EDA** | `EA` `EL` `ER` | ADS1114 | **15 Hz** |
| **Temperature** | `T1` / `TH` | MAX30101 / MLX90632 | **7.5 Hz** |
| **SCR Frequency** | `SF` | Computed | **3 Hz** |
| **Heart Rate** | `HR` | Computed from PPG | Event-based |
| **SCR Amplitude / Rise Time** | `SA` / `SR` | Computed from EDA | Event-based |

---

## Mapping EmotiBit Data to Our Project Metrics

This section maps the hackathon project metrics (from the README) to the corresponding EmotiBit TypeTags:

### 1. Cardiovascular & Blood Flow (Optical Sensors)

| Project Metric | EmotiBit TypeTag | Description |
|---------------|:----------------:|-------------|
| **PPG Red** | `PR` | Deep tissue blood volume (red wavelength) |
| **PPG IR** | `PI` | Deep tissue oxygenation (infrared wavelength) |
| **PPG Green** | `PG` | Surface blood flow, motion-resistant |
| **Heart Rate (HR)** | `HR` | Beats per minute derived from PPG |

### 2. Electrodermal Activity (Stress & Arousal)

| Project Metric | EmotiBit TypeTag | Description |
|---------------|:----------------:|-------------|
| **EDA** | `EA` | Baseline skin conductivity |
| **SCR Amplitude** | `SA` | Intensity of a sudden sweat spike |
| **SCR Frequency** | `SF` | Number of sweat spikes per minute |
| **SCR Rise Time** | `SR` | Time for a sweat spike to reach peak |

### 3. Kinematics & Orientation (Motion Sensors)

| Project Metric | EmotiBit TypeTag | Description |
|---------------|:----------------:|-------------|
| **Accelerometer X/Y/Z** | `AX` `AY` `AZ` | Straight-line acceleration + gravity |
| **Gyroscope X/Y/Z** | `GX` `GY` `GZ` | Angular rotation and tilt |
| **Magnetometer X/Y/Z** | `MX` `MY` `MZ` | Magnetic field / compass orientation |

### 4. Thermodynamics

| Project Metric | EmotiBit TypeTag | Description |
|---------------|:----------------:|-------------|
| **Temperature** | `T1` or `TH` | Localized skin temperature at sensor contact point |

---

## Visualization & Next Steps

### Tools for Viewing Data

| Tool | Use Case |
|------|----------|
| **EmotiBit Oscilloscope** | Real-time streaming visualization |
| **EmotiBit Python Data Viewer** | Offline visualization of all parsed data channels |
| **Microsoft Excel / Google Sheets** | Quick inspection of parsed CSV files |
| **Notepad++ / Text Edit** | Raw file inspection |
| **TouchDesigner** | Real-time creative visualization (via OSC/UDP/LSL) |
| **Python (BrainFlow SDK)** | Programmatic data access and analysis |

### Integration with TouchDesigner

For our hackathon project, EmotiBit data can be streamed to TouchDesigner in real time using:

1. **OSC protocol** — Enable OSC output in the Oscilloscope, configure `oscOutputSettings.xml` with the desired TypeTags, and receive data in TouchDesigner via an OSC In CHOP.
2. **UDP protocol** — Similar setup via `udpOutputSettings.xml` and a UDP In DAT in TouchDesigner.
3. **LSL protocol** — Use an LSL inlet in TouchDesigner for lab-grade synchronized streaming.

---

## Useful Links

| Resource | URL |
|----------|-----|
| **EmotiBit Website** | [emotibit.com](https://www.emotibit.com) |
| **EmotiBit Shop** | [shop.emotibit.com](http://shop.emotibit.com) |
| **EmotiBit Docs (GitHub)** | [github.com/EmotiBit/EmotiBit_Docs](https://github.com/EmotiBit/EmotiBit_Docs) |
| **Software Releases** | [github.com/EmotiBit/ofxEmotiBit/releases](https://github.com/EmotiBit/ofxEmotiBit/releases/latest) |
| **Firmware Releases** | [github.com/EmotiBit/EmotiBit_FeatherWing/releases](https://github.com/EmotiBit/EmotiBit_FeatherWing/releases) |
| **TypeTags Source Code** | [EmotiBit_XPlat_Utils/EmotiBitPacket.cpp](https://github.com/EmotiBit/EmotiBit_XPlat_Utils/blob/master/src/EmotiBitPacket.cpp) |
| **Python Biometric Library** | [github.com/EmotiBit/EmotiBit_Biometric_Lib](https://github.com/EmotiBit/EmotiBit_Biometric_Lib) |
| **Community Forum** | [forum.emotibit.com](http://forum.emotibit.com) |
| **FAQ** | [EmotiBit FAQ on Reddit](https://www.reddit.com/r/EmotiBit/collection/27921349-c38f-4df4-b708-99346979039f) |
