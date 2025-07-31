import numpy as np
import json5
from GenericReceiver import GenericReceiverClass
import socket
import select
import threading
from typing import List
from Sensor import Sensor
import aioconsole
import webbrowser

import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
import serial_asyncio
from flaskApp.index import update_sensors, replay_sensors, start_server
from remote import startController
import utils



class WifiReceiver(GenericReceiverClass):
    def __init__(self,numNodes,sensors:List[Sensor], tcp_ip="10.0.0.67", tcp_port=7000, record=True, stopFlag=None):
        super().__init__(numNodes,sensors,record)
        self.TCP_IP = tcp_ip
        self.tcp_port = tcp_port
        self.connection_is_open = False
        self.connections = {}
        self.setup_TCP()
        self.stopFlag = stopFlag
    
    def setup_TCP(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.TCP_IP, self.tcp_port))
        sock.listen(len(self.sensors))  # Listen for N connections
        print("Waiting for connections")
        while len(self.connections) < len(self.sensors):
            connection, client_address = sock.accept()
            print("Connection found")
            sensorId = self.getSensorIdFromBuffer(connection)
            print(f"Connection found from {sensorId}")
            self.connections[sensorId]=connection
        sock.settimeout(30)
        print("All connections found")

    def getSensorIdFromBuffer(self, connection):
        while True:
            ready_to_read, ready_to_write, in_error = select.select([connection], [], [], 30)
            if len(ready_to_read)>0:
                numBytes = 1+(self.numNodes+1)*2+4
                inBuffer =   connection.recv(numBytes, socket.MSG_PEEK)
                if len(inBuffer) >= numBytes:
                    sendId, startIdx, sensorReadings, packet = self.unpackBytesPacket(inBuffer)
                return sendId

    def reconnect(self, sensorId):
        print(f"Reconnecting to sensor {sensorId}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.TCP_IP, self.tcp_port))
        sock.listen(len(self.sensors))
        print("waiting for connections")
        found_Conn = False
        while not found_Conn:
            connection, client_address = sock.accept()
            connectionSensorId = self.getSensorIdFromBuffer(connection)
            if connectionSensorId == sensorId:
                print(f"Connection from Sensor {sensorId} found")
                self.connections[sensorId]=connection
                found_Conn = True
            else:
                print(f"Connection refused from {client_address}")
                connection.close()

    async def receiveData(self, sensorId):
        print("Receiving Data")
        while not self.stopFlag.is_set():
            connection = self.connections[sensorId]
            ready_to_read, ready_to_write, in_error = await asyncio.get_event_loop().run_in_executor(
                None, select.select, [connection], [], [], 30)
            if len(ready_to_read)>0:
                numBytes = 1+(self.numNodes+1)*2+4
                inBuffer =   await asyncio.get_event_loop().run_in_executor(None, connection.recv, numBytes, socket.MSG_PEEK)
                if len(inBuffer) >= numBytes:
                    data = await asyncio.get_event_loop().run_in_executor(None, connection.recv, numBytes)
                    sendId, startIdx, sensorReadings, packet = self.unpackBytesPacket(data)
                    sensor = self.sensors[sendId]
                    if(sensor.intermittent):
                        sensor.processRowIntermittent(startIdx,sensorReadings,packet,record=self.record)
                    else:
                        if (startIdx==20000):
                            sensor.processRowReadNode(sensorReadings,packet,record=self.record)
                        else:
                            sensor.processRow(startIdx,sensorReadings,packet,record=self.record)
            else:
                print(f"Sensor {sensorId} is disconnected: Reconnecting...")
                await asyncio.get_event_loop().run_in_executor(None, connection.shutdown, 2)
                await asyncio.get_event_loop().run_in_executor(None, connection.close)
                self.reconnect(sensorId)

    def startReceiverThreads(self):
        tasks = []
        for sensorId in self.connections:
            task = self.receiveData(sensorId)
            tasks.append(task)
        return tasks


class BLEReceiver(GenericReceiverClass):
    def __init__(self, numNodes, sensors: List[Sensor],record=True):
        super().__init__(numNodes, sensors, record)
        self.deviceNames = [sensor.deviceName for sensor in sensors]
        self.clients={}

    async def connect_to_device(self, lock, deviceName):
        def on_disconnect(client):
            print(f"Device {deviceName} disconnected, attempting to reconnect...")
            asyncio.create_task(self.connect_to_device(lock, deviceName))
        async with lock:
            device = await BleakScanner.find_device_by_name(deviceName,timeout=30)
            if device:
                print(f"Found device: {deviceName}")
                client = BleakClient(device)
                client.set_disconnected_callback(on_disconnect)
                self.clients[deviceName] = client
                await client.connect()

        def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
            sendId, startIdx, sensorReadings, packet = self.unpackBytesPacket(data)
            sensor = self.sensors[sendId]
            if(sensor.intermittent):
                sensor.processRowIntermittent(startIdx,sensorReadings,packet,record=self.record)
            else:
                if (startIdx==20000):
                    sensor.processRowReadNode(sensorReadings,packet,record=self.record)
                else:
                    sensor.processRow(startIdx,sensorReadings,packet,record=self.record)


        await client.start_notify("1766324e-8b30-4d23-bff2-e5209c3d986f", notification_handler)
        print(f"Connected to {deviceName}")
    
    async def stopReceiver(self):
        for client in self.clients.values():
            await client.stop_notify("1766324e-8b30-4d23-bff2-e5209c3d986f")
            await client.disconnect()
        print("All notifications stopped and devices disconnected.")

    def startReceiverThreads(self):
        lock = asyncio.Lock()
        tasks = [self.connect_to_device(lock, name) for name in self.deviceNames]
        return tasks


    


class SerialReceiver(GenericReceiverClass):
    def __init__(self, numNodes, sensors, port, baudrate, stopFlag=None, record =True):
        super().__init__(numNodes, sensors, record)
        self.port = port #update serial port
        self.baudrate = baudrate
        self.stop_capture_event = False
        self.reader = None
        self.stopStr = bytes('wr','utf-8')
        self.stopFlag = stopFlag

    async def read_serial(self):
        print("Reading Serial")
        self.reader, _ = await serial_asyncio.open_serial_connection(url=self.port, baudrate=self.baudrate)
        while not self.stopFlag.is_set():
            data = await self.reader.read(2048)  # Read available bytes
            if data:
                await self.buffer.put(data)

    

    async def stopReceiver(self):
        print("Stopped reading")


    def startReceiverThreads(self):
        tasks=[]
        tasks.append(self.read_serial())
        tasks.append(self.read_lines())
        # tasks.append(self.listen_for_stop())
        return tasks


def readConfigFile(file):
    with open(file, 'r') as file:
        data = json5.load(file)
    return data

class MultiProtocolReceiver():
    def __init__(self, configFilePath="./WiSensConfigClean.json"):
        self.config = readConfigFile(configFilePath)
        self.sensors = self.config['sensors']
        self.bleSensors = []
        self.wifiSensors = []
        self.serialSensors = []
        self.allSensors = []
        self.stopFlag = asyncio.Event()
        for sensorConfig in self.sensors:
            sensorKeys = list(sensorConfig.keys())
            intermittent = False
            p = 15

            if 'intermittent' in sensorKeys:
                intermittent = sensorConfig['intermittent']['enabled']
                p = sensorConfig['intermittent']['p']

            deviceName = "Esp1"
            userNumNodes = 256

            match sensorConfig['protocol']:
                case 'wifi':
                    userNumNodes = self.config['wifiOptions']['numNodes']
                case 'ble':
                    deviceName = sensorConfig['deviceName']
                    userNumNodes = self.config['bleOptions']['numNodes']
                case 'serial':
                    userNumNodes = self.config['serialOptions']['numNodes']

            numGroundWires = sensorConfig['endCoord'][1] - sensorConfig['startCoord'][1] + 1
            numReadWires = sensorConfig['endCoord'][0] - sensorConfig['startCoord'][0] + 1
            numNodes = min(userNumNodes, numGroundWires*numReadWires)
            newSensor = Sensor(numGroundWires,numReadWires,numNodes,sensorConfig['id'],deviceName=deviceName,intermittent=intermittent, p=p)
            
            match sensorConfig['protocol']:
                case 'wifi':
                    self.wifiSensors.append(newSensor)
                case 'ble':
                    self.bleSensors.append(newSensor)
                case 'serial':
                    self.serialSensors.append(newSensor)
            self.allSensors.append(newSensor)

        self.receivers = []
        self.receiveTasks = []
    
    async def startReceiversAsync(self):
        await asyncio.gather(*self.receiveTasks)
        # await self.listen_for_stop()

    async def listen_for_stop(self):
        print("Listening for stop")
        stop_flag = False
        while not stop_flag:
            input_str = await aioconsole.ainput("Press Enter to stop...\n")
            if input_str == "":
                print("Stop flag set")
                stop_flag = True
                self.stopFlag.set()
                for receiver in self.receivers:
                    if isinstance(receiver, BLEReceiver):
                        await receiver.stopReceiver()


    def initializeReceivers(self,record):
        if len(self.bleSensors)!=0:
            bleReceiver = BLEReceiver(self.config['bleOptions']['numNodes'],self.bleSensors, record)
            self.receivers.append(bleReceiver)
            self.receiveTasks += bleReceiver.startReceiverThreads()
        if len(self.wifiSensors)!=0:
            wifiReceiver = WifiReceiver(self.config['wifiOptions']['numNodes'],self.wifiSensors,self.config['wifiOptions']['tcp_ip'],self.config['wifiOptions']['port'], stopFlag=self.stopFlag, record=record)
            self.receivers.append(wifiReceiver)
            self.receiveTasks += wifiReceiver.startReceiverThreads()
        if len(self.serialSensors)!=0:
            serialReceiver = SerialReceiver(self.config['serialOptions']['numNodes'],self.serialSensors,self.config['serialOptions']['port'],self.config['serialOptions']['baudrate'],stopFlag=self.stopFlag,record=record)
            self.receivers.append(serialReceiver)
            self.receiveTasks += serialReceiver.startReceiverThreads()
        self.receiveTasks.append(self.listen_for_stop())

    def startReceiverThread(self):
        asyncio.run(self.startReceiversAsync())

    def record(self):
        self.initializeReceivers(True)
        captureThread = threading.Thread(target=self.startReceiverThread)
        captureThread.start()
        captureThread.join()

    def visualizeAndRecord(self):
        self.initializeReceivers(True)
        threads=[]
        captureThread = threading.Thread(target=self.startReceiverThread)
        captureThread.start()
        threads.append(captureThread)
        vizThread = threading.Thread(target=update_sensors, args=(self.allSensors,))
        vizThread.start()
        threads.append(vizThread)
        utils.start_nextjs()
        url = "http://localhost:3000"
        webbrowser.open_new_tab(url)
        start_server()
        for thread in threads:
            thread.join()


    def visualize(self):
        self.initializeReceivers(False)
        threads=[]
        captureThread = threading.Thread(target=self.startReceiverThread)
        captureThread.start()
        threads.append(captureThread)
        vizThread = threading.Thread(target=update_sensors, args=(self.allSensors,))
        vizThread.start()
        threads.append(vizThread)
        utils.start_nextjs()
        url = "http://localhost:3000"
        webbrowser.open_new_tab(url)
        start_server()
        for thread in threads:
            thread.join()

    def replayData(self,fileDict, startTs=None,endTs=None, speed=1):
        pressureDict = {}
        totalFrames = None
        frameRate = None
        for sensorId in fileDict:
            pressure, fc, ts = utils.tactile_reading(fileDict[sensorId])
            startIdx = 0
            beginTs = ts[0]
            if startTs is not None:
                startIdx,beginTs = utils.find_closest_index(ts,startTs)
            endIdx, lastTs = len(ts), ts[-1]
            if endTs is not None:
                endIdx, lastTs = utils.find_closest_index(ts, endTs)
            if totalFrames is None or endIdx-startIdx<totalFrames:
                totalFrames = endIdx-startIdx
                frameRate = (totalFrames/(lastTs-beginTs)) * speed
            pressureDict[sensorId] = pressure[startIdx:endIdx,:,:]
        vizThread = threading.Thread(target=replay_sensors, args=(pressureDict,frameRate,totalFrames,))
        vizThread.start()
        utils.start_nextjs()
        url = "http://localhost:3000"
        # webbrowser.open_new_tab(url)
        start_server()

    # Sends all sensors (with real time pressure updates) as input to the custom method
    def runCustomMethod(self, method, record=False, viz=False):
        self.initializeReceivers(record)
        threads=[]
        captureThread = threading.Thread(target=self.startReceiverThread)
        captureThread.start()
        threads.append(captureThread)
        customThread = threading.Thread(target=method, args=(self.allSensors,))
        customThread.start()
        threads.append(customThread)
        if viz:
            vizThread = threading.Thread(target=update_sensors, args=(self.allSensors,))
            vizThread.start()
            threads.append(vizThread)
            utils.start_nextjs()
            url = "http://localhost:3000"
            webbrowser.open_new_tab(url)
            start_server()
        for thread in threads:
            thread.join()
        

    

if __name__ == "__main__":
    # utils.programSensor(1) #测试结果所以注释掉 0731/2025
    # utils.programSensor(2)
    myReceiver = MultiProtocolReceiver()
    # myReceiver.replayData({1:"./recordings/pillowTest4.hdf5"}, speed=2 )
    # receiverModule.runCustomMethod(startController)
    # receiverModule.record()
    myReceiver.visualize()
    

