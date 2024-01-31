import requests

# URL and headers
url = "https://gz-4-api.iot-api.com/device/v1/xyby7l50ju7dm53u/attributes?keys=temperature,humidity"
headers = {
    "Content-Type": "application/json",
    "Project-Key": "HF7n7lcw5h"  
}

print("url: ", url)
print("headers: ", headers)

# Making the GET request
response = requests.get(url, headers=headers)

# Printing the response
print(response.status_code)
print(response.text)
