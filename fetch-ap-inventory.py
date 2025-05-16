#!/usr/bin/env python3

# Copyright (c) 2025 Remi Locherer <remi@arista.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


# Example script to demonstrate how to utilize the API of CV-CUE.
# API documentation: https://apihelp.wifi.arista.com/home
# The script fetches the name and IP address of all managed APs. 
# It prints them one per line and separates the values with a comma.

import json
import requests
import os

# Lookup URL in CV-CUE -> SYSTEM -> Advanced Settings -> Base URLs for APIs
api_url = "https://awm13004-c4.srv.wifi.arista.com/wifi/api/"
# Define a Key in admin settings in LaunchPad.
# User role "Viewer" for wireless manager is sufficient.
key_id = "KEY-ATN123456-1234"
key_value = "1234567890"

credentials = {
   "type": "apikeycredentials",
   "keyId": key_id,
   "keyValue": key_value,
   "timeout": 360,
   "clientIdentifier": os.path.basename(__file__)
}
params = {
    "pagesize": 100,
    "startindex" : 0
}

# create a session with the api
login = requests.post(api_url + "session", json=credentials )
if login:
    jar = login.cookies
else:
    raise Exception(f"Login failed on {login.url} with status code: {str(login.status_code)}")

# get the aps from the api in batches with the size defined in pagesize
while True:
   data = requests.get(api_url + "manageddevices/aps", cookies=jar, params=params)
   if not data:
       raise Exception(f"Request GET {data.url} failed with status code: {str(data.status_code)}")

   devices = json.loads(data.content)
   for ap in devices["managedDevices"]:
      print(ap["name"] + "," + ap["ipAddress"])
   
   params["startindex"] += params["pagesize"]
   if params["startindex"] >= devices["totalCount"]:
      break

# logout
requests.delete(api_url + "session", cookies=jar)