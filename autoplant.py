import requests
import time
import broadlink
from datetime import datetime, timedelta
import logging
import os

from dotenv import load_dotenv
load_dotenv()

# Create a directory for logs if it doesn't exist
if not os.path.exists('log'):
    os.makedirs('log')

# Setting up logging
logging.basicConfig(filename=f'log/autoplant_{datetime.now().strftime("%Y%m%d")}.log', 
                    level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s', 
                    datefmt='%Y-%m-%d %H:%M:%S')

# Constant variables
HUMIDITY_THRESHOLD = 15  # Humidity level to trigger irrigation
COOLDOWN_PERIOD = 10  # Cooldown period in minutes before re-irrigating
IRRIGATION_DURATION1 = 300  # Duration of irrigation in seconds (5 minutes)
IRRIGATION_DURATION2 = 120  # Duration of irrigation in seconds (2 minutes)
SWITCH_DURATION = 20  # Duration of switching water paths (20 seconds)

# # Constant variables for quick testing
# HUMIDITY_THRESHOLD = 18  # Humidity level to trigger irrigation
# COOLDOWN_PERIOD = 2  # Cooldown period in minutes before re-irrigating
# IRRIGATION_DURATION1 = 30  # Duration of irrigation in seconds (5 minutes)
# IRRIGATION_DURATION2 = 12  # Duration of irrigation in seconds (2 minutes)
# SWITCH_DURATION = 5  # Duration of switching water paths (20 seconds)


# 初始化插座
# Initialization for Broadlink plugs with dynamic IP
def init_plugs():
    plugs = {}
    plug_details = {
        'plug_switch': {'mac': os.getenv('PLUG_SWITCH_MAC')}, 
        'plug_water': {'mac': os.getenv('PLUG_WATER_MAC')}
    }

    all_plugs_initialized = False

    while not all_plugs_initialized:
        try:
            # Discover Broadlink devices on the network
            discovered_devices = broadlink.discover(timeout=5)
            all_plugs_initialized = True

            for device in discovered_devices:
                device_mac = ':'.join(['%02x' % b for b in device.mac])
                logging.info(f"Discovered device - Host: {device.host}, MAC: {device_mac}, Name: {device.name}")
                for group, details in plug_details.items():
                    if device_mac.lower() == details['mac'].lower():
                        device.auth()
                        plugs[group] = {'device': device, 'last_irrigated': None}
                        logging.info(f"Initialized plug for {group} with IP: {device.host[0]}")

            # Check if all plugs are initialized
            for group in plug_details.keys():
                if group not in plugs:
                    all_plugs_initialized = False
                    logging.error(f"Initialization failed for plug: {group}")  # Log the plug that failed to initialize
                    break

        except Exception as e:
            logging.error(f"Failed to initialize plugs: {e}")
            all_plugs_initialized = False

        if not all_plugs_initialized:
            logging.info("Retrying plug initialization in 10 seconds...")
            time.sleep(10)

    return plugs

# Initialize plugs
plugs = init_plugs()

# 植物组数据
# Plant group details
plant_groups = [
    {"name": "三角梅土壤传感器1", "access_token": os.getenv('PLANT1_ACCESS_TOKEN'), "project_key": os.getenv('PLANT_PROJ_KEY'), "group_number": 1},
    {"name": "常春藤土壤传感器2", "access_token": os.getenv('PLANT2_ACCESS_TOKEN'), "project_key": os.getenv('PLANT_PROJ_KEY'), "group_number": 2}
]

# 灌溉程序
# Function to control irrigation
def irrigate(group_number):
    plug_switch = plugs['plug_switch']
    plug_water = plugs['plug_water']

    try:
        if group_number == 1:
            # Procedure for plant group 1
            logging.info(f"Irrigating plant group 1: Turning off plug_switch ...")
            plug_switch['device'].set_power(False)
            time.sleep(SWITCH_DURATION)  # Wait 20 seconds
            logging.info(f"Irrigating plant group 1: Turning on plug_water ...")
            plug_water['device'].set_power(True)
            time.sleep(IRRIGATION_DURATION1)  # Wait 5 minutes
        elif group_number == 2:
            # Procedure for plant group 2
            logging.info(f"Irrigating plant group 2: Turning on plug_switch ...")
            plug_switch['device'].set_power(True)
            time.sleep(SWITCH_DURATION)  # Wait 20 seconds
            logging.info(f"Irrigating plant group 2: Turning on plug_water ...")
            plug_water['device'].set_power(True)
            time.sleep(IRRIGATION_DURATION2)  # Wait 2 minutes
    except Exception as e:
        logging.info(f"Irrigation error for group {group_number}: {e}")
    finally:
        # closing irrigation and retry water off until it success
        success = False
        attempt_count = 0
        while not success:
            try:
                if attempt_count > 0:  # Auth is required only from the second attempt onwards
                    logging.info(f"Re-authenticating before retrying for plant group {group_number}")
                    plug_water['device'].auth()

                logging.info(f"Closing irrigation for plant group {group_number}, attempt {attempt_count + 1}")
                plug_water['device'].set_power(False)
                success = True
                logging.info(f"Irrigation closed successfully for plant group {group_number} on attempt {attempt_count + 1}")
            except Exception as e:
                logging.error(f"Failed to close irrigation for plant group {group_number} on attempt {attempt_count + 1}: {e}")
                attempt_count += 1
                time.sleep(5)  # Wait for 5 seconds before retrying

        if group_number == 2:
            time.sleep(SWITCH_DURATION)  # Wait 20 seconds
            logging.info(f"Irrigating plant group 2: Turning off plug_switch ...")
            plug_switch['device'].set_power(False)
        logging.info(f"Irrigation process completed for plant group {group_number}.")

# 获取植物数据
# Function to fetch and evaluate plant data
def get_plant_data(plant_group, access_token, project_key, group_number):
    url = f"https://gz-4-api.iot-api.com/device/v1/{access_token}/attributes?keys=temperature,humidity"
    headers = {
        "Content-Type": "application/json",
        "Project-Key": project_key
    }

    try:
        response = requests.get(url, headers=headers)
        logging.info(f"Data for {plant_group}:")
        logging.info(response.text)
        logging.info("--------------------------------------")

        if response.status_code == 200:
            data = response.json()
            humidity = data['attributes']['humidity']

            # Check humidity level and last irrigation time
            plug_switch = plugs['plug_switch']
            last_irrigated = plug_switch['last_irrigated']
            if humidity < HUMIDITY_THRESHOLD and (last_irrigated is None or datetime.now() - last_irrigated > timedelta(minutes=COOLDOWN_PERIOD)):
                logging.info(f"Initiating irrigation for plant group {group_number} due to low humidity ...")
                irrigate(group_number)
                plug_switch['last_irrigated'] = datetime.now()
        else:
            logging.error(f"Failed to fetch data for {plant_group}: HTTP Status Code {response.status_code}")

    except requests.RequestException as e:
        logging.error(f"Error fetching data for {plant_group}: {e}")

    except Exception as e:
        logging.error(f"Unexpected error while fetching data for {plant_group}: {e}")


# Run every 5 minutes
while True:
    for plant_group in plant_groups:
        get_plant_data(plant_group["name"], plant_group["access_token"], plant_group["project_key"], plant_group["group_number"])
        time.sleep(5)
    time.sleep(300)
