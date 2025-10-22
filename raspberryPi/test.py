import serial
import time

ser = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)

while True:
    ser.write(b'Hello STM32!\n')
    print("Sent: Hello STM32!")
    time.sleep(1)
