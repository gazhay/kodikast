#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as AppIndicator
except:
    from gi.repository import AppIndicator

import re,subprocess,socket
import urllib.parse,time,os,signal,sys
import base64
from random import randint
from zeroconf import ServiceBrowser, Zeroconf

from gi.repository import GObject
tempsock = "/tmp/lukecast"

# TODO
# Playlist  - if we can vlc:quit after a file, we can do multiple files
# Broadcast - stream to all clients found
# Authorisation at Kodi End - uname pwd
#
VERSION = "0.5a"
ICONDIR = "./kodikasticons"
DEVMODE = True

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def alert(msg):
    parent = None
    md = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.CLOSE, msg)
    md.run()
    md.destroy()

Hosts        = []
MandatoryFudgePeriod = 3;

# Check for VLC
isVLC = subprocess.run(["which vlc"], stdout=subprocess.PIPE, shell=True)
# print(isVL/C.stdout)
if (isVLC.stdout==b''):
    alert("VLC is not installed, cannot continue")
    quit()
# Check for webcam
videoDevs = subprocess.run(["ls /dev/video* | wc -l"], stdout=subprocess.PIPE, shell=True)
if (videoDevs.stdout!=b''):
    # print("Number of devices {%d}" % int(videoDevs.stdout));
    videoOn=True
else:
    videoOn=False

def get_resource_path(rel_path):
    dir_of_py_file = os.path.dirname(__file__)
    rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
    abs_path_to_resource = os.path.abspath(rel_path_to_resource)
    return abs_path_to_resource

# ############################################################################## Indicator
class IndicatorKodicast:
    SubMenuRef   = ""
    SubMenuGroup = ""
    KodiTarget   = ""
    VLCPid       = ""
    mode         = 0
    # lastConnect  = None
    # statusIcons = [ "KodiKast-Red", "KodiKast-Grn", "KodiKast-Ylw", "KodiKast-Ppl" ]
    statusIcons = [ "LukeInit", "LukeGrey", "LukeGreen", "LukeBlue" ]

    def addSeperator(self, menu):
        item = Gtk.SeparatorMenuItem()
        item.show()
        menu.append(item)

    def addMenuItem(self, menu, label, handler):
        item = Gtk.MenuItem()
        item.set_label(label)
        item.connect("activate", handler)
        item.show()
        menu.append(item)

    def addRadioMenu(self, menu, label):
        item = Gtk.CheckMenuItem(label=label)
        item.set_active(is_active=False)
        # item.connect("activate", self.toggleMe)
        item.show()
        menu.append(item)

    def addSubMenu(self, menu, label):
        pass

    def aboutDialog(self, evt):
        dlg = Gtk.AboutDialog();
        dlg.set_name("About...")
        dlg.set_program_name("Luke Cast")
        dlg.set_version(VERSION)
        dlg.set_comments("""
A GTK Indicator to stream media to Avahi discovered Kodi instances.

Media, Screen, Webcam, to any Kodi with jsonrpc enabled.
        """)
        dlg.set_authors(['Gareth Hay'])
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(get_resource_path(ICONDIR)+"/"+self.statusIcons[ randint(0, len(self.statusIcons)-1) ]+".png" , 100, 100)
        dlg.set_logo(pixbuf)
        # dlg.set_logo_icon_name("kodi")
        dlg.show()

    def reboot(self, evt):
        self.handler_cast_stop()
        Gtk.main_quit()
        os.execv(__file__, sys.argv)

    def __init__(self):
        self.ind = AppIndicator.Indicator.new("indicator-lukecast", self.statusIcons[0], AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
        self.ind.set_icon_theme_path( get_resource_path(ICONDIR))
        self.ind.set_icon( self.statusIcons[0] )
        self.ind.set_status (AppIndicator.IndicatorStatus.ACTIVE)
        self.mode = 0

        # have to give indicator a menu
        self.menu = Gtk.Menu()

        self.addMenuItem( self.menu, "About...", self.aboutDialog)
        if DEVMODE:
            self.addMenuItem( self.menu, "Restart", self.reboot)
            self.addMenuItem(self.menu, "Reconnect Receiver", self.handler_reconnect )
        self.addSeperator(self.menu)

        item = Gtk.MenuItem()
        item.set_label("Available Receivers")
        submenu = Gtk.Menu()
        subitem = Gtk.RadioMenuItem(group=None, label="Nowhere")
        subitem.set_active(is_active=True)
        subitem.connect("activate", self.handlesubChecks)
        subitem.show()
        submenu.append(subitem)
        submenu.show()
        item.set_submenu( submenu )
        self.SubMenuGroup = subitem
        self.SubMenuRef = submenu
        item.show()
        self.menu.append(item)

        self.addSeperator( self.menu )
        self.addMenuItem(self.menu, "Start Screen Cast" , self.handler_cast_start)
        self.addMenuItem(self.menu, "Start File Cast...", self.handler_cast_file )
        if videoOn:
            self.addMenuItem(self.menu, "Start Webcam Stream0" , self.handler_cast_cam  )
            self.addRadioMenu(self.menu, "    With Sound")
        self.addMenuItem(self.menu, "Stop Cast"         , self.handler_cast_stop )
        self.addSeperator( self.menu )
        self.addMenuItem(self.menu, "Exit"              , self.handler_menu_exit )

        self.menu.show()
        self.ind.set_menu(self.menu)

        GLib.timeout_add_seconds(1, self.handler_timeout)

    def handler_reconnect(self,evt=None, hosts=None):
        if hosts==None:
            hosts = self.KodiTarget
        if socket.gethostname().find('.')>=0:
            thisisme=socket.gethostname()
        else:
            thisisme=socket.gethostbyaddr(socket.gethostname())[0]

        jsonpart  = {'request' : '{"jsonrpc":"2.0", "id":1, "method": "Player.Open","params":{"item":{"file":"http://%s:8554/stream.mp4"}}}' % thisisme }
        jsonstr   = urllib.parse.urlencode(jsonpart) # added parse. as its moved in python3
        # This will have to be for multiple hosts
        streamUrl = 'http://%s:8080/jsonrpc?' % (hosts)
        streamUrl+= jsonstr
        credentials = b'kodi:test'
        encoded_credentials = base64.b64encode(credentials)
        authorization = b'Basic ' + encoded_credentials
        command   = "/usr/bin/curl -g -H 'Content-Type: application/json' -H 'Authorization: %s' -H 'Accept: application/json' '%s'" % (authorization.decode("utf-8") , streamUrl)
        print("Executing %s" % command)
        curlProc  = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
        print(curlProc.stdout)
    connect_hosts=handler_reconnect

    def handlesubChecks(self, evt):
        if evt.get_active()==True:
            self.KodiTarget = evt.get_label()
            self.mode = 1
            if self.KodiTarget == "Nowhere":
                self.mode = 0

    def handler_menu_exit(self, evt):
        Gtk.main_quit()

    def handler_cast_file(self, evt):
        dialog = Gtk.FileChooserDialog("Please choose a file", None,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.set_name("Videos")
        filter.add_mime_type("video/mpeg")
        filter.add_pattern("*.mp4")
        filter.add_pattern("*.ogg")
        filter.add_pattern("*.mkv")
        filter.add_pattern("*.mpeg")
        filter.add_pattern("*.avi")
        dialog.add_filter(filter)

        response = dialog.run()
        ff = self.fudgeUri(dialog.get_filename())
        dialog.destroy()
        time.sleep(0.1)
        if response == Gtk.ResponseType.OK:
            self.streamUrlTo( ff, self.KodiTarget )
            return
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

    def fudgeUri(self, inuri):
        return "file://"+(inuri.replace("\n","").replace(" ","\ ")+" vlc://quit")

    # /* Handle a dropped file on a desktop file with code below */
    def handler_drop_cast_start(self):
        content = open(tempsock, 'r').read()
        if (len(content)>0):
            # trim this and cvlc stream it.
            # refactor stream launch code to function(url, hosts)
            open(tempsock,"w").close()
            content=self.fudgeUri(content)
            # print(content)
            if not self.targetCheck():
                alert("No target selected")
                return
            self.streamUrlTo( content, self.KodiTarget )
        self.lastConnect = None
        time.sleep(0.1) # stops a cpu 100% problem
        return True

    def targetCheck(self):
        if (self.KodiTarget == "") or (self.KodiTarget=="Nowhere"):
            return False
        return True

    def streamUrlTo(self, uri, hostlist):
        self.mode = 2 # :input-slave=alsa://hw:0,0
        sout = "#transcode{vcodec=h264,acodec=mpga,ab=128,channels=2,samplerate=44100}:standard{access=http,mux=ts,ttl=15,dst=:8554/stream.mp4"
        # sout = "#transcode{vcodec=h264,scale=1,vb=0}:standard{access=http,mux=ts,ttl=15,dst=:8554/}"
        command     = 'vlc -Idummy '+uri+' --sout "%s"' % sout
        # print("## Command to exec")
        # print(command)
        # print("##")
        self.VLCPid = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
        self.handler_reconnect(hosts=hostlist)

    def handler_cast_start(self, evt=None):
        if not self.targetCheck():
            alert("No target selected")
            return
        self.streamUrlTo("screen:// :screen-fps=10 :screen-caching=10 vlc://quit", self.KodiTarget)

    def handler_cast_cam(self, evt):
        if not self.targetCheck():
            alert("No target selected")
            return
        # With audio here
        self.streamUrlTo("v4l2:///dev/video0 vlc://quit", self.KodiTarget)

    def handler_cast_stop(self, evt=None):
        self.stopCasting()

    def handler_timeout(self):
        """This will be called every few seconds by the GLib.timeout.
        """
        if self.KodiTarget=="Nowhere":
            self.KodiTarget=""
            self.mode = 0
        if self.KodiTarget=="" and self.VLCPid != "":
            self.killVLC()

        if self.VLCPid != "":
            try:
                if self.VLCPid.poll()==None:
                    pass
                else:
                    self.mode = 1
            except OSError:
                self.mode = 1
        if (self.ind.get_icon() != self.statusIcons[self.mode]):
          self.ind.set_icon(self.statusIcons[self.mode])

        return True

    def killVLC( self ):
        try:
            os.killpg(os.getpgid(self.VLCPid.pid), signal.SIGTERM)
        except:
            command = 'killall vlc'
            process = subprocess.run(command, shell=True)

    def stopCasting( self ):
        self.mode = 1
        self.killVLC()

    def quitApp( self ):
        self.stopCasting()

    def main(self):
        #  attempt multiprocess shenanigans
        GObject.idle_add(self.handler_drop_cast_start)
        Gtk.main()

# ############################################################################## Avahi
class AvahiListener(object):
    # Having problems removing - could be pyhton2->3 conversioj rpbos
    target = ""
    DEBUGME = False;

    def remove_service(self, zeroconf, type, name):
        for host in Hosts:
            if host.get("name")== name:
                info = host

        for itemA in self.target.SubMenuRef.get_children():
            if itemA.get_label()==info['info'].server:
                if itemA.get_active():
                    self.target.KodiTarget = ""
                    self.target.mode=0
                self.target.SubMenuRef.remove(itemA) #itemA.remove()
                if self.DEBUGME: print("Service %s removed" % (info['info'].server,))

        Hosts.remove(info)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        # subitem = Gtk.CheckMenuItem()
        subitem = Gtk.RadioMenuItem(group=self.target.SubMenuGroup, label=info.server)
        subitem.connect("activate", self.target.handlesubChecks)
        subitem.set_label(info.server)
        subitem.show()
        self.target.SubMenuRef.append(subitem)
        self.target.SubMenuRef.show()
        Hosts.append({"name": name, "info": info})
        if self.DEBUGME: print("Service %s removed" % (info['info'].server,))

    def setTarget(self, targetobj):
        self.target = targetobj

# ############################################################################## Main

if __name__ == "__main__":
    try:
        zeroconf = Zeroconf()
        listener = AvahiListener()
        ind      = IndicatorKodicast()
        listener.setTarget(ind);
        browser  = ServiceBrowser(zeroconf, "_xbmc-jsonrpc._tcp.local.", listener)
        try:
            open(tempsock,"w").close();
        except:
            print( "socket file not available")
            pass

        ind.main()
    finally:
        ind.handler_cast_stop()
