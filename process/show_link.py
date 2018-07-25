# coding:utf-8
'''
用于处理proxy底部链接显示
'''
import webbrowser
from PyQt4 import QtGui, QtCore


class link_processor(object):
    '''
    显示链接的方法
    '''

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
        myScaledPixmap = myPixmap.scaled(msg.size() / 2,
                                         QtCore.Qt.KeepAspectRatio)
        msg.setIconPixmap(myScaledPixmap)
        msg.setInformativeText(
            "This software was made by myrfy, LinerSu and LucyWang.")
        msg.setWindowTitle("About Mun Downlink Proxy")
        msg.exec_()
