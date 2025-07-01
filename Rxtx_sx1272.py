#!/usr/bin/env python3

# tuosteven
# -*- coding: utf-8 -*-
import serial,time,threading

def Fun_CRC(data):
    crc = 0
    for i in data:
        crc ^= i
    return crc

# 打開串口（你可以改成 Windows COM port，例如 "COM7"）
ser = serial.Serial("COM5")  # macOS port
ser.baudrate = 115200
lock = threading.Lock()
latest_msg = None
thetext_yousend="0"
# --------- 1. 讀取 F/W 版本及 Chip ID ---------
array1 = [0x80, 0x00, 0x00, 0]
array1[3] = Fun_CRC(array1)
print("Send array1:", array1)
ser.write(bytes(array1))
data = ser.read(10)
print("FW Version:", data.hex())

# --------- 2. 重置模組 ---------
array2 = [0xC1, 0x01, 0x00, 0]
array2[3] = Fun_CRC(array2)
print("Send array2:", array2)
ser.write(bytes(array2))
data = ser.read(5)
print("Reset:", data.hex())

# --------- 3. 讀取模組設定 ---------
array3 = [0xC1, 0x02, 0x00, 0]
array3[3] = Fun_CRC(array3)
print("Send array3:", array3)
ser.write(bytes(array3))
data = ser.read(12)
print("Config:", data.hex())

# --------- 4. 設定模式與頻率 ---------
# Mode = 3 (Rx), SF = 1, Freq = 0x65 0x6C 0x03 (~345 MHz)
array4 = [0xC1, 0x03, 0x05, 0x03, 0x01, 0x65, 0x6C, 0x03, 0]
array4[8] = Fun_CRC(array4)
print("Send array4 (set freq):", array4)
ser.write(bytes(array4))
data = ser.read(5)
print("Freq Set ACK:", data.hex())

# --------- 5. 讀取接收資料 ---------
def read_lora_data():
    global latest_msg
    OLDMSG = None
    while True:
        with lock:
            array = [0xC1, 0x06, 0x00, 0]
            array[3] = Fun_CRC(array)
            #print("Send LoRa read command:", array)

            ser.reset_input_buffer()
            ser.write(bytes(array))
            time.sleep(0.1)  # 增加等待時間，給模組完整反應時間

            header = ser.read(3)
            if len(header) != 3:
                print("⚠️ 未收到完整 header")
                continue

            if header[:2] != b'\xC1\x86':
                print(f"⚠️ 非預期 header: {header.hex()}")
                continue

            #print("Reply header:", header.hex())

            data_len = header[2]
            payload = ser.read(data_len)

            if len(payload) < data_len:
                print(f"⚠️ Payload 不完整（{len(payload)}/{data_len}）")
                continue

            latest_msg = payload
            #print("this test",thetext_yousend,latest_msg[0:len(thetext_yousend)])
            if latest_msg != OLDMSG and latest_msg[0:len(thetext_yousend)]!=thetext_yousend:
                try:
                    print("📥 接收:", latest_msg.decode("utf-8", errors="replace"))
                except:
                    print("⚠️ 解碼錯誤")
                OLDMSG = latest_msg

        time.sleep(0.5)


def send_text(ser, text: str):
	with lock:
	    array4 = [0xC1, 0x03, 0x05, 0x02, 0x01, 0x65, 0x6C, 0x0f, 0x00]
	    array4[8] = Fun_CRC(array4)
	    print("Send array4 (Set Freq):", array4)
	    ser.write(bytes(array4))
	    time.sleep(0.05)  # 給模組反應時間
	    
	    data = ser.read(5)
	    print("Freq Set ACK:", data.hex())
	    if not (1 <= len(text.encode("utf-8")) <= 32):
	        print("❗ 輸入字串長度需在 1~32 bytes 之間")
	        return
	    data_bytes = [ord(c) for c in text]
	    pkt = [0xC1, 0x05, len(data_bytes)] + data_bytes + [0]
	    pkt[-1] = Fun_CRC(pkt)
	    print(f"📤 發送資料封包: {pkt}")
	    ser.write(bytes(pkt))
	    time.sleep(0.05)  # 給模組反應時間
	    
	    ack = ser.read(5)
	    #print(f"📥 收到 ACK: {ack.hex()}")
	
	    array4 = [0xC1, 0x03, 0x05, 0x03, 0x01, 0x65, 0x6C, 0x03, 0]
	    array4[8] = Fun_CRC(array4)
	    print("Send array4 (set freq):", array4)
	    ser.reset_input_buffer()
	    ser.write(bytes(array4))
	    time.sleep(0.05)  # 給模組反應時間
	    
	    data = ser.read(5)
	    print("Freq Set ACK:", data.hex())
    
    
    
    

threading.Thread(target=read_lora_data, daemon=True).start()    



# ---------- 主迴圈 ----------
try:
    while True:
        thetext_yousend=input("🔼 輸入文字（exit 離開）> ")
       
        send_text(ser,thetext_yousend.strip())
        thetext_yousend = thetext_yousend.encode("utf-8")
        time.sleep(5)



except KeyboardInterrupt:
    print("\n✅ 中斷結束")

finally:
    ser.close()
    print("🔚 Serial closed.")
