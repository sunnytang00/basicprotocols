"""
    Sample code for Multi-Threaded Server
    Python 3
    Usage: python3 TCPserver3.py localhost 12000
    coding: utf-8
    
    Author: Wei Song (Tutor for COMP3331/9331)
"""
"""
IMPROVEMENTS COULD BE MADE:
- transform server response into dict, key1 being message and key2 being an (error?) code
"""
from email import message
import fileinput
from genericpath import isfile
from socket import *
from threading import Thread
import sys
import select
from collections import defaultdict
import datetime
import os
import json
from numpy import average
import re
# acquire server host and port from command line parameter
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 TCPServer3.py server_port number_of_consecutive_failed_attempts======\n")
    exit(0)
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
maxFails = int(sys.argv[2])
seqNum = 1
enter_prompt = 'Enter one of the following commands: EDG, UED, SCS, DTE, AED, OUT'
while maxFails not in range(1, 6):
    print(
        f'Invalid number of allowed failed consecutive attempts: {maxFails}. The valid value of argument number is an integer between 1 and 5.')
    exit()

serverAddress = (serverHost, serverPort)

# define socket for the server side and bind address
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)

# dicts to store info on server side
# how many times username has failed to login
login_failed_times = defaultdict(int)
# the time the user can log in again after being blocked
end_block_time = defaultdict(int)
# whether a user is blocked from logging in
login_blocked = defaultdict(bool)
# whether a user is logged in
logged_in = defaultdict(bool)

#remove active device log if it exists
if os.path.isfile('edge-device-log.txt'):
    os.remove('edge-device-log.txt')

#remove deletion log if it exists
if os.path.isfile('deletion-log.txt'):
    os.remove('deletion-log.txt')

#remove upload log if it exists
if os.path.isfile('upload-log.txt'):
    os.remove('upload-log.txt')

"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate therad, which is the multi-threading
"""

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True

    def run(self):

        #MAIN FUNCTION
        command = ''

        while self.clientAlive: 
            # use recv() to receive command from the client
            data = self.clientSocket.recv(16384)

            #if empty data, we know client has disconnected
            if data.decode() == '':
                print("===== the user disconnected - ", clientAddress)
                break

            try:
                request = json.loads(data.decode())
            except:
                continue
            
            #get the needed values from the dict that client has sent
            command = request.get('command')
            username = request.get('username')
            message_to_send = 'empty'

            # if the command from client is empty, the client would be off-line then set the client as offline (alive=False)
            if command == '':
                self.clientAlive = False
                print("===== the user disconnected - ", clientAddress)
                break
            
            #need to process username first
            if command == 'usernameLogin':
                print("[revc] Username authentication request")
                message_to_send = self.process_username(username)

            #login with password
            elif command == 'login':
                print(f"[recv] New login request from {username}")
                password = request.get('password')
                udpPort = request.get('udpPort')
                message_to_send = self.process_login(username, password, udpPort)
            
            elif command == 'UED':
                fileID = request.get('fileID')
                txt = request.get('data')
                print(f"[recv] File upload request for {username}-{fileID}.txt uploaded by {username}")
                message_to_send = self.process_UED(fileID, username, txt)
                
            elif command == 'SCS':
                fileID = request.get('fileID')
                computationOperation = request.get('computationOperation')
                print(f'[recv] Computation service requested by {username} on file {username}-{fileID}.txt')
                message_to_send = self.process_SCS(username, fileID, computationOperation)

            elif command == 'DTE':
                fileID = request.get('fileID')
                print(f'[recv] File deletion requested by {username} on file {username}-{fileID}.txt')
                message_to_send = self.process_DTE(fileID, username)
            
            elif command == 'UVF':
                print(f'[recv] UVF request from {username}')
                deviceName = request.get('deviceName')
                username = request.get('username')
                message_to_send = self.process_UVF(deviceName, username)
                
            elif command == 'AED':
                print(f'[recv] AED requested by {username}')
                message_to_send = self.process_AED(username, False)

            elif command == 'OUT':
                print(f'{username} disconnected')
                message_to_send = self.process_OUT(username)

            else:
                print('ERROR')
                print("[recv] " + command)
                print("[send] Cannot understand this command")
                command = 'Cannot understand this command'
                self.clientSocket.send(command.encode())
        
            if 'blocked' not in message_to_send and 'Disconnected' not in message_to_send and command != 'usernameLogin' and 'Invalid password' not in message_to_send and 'UVF' not in message_to_send:
                message_to_send += enter_prompt
            print('[send] ' + message_to_send)
            self.clientSocket.send(message_to_send.encode())

    #HELPERS
    """
        You can create more customized APIs here, e.g., logic for processing user authentication
        Each api can be used to handle one specific function, for example:
        def process_login(self):
            command = 'user credentials request'
            self.clientSocket.send(command.encode())
    """
    def process_UVF(self, deviceName, username):
        user_found = False
        #issue aed command first
        active_device_list = self.process_AED(username, True)
        print(active_device_list)
        print('AED completed')

        #we need to open the device log file and find the IPaddr + port
        with open('edge-device-log.txt') as f:
            data = f.read().splitlines()

            #loop to find user in device log
            for i in data:
                x = i.split('; ')
                if deviceName == x[2]:
                    user_found = True
                    message = f'User {deviceName} with port {x[4]} found, IP address: {x[3]}'
                    print(message)
                    self.clientSocket.send(message.encode())
                    return 'User found. File tranmission will begin shortly.\n'    
            
            if not user_found:
                return f'{deviceName} is offline. Unable to retrieve their port number.\n'
        
    def process_username(self, username):
        #since we need to check if the username actually exists first before we check password, we just have a separate function
        with open('credentials.txt', 'r') as credentials_file:
            credentials_content = credentials_file.read()

        #check if block is over, can move this into a function later
        if login_blocked[username] == True:
            if login_failed_times.get(username) >= maxFails:
                # if 10sec has not yet passed, reject
                if datetime.datetime.now() < end_block_time[username]:
                    return 'Your account is blocked due to multiple authentication failures. Please try again later.'
                elif datetime.datetime.now() > end_block_time[username]:
                    login_blocked[username] = False
                    login_failed_times[username] = 0
        
        for row in credentials_content.split('\n'):
                try:
                    c_username, c_password = row.split(' ')
                except:
                    continue
                if username == c_username:
                    return 'Username authenticated.'
        
        return 'Invalid username. Please try again.'

    def process_OUT(self, username):
        #since user needs to be logged in to make this command, we know that edge device log must exist
        #therefore we do not need to check if it exists
        logged_in[username] = False
        with open('edge-device-log.txt') as f:
            user_to_remove = ''
            seqNum = 1
            data = f.read().splitlines()

            #loop to remove user from active dev log
            for i in data:
                x = i.split('; ')
                if username == x[2]:
                    user_to_remove = i
                    break
                seqNum += 1
            data.remove(user_to_remove)

            new_log = ''
            #loop to rewrite log file, modifying sequence numbers as needed
            for i in data:
                x = i.split('; ')

                if int(x[0]) < seqNum:
                    new_log += i

                elif int(x[0]) > seqNum:
                    var = int(x[0])
                    var -= 1
                    x[0] = str(var)
                    x.append('\n')
                    new_log += '; '.join(x)

            f.close()

        #overwriting log file
        with open('edge-device-log.txt','w') as f:
            f.write(new_log)
            f.close()
        print(f'Removed {username} from active device list.')

        return 'Disconnected successfully.'

    def process_AED(self, username, calledByUVF):

        aed_list = []
        #open device log, remove seq nums of each line and print
        with open('edge-device-log.txt') as f:
            data = f.read().splitlines()
            for i in data:
                x = i.split('; ')
                if username != x[2]:
                    line = []
                    for j in range(1, len(x)):
                        line.append(x[j])
                    line = '; '.join(line)
                    aed_list.append(line)

        #aed returns false if empty
        if not aed_list:
            return 'There are no currently active edge devices besides yourself\n'

        ret = ''
        for i in aed_list:
            ret = ret + i + '\n'
        if calledByUVF:
            return ret.rstrip()
        else:
            return ret

    def process_DTE(self, fileID, username):

        if not os.path.isfile(f'{username}-{fileID}.txt'):
            return(f'File {username}-{fileID}.txt does not exist on the server.\n')

        #calculate data amount
        dataAmount = sum(1 for line in open(f'{username}-{fileID}.txt'))
        os.remove(f'{username}-{fileID}.txt')

        with open('deletion-log.txt', 'a+') as f:
            f.write(
                f'{username}; {datetime.datetime.now().strftime("%d-%B-%Y %H:%M:%S")}; {fileID}; {dataAmount}\n')
        print(f'Log made for the deletion of {username}-{fileID}.txt')

        return f'File {username}-{fileID}.txt has been successfully deleted from the server.\n'

    def process_SCS(self, username, fileID, computationOperation):

        if not os.path.isfile(f'{username}-{fileID}.txt'):
            return(f'File {username}-{fileID}.txt does not exist on the server.\n')

        with open(f'{username}-{fileID}.txt') as f:
            #split the data file into lines, then calc.
            data = f.read().splitlines()
            data = [eval(i) for i in data]
            print(computationOperation)
            if computationOperation == 'MAX':
                return 'The max of the data sample was ' + str(max(data)) + '\n'
            elif computationOperation == 'MIN':
                return 'The min of the data sample was ' + str(min(data)) + '\n'
            elif computationOperation == 'AVERAGE':
                return 'The average of the data sample was ' + str(sum(data)/len(data)) + '\n'
            elif computationOperation == 'SUM':
                return 'The sum of the data sample was ' + str(sum(data)) + '\n'
            else:
                return 'Failed to compute. Please try again'
 
    def process_UED(self, fileID, username, txt):
        if os.path.isfile(f'{username}-{fileID}.txt'):
            return(f'File already exists. Failed to upload file {username}-{fileID}.txt.\n')
        
        with open(f'{username}-{fileID}.txt', 'a+') as f:
            f.write(txt)
        f.close()
        #make log for uploading file
        dataAmount = txt.count('\n')
        with open('upload-log.txt', 'a+') as f:
            f.write(
                f'{username}; {datetime.datetime.now().strftime("%d-%B-%Y %H:%M:%S")}; {fileID}; {dataAmount}\n')
        print(f'Upload log made for {username}-{fileID}.txt')
        f.close()

        return(f'File {username}-{fileID}.txt has been successfully uploaded.\n')

    def process_login(self, username, password, udpPort):
        # load credentials
        with open('credentials.txt', 'r') as credentials_file:
            credentials_content = credentials_file.read()

        login_success = False

        # if the user is blocked from logging in, we dont need to actually check against the credentials
        if login_blocked[username] == True:
            if login_failed_times.get(username) >= maxFails:
                # if 10sec has not yet passed, reject
                if datetime.datetime.now() < end_block_time[username]:
                    reply_msg = 'Your account is blocked due to multiple authentication failures. Please try again later.'
                elif datetime.datetime.now() > end_block_time[username]:
                    login_blocked[username] = False
                    login_failed_times[username] = 0

        # only allow login process if login is not blocked for username
        if login_blocked[username] == False:
            # read credentials file, maybe change to regex later
            for row in credentials_content.split('\n'):
                try:
                    c_username, c_password = row.split(' ')
                except:
                    continue
                if username == c_username and password == c_password:
                    login_success = True
                    break

            if login_success:
                logged_in[username] = True
                reply_msg = 'Login success.\n'
                global seqNum
                #make a log
                with open('edge-device-log.txt', 'a+') as f:
                    #get ip
                    host, port = clientSockt.getpeername()
                    f.write(
                        f'{seqNum}; {datetime.datetime.now().strftime("%d-%B-%Y %H:%M:%S")}; {username}; {host}; {udpPort}\n')
                print(f'Updated active device log for {username}')
                f.close()
                seqNum += 1

            # if we fail login, we need to increment the count of failed login attempts
            else:
                login_failed_times[username] += 1
                reply_msg = 'Invalid password. Please try again.'
                #if user reaches max fails, we need to block the user
                if login_failed_times.get(username) == maxFails:
                    login_blocked[username] = True
                    # start 10sec timer
                    time_now = datetime.datetime.now()
                    end_block = time_now + datetime.timedelta(0, 10)
                    end_block_time[username] = end_block
                    reply_msg = 'Invalid password. Your account has been blocked. Please try again later.'

        return reply_msg
            

print("\n===== Server is running =====")
print("===== Waiting for connection request from clients...=====")


while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()