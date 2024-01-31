import requests
import time

def get_plant_data(plant_group, access_token, project_key):
    # Setting up the URL and headers
    url = f"https://gz-4-api.iot-api.com/device/v1/{access_token}/attributes?keys=temperature,humidity"
    headers = {
        "Content-Type": "application/json",
        "Project-Key": project_key
    }

    # Making the GET request
    response = requests.get(url, headers=headers)

    # Print the response along with the plant group name
    print(f"Data for {plant_group}:")
    print(response.status_code)
    print(response.text)
    print("--------------------------------------")

# Plant group details
plant_groups = [
    {"name": "三角梅土壤传感器1", "access_token": "xyby7l50ju7dm53u", "project_key": "HF7n7lcw5h"},
    {"name": "常春藤土壤传感器2", "access_token": "xu71x92hbqmhtueo", "project_key": "HF7n7lcw5h"}
]

# Run every 1 minute
while True:
    for plant_group in plant_groups:
        get_plant_data(plant_group["name"], plant_group["access_token"], plant_group["project_key"])
    time.sleep(60)
