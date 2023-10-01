import mss
import os
import cv2
import math
import serial
import time
import win32gui, win32con, win32api, win32ui
import multiprocessing
import CVCRustScriptGuns as WP_CONF
import CVCRustFindGun as WP_DETECT
import pandas as pd
import numpy as np 
import seaborn as sns
import matplotlib.pyplot as plt
from pynput import mouse
from random import *
from multiprocessing    import Process, Queue
from typing import Optional
from ctypes import wintypes, windll, create_unicode_buffer
from CVCRustGetCompass import Compass

ak = [[0.000000,-2.257792],[0.323242,-2.300758],[0.649593,-2.299759],[0.848786,-2.259034],[1.075408,-2.323947],[1.268491,-2.215956],[1.330963,-2.236556],[1.336833,-2.218203],[1.505516,-2.143454],[1.504423,-2.233091],[1.442116,-2.270194],[1.478543,-2.204318],[1.392874,-2.165817],[1.480824,-2.177887],[1.597069,-2.270915],[1.449996,-2.145893],[1.369179,-2.270450],[1.582363,-2.298334],[1.516872,-2.235066],[1.498249,-2.238401],[1.465769,-2.331642],[1.564812,-2.242621],[1.517519,-2.303052],[1.422433,-2.211946],[1.553195,-2.248043],[1.510463,-2.285327],[1.553878,-2.240047],[1.520380,-2.221839],[1.553878,-2.240047],[1.553195,-2.248043]]

def get_config():
    # Attempt to open config file
    try:
        config = open(r"C:/Program Files (x86)/Steam/steamapps/common/Rust/cfg/client.cfg", "r")
        config_content = config.readlines()
        # Loop through each line in client.cfg
        for line in config_content:

            # Input sensitivity
            if "input.sensitivity" in line:             
                SENSITIVITY = float(line.split('"')[1]) 

            # Field of view    
            if "graphics.fov" in line:                 
                FOV = float(line.split('"')[1])

            # Aim down sight sensitivity         
            if "input.ads_sensitivity" in line:         
                ADS_FACTOR = float(line.split('"')[1]) 

            # User interface scale 
            if "graphics.uiscale" in line:              
                UI_SCALE = float(line.split('"')[1])
    # Use default values if opening file failed    
    except:
        SENSITIVITY = 1 # Input sensitivity
        FOV = 90        # Field of view
        ADS_FACTOR = 1  # Aim down sight sensitivity
        UI_SCALE = 1    # User interface scale
        print("Failed to open CFG, using defaults")
    return SENSITIVITY, FOV, ADS_FACTOR, UI_SCALE


def mouse_move(queue_m):
    arduino = None
    # Attempt to setup serial communication over com-port
    try:
        arduino = serial.Serial('COM5', 115200)
        print('Arduino: Ready')
    except:
        print('Arduino: Could not open serial port - Now using virtual input')

    print("Mouse Process: Ready")
    while True:
        # Check if there is data waiting in the queue
        try:
            move_data = queue_m.get()
            out_x, out_y, click = move_data[0], move_data[1], move_data[2]
        except:
            print('Empty')
            continue
        # If using arduino, convert cooridnates
        if(arduino):
            if out_x < 0: 
                out_x = out_x + 256 
            if out_y < 0:
                out_y = out_y + 256 
            pax = [int(out_x), int(out_y), int(click)]
            # Send data to microcontroller to move mouse
            arduino.write(pax)          
        else:
            # Move mouse virtually
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(out_x), int(out_y), 0, 0)

def BarrelData():
    return 1


def ScopeData():
    #return 1.5
    #return 1.2
    return 1

#0.20000000298023224
# W:0x57	
# A:0x41
# S:0x53
# D:0x44
def calculate_pixels(CW_VA_X, CW_VA_Y, SCREENMULTIPLYER, SCREENMULTIPLYER_CROUCH, holo):
    scope = 1
    if (holo):
        scope = 1.2
    MovePenalty = 1
    if(win32api.GetAsyncKeyState(0x41) < 0 or win32api.GetAsyncKeyState(0x44) < 0 or win32api.GetAsyncKeyState(0x57) < 0 or win32api.GetAsyncKeyState(0x53) < 0):
        MovePenalty = 1.18
    # Check if crouched
    if(win32api.GetAsyncKeyState(0x11) < 0 or win32api.GetAsyncKeyState(0x43) < 0):
        CW_PX_X = ((CW_VA_X * scope) * BarrelData() * MovePenalty) / SCREENMULTIPLYER_CROUCH
        CW_PX_Y = ((CW_VA_Y * scope) * BarrelData() * MovePenalty) / SCREENMULTIPLYER_CROUCH
        return CW_PX_X, CW_PX_Y
    # Standing
    CW_PX_X = ((CW_VA_X * scope) * BarrelData() * MovePenalty) / SCREENMULTIPLYER
    CW_PX_Y = ((CW_VA_Y * scope) * BarrelData() * MovePenalty) / SCREENMULTIPLYER
    return CW_PX_X , CW_PX_Y

# More accurate sleep(Performance hit)
def sleep_time(wt):
    target_time = time.perf_counter() + (wt / 1000)
    # Busy-wait loop until the current time is greater than or equal to the target time
    while time.perf_counter() < target_time:
        pass

# Linear interpolation(i think)
def lerp(wt, ct, x1, y1, start, queue_m):
    x_, y_, t_ = 0, 0, 0
    for i in range(1, int(ct) + 1):
        xI = i * x1 // ct
        yI = i * y1 // ct
        tI = (i * ct) // ct
        # Put mouse input in queue
        queue_m.put([xI - x_, yI - y_, 0])
        sleep_time(tI - t_)
        x_ = xI
        y_ = yI
        t_ = tI
    # Find time remaining (Wait time - Control time loop)
    loop_time = (time.perf_counter() - start) * 1000
    sleep_time(wt - loop_time)

# Returns the current foreground window
def get_foreground_window() -> Optional[str]:
    hWnd = windll.user32.GetForegroundWindow()
    length = windll.user32.GetWindowTextLengthW(hWnd)
    buf = create_unicode_buffer(length + 1)
    windll.user32.GetWindowTextW(hWnd, buf, length + 1)
    # 1-liner alternative: return buf.value if buf.value else None
    if buf.value:
        return buf.value
    else:
        return None


def on_scroll(x, y, dx, dy, queue_w, UI_SCALE):
    # Check if current window in focus is Rust
    if(get_foreground_window() == "Rust"):
        # Sleep to give time for hotbar to change
        time.sleep(.050)
        weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
        queue_w.put(weapon)


def detect_weapon(queue_w):
    SENSITIVITY, FOV, ADS_FACTOR, UI_SCALE = get_config()
    # Start listener for mouse wheel
    listener = mouse.Listener(on_scroll=lambda x, y, dx, dy: on_scroll(x, y, dx, dy, queue_w = queue_w, UI_SCALE = UI_SCALE))
    listener.start()
    display = ':0.0'
    os.environ['DISPLAY'] = display
    while True:
        # While the current window in focus is Rust
        while(get_foreground_window() == "Rust"):
            # image = WP_DETECT.screenshot(int(1920/2) - 200, 0, 190, 12)
            # frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            # image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # image_denoise = cpNoise.remove_noise(image)
            # image_lines = cpLines.find_horz_lines(image_denoise)
            # cv2.imshow('Lines', image_lines)
            # # waits for user to press any key
            # # (this is necessary to avoid Python kernel form crashing)
            # cv2.waitKey(1)
            # closing all open windows
            
            # Key 1 
            if(win32api.GetAsyncKeyState(0x31) < 0):
                #Busy while loop
                while(win32api.GetAsyncKeyState(0x31) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)

            if(win32api.GetAsyncKeyState(0x32) < 0):
                # Key 2
                while(win32api.GetAsyncKeyState(0x32) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)

            if(win32api.GetAsyncKeyState(0x33) < 0):
                # Key 3
                while(win32api.GetAsyncKeyState(0x33) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)

            if(win32api.GetAsyncKeyState(0x34) < 0):
                # Key 4
                while(win32api.GetAsyncKeyState(0x34) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)
                
            if(win32api.GetAsyncKeyState(0x35) < 0):
                # Key 5
                while(win32api.GetAsyncKeyState(0x35) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)

            if(win32api.GetAsyncKeyState(0x36) < 0):
                # Key 6
                while(win32api.GetAsyncKeyState(0x36) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)

            if(win32api.GetAsyncKeyState(0x9) < 0):
                # Key tab
                while(win32api.GetAsyncKeyState(0x9) < 0):
                    pass
                time.sleep(0.100)
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)
            if(win32api.GetAsyncKeyState(0x1B) < 0):
                # Key ESC
                while(win32api.GetAsyncKeyState(0x1B) < 0):
                    pass
                weapon = WP_DETECT.get_weapon_equipped(UI_SCALE).split(".")[0]
                queue_w.put(weapon)
            # Sleep for a 50ms(save cpu)
            time.sleep(0.050)
        # Sleep for a 50ms(save cpu)
        time.sleep(0.100)


def recoil(queue_m, queue_w):
    # Get Sens, Fov, ADS Factor from config file
    SENSITIVITY, FOV, ADS_FACTOR, UI_SCALE = get_config()
    print("CONF:", "SENSITIVITY:", SENSITIVITY, "FOV", FOV, "ADS FACTOR", ADS_FACTOR, "UI SCALE", UI_SCALE)

    # Calculate Pixel Conversion
    SCREENMULTIPLYER = (-0.03 * (SENSITIVITY) * 3 * (FOV / 100.0))
    SCREENMULTIPLYER_CROUCH = (-0.03 * ((SENSITIVITY) * 2) * 3.0 * (FOV / 100.0))

    # Compass object
    compass = Compass()

    # Set Current Weapon
    CW               =   WP_CONF.GUNS.get("WEAPON_SEMI")
    CW_WT            =   CW.get("WT")
    CW_MIN_CT        =   CW.get("MIN_CT")
    CW_MAX_CT        =   CW.get("MAX_CT")
    CW_AMMO_AMOUNT   =   CW.get("AMMO_AMOUNT")
    CW_TAP           =   CW.get("TAP")
    CW_VA_X, CW_VA_Y = 0,0

    # Setup variable to be used for tapping fully auto weapons
    prev_time_error = 0
    repeat_delay_start = 0
    diff = 0
    xyxy_all = []
    holo = False
    diff_stats = []
    bullet_num = []
    # Var to track which view angle is currenly selected
    bullet_count = 0
    CT_AVG = 0
    diff_dict = {i:[] for i in range(1,31)}
    print("Recoil Process: Ready")
    while True:
        # Start clock
        start = time.perf_counter()
        # If weapon since last shot is no longer within its repeat delay, then set view angle index back to 0
        if(((start - repeat_delay_start) * 1000) > (CW_WT) or bullet_count >= CW_AMMO_AMOUNT):
            CT_AVG = 0
            bullet_count = 0
            prev_time_error = 0
        # Once player holds left and right mouse
        while(win32api.GetAsyncKeyState(0x01) < 0 and win32api.GetAsyncKeyState(0x02) < 0):
            # Get view angle off by
            compass_time = time.perf_counter()
            #diff, xyxy_all = compass.image_correction()
            #if(bullet_count == 0):
                #diff = 0 
                #compass.set_previous(0, xyxy_all)
          
            #diff_dict[bullet_count + 1].append(diff)
            current_time = ((time.perf_counter() - compass_time) * 1000)
            # Check if weapon is a tap fire
            if(CW_TAP):
                # Get Current View Angle For Which Bullet For Current Weapon
                CW_VA_X, CW_VA_Y = CW.get("VIEW_ANGLES")[0], CW.get("VIEW_ANGLES")[1]
            else:
                # Get Current View Angle For Which Bullet For Current Weapon
                CW_VA_X, CW_VA_Y = CW.get("VIEW_ANGLES")[bullet_count][0], CW.get("VIEW_ANGLES")[bullet_count][1]
                #compass.set_previous(0, xyxy_all)
            
            # Calculate Current Pixel Values For Current Weapon
            CW_PX_X, CW_PX_Y = calculate_pixels(CW_VA_X, CW_VA_Y, SCREENMULTIPLYER, SCREENMULTIPLYER_CROUCH, holo)

            # Get Random CT Value based on Current Weapon
            CW_CT = randint(CW_MIN_CT, CW_MAX_CT)

            # Linear Interpolate / Correct For Recoil
            current_time = (time.perf_counter() - start) * 1000
            lerp(CW_WT , CW_MAX_CT - current_time, CW_PX_X, CW_PX_Y, start, queue_m)

            # Get the current timestamp
            ct = time.perf_counter()
            # Debug time print
            print("Time:", (ct - start) * 1000, "Goal:", CW_WT)

            prev_time_error += (ct - start) * 1000 - CW_WT
            print(prev_time_error)
            # Time for next loop
            start = ct

            # For tapping with fully auto weapons
            repeat_delay_start = ct
            
            # Busy while loop only if weapon is tap fired
            while(CW_TAP and win32api.GetAsyncKeyState(0x01) < 0):
                pass

            # Check how many bullets have been fired 
            if(bullet_count < CW_AMMO_AMOUNT - 1):
                bullet_count += 1

        # Check if a new weapon has been equipped
        # try:
        #     weapon = queue_w.get(block = False)
        #     CW               =   WP_CONF.GUNS.get(weapon)
        #     CW_WT            =   CW.get("WT")
        #     CW_MIN_CT        =   CW.get("MIN_CT")
        #     CW_MAX_CT        =   CW.get("MAX_CT")
        #     CW_AMMO_AMOUNT   =   CW.get("AMMO_AMOUNT")
        #     CW_TAP           =   CW.get("TAP")
        #     print("Current Weapon:", weapon)
        # except:
        #     pass
        if(win32api.GetAsyncKeyState(0x28) < 0):
            while(win32api.GetAsyncKeyState(0x28) < 0):
                pass
            if(holo):
                holo = False
            else:
                holo = True
            print("Scope: ", holo)

if __name__ == '__main__':
    multiprocessing.freeze_support()

    # Queue to communicate mouse movements, Recoil -> queue_m -> Mouse
    queue_m = Queue(1)
    # Queue to communicate weapon detection results, Detect -> queue_w -> Recoil
    queue_w = Queue(1)

    # Start Mouse process, handles sending mouse out data, communicate with using queue_m
    mouse = Process(target=mouse_move, args=(queue_m,))
    mouse.daemon = True
    mouse.start()
    print("Mouse PID:", mouse.pid)

    # Start Detect process, handles visually detecting which gun is equipped
    #detect = Process(target=detect_weapon, args=(queue_w,))
    #detect.daemon = True
    #detect.start()
    #print("Detect PID:", detect.pid)

    # Main process essentially becomes Recoil, handles computing mouse movement coordinates
    print("Main PID:", os.getpid())
    recoil(queue_m, queue_w)
    
