# -*- encoding: utf-8 -*-

"""Implementation of the proxy for XXXX

`XXXX proxy <url git>`_ allow for tcp protocol
communication between GNU Radio and the proxy,
and allow for bidirectional communication
between the proxy and tornado server.

Proxy is supported in the current versions of GNU Radio
and tornado server.


.. version:: 1.0
.. author:: myrfy, LinerSu, LucyWang
"""

import sys
import os
import webbrowser
import socket
import time
import threading
import struct
import Queue
import codecs
import urllib2
import requests
import json
import datetime
import PyQt4
import xml.dom.minidom as minidom

from PyQt4.QtGui import *
from PyQt4 import QtGui,QtCore
from proxy_ui import Ui_MainWindow
from core_mun_downlink_proxy import *
from _dbus_bindings import String
from xml.dom.minidom import Document
from kiss_decoder import KISS_Decoder



class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Setup thread for tornado application
        self.thread = MyThread()
        self.thread.start()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Button initial
        self.ui.start_proxy_button.clicked.connect(self.start_proxy)
        self.ui.save_config_button.clicked.connect(self.save_settings)
        self.ui.exit_button.clicked.connect(self.exit)
        self.ui.update_button.clicked.connect(self.update_orbit)
        self.ui.about_button.clicked.connect(self.popup_about)
        self.ui.by2hit_logo.clicked.connect(self.link_by2hit)
        self.ui.hit_logo.clicked.connect(self.link_hit)
        self.ui.lilacsat_logo.clicked.connect(self.link_lilac)

        # Initial refresh time for signal
        self.refresh_timer = QtCore.QTimer()
        QtCore.QObject.connect(self.refresh_timer,QtCore.SIGNAL("timeout()"),
            self.on_timer)
        self.refresh_timer.start( 500 )

        self.host = None
        self.host_back = None
        self.server_port = None
        self.web_socket = None
        self.backup_web_socket = None
        self.proxy_running = False
        self.input_error = False
        self.kiss_decoder = KISS_Decoder(self.handle_func_kiss)

        # Setup Dict
        """ This array contains data as follow:
            name  long  alt   lat
        """
        self.usr_dict = [
            None, None, None, None
        ]
        """ This array contains data as follow:
            Proxy, ui_status, port_enable_status, port_text, sate_name_text, port_name, sat_name,
            channel_text, channel_name
        """
        self.port_dict = [
            [None, self.ui.port1_status, self.ui.port1_enabled, self.ui.port1_text,
                self.ui.sat1_name_text, None, None, self.ui.channel1_text, None],
            [None, self.ui.port2_status, self.ui.port2_enabled, self.ui.port2_text,
                self.ui.sat2_name_text, None, None, self.ui.channel2_text, None],
            [None, self.ui.port3_status, self.ui.port3_enabled, self.ui.port3_text,
                self.ui.sat3_name_text, None, None, self.ui.channel3_text, None],
            [None, self.ui.port4_status, self.ui.port4_enabled, self.ui.port4_text,
                self.ui.sat4_name_text, None, None, self.ui.channel4_text, None],
            [None, self.ui.port5_status, self.ui.port5_enabled, self.ui.port5_text,
                self.ui.sat5_name_text, None, None, self.ui.channel5_text, None]
        ]
        """ This array contains data as logfile's objects for each port
        """
        self.log_dict = [None, None, None, None, None]

        # Setup console output, emmit stdout
        sys.stdout = EmittingStream(textWritten = self.normal_output_written)

        # Read configuration from file
        self.read_settings()



    def read_settings(self):
        """ Read Configuration from document.

        Raises:
            Exception: an error occured accessing configuration file or tag name
        """
        try:
            dom = minidom.parse(os.path.split(os.path.realpath(__file__))[0] +"/settings.xml")
            domroot = dom.documentElement
            self.ui.name_text.setText(domroot.getElementsByTagName(
                'nickname')[0].childNodes[0].nodeValue)
            self.ui.long_text.setText(domroot.getElementsByTagName(
                'lon')[0].childNodes[0].nodeValue)
            self.ui.lat_text.setText(domroot.getElementsByTagName(
                'lat')[0].childNodes[0].nodeValue)
            self.ui.alt_text.setText(domroot.getElementsByTagName(
                'alt')[0].childNodes[0].nodeValue)
            self.ui.server_url_text.setText(domroot.getElementsByTagName(
                'server_url')[0].childNodes[0].nodeValue)
            self.ui.backup_server_url_text.setText(domroot.getElementsByTagName(
                'backup_server_url')[0].childNodes[0].nodeValue)
            self.ui.backup_enabled.setCheckState(int(domroot.getElementsByTagName(
                'back_server_enable')[0].childNodes[0].nodeValue))
            self.ui.server_port_text.setText(domroot.getElementsByTagName(
                'server_port')[0].childNodes[0].nodeValue)
            self.ui.tle_url_text.setText(domroot.getElementsByTagName(
                'tle_url')[0].childNodes[0].nodeValue)
            self.ui.port1_text.setText(domroot.getElementsByTagName(
                'port_1')[0].childNodes[0].nodeValue)
            self.ui.sat1_name_text.setText(domroot.getElementsByTagName(
                'port_1_sat')[0].childNodes[0].nodeValue)
            self.ui.channel1_text.setText(domroot.getElementsByTagName(
                'channel_1')[0].childNodes[0].nodeValue)
            self.ui.port1_enabled.setCheckState(int(domroot.getElementsByTagName(
                'port_1_enable')[0].childNodes[0].nodeValue))
            self.ui.port2_text.setText(domroot.getElementsByTagName(
                'port_2')[0].childNodes[0].nodeValue)
            self.ui.sat2_name_text.setText(domroot.getElementsByTagName(
                'port_2_sat')[0].childNodes[0].nodeValue)
            self.ui.channel2_text.setText(domroot.getElementsByTagName(
                'channel_2')[0].childNodes[0].nodeValue)
            self.ui.port2_enabled.setCheckState(int(domroot.getElementsByTagName(
                'port_2_enable')[0].childNodes[0].nodeValue))
            self.ui.port3_text.setText(domroot.getElementsByTagName(
                'port_3')[0].childNodes[0].nodeValue)
            self.ui.sat3_name_text.setText(domroot.getElementsByTagName(
                'port_3_sat')[0].childNodes[0].nodeValue)
            self.ui.channel3_text.setText(domroot.getElementsByTagName(
                'channel_3')[0].childNodes[0].nodeValue)
            self.ui.port3_enabled.setCheckState(int(domroot.getElementsByTagName(
                'port_3_enable')[0].childNodes[0].nodeValue))
            self.ui.port4_text.setText(domroot.getElementsByTagName(
                'port_4')[0].childNodes[0].nodeValue)
            self.ui.sat4_name_text.setText(domroot.getElementsByTagName(
                'port_4_sat')[0].childNodes[0].nodeValue)
            self.ui.channel4_text.setText(domroot.getElementsByTagName(
                'channel_4')[0].childNodes[0].nodeValue)
            self.ui.port4_enabled.setCheckState(int(domroot.getElementsByTagName(
                'port_4_enable')[0].childNodes[0].nodeValue))
            self.ui.port5_text.setText(domroot.getElementsByTagName(
                'port_5')[0].childNodes[0].nodeValue)
            self.ui.sat5_name_text.setText(domroot.getElementsByTagName(
                'port_5_sat')[0].childNodes[0].nodeValue)
            self.ui.channel5_text.setText(domroot.getElementsByTagName(
                'channel_5')[0].childNodes[0].nodeValue)
            self.ui.port5_enabled.setCheckState(int(domroot.getElementsByTagName(
                'port_5_enable')[0].childNodes[0].nodeValue))
        except Exception as error:
            print "[File] Configured file read failed. Error: " + str(error)
            pass


    def start_proxy(self):
        """ Start proxy.

        When user starts proxy, start_proxy checks all information where user input.
        If any input with type or range error, proxy will pop up
        alert for corresponding error and stop.

        Connection between GNU radio and the proxy must be Transmission Control Protocol(TCP).
        Connection between the proxy and server must be websocket.
        """
        if self.proxy_running == False:
            self.proxy_running = True;
            self.ui.start_proxy_button.setText("Stop Proxy")

            # Get log file
            for index in range(0, 5):
                self.log_dict[index] = open(os.path.split(os.path.realpath(__file__))[0]
                    + "/logs/Port" + str(index + 1) + "DownLink.log", 'a')

            #Get User Info
            self.usr_dict[0] = str(self.ui.name_text.text())
            self.usr_dict[1] = self.check_string_valid(self.ui.long_text.text(),
                "float", "Longitude")
            self.usr_dict[2] = self.check_string_valid(self.ui.alt_text.text(),
                "float", "Altitude")
            self.usr_dict[3] = self.check_string_valid(self.ui.lat_text.text(),
                "float", "Latitiude")

            # Get Server Info
            self.host = str(self.ui.server_url_text.text())
            self.host_back = str(self.ui.backup_server_url_text.text())
            self.backup_enable = self.ui.backup_enabled.isChecked()
            self.server_port = self.check_string_valid(self.ui.server_port_text.text(),
                "integer", "Server Port")

            # Get Port Info
            for index in range(0, 5):
                self.port_dict[index][5] = self.check_string_valid(self.port_dict[index][3].text()
                    if self.port_dict[index][2].isChecked() else None, "integer",
                    "Port " + str(index + 1))
                self.port_dict[index][6] = str(self.port_dict[index][4].text()
                    if self.port_dict[index][2].isChecked() else None)
                self.port_dict[index][8] = self.check_string_valid(self.port_dict[index][7].text(),
                    "integer", "Channel" + str(index + 1))
                if self.port_dict[index][8] != None:
                	if self.port_dict[index][8] > 9 or self.port_dict[index][8] < 0:
                		print("[Input] Channel" + str(index + 1) + " input can only write between 0 to 9")
                		self.input_error = True

            # Checking Input is correct or not
            if self.input_error:
                self.stop_proxy()
                return

            # Connect Proxy
            for index in range(0, 5):
                self.port_dict[index][0] = ProxyListenInterface("0.0.0.0",
                    self.port_dict[index][5], self.handle_func, None,
                    "Port " + str(index + 1)) if self.port_dict[index][5] else None

            self.web_socket = WebSocketClient(self.host + ":" + str(self.server_port), "Server")
            if self.backup_enable:
                    self.backup_web_socket = WebSocketClient(self.host_back + ":" + str(self.server_port),
                        "Backup server")

            # Start Proxy
            for index in range(0, 5):
                if self.port_dict[index][0]:
                    self.port_dict[index][0].start()

        else:
            self.stop_proxy()


    def save_settings(self):
        """ Save Configuration to document.
        """
        doc = Document()  # Create Dom Object

        settings = doc.createElement('settings') # Create Root Element
        doc.appendChild(settings)

        entry = doc.createElement("nickname")
        entry.appendChild(doc.createTextNode(str(self.ui.name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("lon")
        entry.appendChild(doc.createTextNode(str(self.ui.long_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("lat")
        entry.appendChild(doc.createTextNode(str(self.ui.lat_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("alt")
        entry.appendChild(doc.createTextNode(str(self.ui.alt_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("server_url")
        entry.appendChild(doc.createTextNode(str(self.ui.server_url_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("backup_server_url")
        entry.appendChild(doc.createTextNode(str(self.ui.backup_server_url_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("back_server_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.backup_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("server_port")
        entry.appendChild(doc.createTextNode(str(self.ui.server_port_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("tle_url")
        entry.appendChild(doc.createTextNode(str(self.ui.tle_url_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_1")
        entry.appendChild(doc.createTextNode(str(self.ui.port1_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_1_sat")
        entry.appendChild(doc.createTextNode(str(self.ui.sat1_name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("channel_1")
        entry.appendChild(doc.createTextNode(str(self.ui.channel1_text.text())))
        settings.appendChild(entry)


        entry = doc.createElement("port_1_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.port1_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("port_2")
        entry.appendChild(doc.createTextNode(str(self.ui.port2_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_2_sat")
        entry.appendChild(doc.createTextNode(str(self.ui.sat2_name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("channel_2")
        entry.appendChild(doc.createTextNode(str(self.ui.channel2_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_2_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.port2_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("port_3")
        entry.appendChild(doc.createTextNode(str(self.ui.port3_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_3_sat")
        entry.appendChild(doc.createTextNode(str(self.ui.sat3_name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("channel_3")
        entry.appendChild(doc.createTextNode(str(self.ui.channel3_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_3_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.port3_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("port_4")
        entry.appendChild(doc.createTextNode(str(self.ui.port4_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_4_sat")
        entry.appendChild(doc.createTextNode(str(self.ui.sat4_name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("channel_4")
        entry.appendChild(doc.createTextNode(str(self.ui.channel4_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_4_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.port4_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("port_5")
        entry.appendChild(doc.createTextNode(str(self.ui.port5_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_5_sat")
        entry.appendChild(doc.createTextNode(str(self.ui.sat5_name_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("channel_5")
        entry.appendChild(doc.createTextNode(str(self.ui.channel5_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("port_5_enable")
        entry.appendChild(doc.createTextNode(str(self.ui.port5_enabled.checkState())))
        settings.appendChild(entry)

        # Write Dom Object into file
        f = open(os.path.split(os.path.realpath(__file__))[0] +'/settings.xml','w')
        f.write(doc.toprettyxml(indent = ''))
        f.close()
        print "[File] Configuration saved successfully."


    def exit(self):
        """ Exit proxy by exit button.

        Stop all connections before exit, including multithreading and coroutine.
        Alert a message to user.
        """
        if self.proxy_running:
            msgBox = QtGui.QMessageBox(text="Proxy is still running, stopping now...")
            msgBox.setWindowModality(QtCore.Qt.NonModal)
            msgBox.setStandardButtons(QtGui.QMessageBox.Close)
            ret = msgBox.exec_()
            self.proxy_running = False
            self.stop_proxy()
            self.thread.join()
            self.close()
        self.close()


    def closeEvent(self, event):
        """ Exit proxy by title bar exit.

        Same feature as exit() function.
        """
        self.exit()
        event.accept()


    def update_orbit(self):
        """ Update orbit for proxy

        Raises:
            Exception: an error occured accessing tle file or grc_param.py
        """
        try:
            f = urllib2.urlopen(str(self.ui.tle_url_text.text()))
            tle = f.read()
            tle = tle.split("\n")

            tle1 = tle[1]
            tle2 = tle[2]

            with open(os.path.split(os.path.realpath(__file__))[0] + "/grc_param.py", 'w') as fp:
                fp.write("lat=" + str(self.ui.lat_text.text()) + "\n")
                fp.write("lon=" + str(self.ui.long_text.text()) + "\n")
                fp.write("alt=" + str(self.ui.alt_text.text()) + "\n")
                fp.write("tle_line1=\"" + tle1 + "\"\n")
                fp.write("tle_line2=\"" + tle2 + "\"\n")
                fp.close()

            print "[Orbit] Orbit Data updated successfully!"

        except Exception as msg:
            print msg


    def handle_func_kiss(self, name, data):
        """ Callback function after kiss decode.

        Send json data when the first data received.
        """

        # Handle Json data
        port_index = 0
        for index in range(0, 5):
        	if(name.find(str(index  + 1)) > -1):
        		port_index = index
        http_data = {
        	'sat_name': str(self.port_dict[port_index][4].text()),
        	'physical_channel': self.port_dict[port_index][8],
            'proxy_nickname': self.usr_dict[0],
            'proxy_long': self.usr_dict[1],
            'proxy_alt': self.usr_dict[2],
            'proxy_lat': self.usr_dict[3],
            'raw_data': codecs.encode(data, 'hex'),
            'proxy_receive_time': int(time.time()*1000)
        }

        # Web Socket sending
        self.web_socket.send(json.dumps(http_data))
        if self.ui.backup_enabled.isChecked():
            self.backup_web_socket.send(json.dumps(http_data))
        self.save_log(http_data, name)


    def save_log(self, data, name):
        """ Save log file and print log on console.
        """
        # Log recording
        for index in range(0, 5):
            if(name.find(str(index  + 1)) > -1):
                self.log_dict[index].write("Timestamp: " + datetime.datetime.utcfromtimestamp(
                    float(data['proxy_receive_time']/1000)).strftime('%Y-%m-%d %H:%M:%S') + "\n")
                self.log_dict[index].write("Nickname: " + self.usr_dict[0].replace("\x00", "") + "\n")
                self.log_dict[index].write("Satname: " + str(data['sat_name']) + "\n")
                self.log_dict[index].write("Longitude: " + str(self.usr_dict[1]) + "\n")
                self.log_dict[index].write("Altitude: " + str(self.usr_dict[2]) + "\n")
                self.log_dict[index].write("Latitiude: " + str(self.usr_dict[3]) + "\n")
                count = 0
                log = ""
                for i in codecs.decode(data['raw_data'], 'hex'):
                	log += "%02X"%ord(i) + " "
                	count += 1
                self.log_dict[index].write("Data: " + log + "\n\n")
                print "[Data] Received time is " + datetime.datetime.utcfromtimestamp(
                    float(data['proxy_receive_time']/1000)).strftime('%Y-%m-%d %H:%M:%S')
                print "Data is: " + log + "\n" + "Data Length is: " + str(count)
                self.log_dict[index].flush()


    def handle_func(self, caller, name, data):
        """ Callback function when proxy received data from GNU radio.
        """
        self.kiss_decoder.AppendStream(name, data)


    def stop_proxy(self):
        """ Stop proxy.
        """
        self.ui.start_proxy_button.setEnabled(False)
        self.ui.start_proxy_button.setText("Stopping...")

        # Close port listener
        for port in self.port_dict:
            if port[0]:
                port[0].stop()

        for port in self.port_dict:
            while (port[0] and port[0].isAlive()):
                    time.sleep(0.2)

        # Close websocket
        if self.web_socket:
            self.web_socket.stop()
        if self.backup_web_socket:
            self.backup_web_socket.stop()

        self.ui.start_proxy_button.setEnabled(False)
        self.input_error = False
        self.proxy_running = False
        self.ui.start_proxy_button.setText("Start Proxy")
        self.ui.start_proxy_button.setEnabled(True)


    def check_string_valid(self, line_text, n_type, position):
        """ Check user input format.

        Float type for altitude, longitude and altitude.
        Int type for port number and channel number.
        """
        if line_text is None:
            return None
        else:
            try:
                if n_type == "float":
                    return float(line_text)
                elif n_type == "integer":
                    return int(line_text)
            except Exception:
                self.input_error = True;
                # Tell user which input is not correct
                print("[Input] " + position + " input can only be a " + n_type)
                return None


    def normal_output_written(self, text):
        """ Initial output console length and buffer.
        """
        # Append text to the QTextEdit.
        str_buf = self.ui.log_text.toPlainText()
        str_buf = str_buf + text
        length = str_buf.count()

        maxLength = 3000
        if(length > maxLength):
            str_buf.remove(0, length - maxLength);

        self.ui.log_text.setText(str_buf);
        textCursor = self.ui.log_text.textCursor();
        self.ui.log_text.setText(str_buf);
        textCursor.setPosition(str_buf.count());
        self.ui.log_text.setTextCursor(textCursor);


    def on_timer(self):
        """ Set up timer to refresh time.
        """
        for i in range(0,5):
            self.set_port_status(i)
        if self.web_socket != None and self.web_socket.is_alive():
            self.color_set = "color:green"
            self.ui.server_status.setText("Connected")
        else:
            self.color_set = "color:red"
            self.ui.server_status.setText("Not connected")
        self.ui.server_status.setStyleSheet(self.color_set)
        if self.backup_web_socket != None:
            if self.backup_web_socket.is_alive():
                self.color_set = "color:green"
                self.ui.backup_server_status.setText("Connected")
            else:
                self.color_set = "color:red"
                self.ui.backup_server_status.setText("Not connected")
        else:
            if self.ui.backup_enabled.isChecked():
                self.color_set = "color:red"
                self.ui.backup_server_status.setText("Not connected")
            else:
                self.color_set = "color:grey"
                self.ui.backup_server_status.setText("Disabled")
        self.ui.backup_server_status.setStyleSheet(self.color_set)


    def set_port_status(self, index):
        """ Set port and server status for user.

        The status includes disabled, not connected and connected.
        """
        if self.port_dict[index][0] != None:
            if self.port_dict[index][0].StateNow == 2 and self.port_dict[index][0].isAlive():
                self.color_set = "color:green"
                self.port_dict[index][1].setText("Connected")
            elif self.port_dict[index][2].isChecked():
                self.color_set = "color:red"
                self.port_dict[index][1].setText("Not connected")
            else:
                self.color_set = "color:grey"
                self.port_dict[index][1].setText("Disabled")
        else:
            if self.port_dict[index][2].isChecked():
                self.color_set = "color:red"
                self.port_dict[index][1].setText("Not connected")
            else:
                self.color_set = "color:grey"
                self.port_dict[index][1].setText("Disabled")
        self.port_dict[index][1].setStyleSheet(self.color_set)


    def link_hit(self):
        """ Link to hit official website.
        """
        webbrowser.open("http://www.hit.edu.cn")


    def link_by2hit(self):
        """ Link to by2hit official website.
        """
        webbrowser.open("http://www.by2hit.net")


    def link_lilac(self):
        """ Link to lilacsat official website.
        """
        webbrowser.open("http://lilacsat.hit.edu.cn")


    def popup_about(self):
        """ pop up proxy infomation messagebox.
        """
        msg = QtGui.QMessageBox()
        # msg.setStyleSheet("min-width: 128px;min-height: 76px")
        msg.setText("Mun Downlink Proxy\n\nVersion 1.0\n")
        myPixmap = QtGui.QPixmap(QtCore.QString.fromUtf8("logo/mun.png"))
        myScaledPixmap = myPixmap.scaled(msg.size()/2, QtCore.Qt.KeepAspectRatio)
        msg.setIconPixmap(myScaledPixmap)
        msg.setInformativeText("This software was made by myrfy, LinerSu and LucyWang.")
        msg.setWindowTitle("About Mun Downlink Proxy")
        retval = msg.exec_()



class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))



class MyThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)


    def run(self):
        tornado.ioloop.IOLoop.current().start()


    def join(self):
        tornado.ioloop.IOLoop.current().stop()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MainWindow()
    myapp.show()
    sys.exit(app.exec_())
