import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports
import time
import json
import threading
import serial
import tkinter as tk
from tkinter import ttk


UartBuff = []
BleDeviceList = []
ser = None
client = None


def ReadUART():
    global UartBuff, ser
    while True:
        msg = ser.readline().decode()
        if msg != '':
            UartBuff.append(msg)
        time.sleep(0.05)


def searchComPorts():
    portList = []
    statusWin['text'] = "COM Port Search..."
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        portList.append(f"{port}:{desc}")

    comPortList['values'] = tuple(portList)
    comPortList.current(0)


def comPortSelected():
    global UartBuff, ser, pb, BleDeviceList
    comPortName = comPortList.get().split(":")
    ser = serial.Serial(comPortName[0], 115200,
                        bytesize=8, parity='N', stopbits=1, timeout=0.08)
    ser.close()
    ser.open()
    ReadUARTThread = threading.Thread(target=ReadUART, daemon=True)
    ReadUARTThread.start()
    statusWin['text'] = "BLE Device Search..."
    progressBar.step(40)
    progressBar.start()
    ser.write(b'!CCMD@')
    time.sleep(0.2)
    ser.write(b'AT+ROLE=C\r\n')
    time.sleep(0.2)
    UartBuff = []
    ser.write(b'AT+SCAN\r\n')
    while True:
        uartBufLength = len(UartBuff)
        if uartBufLength > 0:
            if "NUM" in UartBuff[uartBufLength-1]:

                BleDeviceList = UartBuff[1:-1]
                UartBuff = []

                bleDevice['values'] = BleDeviceList
                bleDevice.current(0)
                progressBar.stop()
                break
        time.sleep(0.01)


def startDeviceDiscovery(event):
    deviceDiscoveryThread = threading.Thread(
        target=comPortSelected, daemon=True)
    deviceDiscoveryThread.start()


def bleDeviceSelected(event):
    global UartBuff
    bleSelectedNum = bleDevice.get().split(" ")[0]
    print("num", bleSelectedNum)
    ser.write(b'AT+CONN=1\r\n')
    while True:
        if UartBuff:
            if "CONNECTED OK" in UartBuff[-1]:
                ser.write(b'AT+MODE_DATA\r\n')
                statusWin['text'] = "BLE Device Connected"
                UartBuff = []
                break
        time.sleep(0.01)
    RecvDataThread = threading.Thread(target=RecvDataFromBle, daemon=True)
    RecvDataThread.start()


def RecvDataFromBle():
    global UartBuff, client
    while True:
        if UartBuff:
            msg = UartBuff[-1]
            print(msg)
            if "TEMP" in msg:
                data_dect = json.loads(msg)
                tempvalue['text'] = str(data_dect['TEMP']) + '度'
                humivalue['text'] = str(data_dect['HUMI']) + '%'
                client.loop()
                # 要發布的主題和內容
                client.publish("Tempe", data_dect['TEMP'])
                client.publish("Humi", data_dect['HUMI'])
                UartBuff = []
        time.sleep(0.5)


def on_connect(client, userdata, flags, rc):
    # 將訂閱主題寫在on_connet中
    # 如果我們失去連線或重新連線時
    # 地端程式將會重新訂閱
    client.subscribe("LightSW")


def on_message(client, userdata, msg):
    # 轉換編碼utf-8才看得懂中文
   # print(msg.topic+" " + msg.payload.decode('utf-8'))
    if msg.topic == "LightSW":
        if msg.payload.decode('utf-8') == "ON":
            lightStatusLabel.configure(image=bmON)
            ser.write(b'ON\r\n')
        if msg.payload.decode('utf-8') == "OFF":
            lightStatusLabel.configure(image=bmOFF)
            ser.write(b'OFF\r\n')


def mqttClientInit():
    global client
    client = mqtt.Client()
    # 設定登入帳號密碼
    # client.username_pw_set("try","xxxx")

    # 設定連線資訊(IP, Port, 連線時間)
    client.connect("127.0.0.1", 1883, 60)
    # 設定連線的動作
    client.on_connect = on_connect
    # 設定接收訊息的動作
    client.on_message = on_message


window = tk.Tk()
bmON = tk.PhotoImage(file="L_ON.png")
bmOFF = tk.PhotoImage(file="L_OFF.png")

window.title('RL62M USB Connect tools')
window.geometry('800x700')
comPortScan = tk.Label(window, text='USB COM search:', font=('Arial', 18))
statusWin = tk.Label(window, text='status information ', font=('Arial', 18),
                     bg='white')
comPortList = ttk.Combobox(window, width=40)
bleDevice = ttk.Combobox(window, width=40)
comPortList.bind("<<ComboboxSelected>>", startDeviceDiscovery)
bleDevice.bind("<<ComboboxSelected>>", bleDeviceSelected)
progressBar = ttk.Progressbar(window, orient='horizontal',
                              mode='indeterminate', length=280)
tempLabel = tk.Label(window, text='溫度:', font=('Arial', 18))
humiLabel = tk.Label(window, text='濕度:', font=('Arial', 18))
tempvalue = tk.Label(window, text='   度C', font=('Arial', 18))
humivalue = tk.Label(window, text='   %    ', font=('Arial', 18))
lightStatusLabel = tk.Label(window, image=bmOFF)

statusWin.grid(column=0, row=0)
comPortList.grid(column=1, row=0)
bleDevice.grid(column=1, row=1)
progressBar.grid(column=1, row=2)
lightStatusLabel.grid(column=1, row=5)
tempLabel.grid(column=0, row=3, sticky='e')
humiLabel.grid(column=0, row=4, sticky='e')
tempvalue.grid(column=1, row=3, sticky='w')
humivalue.grid(column=1, row=4, sticky='w')

searchComPorts()
mqttClientInit()
window.mainloop()
