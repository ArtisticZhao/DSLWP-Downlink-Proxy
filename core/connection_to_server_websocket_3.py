# coding:utf-8
import asyncio
import queue
import math
import time

import tornado
import threading
import json

import websocket



class WebSocketClient(object):
    def __init__(self, url, name):
        self._url = url
        self._name = name
        self._ws = None
        self._queue = queue.Queue(maxsize=100)  # change queue size from here
        self._time_out = 0
    def clientloop(self):
        while True:
            try:
                if self._ws == None:

                    s=websocket.create_connection(self._url)
                    print("connect",s)
                    self._ws=s
                    self.on_connected()

                else:
                    self.on_connected()

            except Exception as e:
                print("error",repr(e))
                print('Waiting 10 sec to retry...')
                time.sleep(10)
                self._close()
    def recvloop(self):
        while True:
            if self._ws:
                msg=self._ws.recv()
                print(msg)
            else:
                time.sleep(0.1)
    def get_name(self):
        '''
        返回websocket连接的名字
        '''
        return self._name




    async def on_message(self):
        while True:
            try:
                print("before recv")
                msg = await asyncio.wait_for(self._ws.recv(),timeout=0.1)
                print("msg",msg)
                if msg is None:
                    print ("[WebSocket] " + self._name + " socket connection closed")
                    await self._close()
                    break
                else:
                    #message = json.loads(msg)
                    print (msg)
            except Exception as e:
                print(repr(e))
                await self._close()
                break
    def on_connected(self):
        while self._queue.empty() is False:
            msg = self._queue.get()
            self._ws.send(msg)
            # self._close()


    def _close(self):
        if self._ws:
            self._ws.close()
            self._ws = None



    def SendData(self, data):
        if not self._queue.full():
            self._queue.put(data)
        else:
            print ("[Queue] Websocket queue received maximum, throw away old data")
            self._queue.get()
            self._queue.put(data)

    def is_alive(self):
        return self._ws is not None

    def stop(self):
        self._close()
        print(" [Websocket] " + self._name + " stopped")



class Websocket_send_thread(threading.Thread):
    def __init__(self,client):
        threading.Thread.__init__(self)
        self.client=client

    def run(self):
        self.client.clientloop()

class Websocket_recv_thread(threading.Thread):
    def __init__(self,client):
        threading.Thread.__init__(self)
        self.client=client

    def run(self):
        self.client.recvloop()
if __name__ == '__main__':
    client=WebSocketClient("ws://127.0.0.1:8888","test")
    t=Websocket_send_thread(client)
    t.start()
    t2=Websocket_recv_thread(client)
    t2.start()
    while True:
        time.sleep(1)
        client.SendData("111")
        print("send")