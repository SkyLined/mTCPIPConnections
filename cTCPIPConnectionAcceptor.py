import select, socket;

from .cTCPIPConnection import cTCPIPConnection;
from .fbExceptionMeansSocketDisconnected import fbExceptionMeansSocketDisconnected;
from .fbExceptionMeansSocketShutdown import fbExceptionMeansSocketShutdown;

from mDebugOutput import ShowDebugOutput, fShowDebugOutput;
from mMultiThreading import cLock, cThread, cWithCallbacks;

class cTCPIPConnectionAcceptor(cWithCallbacks):
  def __init__(oSelf, fNewConnectionHandler, szHostname = None, uzPort = None, ozSSLContext = None, nzSecureTimeoutInSeconds = None):
    oSelf.__fNewConnectionHandler = fNewConnectionHandler;
    oSelf.__sHostname = szHostname or socket.gethostname();
    oSelf.__uPort = uzPort or (443 if ozSSLContext else 80);
    oSelf.__ozSSLContext = ozSSLContext;
    oSelf.__nzSecureTimeoutInSeconds = nzSecureTimeoutInSeconds;
    
    oSelf.__bStopping = False;
    oSelf.__oTerminatedLock = cLock(
      "%s.__oTerminatedLock" % oSelf.__class__.__name__,
      bLocked = True
    );
    
    oSelf.__oPythonSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0);
    oSelf.__oPythonSocket.settimeout(None);
    oSelf.__oPythonSocket.bind((oSelf.__sHostname, oSelf.__uPort));
    oSelf.__oPythonSocket.listen(1);
    oSelf.__oMainThread = cThread(oSelf.__fMain);
    oSelf.__oMainThread.fStart(bVital = False);
    oSelf.fAddEvents(
      "new connection", # Fired first for both secure and nonsecure connections
      "new nonsecure connection", # Fired for nonsecure connections only.
      "new secure connection", # Fired after SSL negotiation has completed successfully.
      "connection cannot be secured", # Fired if SSL negotiation failed to complete successfully and before timeout.
      "terminated" # Fired when the acceptor stops accepting connections.
    );
  
  @property
  def sHostname(oSelf):
    return oSelf.__sHostname;
  @property
  def uPort(oSelf):
    return oSelf.__uPort;
  @property
  def ozSSLContext(oSelf):
    return oSelf.__ozSSLContext;
  @property
  def bSecure(oSelf):
    return oSelf.__ozSSLContext is not None;
  @property
  def sIPAddress(oSelf):
    return oSelf.__oPythonSocket.getsockname()[0];
  @property
  def bTerminated(oSelf):
    return not oSelf.__oTerminatedLock.bLocked;
  
  @ShowDebugOutput
  def fStop(oSelf):
    if oSelf.__bStopping:
      return fShowDebugOutput("Already stopping");
    if not oSelf.__oTerminatedLock.bLocked:
      return fShowDebugOutput("Already terminated");
    oSelf.__bStopping = True;
    fShowDebugOutput("Closing server socket...");
    oSelf.__oPythonSocket.close();

  @ShowDebugOutput
  def fTerminate(oSelf):
    if not oSelf.__oTerminatedLock.bLocked:
      return fShowDebugOutput("Already terminated");
    oSelf.__bStopping = True;
    fShowDebugOutput("Closing server socket...");
    oSelf.__oPythonSocket.close();

  @ShowDebugOutput
  def fbWait(oSelf, nzTimeoutInSeconds):
    return oSelf.__oTerminatedLock.fbWait(nzTimeoutInSeconds);
  
  def foCreateNewConnectionForPythonSocket(oSelf, oPythonSocket):
    return cTCPIPConnection(oPythonSocket, bCreatedLocally = False);
  
  @ShowDebugOutput
  def __fMain(oSelf):
    fShowDebugOutput("Waiting to accept first connection...");
    while not oSelf.__bStopping:
      try:
        # This select call will wait for the socket to be closed or a new connection to be made.
        select.select([oSelf.__oPythonSocket], [], [oSelf.__oPythonSocket]);
        # This accept call will accept a new connection or raise an exception if the socket is closed.
        (oPythonSocket, (sClientIP, uClientPort)) = oSelf.__oPythonSocket.accept();
        oPythonSocket.fileno(); # will throw "bad file descriptor" if the server socket was closed
      except Exception as oException:
        if (
          fbExceptionMeansSocketShutdown(oException)
          or fbExceptionMeansSocketDisconnected(oException)
        ):
          fShowDebugOutput("Server socket disconnected; stopped accepting connections...");
          break;
        else:
          raise;
      fShowDebugOutput("New connection accepted from %s:%d..." % (sClientIP, uClientPort));
      oSelf.__fHandleNewPythonSocket(oPythonSocket);
      fShowDebugOutput("Waiting to accept next connection...");
    fShowDebugOutput("cTCPIPConnectionAcceptor terminated.");
    oSelf.__oTerminatedLock.fRelease();
    oSelf.fFireCallbacks("terminated");
  
  def __fHandleNewPythonSocket(oSelf, oPythonSocket):
    oNewConnection = oSelf.foCreateNewConnectionForPythonSocket(oPythonSocket);
    if oSelf.__ozSSLContext:
      try:
        oNewConnection.fSecure(oSelf.__ozSSLContext, bCheckHostname = False, nzTimeoutInSeconds = oSelf.__nzSecureTimeoutInSeconds);
      except oNewConnection.cTimeoutException as oException:
        fShowDebugOutput("Timeout while securing connection.");
        oSelf.fFireCallbacks("connection cannot be secured", oNewConnection, "timeout");
        return;
      except oNewConnection.cShutdownException as oException:
        fShowDebugOutput("Shut down while securing connection.");
        oSelf.fFireCallbacks("connection cannot be secured", oNewConnection, "shutdown");
        return;
      except oNewConnection.cShutdownException as oException:
        fShowDebugOutput("Disconnected while securing connection.");
        oSelf.fFireCallbacks("connection cannot be secured", oNewConnection, "disconnected");
        return;
      else:
        oSelf.fFireCallbacks("new secure connection", oNewConnection);
    else:
        oSelf.fFireCallbacks("new nonsecure connection", oNewConnection);
    oSelf.fFireCallbacks("new connection", oNewConnection);
    oSelf.__fNewConnectionHandler(oSelf, oNewConnection);
  
  def fasGetDetails(oSelf):
    # This is done without a property lock, so race-conditions exist and it
    # approximates the real values.
    bTerminated = oSelf.bTerminated;
    bStopping = not bTerminated and oSelf.__bStopping;
    return [s for s in [
      "%s:%d" % (oSelf.sHostname, oSelf.uPort),
      "secure" if oSelf.bSecure else None,
      "terminated" if bTerminated else
          "stopping" if bStopping else None,
    ] if s];
  
  def __repr__(oSelf):
    sModuleName = ".".join(oSelf.__class__.__module__.split(".")[:-1]);
    return "<%s.%s#%X|%s>" % (sModuleName, oSelf.__class__.__name__, id(oSelf), "|".join(oSelf.fasGetDetails()));
  
  def __str__(oSelf):
    return "%s#%X{%s}" % (oSelf.__class__.__name__, id(oSelf), ", ".join(oSelf.fasGetDetails()));