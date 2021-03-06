import select, socket, ssl, threading, time;
from fbExceptionMeansSocketDisconnected import fbExceptionMeansSocketDisconnected;
from fbExceptionMeansSocketShutdown import fbExceptionMeansSocketShutdown;
from fbExceptionMeansSocketTimeout import fbExceptionMeansSocketTimeout;

nConnectTimeoutInSeconds = 1.0;
sHostname = "localhost";
uPort = 31337;
uReceiveBytes = 10;
sSendBytes = "X" * 10;

oListeningSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0);
oListeningSocket.settimeout(0);
oListeningSocket.bind((sHostname, uPort));
oListeningSocket.listen(1);

oServerSocket = None;
oSecureServerSocket = None;
oClientSocket = None;
oSecureClientSocket = None;
def foCreateSockets(bSecure, bClient):
  global oClientSocket, oSecureClientSocket, \
         oServerSocket, oSecureServerSocket
  try:
   oSecureClientSocket.close();
  except:
   pass;
  try:
   oClientSocket.close();
  except:
   pass;
  try:
   oSecureServerSocket.close();
  except:
   pass;
  try:
   oServerSocket.close();
  except:
   pass;
    
  # Create client socket
  oClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0);
  oClientSocket.settimeout(nConnectTimeoutInSeconds);
  oClientSocket.connect((sHostname, uPort));
  # Create server socket
  aoR, aoW, aoX = select.select([oListeningSocket], [oListeningSocket], [oListeningSocket]);
  assert len(aoW) == 0, \
      "Listening socket is ready for writing!?";
  assert len(aoX) == 0, \
      "Listening socket has exception!?";
  assert len(aoR) == 1, \
      "Listening socket is not ready for reading!?";
  (oServerSocket, (sClientIP, uClientPort)) = oListeningSocket.accept();
  if bSecure:
    def fSecureServerSide():
      global oSecureServerSocket;
      oSecureServerSocket = ssl.wrap_socket(oServerSocket, server_side=True, keyfile="localhost.key.pem", certfile="localhost.cert.pem");
    oThread = threading.Thread(target = fSecureServerSide);
    oThread.start();
    oSecureClientSocket = ssl.wrap_socket(oClientSocket, server_side=False);
    oThread.join();
    oSecureClientSocket.settimeout(0);
    oSecureServerSocket.settimeout(0);
    return oSecureClientSocket if bClient else oSecureServerSocket;
  else:
    oSecureClientSocket = None;
    oSecureServerSocket = None;
    return oClientSocket if bClient else oServerSocket;



def fTestSockets(bSecure, sState, bTestClient = True, bTestServer = True, bCanWaitForReading = True):
  global oClientSocket, oSecureClientSocket, \
         oServerSocket, oSecureServerSocket
  if bTestClient: sClientLog = "client:";
  if bTestServer: sServerLog = "server:";
  try:
    if bTestClient: sClientLog += " [" + fsTestSocketStatus(oSecureClientSocket, oClientSocket, bCanWaitForReading) + "]";
    if bTestServer: sServerLog += " [" + fsTestSocketStatus(oSecureServerSocket, oServerSocket, bCanWaitForReading) + "]";
    try:
      assert (oSecureClientSocket or oClientSocket).send("x") == 1, "";
    except Exception as oException:
      if bTestClient: sClientLog += " wXXX";
    else:
      if bTestClient: sClientLog += " W";
    try:
      assert (oSecureServerSocket or oServerSocket).send("x") == 1, "";
    except Exception as oException:
      if bTestServer: sServerLog += " wXXX";
    else:
      if bTestServer: sServerLog += " W";
    try:
      assert (oSecureClientSocket or oClientSocket).recv(10) != "", "";
    except Exception as oException:
      if bTestClient: sClientLog += " rXXX";
    else:
      if bTestClient: sClientLog += " R";
    try:
      assert (oSecureServerSocket or oServerSocket).recv(10) != "", "";
    except Exception as oException:
      if bTestServer: sServerLog += " rXXX";
    else:
      if bTestServer: sServerLog += " R";
  finally:
    print (",--- %s %s " % ("secure" if bSecure else "non-secure", sState)).ljust(80, "-");
    if bTestClient: print "| " + sClientLog;
    if bTestServer: print "| " + sServerLog;
    print "'".ljust(80, "-");

def fsTestSocketSelect(oSocket):
  if oSocket is None: return "---";
  try:
    bR, bW, bX = [len(ax) == 1 for ax in select.select([oSocket], [oSocket], [oSocket], 0)];
  except Exception as oException:
    if fbExceptionMeansSocketDisconnected(oException):
      return "XXX";
    if fbExceptionMeansSocketShutdown(oException):
      return "...";
    return "*** => %s" % repr(oException);
  else:
    return "%s%s%s" % ("R" if bR else ".", "W" if bW else ".", "X" if bX else ".");

def fsTestSocketRecv(oSocket):
  try:
    sReceviedBytes = oSocket.recv(uReceiveBytes);
  except Exception as oException:
    if fbExceptionMeansSocketTimeout(oException):
      return "timeout".ljust(8);
    if fbExceptionMeansSocketDisconnected(oException):
      return "XXX".ljust(8);
    if fbExceptionMeansSocketShutdown(oException):
      return "shutdown".ljust(8);
    return "*** %s" % repr(oException);
  else:
    return ("%d bytes" % len(sReceviedBytes)).ljust(8);

def fsTestSocketSend(oSocket):
  uBytesSent = None;
  try:
    oSocket.settimeout(0);
    uSentBytes = oSocket.send(sSendBytes);
  except Exception as oException:
    if fbExceptionMeansSocketTimeout(oException):
      return "timeout".ljust(8);
    if fbExceptionMeansSocketDisconnected(oException):
      return "XXX".ljust(8);
    if fbExceptionMeansSocketShutdown(oException):
      return "shutdown".ljust(8);
    return "*** => %s" % repr(oException);
  else:
    return ("%d bytes" % uSentBytes).ljust(8);

def fsTestSocketFileNo(oSocket):
  if oSocket is None: return "---";
  try:
    oSocket.settimeout(0);
    uFileNo = oSocket.fileno();
  except Exception as oException:
    if fbExceptionMeansSocketDisconnected(oException):
      return "XXX";
    return "*** => %s" % repr(oException);
  else:
    return "%3d" % uFileNo;

def fsTestSocketStatus(oSecureSocket, oNonSecureSocket, bCanWaitForReading):
  sLog = "";
  oSocket = oSecureSocket or oNonSecureSocket;
  oSocket.settimeout(0);
  try:
    sData = oNonSecureSocket.recv(0);
  except Exception as oException:
    if fbExceptionMeansSocketTimeout(oException):
      sLog += "R0:T|";
      bIsOpenForReading = True;
    elif fbExceptionMeansSocketShutdown(oException):
      sLog += "R0:S|";
      bIsOpenForReading = False;
    elif fbExceptionMeansSocketDisconnected(oException):
      return "xx:%sR0:X" % sLog;
    else:
      raise;
  else:
    sLog += "R0:0|";
    bIsOpenForReading = True;
  
  nStartTime = time.time();
  nWaitTimeout = 1;
  bDataAvailable, bUnused, bException = [
    len(aoSocket) == 1
    for aoSocket in select.select([oSocket], [], [oSocket], nWaitTimeout)
  ];
  assert not bException, \
      "Unexpected exception";
  assert bCanWaitForReading or time.time() < nStartTime + nWaitTimeout, \
      "Waiting despite this is not expected."
  sLog += "S:R|" if bDataAvailable else "S:r|";
  if bDataAvailable:
    try:
      oSocket.settimeout(0);
      sData = oSocket.recv(1);
    except socket.error as oException:
      if fbExceptionMeansSocketShutdown(oException):
        sLog += "R1:S|";
        bIsOpenForReading = False;
      elif fbExceptionMeansSocketDisconnected(oException):
        return "xx:%sR1:X" % sLog;
      else:
        raise;
    else:
      if len(sData) == 1:
        sLog += "R1:1|";
      else:
        sLog += "R1:0|";
        bIsOpenForReading = False;
  bUnused, bIsOpenForWriting, bException = [
    len(aoSocket) == 1
    for aoSocket in select.select([], [oSocket], [oSocket], 0)
  ];
  assert not bException, \
      "Unexpected exception";
  sLog += "S:W|" if bIsOpenForWriting else "S:w|";
  if bIsOpenForWriting:
    try:
      oNonSecureSocket.send("");
    except socket.error as oException:
      if fbExceptionMeansSocketShutdown(oException):
        sLog += "W0:S|";
        bIsOpenForWriting = False;
      elif fbExceptionMeansSocketDisconnected(oException):
        return "xx:%sW0:X" % sLog;
      else:
        raise;
    else:
      sLog += "W0:0|";
  return "%s%s:%s" % ("R" if bIsOpenForReading else "x", "W" if bIsOpenForWriting else "x", sLog);

for bSecure in (False, True):
  foCreateSockets(bSecure, False);
  fTestSockets(bSecure, "RW: connected");

for bClient in (True, False):
  for bSecure in (False, True):
    foCreateSockets(bSecure, bClient).shutdown(socket.SHUT_RD);
    fTestSockets(bSecure, "Rx: read shutdown by %s" % ("client" if bClient else "server"), bTestClient = not bClient, bTestServer = bClient);
    
    foCreateSockets(bSecure, bClient).shutdown(socket.SHUT_WR);
    fTestSockets(bSecure, "xW: write shutdown by %s" % ("client" if bClient else "server"), bTestClient = not bClient, bTestServer = bClient, bCanWaitForReading = False);
    
    foCreateSockets(bSecure, bClient).shutdown(socket.SHUT_RDWR);
    fTestSockets(bSecure, "xx: shutdown by %s" % ("client" if bClient else "server"), bTestClient = not bClient, bTestServer = bClient, bCanWaitForReading = False);
    
    foCreateSockets(bSecure, bClient).close();
    if bSecure:
      (oClientSocket if bClient else oServerSocket).close();
    fTestSockets(bSecure, "xx: closed by %s" % ("client" if bClient else "server"), bTestClient = not bClient, bTestServer = bClient, bCanWaitForReading = False);

    oSocket = foCreateSockets(bSecure, bClient);
    oSocket.shutdown(socket.SHUT_RDWR);
    oSocket.close();
    if bSecure:
      (oClientSocket if bClient else oServerSocket).shutdown(socket.SHUT_RDWR);
      (oClientSocket if bClient else oServerSocket).close();
    fTestSockets(bSecure, "xx: shutdown and closed by %s" % ("client" if bClient else "server"), bTestClient = not bClient, bTestServer = bClient, bCanWaitForReading = False);

