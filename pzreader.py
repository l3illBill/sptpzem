from pyModbusTCP.client import ModbusClient
from datetime import datetime
import threading
import json
import struct
import time
import os
from flask import Flask, jsonify
from flask_httpauth import HTTPBasicAuth
from pyngrok import ngrok
app = Flask(__name__)
modbus_clients = {}
devices = [
{"ip":"192.168.4.221","filename":"rbw4.json","name":"rbw4","location":"Welding"},
{"ip":"192.168.4.222","filename":"rbw5.json","name":"rbw5","location":"Welding"},
{"ip":"192.168.5.26","filename":"rbw6.json","name":"rbw6","location":"Welding"}
,{"ip":"192.168.5.27","filename":"rbw7.json","name":"rbw7","location":"Welding"}
,{"ip":"192.168.5.28","filename":"rbw8.json","name":"rbw8","location":"Welding"}
,{"ip":"192.168.5.29","filename":"rbw9.json","name":"rbw9","location":"Welding"}]

#####
def read_modbus(ip):
    client = get_modbus_client(ip)
    return client.read_holding_registers(0, 10)
#####
def get_modbus_client(ip, port=502):
    key = f"{ip}:{port}"
    if key not in modbus_clients:
        modbus_clients[key] = ModbusClient(host=ip, port=port, auto_open=True)
    return modbus_clients[key]
#####
def safe_write_json(filename, data):
    tmp_filename = filename + ".tmp"
    with open(tmp_filename, "w") as tmp_file:
        json.dump(data, tmp_file, indent=4)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
    os.replace(tmp_filename, filename)  # atomic replace
#####
def rbw(ip, filename,name,location):
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = read_modbus(ip)
        #print("Timestamp:", timestamp)
        #print("Data read from Modbus:", data)
        if data:
                combined = (data[1] << 16) | data[0]
                float_value = struct.unpack('<f', struct.pack('<I', combined))[0]
                combined2 = (data[3] << 16) | data[2]
                float_value2 = struct.unpack('<f', struct.pack('<I', combined2))[0]
                combined3 = (data[7] << 16) | data[6]
                float_value3 = struct.unpack('<f', struct.pack('<I', combined3))[0]
                watt = float_value * float_value2
                if float_value2 == 0 or float_value2 < 2:
                    status = "off"
                elif 2 < float_value2 <= 4.5:
                    status = "handtime"
                elif float_value2 > 5.0:
                    status = "running"
                new_data = {
                    "timestamp": now,
                    "machine_id":name,
                    "line_id":location,
                    "line_name":location,
                    "status": status,
                    "volt": {"value":float_value,"unit":"volt"},
                    "amp": {"value":float_value2,"unit":"amp"},
                    "watt": {"value":watt,"unit":"watt"},
                    "kwh": {"value":float_value3, "unit":"kWh"},
                    #"kwh total":sum(entry['kwh'] for entry in data_list)
                }
                print("New data:", new_data)
                #filename = "rbw5.json"
                if os.path.exists(filename):
                    with open(filename, "r") as file:
                        data_list = json.load(file)
                else:
                    data_list = []
                data_list.append(new_data)
                safe_write_json(filename, data_list)
                time.sleep(5)
        #print("Main thread is running...")
@app.route("/<string:filename>")
def get_data(filename):
    # Only allow filenames that exist in your devices list for security
    allowed_files = {d["filename"].replace(".json", ""): d["filename"] for d in devices}
    if filename not in allowed_files:
        return jsonify({"error": "Invalid file name."}), 400

    file_path = allowed_files[filename]
    print(f"Looking for JSON at: {file_path}")

    if not os.path.exists(file_path):
        return jsonify({"error": f"{file_path} not found"}), 404

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to load {file_path}: {str(e)}"}), 500

    return jsonify(data)

threads = []
for d in devices:
    t = threading.Thread(target=rbw, args=(d["ip"], d["filename"],d["name"],d["location"]))
    t.start()
    threads.append(t)
while True:

        app.run(host="0.0.0.0", port=5000)
        #
