#!/usr/bin/env python3

"""LevelNet reads messages from a network FIS-B server.

Given a host and a port (supplied in :mod:`fisb.levelNet.levelNetConfig`),
connect to the server and supply messages to standard out.
Generally, is run with ``cfg.PRINT_ERRORS = False``, so any disconnects
and reconnects are silent. If it cannot connect, or if the
connection is dropped, will continually (after a small sleep)
try to reconnect.

If ``cfg.PRINT_ERRORS`` is ``True``, will print errors to ``sys.stderr``.
"""

import socket, sys, os, time

import fisb.levelNet.levelNetConfig as cfg

def connectToServer():
    """Connect to FIS-B server and do not return until successful.

    Returns:
        socket: Socket containing an open and working connected socket
    """
    while True:
        # Connect to server and return socket. If not successful, 
        # keep trying.
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( (cfg.NETWORK_HOST, cfg.NETWORK_PORT) )
            return(client_socket)
        except Exception as ex:
            if cfg.PRINT_ERRORS:
                print(ex, file=sys.stderr)
            try:
                client_socket.close()
            except:
                pass
            time.sleep(5)

def mainLoop():
    """Loops forever reading data from FIS-B server or attempting reconnect.

    Connects to FIS-B server and reads and outputs data to standard output.
    If a connection to a server cannot be made, or if the connection is lost,
    will continually try to resolve the problem.

    Will never exit unless terminated.
    """
    connected = False

    try:
        while True:
            # Connect if not connected
            if not connected:
                client_socket = connectToServer()
                connected = True

            # Get data from server. If len() is 0, disconnect happened.
            # Otherwise, send data to standard output.
            msg = client_socket.recv(1024).decode("UTF-8")  
            if len(msg) == 0:
                connected = False
                time.sleep(3)
            else:
                print(msg, end = '', flush=True)
                #print(msg)

    except Exception as ex:
        if cfg.PRINT_ERRORS:
            print(ex, file=sys.stderr)
        connected = False

        try:            
            client_socket.close()
        except:
            pass

        time.sleep(3)

if __name__ == "__main__":
    mainLoop()
