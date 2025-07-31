# WiSensPy

Python library for wireless collection and visualization of resistive tactile sensing 

## Pre-Requisities

The following assumes you already have the following installed on your machine:

- Python 3.10 or higher ([Installation](https://www.python.org/downloads/))
- Node and NPM v20.14.0 or higher ([Installation](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm))

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/WiReSens-Toolkit/WiReSensPy.git
   cd WiReSensPy
   ```

### Python Setup

1. **Create a virtual environment** (optional but recommended):

   - For Python 3.x:
     ```bash
     python3 -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```

2. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Node Setup
1. **Install node packages**
```bash
cd ui/nextjs-flask
npm i
```

## JSON Configuration and Programming Devices

You will use a WiReSens Toolkit JSON configuration to configure your tactile sensor readout and visualization. This section gives an overview of the parameters that can be configured via the JSON file.

### 1. wifiOptions

- **tcp_ip**: The IP address of the receiving device where the device will send data packets.
- **port**: The port number to listen on for incoming packets.
- **numNodes**: The expected number of sensor nodes to receive per packet.
- **ssid**: The name of the Wi-Fi network to connect to.
- **password**: The password for the Wi-Fi network (leave empty for open networks).
- **delay**: Delay in milliseconds between successive packets.

### 2. serialOptions

- **port**: The serial port to listen on (e.g., `COM7` on Windows).
- **baudrate**: The default communication speed (bit rate) for serial communication.
- **numNodes**: The number of sensor nodes expected per serial data line.
- **delay**: Delay in milliseconds between successive serial packets.

### 3. bleOptions

- **numNodes**: The expected number of sensor readings per BLE notification.
- **delay**: Delay in milliseconds between successive BLE characteristic notifications.

### 4. espOptions

- **macAddress**: The MAC address of the ESP receiver device used in ESP-NOW communication.
- **numNodes**: The number of sensor nodes expected over ESP-NOW communication.
- **delay**: Delay in milliseconds between successive ESP-NOW packets.

### 5. vizOptions

- **pitch**: The starting pixel pitch for visualizing sensor data.
- **localIp**: The local IP address for mobile or browser-based visualization of sensor data.

### 6. readoutOptions

- **groundPins**: Digital pins used to control ground wire selection during sensor readout.
- **readPins**: Digital pins used to control which wires are read during sensor readout.
- **adcPin**: The pin connected to the analog-to-digital converter (ADC) to read sensor signals.
- **resistance**: Resistance value for the digital potentiometer controlling sensor sensitivity.

### 7. sensors (Array of objects)

Each object in the `sensors` array represents a particular tactile sensing device configuration:

- **id**: A unique identifier for each sensor (as an integer). 
- **protocol**: The communication protocol used by the sensor (`wifi`, `ble`, or `serial`).
- **deviceName**: The name of the device (necessary only for BLE receivers).
- **startCoord**: The starting coordinate for sensor readout (represented as `[readWire, groundWire]`).
- **endCoord**: The ending coordinate for sensor readout (represented as `[readWire, groundWire]`).
- **intermittent**: A sub-object controlling intermittent data sending:
  - **enabled**: Whether intermittent sending is enabled (true or false).
  - **p**: Proportional control factor for the intermittent sending algorithm.
  - **d**: Error threshold for triggering intermittent sending.
- **outlineImage**: Path to an image file used as a background for visualizing sensor data (e.g., for a hand or foot outline).

### Programming a Device
To program a device:

1. After you've [flashed a base WiReSens Toolkit arduino firmware program](https://github.com/WiReSens-Toolkit/WiReSensToolkit-Arduino?tab=readme-ov-file#using-the-library): Connect your microcontroller to your laptop using a USB cable.
2. Set the port and baudrate for the device you want to program (making sure the baudrate matches your Serial.begin() in your .ino file) in the serialOptions of the JSON configuration
3. Import the utils to a Python script and call the *programSensor(id, configuration)* function, where id matches the "id" of the sensor object in your JSON configuration you would like to configure this microcontroller for, and configuration is a string matching the path to the JSON configuration to use. Make sure the serial port is closed before calling this method.

```python
import utils
utils.programSensor(1,"./WiReSensConfigClean.json")
```

## Recording, Playback, Visualization, and Custom Methods
The Python library provides a MultiProtocolReceiver class in the TouchSensorWireless.py file which can be used to record, playback, visualize, and write custom methods for multi-sender real time wireless communication. MultiProtocolReceiver class is configured via the same JSON file as the microcontrollers. It handles data serialization for the sensors defined in the "sensors" field, (mixed protocol communication is supported! You can use any combination BLE, Wi-Fi, or ESP-NOW/Serial senders). 

First create an instance of the MultiProtocolReceiver class:

```python
from TouchSensorWireless import MultiProtocolReceiver
myReceiver = MultiProtocolReceiver("./WiSensConfigClean.json")
```
Once configured, the receiver object provides a variety of methods that can be used to receive and process the tactile sensing data.

### record()

This method saves the received pressure data for each tactile sensor to its own [HDF5 file](https://docs.h5py.org/en/stable/), in the format: "./recordings/recordings_{id}_{timestamp}.hdf5".

```python
myReceiver.record()
```

Each row of the HDF5 file represents a new frame of pressure in the array (defined by the startCoord and endCoord for the sensor), and is saved with a timestamp. The "tactile_reading" function in utils.py can be used to read this pressure data back into Python for further analysis.

```python
import utils
pressure, fc, ts = utils.tactile_reading("./recordings/myRecording1.hdf5")
```
Fc is an integer representing the number of tactile frames
Pressure is a numpy array with dimensions (fc, groundWires, readWires), where groundWires and readWires are the dimensions of the sensing area defined by your startCoord and endCoord.
Timestamp is a numpy array of length fc, containing the timestamp for each frame of pressure data. 

### visualize()

This method starts a web based interactive visualization that shows the pressure readouts for each sensor in your "sensors" configuration in real time. 

```python
myReceiver.visualize()
```
![image](https://github.com/user-attachments/assets/9bc4d2da-6e83-462d-b0e3-4b56cda7596f)

The initial distance between each sensing pixel in the array can be configured via the "pitch" parameter, and the visualization can be viewed on mobile when "localIP" is set to the IP address of your computer when on the same network as your mobile device. 

Additionally, a background image to help guide your visualization configuration can be included by:
1. Placing the image file in the ".ui/nextjs-flask/public" directory and
2. specifying the name of the image file in the "outlineImage" parameter for the sensor

To visualize and record at the same time, use *recordAndVisualize()*


### replay({sensorId: hdf5File}, startTs=None, endTs=None, speed=1)
The replay method takes a mapping of sensor Ids to hdf5 recordings and replays each recording in your custom visualization. There are additional options to specify the start and end of playback based on specific timestamps, and also the rate of playback using the speed configuration.

```python
# Replay recordings from two sensors
myReceiver.replayData({1:"./recordings/pillowRemote1.hdf5", 2:"./recordings/pillowReomte2.hdf5"})
#Play 4x faster
myReceiver.replayData({1:"./recordings/pillowRemote1.hdf5", 2:"./recordings/pillowReomte2.hdf5"}, speed=4)
#Play from 17000000 unix time
myReceiver.replayData({1:"./recordings/pillowRemote1.hdf5", 2:"./recordings/pillowReomte2.hdf5"},startTs=17000000)
```

### runCustomMethod(methodName)

You can supply a custom function which takes an array of [Sensor objects](./Sensor.py), one for each sensor in your configuration. 

These objects have a *pressure* property which you can access to perform some additional computation in real-time. See the example in [remote.py](./remote.py).

In your custom function, you will likely need to reshape the pressure to a 2D array based on the readWires and selWires properties of the sensor

```python
pressureGrid = sensor.pressure.reshape(sensor.selWires, sensor.readWires)
```
The following code snippet runs the "startController" method:

```python
from remote import startController
myReceiver.runCustomMethod(startController)
```








