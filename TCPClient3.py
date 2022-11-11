"""
    Python 3
    Usage: python3 TCPClient3.py localhost 12000
    coding: utf-8
"""

from socket import *
import sys
from threading import Thread
import json
import re
import threading
from requests import request
import os
from pathlib import Path
import random
from time import sleep
#functions
def generate_data(username, fileID, dataAmount):
    #if file exists we overwrite, simply delete original
    if os.path.isfile(f'{username}-{fileID}.txt'):
        os.remove(f'{username}-{fileID}.txt')
    
    with open(f'{username}-{fileID}.txt', 'a+') as f:
        for i in range(int(dataAmount)):
            num = random.randint(0, 10000)
            f.write(f'{num}\n')
        f.close()

    print(f'Data generation done, {dataAmount} data samples have been generated and stored in the file {username}-{fileID}.txt')

#Server would be running on the same host as Client
if len(sys.argv) != 4:
    print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT CLIENT_UDP_SERVER_PORT======\n")
    exit(0)
serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
udpPort = int(sys.argv[3])
serverAddress = (serverHost, serverPort)
enter_prompt = 'Enter one of the following commands: EDG, UED, SCS, DTE, AED, OUT'

# define a socket for the client side, it would be used to communicate with the server
clientSocket = socket(AF_INET, SOCK_STREAM)

clientHost = '127.0.0.1'
udpAddress = (clientHost, udpPort)
udpSocket = socket(AF_INET, SOCK_DGRAM)
udpSocket.bind(udpAddress)
bufflen = 2048


# build connection with the server and send message to it
clientSocket.connect(serverAddress)
#we only have one subthread for each loop to listen for server response
started_listening_thread = False
started_p2p_thread = False
print("===== Provide username and password =====\n")

usernameAccepted = False
loggedIn = False
command = ''

class ListeningThread(Thread):

    def __init__(self, *args, **kwargs):
        Thread.__init__(self)
        self.flag = threading.Event()
        self.flag.set()
        self.flag_running = threading.Event()
        self.flag_running.set()

    def run(self):
        while self.flag_running.isSet():
            self.flag.wait()
            try:
                data = clientSocket.recv(4096)
                receivedMessage = data.decode()
                print(receivedMessage)
            except:
                break
    
    def pause(self):
        self.flag.clear()

    def resume(self):
        self.flag.set()

    def stop(self):
        self.flag.set()
        self.flag_running.clear()
        exit()

class UDPListeningThread(Thread):

    def __init__(self, socket):
        Thread.__init__(self)
        self.socket = socket
        self.flag = threading.Event()
        self.flag.set()
        self.flag_running = threading.Event()
        self.flag_running.set()

    def run(self):
        while self.flag_running.isSet():
            self.flag.wait()
            try:
                content, udpAddress = self.socket.recvfrom(bufflen)
                print('Received file:', content.decode().strip())
                
                f = open(content.strip(), 'wb')
                content, udpAddress = self.socket.recvfrom(bufflen)
                #write file
                try:
                    while(content):
                        f.write(content)
                        self.socket.settimeout(2)
                        content, udpAddress = self.socket.recvfrom(bufflen)
                except timeout:
                    f.close()
                    print('Finished downloading file.')
                    print(enter_prompt)
            except:
                continue
    
    def pause(self):
        self.flag.clear()

    def resume(self):
        self.flag.set()

    def stop(self):
        self.flag.set()
        self.flag_running.clear()
        exit()
                
while usernameAccepted == False:
    #since we need to check if username is valid, we need to send a request separately to the server
    username = input("Username: ")

    request = {
        'command': 'usernameLogin',
        'username': username
    }

    clientSocket.sendall(json.dumps(request).encode())

    data = clientSocket.recv(4096)
    receivedMessage = data.decode()
    print(receivedMessage)

    if 'authenticated' in receivedMessage:
        usernameAccepted = True
        break
    
    if 'blocked' in receivedMessage:
        clientSocket.close()
        exit()


while True:

    sent_to_server = False
    #logging in
    while (loggedIn == False):
        
        password = input("Password: ")

        request = {
            'command': 'login',
            'username': username,
            'password': password,
            'udpPort': udpPort
        }

        clientSocket.sendall(json.dumps(request).encode())

        sent_to_server = True
        
        data = clientSocket.recv(4096)
        receivedMessage = data.decode()

        print(receivedMessage)

        if 'blocked' in receivedMessage:
            clientSocket.close()
            exit()

        if 'success' in receivedMessage:
            request = None
            loggedIn = True

    #start thread to listen for downloads
    if not started_p2p_thread:
        started_p2p_thread = True
        p2p_thread = UDPListeningThread(udpSocket)
        p2p_thread.start()
        
    #start a thread to listen. we dont do this outside of the while true due to the implementation of login
    if not started_listening_thread:
        started_listening_thread = True
        listeningThread = ListeningThread()
        listeningThread.start()

    #after logged in
    request = None
    sleep(0.01)
    command = input('> ')
    sent_to_server = False
    
    #edg
    if 'EDG' in command:
        if re.search(r'^EDG \d+ \d+$', command) != None:
            edg, fileID, dataAmount = command.split(' ')
            print(f'The edge device is generating {dataAmount} data samples...')
            generate_data(username, fileID, dataAmount)
        else:
            if re.search(r'(^EDG$|^EDG $|^EDG \d$|^EDG \d $)', command) != None:
                print('EDG command requires fileID and dataAmount as arguments.')
            elif re.search(r'^EDG \d+ \D+$', command) != None:
                print('The dataAmount is not an integer. The parameter must be of type integer.')
            elif re.search(r'^EDG \D+ \d+$', command) != None:
                print('The fileID is not an integer. The parameter must be of type integer.')
            elif re.search(r'^EDG \D+ \D+$', command) != None:
                print('The fileID and/or dataAmount are not integers. The parameters must be of type integer.')
            else:
                print('Invalid format. Correct usage is UED fileID dataAmount.')

    #ued
    elif 'UED' in command:
        if re.search(r'^UED \d+$', command) != None:
            fileID = re.findall(r'\d+', command)[0]
            if not os.path.isfile(f'{username}-{fileID}.txt'):
                print(f'The file with fileID {fileID} does not exist.')
            else:
                txt = Path(f'{username}-{fileID}.txt').read_text()
                request = {
                    'command': 'UED',
                    'username': username,
                    'fileID': fileID,
                    'data' : txt
                }
                sent_to_server = True
        elif re.search(r'(^UED$|^UED $)', command) != None:
            print('fileID is needed to upload the data.')
        else:
            print('Invalid format. Correct usage is: UED fileID')

    #scs
    elif 'SCS' in command:
        if re.search(r'^SCS \d+ (SUM$|AVERAGE$|MAX$|MIN$)', command) != None:
            fileID = re.findall(r'\d+', command)[0]
            computationOperation = re.findall(r'(SUM$|AVERAGE$|MAX$|MIN$)', command)[0]
            request = {
                'command': 'SCS',
                'username': username,
                'fileID': fileID,
                'computationOperation': computationOperation
            }
            sent_to_server = True
        elif re.search(r'(^SCS$|^SCS $|^SCS \d$|^SCS \d $)', command):
            print('SCS command requires fileID and computationOperation as arguments.')
        elif re.search(r'^SCS \D+ (SUM$|AVERAGE$|MAX$|MIN$)', command):
            print('fileID is missing or fileID is not an integer.')
        elif re.search(r'^SCS \d+ .', command):
            print('The computationArgument must be either SUM, AVERAGE, MAX or MIN.')
        else:
            print('Invalid format. Correct usage is SCS fileID computationOperation')

    #dte
    elif 'DTE' in command:
        if re.search(r'^DTE \d+$', command) != None:
            fileID = re.findall(r'\d+', command)[0]
            request = {
                'command': 'DTE',
                'username': username,
                'fileID': fileID,
            }
            sent_to_server = True
        elif re.search(r'^DTE \D+$', command):
            print('fileID must be an integer.')
        else:
            print('Invalid format. Correct usage is DTE fileID')

    #aed
    elif 'AED' in command:
        if re.search(r'^AED$', command) != None:
            request = {
                'command': 'AED',
                'username': username
            }
            sent_to_server = True
        else:
            print('Invalid format. AED must be the only argument.')

    #out
    elif 'OUT' in command:
        if re.search(r'^OUT$', command) != None:
            request = {
                'command': 'OUT',
                'username': username
            }

            clientSocket.sendall(json.dumps(request).encode())
            print('Goodbye :(')
            clientSocket.close()
            os._exit(1)
            # p2p_thread.stop()
            # listeningThread.stop()
            exit()
        else:
            print('Invalid format. OUT requires no additional arguments.')
    
    #uvf
    elif 'UVF' in command: 
        if re.search(r'^UVF .* .*$', command) != None:
            txt = command.split(' ')
            deviceName = txt[1]
            fileName = txt[2]
            if os.path.isfile(fileName) == False:
                print(f'{fileName} does not exist.')
            else:
                request = {
                    'command': 'UVF',
                    'deviceName': deviceName,
                    'username': username
                }
                clientSocket.sendall(json.dumps(request).encode())
                sent_to_server = True
                #stop non-p2p listening thread so we can extract the udp port
                listeningThread.pause()
                data = clientSocket.recv(2048)
                receivedMessage = data.decode()
                print(receivedMessage)
                if re.search(r'\d+', receivedMessage) != None:
                    #first we need to find the port number and ip addr from the response sent from server
                    portNum = re.findall(r'\d+', receivedMessage)[0]
                    portNum = int(portNum)
                    splitMSG = receivedMessage.split(' ')
                    ipAddr = splitMSG[len(splitMSG)-1]
                    bufflen = 2048
                    addr = (ipAddr, portNum)
                    udpsocket = socket(AF_INET, SOCK_DGRAM)
                    hostfName = username + '_' + fileName
                    #send filename
                    udpSocket.sendto(hostfName.encode(), addr)  
                    #send filecontent
                    f = open(fileName, 'rb')
                    content = f.read(bufflen)
                    while (content):
                        if udpSocket.sendto(content, addr):
                            #throttle sending rate
                            sleep(0.000001)
                            content = f.read(bufflen)
                    f.close()
                    print('Finished sending file.')
                    listeningThread.resume()
        else:
            print('Invalid format. Correct usage is UVF deviceName fileID')

    else:
        print('Invalid command. Please enter a valid command:')

    if request != None and 'UVF' not in command:
        clientSocket.sendall(json.dumps(request).encode())
    
    #since server prompts the enter a command message, if we do not send a req to server we need to prompt from client end
    if sent_to_server == False:
        print(enter_prompt)

clientSocket.close()
