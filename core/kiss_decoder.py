# coding:utf-8
'''
@ 用于KISS解码功能
KISS 协议 数据包以C0开头 ，以C0结尾
当数据中有C0时， 以 DB DC替换
当数据中有DB时， 以 DB DD替换
'''
KISS_FEND = int.from_bytes(b'\xC0', byteorder='big')
KISS_FESC = int.from_bytes(b'\xDB', byteorder='big')
KISS_TFEND = int.from_bytes(b'\xDC', byteorder='big')
KISS_TFESC = int.from_bytes(b'\xDD', byteorder='big')


class KISS_Decoder():
    '''
    @ KISS协议解码器
    '''
    def __init__(self):
        self.InEscMode = False
        self.DataBuf = b""
        self.DecodedLength = 0

    def AppendStream(self, stream_data):
        '''
        @ stream_data : kiss 编码的数据，只需要讲KISS数据帧，按照顺序通过
        stream_data传入，当解码完毕后会自动返回数据包，并重置解码器等待下一次解码
        '''
        all_data = []
        for b in stream_data:
            if not self.InEscMode:
                if b == KISS_FEND:
                    if self.DecodedLength != 0:
                        data = self.DataBuf
                        self.reset_kiss()
                        all_data.append(data)  # 解码结束

                elif b == KISS_FESC:
                    self.InEscMode = True

                else:
                    self.DataBuf = self.DataBuf + b.to_bytes(1, byteorder='big')
                    self.DecodedLength += 1

            else:
                if b == KISS_TFEND:
                    self.DataBuf = self.DataBuf + KISS_FEND.to_bytes(1, byteorder='big')
                elif b == KISS_TFESC:
                    self.DataBuf = self.DataBuf + KISS_FESC.to_bytes(1, byteorder='big')

                self.DecodedLength += 1
                self.InEscMode = False
        return all_data

    def reset_kiss(self):
        self.DataBuf = b""
        self.DecodedLength = 0
