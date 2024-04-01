#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""Implementation of the proxy for XXXX

`XXXX proxy <url git>`_ allow for tcp protocol
communication between GNU Radio and the proxy,
and allow for bidirectional communication
between the proxy and tornado server.

Proxy is supported in the current versions of GNU Radio
and tornado server.


.. version:: 1.0
.. author:: myrfy, LinerSu, LucyWang, 3#
"""

import sys
import os
import time
import codecs
import datetime
import xml.dom.minidom as minidom
import pickle
# import urllib2
import requests

import PyQt5
from PyQt5 import QtCore, QtWidgets
from PyQt5 import QtWidgets as QtGui
from PyQt5.QtCore import QCoreApplication

from Qt.MiniWindow import MiniWindow
from Qt.Settings import Settings
# import ui confige
from ui.proxy_ui import Ui_MainWindow

from xml.dom.minidom import Document

# confige data
from core.data import server_data
from core.data import port_data
from core.data import DataBuf
# connector
from core.connection_to_grc import LinkToGRC
from core.connection_to_server_websocket_3 import WebSocketClient
from core.connection_to_server_websocket_3 import Websocket_send_thread
from core.connection_to_server_socket import SocketSender

# processor
from process.show_link import link_processor
from process.send_msg import sender


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()

        # 为了使用websocket， 先要启动Websocket_send_thread线程
        # Setup thread for tornado application
        self.thread = []

        # setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # setup processor
        self.show_link = link_processor()
        self.sender = sender()

        # -------------------data-------------
        # time count, 给 on_timer 使用
        self.time_count = 0
        # server data
        self.servers = server_data()
        # port data
        self.ports = port_data()
        # data_buffer
        self.data_buffer_list = list()
        for i in range(5):
            self.data_buffer_list.append(DataBuf('Port' + str(i + 1)))
            self.data_buffer_list[i].set_logger(self.save_log)
        # ----------------连接------------------
        self.socket_to_grc_list = list()
        self.websocket_to_server = list()
        self.socket_to_server = list()

        self.host_back = None
        self.server_port = None
        self.web_socket = None
        self.backup_web_socket = None
        self.proxy_running = False
        self.input_error = False
        # self.kiss_decoder = KISS_Decoder(self.handle_func_kiss)

        # Setup Dict
        """ This array contains data as follow:
            name  long  alt   lat
        """
        self.usr_dict = [None, None, None, None]
        """ This array contains data as logfile's objects for each port
        """
        self.log_dict = [None, None, None, None, None]

        # --------------confige------------------------------
        # 输入控制, 经度纬度海拔只能是浮点型.
        self.ui.lat_text.setValidator(PyQt5.QtGui.QDoubleValidator())
        self.ui.long_text.setValidator(PyQt5.QtGui.QDoubleValidator())
        self.ui.alt_text.setValidator(PyQt5.QtGui.QDoubleValidator())

        # --------------端口列表----------------
        self.ui.port_list.setColumnCount(6)
        self.ui.port_list.setRowCount(5)
        # 添加表头
        self.ui.port_list.setHorizontalHeaderLabels([
            'GRC Port', '  Satellite  ', 'Channel', 'Server', 'Protocol',
            'Enable'
        ])
        # 添加列头
        self.ui.port_list.setVerticalHeaderLabels(
            ['Port 1', 'Port 2', 'Port 3', 'Port 4', 'Port 5'])
        self.ui.port_list.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectRows)  # 一次选中一行

        # grc port select
        self.grc_port_list = list()
        for each in range(5):
            self.grc_port_list.append(QtGui.QSpinBox())
            self.grc_port_list[each].setRange(1001, 65535)
            self.ui.port_list.setCellWidget(each, 0, self.grc_port_list[each])
        # sat_name
        self.sat_name_list = list()
        for each in range(5):
            self.sat_name_list.append(QtGui.QLineEdit())
            self.sat_name_list[each].setMaximumSize(QtCore.QSize(82, 29))
            self.ui.port_list.setCellWidget(each, 1, self.sat_name_list[each])
        # channel
        self.channel_list = list()
        for each in range(5):
            self.channel_list.append(QtGui.QSpinBox())
            self.channel_list[each].setRange(0, 10)
            self.ui.port_list.setCellWidget(each, 2, self.channel_list[each])
        # 服务器列表选择
        self.server_port_list = list()
        for each in range(5):
            self.server_port_list.append(QtGui.QComboBox())
            self.ui.port_list.setCellWidget(each, 3,
                                            self.server_port_list[each])
        # 协议选择
        self.protocol_list = list()
        for each in range(5):
            cbox = QtGui.QComboBox()
            cbox.addItems(['websocket', 'socket', 'HTY'])
            self.protocol_list.append(cbox)
            self.ui.port_list.setCellWidget(each, 4, self.protocol_list[each])
        # proxy 使能选择
        self.enable_port_list = list()
        for each in range(5):
            self.enable_port_list.append(QtGui.QCheckBox())
            self.ui.port_list.setCellWidget(each, 5,
                                            self.enable_port_list[each])
        self.ui.port_list.resizeColumnsToContents()  # 自动列宽
        self.ui.port_list.resizeRowsToContents()  # 自动行宽
        # 端口状态标签
        self.port_status_list = list()
        self.port_status_list.append(self.ui.port1_status)
        self.port_status_list.append(self.ui.port2_status)
        self.port_status_list.append(self.ui.port3_status)
        self.port_status_list.append(self.ui.port4_status)
        self.port_status_list.append(self.ui.port5_status)

        # -------------按钮功能绑定---------------
        self.ui.new_server.clicked.connect(self.new_server)
        self.ui.del_server.clicked.connect(self.del_server)
        # Button initial
        self.ui.start_proxy_button.clicked.connect(self.start_proxy)
        self.ui.save_config_button.clicked.connect(self.save_settings)
        self.ui.exit_button.clicked.connect(self.exit)
        self.ui.update_button.clicked.connect(self.update_orbit)
        self.ui.about_button.clicked.connect(self.show_link.popup_about)
        self.ui.by2hit_logo.clicked.connect(self.show_link.link_by2hit)
        self.ui.hit_logo.clicked.connect(self.show_link.link_hit)
        self.ui.lilacsat_logo.clicked.connect(self.show_link.link_lilac)
        self.ui.send_msg_button.clicked.connect(
            lambda: self.sender.send_msg(self.ui.send_msg.text()))
        self.ui.server_list.itemDoubleClicked.connect(self.edit_server)
        self.ui.set_time.clicked.connect(self.set_time)
        # Initial refresh time for signal
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.on_timer)
        self.refresh_timer.start(500)

        # Setup console output, emmit stdout
        sys.stdout = EmittingStream(textWritten=self.normal_output_written)
        # read settings after init
        self.read_settings()

    # ------------ 召唤出小窗按钮函数 ------------
    def new_server(self):
        # 输入小窗
        self.new_server_window = MiniWindow(self.servers, self, None)
        self.new_server_window.show()

    def del_server(self):
        index = self.ui.server_list.currentRow()
        if index != -1:  # 是否选中了一个项目
            text = str(self.ui.server_list.item(index).text())

            name = text[:text.find('-->')]
            self.servers.del_server(name)
            self.ui.server_list.takeItem(self.ui.server_list.currentRow())
            # self.servers.del_server(name)
            self.refresh_combo_box()

    def edit_server(self):
        text = str(self.ui.server_list.currentItem().text())
        name = text[:text.find('-->')]
        server = self.servers.select_server(name)
        server.append(name)
        self.servers.del_server(name)
        self.ui.server_list.takeItem(self.ui.server_list.currentRow())
        self.new_server_window = MiniWindow(self.servers, self, server)
        self.new_server_window.show()

    #  ------------更新数据--------------
    def refresh_port_data(self):
        '''
        当proxy启动时，刷新数据
        '''
        for i in range(5):
            self.ports.change_data(i, self.grc_port_list[i].value(),
                                   str(self.sat_name_list[i].text()),
                                   self.channel_list[i].value(),
                                   str(self.server_port_list[i].currentText()),
                                   str(self.protocol_list[i].currentText()),
                                   self.enable_port_list[i].isChecked())

    def add_to_list(self, name):
        '''
        @ 添加服务器项目
        '''
        server = self.servers.select_server(str(name))
        server_conf = (
            str(name) + "-->" + str(server[0]) + ':' + str(server[1]))
        if server[2]:
            server_conf = server_conf + " kiss:" + 'enable'
        else:
            server_conf = server_conf + " kiss:" + 'disable'
        self.ui.server_list.addItem(server_conf)
        self.refresh_combo_box()

    def refresh_combo_box(self):
        '''
        @ 刷新全部下拉菜单内容
        '''
        servers = self.servers.show_all_names()
        for port in self.server_port_list:
            port.clear()
            port.addItems(servers)

    # --------- 配置文件操作-----------
    def read_settings(self):
        """ Read Configuration from document.

        Raises:
            Exception:
                an error occured accessing configuration file or tag name
        """
        try:
            setting_path = os.path.split(os.path.realpath(__file__))[0] + "/../settings/settings.xml"
            if not os.path.exists(setting_path):
                print("No setting file found!")
                return
            dom = minidom.parse(setting_path)
            domroot = dom.documentElement
            self.ui.name_text.setText(
                domroot.getElementsByTagName('nickname')[0].childNodes[0]
                .nodeValue)
            self.ui.long_text.setText(
                domroot.getElementsByTagName('lon')[0].childNodes[0].nodeValue)
            self.ui.lat_text.setText(
                domroot.getElementsByTagName('lat')[0].childNodes[0].nodeValue)
            self.ui.alt_text.setText(
                domroot.getElementsByTagName('alt')[0].childNodes[0].nodeValue)
            self.ui.backup_server_url_text.setText(
                domroot.getElementsByTagName('backup_server_url')[0]
                .childNodes[0].nodeValue)
            self.ui.backup_enabled.setCheckState(
                int(
                    domroot.getElementsByTagName('back_server_enable')[0]
                    .childNodes[0].nodeValue))
            self.ui.tle_url_text.setText(
                domroot.getElementsByTagName('tle_url')[0].childNodes[0]
                .nodeValue)
            # read the servers settings
            f = open(
                os.path.split(os.path.realpath(__file__))[0] +
                '/../settings/server_settings.dat', 'rb')
            self.servers = pickle.load(f)
            f.close()
            # read the ports settings
            f = open(
                os.path.split(os.path.realpath(__file__))[0] +
                '/../settings/port_settings.dat', 'rb')
            self.ports = pickle.load(f)
            f.close()
            self.reload()
        except Exception as error:
            print("[File] Configured file read failed. Error: " + str(error))

    def reload(self):
        '''
            在read_server 执行后，更新界面数据
            在servers 与 ports 更新后刷新页面
        '''
        # 刷新服务器列表
        for each in self.servers.show_all_names():
            self.add_to_list(each)
        self.refresh_combo_box()  # 刷新选择框数据

        # 刷新右侧端口表格
        for i in range(5):  # 刷新grc端口
            item = self.ports.return_data('port')[i]
            self.grc_port_list[i].setValue(item)
        for i in range(5):  # satellite_name
            item = self.ports.return_data('satellite')[i]
            self.sat_name_list[i].setText(item)
        for i in range(5):  # channel
            item = self.ports.return_data('channel')[i]
            self.channel_list[i].setValue(item)
        for i in range(5):  # server
            item = self.ports.return_data('server')[i]
            index = self.server_port_list[i].findText(
                item, QtCore.Qt.MatchFixedString)
            self.server_port_list[i].setCurrentIndex(index)
        for i in range(5):  # protocol
            item = self.ports.return_data('protocol')[i]
            index = self.protocol_list[i].findText(item,
                                                   QtCore.Qt.MatchFixedString)
            self.protocol_list[i].setCurrentIndex(index)
        for i in range(5):  # enable
            item = self.ports.return_data('enable')[i]
            if item:
                self.enable_port_list[i].nextCheckState()

    def save_settings(self):
        """ Save Configuration to document.
        """
        self.refresh_port_data()  # 刷新ports输入的数据

        doc = Document()  # Create Dom Object

        settings = doc.createElement('settings')  # Create Root Element
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
        # -------- for servers' setting---------
        # save server data
        f = open(
            os.path.split(os.path.realpath(__file__))[0] +
            '/../settings/server_settings.dat', 'wb')
        pickle.dump(self.servers, f)
        f.close()

        entry = doc.createElement("backup_server_url")
        entry.appendChild(
            doc.createTextNode(str(self.ui.backup_server_url_text.text())))
        settings.appendChild(entry)

        entry = doc.createElement("back_server_enable")
        entry.appendChild(
            doc.createTextNode(str(self.ui.backup_enabled.checkState())))
        settings.appendChild(entry)

        entry = doc.createElement("tle_url")
        entry.appendChild(doc.createTextNode(str(self.ui.tle_url_text.text())))
        settings.appendChild(entry)
        # ---------- for server_ports' setting --------
        # save port data
        f = open(
            os.path.split(os.path.realpath(__file__))[0] +
            '/../settings/port_settings.dat', 'wb')
        pickle.dump(self.ports, f)
        f.close()
        # Write Dom Object into file
        f = open(
            os.path.split(os.path.realpath(__file__))[0] +
            '/../settings/settings.xml', 'w')
        f.write(doc.toprettyxml(indent=''))
        f.close()
        print("[File] Configuration saved successfully.")

    # ------------- 启动/停止链接---------
    def start_proxy(self):
        """ Start proxy.

        When user starts proxy,
        -start_proxy checks all information where user input.
        -If any input with type or range error, proxy will pop up
        alert for corresponding error and stop.

        -Connection between GNU radio and the proxy must be
        Transmission Control Protocol(TCP).
        -Connection between the proxy and server must be websocket.
        """
        # to get server status
        self.time_count = 20
        # get port setting data
        self.refresh_port_data()
        # start proxy
        if not self.proxy_running:
            self.proxy_running = True
            self.ui.start_proxy_button.setText("Stop Proxy")

            # Get log file
            '''
                log_dict 是一个文件对象list
            '''
            for index in range(0, 5):
                self.log_dict[index] = open(
                    os.path.split(os.path.realpath(__file__))[0] + "/../logs/Port"
                    + str(index + 1) + "DownLink.log", 'a')

            # Get User Info
            try:
                self.usr_dict[0] = str(self.ui.name_text.text())
                self.usr_dict[1] = float(self.ui.long_text.text())
                self.usr_dict[2] = float(self.ui.alt_text.text())
                self.usr_dict[3] = float(self.ui.lat_text.text())
            except ValueError:
                self.usr_dict[0] = ''
                self.usr_dict[1] = 0.0
                self.usr_dict[2] = 0.0
                self.usr_dict[3] = 0.0

            # Get backup Server Info
            self.host_back = str(self.ui.backup_server_url_text.text())
            self.backup_enable = self.ui.backup_enabled.isChecked()

            # Get Port Info

            # Checking Input is correct or not

            # listen to GRC
            enable_server = self.ports.get_enabled()
            '''
            因为此处要求，如果配置时选择监听同一个端口，
            数据将发送至不同的服务器，所以
            LinkToGRC中data_buffer为list
            这里需要对端口进行逻辑判断
            '''
            for server in enable_server:
                port = server['port']
                index = server['port_num']
                is_exist = False
                exist_index = None
                # 下面一个循环用于遍历所有的GRC Listener， 如果监听的端口已经出现，则is_exist = True
                # exist_index 为已经启动监听的端口
                for link in self.socket_to_grc_list:
                    if port == link.get_port():
                        is_exist = True
                        exist_index = link.get_index()
                        break
                if not is_exist:
                    self.socket_to_grc_list.append(
                        LinkToGRC([
                            self.data_buffer_list[index],
                        ], '0.0.0.0', port, index))
                else:
                    # 增加收到的队列
                    for each in self.socket_to_grc_list:
                        if exist_index == each.get_index():
                            each.append_data_buf(self.data_buffer_list[index])

            # 设置kiss decode
            for each in enable_server:
                server_name = each['server']
                index = each['port_num']
                kiss_status = self.servers.select_server(server_name)[2]
                self.data_buffer_list[index].set_kiss_decode_mode(kiss_status)

            # 设置输出包内容
            for each in self.ports.get_enabled():
                http_data = {
                    'sat_name': str(each['satellite']),
                    'physical_channel': each['channel'],
                    'proxy_nickname': self.usr_dict[0],
                    'proxy_long': self.usr_dict[1],
                    'proxy_alt': self.usr_dict[2],
                    'proxy_lat': self.usr_dict[3]
                }
                self.data_buffer_list[each['port_num']].set_info(http_data)

            # 启动GRC 接收线程
            for sock in self.socket_to_grc_list:
                sock.start()

            # Start Proxy to server
            for each in self.ports.get_enabled():
                if each['protocol'] == 'websocket':
                    # 启动websocket连接
                    server_name = each['server']
                    server = self.servers.select_server(server_name)
                    if_new_server = True
                    connection = None
                    # 遍历websocket列表，如果存在
                    for ws in self.websocket_to_server:
                        if ws.get_name() == server_name:
                            # 已经存在的服务连接
                            if_new_server = False
                            connection = ws
                            break
                    if if_new_server:
                        # 需要新建服务连接
                        url = 'ws://' + server[0] + ':' + str(server[1])
                        connection = WebSocketClient(url, server_name)
                        self.websocket_to_server.append(connection)
                        t = Websocket_send_thread(connection)
                        self.thread.append(t)
                        t.start()
                    # 没一个dataBuf 都需要  sender ，所以有重复的服务器也需要添加sender
                    self.data_buffer_list[each['port_num']].set_sender(
                        connection)

                elif each['protocol'] == 'socket':
                    # 启动socket连接
                    server = self.servers.select_server(each['server'])
                    host = server[0]
                    port = server[1]
                    sk = SocketSender('Port' + str(each['port_num'] + 1),
                                      'socket')
                    sk.create_connection(host, port)
                    sk.start()  # 启动连接
                    self.data_buffer_list[each['port_num']].set_sender(sk)
                    self.socket_to_server.append(sk)
                elif each['protocol'] == 'HTY':
                    # TODO  准备加入临时测试功能
                    # 启动HTY连接
                    server = self.servers.select_server(each['server'])
                    host = server[0]
                    port = server[1]
                    sk = SocketSender('Port' + str(each['port_num'] + 1),
                                      'HTY')
                    sk.create_connection(host, port)
                    sk.start()  # 启动连接
                    self.data_buffer_list[each['port_num']].set_sender(sk)
                    self.socket_to_server.append(sk)
            # set msg sender
            # 使用名为 DSLWP 的服务器
            connection = None
            for ws in self.websocket_to_server:
                if ws.get_name() == 'DSLWP':
                    connection = ws
                    break
            self.sender.set_info(self.usr_dict)
            self.sender.set_time_obj(self.ui.send_msg_time)
            self.sender.set_sender(connection)

        else:
            self.stop_proxy()

    def stop_proxy(self):
        """ Stop proxy.
        """
        # TODO 这个还不好使GG
        self.ui.start_proxy_button.setText("Stopping...")
        self.ui.start_proxy_button.setEnabled(False)

        # Close port listener
        for sock in self.socket_to_grc_list:
            sock.stop()

        # wait for closing
        for sock in self.socket_to_grc_list:
            while sock.is_alive():
                time.sleep(0.2)
        # remove proxy obj
        self.socket_to_grc_list = list()

        # Close websocket
        for each in self.websocket_to_server:
            each.stop()

        # Close socket
        for each in self.socket_to_server:
            each.stop()
        '''
        if self.backup_web_socket:
            self.backup_web_socket.stop()
        '''
        self.proxy_running = False
        self.ui.start_proxy_button.setText("Start Proxy")
        self.ui.start_proxy_button.setEnabled(True)

    def exit(self, ignore):
        """ Exit proxy by exit button.

        Stop all connections before exit, including multithreading
        and coroutine.
        Alert a message to user.
        """
        if self.proxy_running:
            msgBox = QtGui.QMessageBox(
                text="Proxy is still running, stopping now...")
            msgBox.setWindowModality(QtCore.Qt.NonModal)
            msgBox.setStandardButtons(QtGui.QMessageBox.Close)
            ret = msgBox.exec_()
            self.proxy_running = False
            self.stop_proxy()
            for each in self.thread:
                each.stop()
                each.join()
            # self.close()
        if not ignore:
            self.close()

    def closeEvent(self, event):
        """ Exit proxy by title bar exit.

        Same feature as exit() function.
        """
        self.exit(True)
        QCoreApplication.instance().quit()


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

            with open(
                    os.path.split(os.path.realpath(__file__))[0] +
                    "/grc_param.py", 'w') as fp:
                fp.write("lat=" + str(self.ui.lat_text.text()) + "\n")
                fp.write("lon=" + str(self.ui.long_text.text()) + "\n")
                fp.write("alt=" + str(self.ui.alt_text.text()) + "\n")
                fp.write("tle_line1=\"" + tle1 + "\"\n")
                fp.write("tle_line2=\"" + tle2 + "\"\n")
                fp.close()

            print("[Orbit] Orbit Data updated successfully!")

        except Exception as msg:
            print(msg)

    def save_log(self, data, name):
        """ Save log file and print log on console.
        """
        # Log recording
        for index in range(0, 5):
            if (name.find(str(index + 1)) > -1):
                self.log_dict[index].write(
                    "Timestamp: " + datetime.datetime.utcfromtimestamp(
                        float(data['proxy_receive_time'] /
                              1000)).strftime('%Y-%m-%d %H:%M:%S') + "\n")
                self.log_dict[index].write(
                    "Nickname: " + self.usr_dict[0].replace("\x00", "") + "\n")
                self.log_dict[index].write("Satname: " +
                                           str(data['sat_name']) + "\n")
                self.log_dict[index].write("Longitude: " +
                                           str(self.usr_dict[1]) + "\n")
                self.log_dict[index].write("Altitude: " +
                                           str(self.usr_dict[2]) + "\n")
                self.log_dict[index].write("Latitiude: " +
                                           str(self.usr_dict[3]) + "\n")
                count = 0
                log = ""
                for i in codecs.decode(data['raw_data'], 'hex'):
                    log += format(i, '02X') + " "
                    count += 1
                self.log_dict[index].write("Data: " + log + "\n\n")
                print("[Data] Received time is " +
                      datetime.datetime.utcfromtimestamp(
                          float(data['proxy_receive_time'] /
                                1000)).strftime('%Y-%m-%d %H:%M:%S'))
                print(
                    "Data is: " + log + "\n" + "Data Length is: " + str(count))
                self.log_dict[index].flush()

    def normal_output_written(self, text):
        """ Initial output console length and buffer.
        """
        # Append text to the QTextEdit.
        str_buf = self.ui.log_text.toPlainText()
        str_buf = str_buf + text
        length = len(str_buf)

        maxLength = 30000
        if (length > maxLength):
            str_buf = str_buf[maxLength:]

        self.ui.log_text.setText(str_buf)
        textCursor = self.ui.log_text.textCursor()
        self.ui.log_text.setText(str_buf)
        textCursor.setPosition(len(str_buf))
        self.ui.log_text.setTextCursor(textCursor)

    def on_timer(self):
        """ Set up timer to refresh time.
        """
        status = -1
        enabled_list = list()
        for each in self.socket_to_grc_list:
            enabled_list.append(each.get_index())
        index = 0
        for i in range(0, 5):
            if i in enabled_list:
                if self.socket_to_grc_list[index].is_connected:
                    self.set_port_status(i, 'Connected')
                else:
                    self.set_port_status(i, 'Not connected')
                index += 1
            else:
                self.set_port_status(i, 'disabled')
        if self.proxy_running is False:
            server_names = list()
            for ws in self.websocket_to_server:
                server_names.append(ws.get_name())
            for name in server_names:
                self.set_server_status(name, 'Disable')
        elif self.time_count == 20:
            # 10s
            # 更新服务器信息
            self.time_count = 0
            server_names = list()
            for ws in self.websocket_to_server:
                server_names.append(ws.get_name())
            for name in server_names:
                server = self.servers.select_server(name)
                # server[0] is server address
                url = "http://" + server[0] + ':' + str(server[1])
                for each in self.websocket_to_server:
                    if name == each._name:
                        status = (0 if each.connected else 1)
                        break
                # response = requests.get(url=url, timeout=0.2)
                # if response.text == 'Can "Upgrade" only to "WebSocket".':
                #     status = 0
                # # status == 0 is OK!
                if status == 0:
                    self.set_server_status(name, 'Connected')
                else:
                    self.set_server_status(name, 'Not connected')

        self.time_count += 1

    def set_port_status(self, index, status):
        """ Set port and server status for user.

        The status includes disable, not connected and connected.
        """
        if status == 'Connected':
            self.port_status_list[index].setText("Connected")
            self.port_status_list[index].setStyleSheet("color:green")
        elif status == 'Not connected':
            self.port_status_list[index].setText("Not connected")
            self.port_status_list[index].setStyleSheet("color:red")

        elif status == 'disabled':
            self.port_status_list[index].setText("disabled")
            self.port_status_list[index].setStyleSheet("color:grey")

    def set_server_status(self, name, status):
        # get qlistwightitem with name
        items = self.ui.server_list.findItems(name, QtCore.Qt.MatchContains)
        item = items[0]
        # refresh status
        if status == 'Connected':
            item.setBackground(PyQt5.QtGui.QColor('green'))
            item.setForeground(PyQt5.QtGui.QColor('white'))
        elif status == 'Not connected':
            item.setBackground(PyQt5.QtGui.QColor('red'))
            item.setForeground(PyQt5.QtGui.QColor('white'))
        elif status == 'Disable':
            item.setBackground(PyQt5.QtGui.QColor('white'))
            item.setForeground(PyQt5.QtGui.QColor('black'))

    def set_time(self):
        now_time = QtCore.QDateTime.currentDateTime()
        now_time = now_time.toUTC()
        self.ui.send_msg_time.setDateTime(now_time)


class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))


