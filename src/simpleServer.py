#/usr/bin/env python3

import re
import sys
import socket

# Nahradi znaky odradkovani mezerami
def replaceCRLF(data):
    data = data.replace('\\n', " ")
    return data.replace('\\r', " ")

# Kontrola formatu ip adresy a domenoveho jmena
def ipVsDomain(word):
    if(re.match('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', word)):
        return "IP"
    elif(re.match('^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', word)):
        return "DOMAIN"
    else:
        return ""

# Komunikace s klientem
def sendResponse(conn, code, body, data):
    if(code == 200):
        codeMsg = "OK"
    elif(code == 400):
        codeMsg = "Bad Request"
    elif(code == 404):
        codeMsg = "Not Found"
    elif(code == 405):
        codeMsg = "Method Not Allowed"
    elif(code == 500):
        codeMsg = "Internal Server Error"

    data = replaceCRLF(data)

    # Kontrola verze HTTP
    if(re.search(' +HTTP/1\.1 +', data)):
        version = "HTTP/1.1"
    elif(re.search(' +HTTP/2\.0 +', data)):
        version = "HTTP/2.0"
    elif(re.search(' +HTTP/1\.0 +', data)):
        version = "HTTP/1.0"
    else:
        version = "HTTP/1.1"
    
    # Slozeni hlavicky odpovedi
    response = version + " " + str(code) + " " + codeMsg + "\r\n\r\n"

    if(body != ""):
        response += (body + "\n")

    conn.sendall(response.encode('utf-8'))

# Reseni metody GET
def doGet(data, conn):
    nameTypes = []
    parNames = []
    parType = ""

    data = replaceCRLF(data)

    words = re.split('[?&]', data.split()[1])

    if(words[0] != "/resolve"):
        sendResponse(conn, 400, "", data)
        return
    
    words.pop(0)

    # Nacitani parametru v cyklu
    for word in words:
        if(re.match('^name=', word)):
            word = word.replace("name=", "", 1)
        
            retVal = ipVsDomain(word)

            if(retVal == ""):
                sendResponse(conn, 400, "", data)
                return

            nameTypes.append(retVal)

            parNames.append(word)

        elif(re.match('^type=(A|PTR)', word)):
            if(parType == ""):
                parType = word.replace("type=", "")
            else:
                sendResponse(conn, 400, "", data)
                return
        else:
            sendResponse(conn, 400, "", data)
            return

    result = ""

    # Kotrola kombinaci parametru a preklad
    for parName in parNames:
        if(parType == 'A' and nameTypes[0] == "DOMAIN"):
            try:
                translatedName = socket.gethostbyname(parName)
            except:
                sendResponse(conn, 404, "", data)
                return
        elif(parType == 'PTR' and nameTypes[0] == "IP"):
            try:
                translatedName = socket.gethostbyaddr(parName)[0]
            except:
                sendResponse(conn, 404, "", data)
                return
        else:
            sendResponse(conn, 400, "", data)
            return

        nameTypes.pop(0)

        if(result != ""):
            result += "\n"

        # vysledek
        result += (parName + ":" + parType + "=" + translatedName)

    if(result != ""):
        sendResponse(conn, 200, result, data)
    else:
        sendResponse(conn, 400, "", data)

# Reseni metody POST
def doPost(data, conn):
    if(data.split()[1] != "/dns-query"):
        sendResponse(conn, 400, "", data)
        return

    words = data.split('\\r\\n\\r\\n')
    words = words[1].replace('\\r', " ")
    words = words.replace('\\t', " ")
    words = re.sub('^ +', "", words)
    words = re.sub(' *\\\\n?\'$', "", words)
    words = words.split('\\n')

    result = ""

    # cyklus nacitani jednotlivych pozadavku ze vstupu a kontrola formatu
    for line in words:
        line = line.split(':')

        if(len(line) != 2):
            sendResponse(conn, 400, "", data)
            return

        line[0] = re.sub('(^ +| +$)', "", line[0])
        line[1] = re.sub('(^ +| +$)', "", line[1])

        if(line[1] != "A" and line[1] != "PTR"):
            continue
        
        retVal = ipVsDomain(line[0])

        if(retVal == "DOMAIN" and line[1] == "A"):
            try:
                translatedName = socket.gethostbyname(line[0])
            except:
                continue
        elif(retVal == "IP" and line[1] == "PTR"):
            try:
                translatedName = socket.gethostbyaddr(line[0])[0]
            except:
                continue
        else:
            continue
        
        # Ukladani vysledku
        if(result != ""):
            result += "\n"

        result += (line[0] + ":" + line[1] + "=" + translatedName)

    if(result != ""):
        sendResponse(conn, 200, result, data)
    else:
        sendResponse(conn, 400, "", data)

# Funkce rozhodujici o tom, jaka metoda bude provedena
def processMethod(data, conn):
    if(re.match('^b\'GET\s', data)):
        doGet(data, conn)
    elif(re.match('^b\'POST\s', data)):
        doPost(data, conn)
    else:
        sendResponse(conn, 405, "", data)

# Reseni vstupnich argumentu
if(len(sys.argv) != 2):
    sys.stderr.write("Wrong number of arguments!\n")
    exit()
elif(re.match('^\d+$', sys.argv[1]) == None):
    sys.stderr.write("Wrong argument!\n")
    exit()

HOST = '127.0.0.1'
PORT = int(sys.argv[1])

# Samotny server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind((HOST, PORT))
    while True:
        try:
            server.listen()
            conn, addr = server.accept()
            with conn:
                data = conn.recv(1024)
                if not data:
                    break
                processMethod(str(data), conn)
        except:
            exit()
