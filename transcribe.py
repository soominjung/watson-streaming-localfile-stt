#!/usr/bin/env python
#
# Copyright 2016 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from os.path import join, dirname, getsize
import argparse
import base64
import configparser
import json
import threading
import time

import websocket
from websocket._abnf import ABNF

CHUNK = 1024
RATE = 16000
PATH = join(dirname(__file__), 'resources', 'sample_short_A.flac')
FINALS = []

REGION_MAP = {
    'us-east': 'gateway-wdc.watsonplatform.net',
    'us-south': 'stream.watsonplatform.net',
    'eu-gb': 'stream.watsonplatform.net',
    'eu-de': 'stream-fra.watsonplatform.net',
    'au-syd': 'gateway-syd.watsonplatform.net',
    'jp-tok': 'gateway-tok.watsonplatform.net',
}

def read_audio(ws):
    with open(PATH, 'rb') as audio_file:
        fileSize = getsize(PATH)
        global start_time
        start_time = time.time()
        for i in range(0, int(fileSize / CHUNK)):
            print("Sending packet... %d" % i)
            data = audio_file.read(CHUNK)
            ws.send(data, ABNF.OPCODE_BINARY)
    data = {"action": "stop"}
    ws.send(json.dumps(data).encode('utf8'))

def on_message(ws, msg):
    global start_time
    data = json.loads(msg)
    if "results" in data:
        if data["results"][0]["final"]:
            end_time = time.time()
            # FINALS.append(data)
            print("Transcript:" + data['results'][0]['alternatives'][0]['transcript'])
            print('Latency: {} sec'.format(end_time-start_time))
            ws.close()
'''     
        else:
            # This prints out the current fragment that we are working on
            print(data['results'][0]['alternatives'][0]['transcript'])
'''

def on_error(self, error):
    print(error)

'''
def on_close(ws):
    transcript = "".join([x['results'][0]['alternatives'][0]['transcript']
                          for x in FINALS])
    print(transcript)
'''

def on_open(ws):
    """Triggered as soon a we have an active connection."""
    data = {
        "action": "start",
        # this means we get to send it straight raw sampling
        # "content-type": "audio/flac;rate=%d" % RATE,
        "continuous": True,
        "interim_results": True,
        "inactivity_timeout": 5, # in order to use this effectively
        # you need other tests to handle what happens if the socket is
        # closed by the server.
        # "word_confidence": True,
        # "timestamps": True,
        # "max_alternatives": 3
    }

    # Send the initial control message which sets expectations for the
    # binary stream that follows:
    ws.send(json.dumps(data).encode('utf8'))
    # Spin off a dedicated thread where we are going to read and
    # stream out audio.
    threading.Thread(target=read_audio,
                     args=(ws,)).start()

def get_url():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    # See
    # https://console.bluemix.net/docs/services/speech-to-text/websockets.html#websockets
    # for details on which endpoints are for each region.
    region = config.get('auth', 'region')
    host = REGION_MAP[region]
    return ("wss://{}/speech-to-text/api/v1/recognize"
           "?model=ko-KR_BroadbandModel").format(host)

def get_auth():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    apikey = config.get('auth', 'apikey')
    return ("apikey", apikey)

'''
def parse_args():
    parser = argparse.ArgumentParser(
        description='Transcribe Watson text in real time')
    # parser.add_argument('-t', '--timeout', type=int, default=5)
    # parser.add_argument('-d', '--device')
    # parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    return args
'''

def main():
    # Connect to websocket interfaces
    headers = {}
    userpass = ":".join(get_auth())
    headers["Authorization"] = "Basic " + base64.b64encode(
        userpass.encode()).decode()
    url = get_url()

    # If you really want to see everything going across the wire,
    # uncomment this. However realize the trace is going to also do
    # things like dump the binary sound packets in text in the
    # console.
    #
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(url,
                                header=headers,
                                on_message=on_message,
                                on_error=on_error
                                #on_close=on_close
                                )
    ws.on_open = on_open
    # This gives control over the WebSocketApp. This is a blocking
    # call, so it won't return until the ws.close() gets called (after
    # 6 seconds in the dedicated thread).
    ws.run_forever()


if __name__ == "__main__":
    main()