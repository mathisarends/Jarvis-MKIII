import re
import time
from datetime import datetime, timedelta

from core.audio.audio_player_factory import AudioPlayerFactory
from core.audio.py_audio_player import PyAudioPlayer
from plugins.alarm.daylight_alarm import AlarmSystem

if __name__ == "__main__":
    import argparse

    from core.audio.py_audio_player import PyAudioPlayer
    from shared.logging_mixin import setup_logging

    # Setup logging
    setup_logging()

    # Initialize audio player
    AudioPlayerFactory.initialize_with(PyAudioPlayer)
    alarm_system = AlarmSystem.get_instance()

    # Function to display a list of options and get user selection
    def select_from_options(options, prompt):
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option.label}")
        
        while True:
            try:
                choice = int(input("Enter the number of your choice: "))
                if 1 <= choice <= len(options):
                    return options[choice-1]
                print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a valid number")

    # Get available sounds
    wake_up_options = alarm_system.get_wake_up_sound_options()
    get_up_options = alarm_system.get_get_up_sound_options()
    
    if not wake_up_options or not get_up_options:
        print("Error: No alarm sounds found. Please check your installation.")
        exit(1)

    # Main menu
    print("\n=== DAYLIGHT ALARM SETUP ===")
    
    # 1. Select wake-up sound
    wake_sound = select_from_options(wake_up_options, "Select wake-up sound:")
    print(f"Selected: {wake_sound.label}")
    
    # 2. Select get-up sound
    get_sound = select_from_options(get_up_options, "Select get-up sound:")
    print(f"Selected: {get_sound.label}")
    
    # 3. Set volume
    while True:
        try:
            volume = float(input("\nEnter volume (0.0-1.0): "))
            if 0.0 <= volume <= 1.0:
                break
            print("Volume must be between 0.0 and 1.0")
        except ValueError:
            print("Please enter a valid number")
    
    # 4. Set sunrise brightness
    while True:
        try:
            brightness = float(input("\nEnter maximum brightness (0-100): "))
            if 0 <= brightness <= 100:
                break
            print("Brightness must be between 0 and 100")
        except ValueError:
            print("Please enter a valid number")
    
    # 5. Set wake up timer duration
    while True:
        try:
            duration = int(input("\nEnter wake-up timer duration in seconds: "))
            if duration > 0:
                alarm_system.wake_up_timer_duration = duration
                break
            print("Duration must be greater than 0")
        except ValueError:
            print("Please enter a valid number")
    
    # 6. Set alarm time
    print("\nWhen should the alarm go off?")
    print("1. In X seconds from now")
    print("2. At a specific time (HH:MM)")
    
    while True:
        try:
            time_choice = int(input("Enter your choice (1 or 2): "))
            if time_choice in [1, 2]:
                break
            print("Please enter 1 or 2")
        except ValueError:
            print("Please enter a valid number")
    
    if time_choice == 1:
        seconds = int(input("Enter seconds from now: "))
        time_str = (datetime.now() + timedelta(seconds=seconds)).strftime("%H:%M")
    else:
        while True:
            time_str = input("Enter time (HH:MM): ")
            if re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_str):
                break
            print("Please use format HH:MM (e.g., 07:30)")
    
    # Schedule the alarm
    print("\n=== ALARM SUMMARY ===")
    print(f"Wake-up sound: {wake_sound.label}")
    print(f"Get-up sound: {get_sound.label}")
    print(f"Volume: {volume:.1f}")
    print(f"Brightness: {brightness:.0f}%")
    print(f"Duration between alarms: {duration} seconds")
    print(f"Alarm time: {time_str}")
    
    confirm = input("\nSchedule this alarm? (y/n): ").lower()
    if confirm == 'y':
        alarm_system.schedule_alarm(
            "cli_alarm",
            time_str,
            wake_up_sound_id=wake_sound.value,
            get_up_sound_id=get_sound.value,
            volume=volume,
            max_brightness=brightness
        )
        
        print(f"\nAlarm scheduled for {time_str}")
        print("\nPress Ctrl+C to cancel and exit")
        
        # Wait for the alarm to trigger
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            alarm_system.cancel_alarm("cli_alarm")
            print("\nAlarm cancelled. Program terminated.")
    else:
        print("Alarm setup cancelled.")
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for alarm_id in list(alarm_system._active_alarms):
            alarm_system.cancel_alarm(alarm_id)
        print("Program terminated")