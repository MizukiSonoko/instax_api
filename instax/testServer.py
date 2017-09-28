"""
Fujifilm Instax-SP2 Server for testing.

James Sutton - 2017 - jsutton.co.uk
"""
import socket
from .packet import Packet, PacketFactory, SpecificationsCommand, \
    VersionCommand, PrintCountCommand, ModelNameCommand, PrePrintCommand, \
    PrinterLockCommand, ResetCommand, PrepImageCommand, SendImageCommand
import signal
import sys
import time
import json
import threading

def __init__():
    print("Let's get this going!")


class TestServer:
    """A Test Server for the Instax Library."""

    def __init__(self, verbose=False, log=None, host='0.0.0.0', port=8080,
                 dest="images", battery=2, remaining=10, total=20):
        """Initialise Server."""
        self.packetFactory = PacketFactory()
        self.host = host
        self.verbose = verbose
        self.log = log
        self.dest = dest
        self.port = port
        self.backlog = 5
        self.returnCode = Packet.RTN_E_RCV_FRAME
        self.ejecting = 0
        self.battery = battery
        self.printCount = total
        self.remaining = remaining
        self.running = True
        self.finished = False
        self.messageLog = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        signal.signal(signal.SIGINT, self.signal_handler)

    def start(self):
        """Start the Server."""
        self.socket.listen(self.backlog)
        print(('Server Listening on %s port %s' % (self.host, self.port)))
        while True:
            client, address = self.socket.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient, args = (client, address)).start()

        
    def listenToClient(self, client, address):
        print('New Client Connected')
        length = None
        buffer = bytearray()
        while True:
            #try:
            data = client.recv(70000)
            if not data:
                break
            buffer += data
            while True:  
                #print(('received: %s' % self.printByteArray(buffer)))
                if length is None:
                    length = ((buffer[2] & 0xFF) << 8 |
                                (buffer[3] & 0xFF) << 0)
                    print('Length: %s' % str(length))
                if len(buffer) < length:
                    break
                
                response = self.processIncomingMessage(buffer)
                client.send(response)
                buffer = bytearray()
                length = None
                break
            #except:
            #    print('Client disconnected: %s' % sys.exc_info()[0])
            #    client.close()
            #    return False
        

    def signal_handler(self, signal, frame):
        """Handle Ctrl+C events."""
        print()
        print('You pressed Ctrl+C! Saving Log and shutting down.')
        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = "instaxServer-" + timestr + ".json"
        print("Saving Log to: %s" % filename)
        with open(filename, 'w') as outfile:
            json.dump(self.messageLog, outfile, indent=4)
        print("Log file written, have a nice day!")
        sys.exit(0)

    def printByteArray(self, byteArray):
        """Print a Byte Array.

        Prints a Byte array in the following format: b1b2 b3b4...
        """
        hexString = ''.join('%02x' % i for i in byteArray)
        data = ' '.join(hexString[i:i + 4]
                        for i in range(0, len(hexString), 4))
        info = (data[:80] + '..') if len(data) > 80 else data
        return(info)

    def processIncomingMessage(self, payload):
        """Take an incoming message and return the response."""
        packetFactory = PacketFactory()
        decodedPacket = packetFactory.decode(payload)
        #decodedPacket.printDebug()
        decodedPacketObj = decodedPacket.getPacketObject()
        self.messageLog.append(decodedPacketObj)
        print("Processing message type: %s" % decodedPacket.NAME)
        response = None

        if(decodedPacket.TYPE == Packet.MESSAGE_TYPE_PRINTER_VERSION):
            response = self.processVersionCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_SPECIFICATIONS):
            response = self.processSpecificationsCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_MODEL_NAME):
            response = self.processModelNameCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_PRINT_COUNT):
            response = self.processPrintCountCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_PRE_PRINT):
            response = self.processPrePrintCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_LOCK_DEVICE):
            response = self.processLockPrinterCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_RESET):
            response = self.processResetCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_PREP_IMAGE):
            response = self.processPrepImageCommand(decodedPacket)
        elif(decodedPacket.TYPE == Packet.MESSAGE_TYPE_SEND_IMAGE):
            response = self.processSendImageCommand(decodedPacket)
        else:
            print('Unknown Command. Failing!')

        decodedResponsePacket = packetFactory.decode(response)
        self.messageLog.append(decodedResponsePacket.getPacketObject())
        return response

    def processVersionCommand(self, decodedPacket):
        """Process a version command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = VersionCommand(Packet.MESSAGE_MODE_RESPONSE,
                                   unknown1=254,
                                   firmware=275,
                                   hardware=0)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processSpecificationsCommand(self, decodedPacket):
        """Process a specifications command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = SpecificationsCommand(Packet.MESSAGE_MODE_RESPONSE,
                                          maxHeight=800,
                                          maxWidth=600,
                                          maxColours=256,
                                          unknown1=10,
                                          maxMsgSize=60000,
                                          unknown2=16,
                                          unknown3=0)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processModelNameCommand(self, decodedPacket):
        """Process a model name command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = ModelNameCommand(Packet.MESSAGE_MODE_RESPONSE,
                                     modelName='SP-2')
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processPrintCountCommand(self, decodedPacket):
        """Process a Print Count command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = PrintCountCommand(Packet.MESSAGE_MODE_RESPONSE,
                                      printHistory=20)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processPrePrintCommand(self, decodedPacket):
        """Process a Pre Print command."""
        cmdNumber = decodedPacket.payload['cmdNumber']
        if(cmdNumber in [6, 7, 8]):
            respNumber = 0
        elif(cmdNumber in [4, 5]):
            respNumber = 1
        elif(cmdNumber in [1, 2, 3]):
            respNumber = 2
        else:
            print("Unknown cmdNumber")
            respNumber = 0
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = PrePrintCommand(Packet.MESSAGE_MODE_RESPONSE,
                                    cmdNumber=cmdNumber,
                                    respNumber=respNumber)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processLockPrinterCommand(self, decodedPacket):
        """Process a Lock Printer Command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = PrinterLockCommand(Packet.MESSAGE_MODE_RESPONSE)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processResetCommand(self, decodedPacket):
        """Process a Rest command."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = ResetCommand(Packet.MESSAGE_MODE_RESPONSE)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processPrepImageCommand(self, decodedPacket):
        """Process a Prep Image Commnand."""
        sessionTime = decodedPacket.header['sessionTime']
        resPacket = PrepImageCommand(Packet.MESSAGE_MODE_RESPONSE,
                                     maxLen=60000)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse

    def processSendImageCommand(self, decodedPacket):
        """Process a Send Image Command."""
        sessionTime = decodedPacket.header['sessionTime']
        sequenceNumber = decodedPacket.payload['sequenceNumber']
        resPacket = SendImageCommand(Packet.MESSAGE_MODE_RESPONSE,
                                     sequenceNumber=sequenceNumber)
        encodedResponse = resPacket.encodeResponse(sessionTime,
                                                   self.returnCode,
                                                   self.ejecting,
                                                   self.battery,
                                                   self.printCount)
        return encodedResponse
