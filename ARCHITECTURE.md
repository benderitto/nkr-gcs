# NKR Ground Control Station (GCS)
## Architecture

Version: 1.0

---

# Purpose

NKR GCS is a standalone operator application.

It provides:

- robot control
- live video
- telemetry
- mission visualization
- settings
- diagnostics

GCS MUST NOT depend on ROS2.

Communication with the robot is performed exclusively through the NKR UDP protocol.

---

# High Level Architecture

                        +---------------------+
                        |     Steam Deck      |
                        |---------------------|
                        |      NKR GCS        |
                        +----------+----------+
                                   |
                            UDP protocol
                                   |
                        +----------v----------+
                        |      NKR Robot      |
                        |---------------------|
                        |        ROS2         |
                        +---------------------+

---

# Main Components

Application

Application owns every global service.

No global variables are allowed.

Application contains:

- RobotModel
- OperatorModel
- Settings
- NetworkManager
- InputManager
- VideoManager
- CameraManager
- MainWindow

Application is responsible for creating and connecting every module.

---

# RobotModel

Contains ONLY the actual state of the robot.

Examples:

- speed
- heading
- battery
- voltage
- gps
- imu
- satellites
- current camera
- current drive mode
- current light mode
- link quality
- bitrate
- latency

RobotModel is updated from authenticated robot-state packets and local
measurements derived from the active video frame, such as video latency.

RobotModel never sends commands.

---

# OperatorModel

Contains ONLY operator intentions.

Examples:

- throttle
- steering
- brake
- requested camera
- requested drive mode
- requested light mode
- menu state

OperatorModel never contains telemetry.

---

# Settings

Persistent application configuration.

Stored in YAML.

Examples:

- robot IP
- robot port
- joystick sensitivity
- deadzones
- video quality
- map provider
- UI options

Settings are loaded on startup.

Settings are saved automatically.

---

# NetworkManager

Responsibilities:

- UDP connection
- packet serialization
- packet parsing
- heartbeat
- packet statistics
- latency measurement

NetworkManager updates RobotModel.

NetworkManager reads OperatorModel.

NetworkManager never draws UI.

---

# InputManager

Responsibilities:

- Steam Input
- controller state
- button mapping
- trigger mapping
- stick mapping

InputManager updates OperatorModel.

InputManager never sends packets.

InputManager never updates UI.

---

# VideoManager

Responsibilities:

- receive video stream
- decode stream
- provide video frames

Supported cameras:

- Main
- Night
- Thermal
- Rear

VideoManager knows nothing about HUD.

Linux/SteamOS use the in-process GStreamer API. Windows launches the private
GStreamer runtime shipped beside the executable and reads a framed raw-RGB
pipe; PyAV is retained only as an automatic recovery backend. The portable
frame mailbox replaces an unpainted frame instead of queueing it.

---

# CameraManager

Controls camera selection.

CameraManager requests camera changes through OperatorModel.

CameraManager receives actual camera state through RobotModel.

---

# MainWindow

Contains only UI.

MainWindow owns no robot logic.

MainWindow contains:

- VideoWidget
- HUDWidget
- MenuWidget
- DialogLayer

---

# VideoWidget

Responsible for decoding and displaying video, extracting the embedded capture
timestamp, and reporting capture-to-display latency.

The marker is removed before the frame is painted. UTC correction comes from a
background SNTP synchronizer; unavailable or stale synchronization yields no
latency value.

Video is painted directly into its aspect-ratio-preserving target rectangle
with Qt smooth transformation. No intermediate enlarged image is allocated.

No robot-control networking.

No input handling.

---

# HUDWidget

Displays telemetry.

Reads only:

- RobotModel
- OperatorModel

HUD never communicates directly with the robot.

---

# MenuWidget

Displays:

- settings
- diagnostics
- camera configuration
- network status

Menu does not communicate directly with hardware.

---

# Data Flow

Operator

↓

Steam Input

↓

InputManager

↓

OperatorModel

↓

NetworkManager

↓

UDP

↓

Robot

↓

UDP

↓

NetworkManager

↓

RobotModel

↓

HUD

↓

Operator

---

# Thread Model

Main Thread

- Qt GUI

Network Thread

- UDP

Video Thread

- decoder

Future Threads

- logging
- recording

No blocking operations are allowed in the GUI thread.

---

# Communication Rules

Modules communicate only through:

- RobotModel
- OperatorModel

Modules never call each other directly.

Example:

GOOD

InputManager

↓

OperatorModel

↓

NetworkManager

BAD

InputManager

↓

NetworkManager

---

# Design Principles

Single Responsibility Principle.

Each class has exactly one responsibility.

Examples:

GOOD

InputManager

NetworkManager

VideoManager

HUDWidget

BAD

GodClass

---

No global variables.

No circular dependencies.

No hidden state.

No UI logic inside networking.

No networking inside UI.

---

# Future Modules

Future modules are expected to fit into the existing architecture.

Examples:

- Recorder
- Autopilot UI
- Mission Planner
- Object Detection
- AI Assistant
- Route Editor
- Remote Firmware Update

No architecture changes should be required to add them.

---

# Target Platforms

Primary:

- Steam Deck

Secondary:

- Linux Desktop

Possible future:

- Windows
- Tablet

---

# Communication

Robot <-> GCS

Transport:

UDP

Video:

GStreamer

Configuration:

YAML

Telemetry:

NKR Protocol

---

# Project Goal

The architecture should remain stable for the lifetime of the project.

Future development should consist of adding modules, not redesigning the system.
