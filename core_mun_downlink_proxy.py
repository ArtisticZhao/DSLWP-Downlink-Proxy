#coding:utf-8

import time
import threading
import socket
import select
import Queue
import math
import json

import tornado
from tornado.websocket import websocket_connect
from tornado import gen, locks
from tornado.ioloop import IOLoop


class SocketSender(threading.Thread):
    def __init__(self,Proxy_Interface,CB,MyName):
        threading.Thread.__init__(self)
        self.thread_stop = False
        self.MyName = MyName
        self.CallBackFun = CB
        self.Proxy_Interface = Proxy_Interface
        self.SendQueue = Queue.Queue()
        self.ReSendBuf = None


    def run(self):
        while not self.thread_stop:
            if self.Proxy_Interface.sock == None or self.Proxy_Interface.StateNow != 2:
                time.sleep(0.05)
                continue

            if self.SendQueue.empty() == False or self.ReSendBuf != None:
                try:
                    infds,outfds,errfds = select.select([],[self.Proxy_Interface.sock,],[],5)
                except:
                    continue

                if len(outfds)!=0:
                    if self.ReSendBuf != None:
                        data = self.ReSendBuf
                        print("["+self.MyName+"]" + " Trying To Send Resend Buffer")
                        self.ReSendBuf = None
                    else:
                        data = self.SendQueue.get()

                    if self.CallBackFun != None:
                        data_s = self.CallBackFun(self.Proxy_Interface, self.MyName, data)
                    else:
                        data_s = data

                    try:
                        self.Proxy_Interface.sock.send(data_s)
                        print("["+self.MyName+"]" + " Successfully Send Data Length = %d"%len(data)  )
                    except socket.error as msg:
                        self.ReSendBuf = data
                        print("["+self.MyName+"]" + " Fialed To Send" + str(msg))
            else:
                time.sleep(0.05)

    def SendData(self,data):
        self.SendQueue.put(data)

    def stop(self):
        self.thread_stop = True
        print("["+self.MyName+"]" + " Sender Is Stopping")



class ProxyListenInterface(threading.Thread):
    def __init__(self,Host,Port,Rcv_CB,Snt_CB,MyName):
        threading.Thread.__init__(self)
        self.StateNow=0
        self.thread_stop = False
        self.Host = Host
        self.Port = Port
        self.MyName = MyName
        self.Rcv_CB = Rcv_CB
        self.Snt_CB = Snt_CB
        self.sender = SocketSender(self,Snt_CB,MyName)
        self.listen_sock = None
        self.sock = None
        self.CB_Connected = None

    def SetCB_Connected(self,CBFunction):
        self.CB_Connected = CBFunction

    def run(self):
        self.sender.start()
        while not self.thread_stop:
            if self.StateNow == 0:#状态0:准备监听
                try:
                    self.listen_sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR  , 1)
                    self.listen_sock.bind((self.Host,self.Port))
                    self.listen_sock.listen(1)
                    self.StateNow=1
                except socket.error as msg:
                    print("["+self.MyName+"]" + " Fialed To Create Socket Or Listen" + str(msg))
                    self.listen_sock.close()
                    time.sleep(0.1)
                    continue

            elif self.StateNow == 1: #状态1：等待连接
                while(not self.thread_stop):#等待本地连接
                    infds,outfds,errfds = select.select([self.listen_sock,],[],[],5)
                    if len(infds)!=0:
                        self.sock, addr = self.listen_sock.accept()
                        self.listen_sock.close()
                        self.listen_sock = None

                        while (self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) <0):
                            print "Connection Not Ready..."
                            time.sleep(0.1)
                            pass


                        print("["+self.MyName+"]" + " Connected To Proxy...")
                        if self.CB_Connected != None:
                            self.CB_Connected()
                        self.StateNow=2#切换到下一个状态，等待接收数据
                        break
                    else:
#                         print ("["+self.MyName+"]"+"No Connection In 5 Seconds...")
                        pass
                try:
                    self.listen_sock.close()
                    self.listen_sock = None
                except:
                    pass

            elif self.StateNow == 2:#状态2：等待接收远程服务器发回的消息
                while (not self.thread_stop):
                    infds,outfds,errfds = select.select([self.sock,],[],[],5)
                    if len(infds)!=0:
                        try:
                            data = self.sock.recv(1024)
                            if data:#如果收到的数据不是空字符串
                                print("["+self.MyName+"]" + " Received Data ...")
                                if self.Rcv_CB != None:
                                    self.Rcv_CB(self, self.MyName, data)
                            else:#收到空字符串，认为是对方断开链接
                                self.sock.close()
                                self.sock = None
                                self.StateNow=0;
                                print ("["+self.MyName+"]" + " The Connection Is Closed...")
                                break;
                        except socket.error as msg:
                            self.sock.close()
                            self.sock = None
                            self.StateNow=0;
                            print("["+self.MyName+"]" + " Error In Recv ..."+str(msg))
                            break;

                    else:
                        #print ("["+self.MyName+"]"+"No Data In 5 Seconds...")
                        pass


        print("["+self.MyName+"]" +  " Stopped")

        while self.sender.isAlive() == True:
            time.sleep(0.1)
        print("["+self.MyName+"]" + " Sender Stopped")

    def SendData(self,data):
        self.sender.SendData(data)

    def stop(self):
        self.sender.stop()
        self.thread_stop = True
        print("["+self.MyName+"]" + " Stopping")



class WebSocketClient(object):
    def __init__(self, url, name):
        self._url = url
        self._name = name
        self._ws = None
        self.__lock = locks.Lock()
        self._io_loop = tornado.ioloop.IOLoop.current()
        self._queue = Queue.Queue(maxsize = 100) # change queue size from here
        self._time_out = 0
        self._period = None


    @gen.coroutine
    def start(self):
        with (yield self.__lock.acquire()):
            if self._ws is None:
                try:
                    self._ws = yield websocket_connect(self._url, io_loop=self._io_loop)
                except Exception, e:
                    self._time_out += 1
                    if self._time_out >= 10:
                        self._period.change_callback_time(10000)
                else:
                    self.on_message()
            if self._ws:
                self._time_out = 0
                self._period.change_callback_time(1000)
                self.on_connected()


    def _period_start(self):
        if self._period is None:
            self._period = PeriodicCallback(self.start, 1000, io_loop=self._io_loop)
            self._period.start()


    @gen.coroutine
    def on_message(self):
        while True:
            msg = yield self._ws.read_message()
            if msg is None:
                print "[WebSocket] " + self._name + " socket connection closed"
                self._close()
                break
            else:
                message = json.loads(msg)
                print message['message']


    def on_connected(self):
        while self._queue.empty() == False:
            self._ws.write_message(self._queue.get())


    def _close(self):
        if self._ws:
            self._ws.close()
            self._ws = None

    def _restart_now(self):
        if self._ws is None:
            self.start()


    def send(self, data):
        self._period_start()
        self._restart_now()
        if self._queue.full() == False:
            self._queue.put(data)
        else:
            print "[Queue] Websocket queue received maximum, throw away old data"
            self._queue.get()
            self._queue.put(data)


    def is_alive(self):
        return self._ws != None


    def stop(self):
        self._close()
        if self._period and self._period.is_running():
            self._period.stop()



class PeriodicCallback(object):
    def __init__(self, callback, callback_time, io_loop=None):
        self.callback = callback
        if callback_time <= 0:
            raise ValueError("Periodic callback must have a positive callback_time")
        self.callback_time = callback_time
        self.io_loop = io_loop or IOLoop.current()
        self._running = False
        self._timeout = None


    def start(self):
        """Starts the timer."""
        self._running = True
        self._next_timeout = self.io_loop.time()
        self._schedule_next()


    def stop(self):
        """Stops the timer."""
        self._running = False
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None


    def is_running(self):
        return self._running


    def _run(self):
        if not self._running:
            return
        try:
            return self.callback()
        except Exception:
            self.io_loop.handle_callback_exception(self.callback)
        finally:
            self._schedule_next()


    def _call_io_loop_thread(self):
        self._timeout = self.io_loop.add_timeout(self._next_timeout, self._run)


    def _schedule_next(self):
        if self._running:
            current_time = self.io_loop.time()

            if self._next_timeout <= current_time:
                callback_time_sec = self.callback_time / 1000.0
                self._next_timeout += (math.floor((current_time - self._next_timeout) /
                                                  callback_time_sec) + 1) * callback_time_sec

            self.io_loop.add_callback(self._call_io_loop_thread)


    def change_callback_time(self, callback_time):
        self.callback_time = callback_time
