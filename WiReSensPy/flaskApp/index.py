from flask import Flask
import json
from flask_socketio import SocketIO
from flask_cors import CORS
import time
import numpy as np
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 
socketio = SocketIO(app, cors_allowed_origins="*")

def replay_sensors( pressureDict, frameRate, numFrames):
    with app.app_context():
        for i in range(numFrames):
            sensors={}
            for j in pressureDict:
                pressure=pressureDict[j][i]
                sensors[j]= (pressure).tolist()
            jsonSensors = json.dumps(sensors)
            socketio.emit('sensor_data', jsonSensors)
            time.sleep(1/frameRate)

def update_sensors(allSensors):
    with app.app_context():
        sensors={}
        while True:
            for i in range(len(allSensors)):
                pressure=allSensors[i].pressure.reshape(allSensors[i].selWires,allSensors[i].readWires)
                sensors[allSensors[i].id]= (pressure).tolist()
                
            jsonSensors = json.dumps(sensors)
            socketio.emit('sensor_data', jsonSensors)
            time.sleep(1/50)  # 50 FPS

def start_server():
    socketio.run(app, host="0.0.0.0", port=5328, debug=True, use_reloader=False)


@app.route('/api/python')
def index():
    return "WebSocket server is running..."