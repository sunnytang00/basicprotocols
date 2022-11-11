## Information
Implementation of basic communication between a client and server through TCP, and client to client through UDP  
## Instructions
Ensure client and server files are in separate directories - multiple instances of the client file can be ran in separate directories. This is highly recommended  
Create a file named credentials.txt in the same directory as the server file. You can fill this with whatever you want. A valid credential consists of a username and password, separated by a whitespace. Credentials are separated by a newline character. See sample provided for examples  
for server, python3 TCPServer.py server_port number_of_max_failed_attempts  
for client, python3 TCPClient.py server_ip server_port port_for_p2p_udp_transfer  
## Commands
Commmands should be ran on the client  
EDG fileID dataAmount - Generates dataAmount of random numbers in the same directory as the client  
UED fileID - Uploads a file to the server directory  
SCS fileID computationOperation - computationOperation is either 'MAX, MIN, SUM, AVERAGE'. Server performs the operation on requested fileID  
DTE fileID - Deletes file with fileID  
AED - Lists all the other active devices connected to server
OUT - Disconnects client from the server
UVF deviceName fileName - Uploads fileName to another device through UDP  

