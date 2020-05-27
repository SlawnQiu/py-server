import aiohttp
import asyncio
import io
import datetime, time
import json
import smbus
import time
import sys
import os
import RPi.GPIO as GPIO
import serial

# 設定 GPIO
GPIO.setwarnings(False)
DEVICE = 0x23

ONE_TIME_HIGH_RES_MODE_1 = 0x20
ONE_TIME_HIGH_RES_MODE_2 = 0x21

GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)
GPIO.setup(40, GPIO.IN, pull_up_down=GPIO.PUD_UP)

ser = serial.Serial("/dev/rfcomm0", 9600, timeout=0.5)
ser.write("test ".encode())

bus = smbus.SMBus(1)

# 控制用變數
POWER_ON = False
AUTO_BRIGHTNESS = True
BRIGHTNESS = 4
LED_GPIO_INDEX = [11, 16, 13, 15]
TOUCH_SWITCH_GPIO = 40
TOUCH_LONG_THRESHOLD_MILISEC = 1500  # 觸控板長按時間閾值
LIGHT_DETECT_INTERVAL_SEC = 5  # 亮度探測間隔


def convertToNumber(data):
    return (data[1] + (256 * data[0])) / 1.2


def readLight(addr=DEVICE):
    data = bus.read_i2c_block_data(addr, ONE_TIME_HIGH_RES_MODE_2)
    return convertToNumber(data)


# 更改亮度
def output_brightness(brightness):
    for i in range(brightness):
        GPIO.output(LED_GPIO_INDEX[i], GPIO.HIGH)
    for i in range(brightness, len(LED_GPIO_INDEX)):
        GPIO.output(LED_GPIO_INDEX[i], GPIO.LOW)


# 循環監聽狀態
async def led_control_task():
    global POWER_ON, BRIGHTNESS, LED_GPIO_INDEX
    while True:
        if POWER_ON:
            output_brightness(BRIGHTNESS)
        else:
            output_brightness(0)

        await asyncio.sleep(0.05)


# 觸摸板操作
async def touch_switch_task():
    global POWER_ON, AUTO_BRIGHTNESS
    time_pressed = 0
    while True:
        if GPIO.input(TOUCH_SWITCH_GPIO) and time_pressed == 0:
            time_pressed = int(time.time() * 1000)
        if not GPIO.input(TOUCH_SWITCH_GPIO) and time_pressed != 0:
            time_elapsed = int(time.time() * 1000) - time_pressed
            time_pressed = 0
            if time_elapsed < TOUCH_LONG_THRESHOLD_MILISEC:
                # 短按操作：開關電源
                if POWER_ON:
                    POWER_ON = False
                else:
                    POWER_ON = True
            else:
                # 長按操作：開關自動亮度
                if AUTO_BRIGHTNESS:
                    AUTO_BRIGHTNESS = False
                else:
                    AUTO_BRIGHTNESS = True

        await asyncio.sleep(0.03)


# 亮度感應器操作
async def light_detector_task():
    global AUTO_BRIGHTNESS, BRIGHTNESS
    while True:
        if AUTO_BRIGHTNESS:
            num = readLight()
            if num < 100:
                BRIGHTNESS = 1
            elif 100 <= num < 400:
                BRIGHTNESS = 2
            elif 400 <= num < 800:
                BRIGHTNESS = 3
            elif 800 <= num:
                BRIGHTNESS = 4

        await asyncio.sleep(LIGHT_DETECT_INTERVAL_SEC)


def main():
    loop.create_task(led_control_task())
    loop.create_task(touch_switch_task())
    loop.create_task(light_detector_task())
    loop.run_forever()


loop = asyncio.get_event_loop()

if __name__ == '__main__':
    main()
