import numpy as np
from pynput.keyboard import Controller, Key
import time

# Initialize mouse controller
keyboard = Controller()

#Example custom method run using WiReSens Toolkit to use pressure sensor as a remote control
def startController(sensors):
    print(len(sensors))
    volumeUpRegion = (slice(0,8), slice(16,32))
    volumeDownRegion = (slice(24,32), slice(16,32))
    playRegion = (slice(0,10),slice(0,16))
    pauseRegion = (slice(20,32),slice(0,10))

    playThreshold = 1500
    pauseThreshold = 1000
    volumeUpThreshold = 1400
    volumeDownThreshold = 1800
    running = True
    paused = False
    while running:
        pressureGrid = sensors[0].pressure.reshape(sensors[0].selWires, sensors[0].readWires)
        if sensors[0].init:
            volumeUpAvg = np.mean(pressureGrid[volumeUpRegion[0],volumeUpRegion[1]])
            volumeDownAvg = np.mean(pressureGrid[volumeDownRegion[0],volumeDownRegion[1]])
            playAvg = np.mean(pressureGrid[playRegion[0],playRegion[1]])
            pauseAvg = np.mean(pressureGrid[pauseRegion[0],pauseRegion[1]])

            print(playAvg, pauseAvg)


            if playAvg <= playThreshold and paused:
                print("Play")
                keyboard.press(Key.media_play_pause)
                paused=False
            elif pauseAvg <= pauseThreshold and not paused:
                print("Paused")
                keyboard.press(Key.media_play_pause)
                paused = True

            if volumeUpAvg <volumeUpThreshold:
                print("Volume Up")
                sleepFactor = 3
                diff = volumeUpThreshold - volumeUpAvg
                if diff < 150:
                    sleepFactor = 5
                elif diff < 300:
                    sleepFactor = 15
                else:
                    sleepFactor = 30
                keyboard.press(Key.media_volume_up)
                print(sleepFactor)
                time.sleep(1/sleepFactor)
            elif volumeDownAvg < volumeDownThreshold:
                sleepFactor = 3
                diff = volumeDownThreshold - volumeDownAvg
                if diff < 150:
                    sleepFactor = 5
                elif diff < 300:
                    sleepFactor = 15
                else:
                    sleepFactor = 30
                print("Volume Down")
                print(sleepFactor)
                keyboard.press(Key.media_volume_down)
                time.sleep(1/sleepFactor)

