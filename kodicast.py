#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as AppIndicator
except:
    from gi.repository import AppIndicator

import re,subprocess,socket
import urllib.parse,time,os,signal
from zeroconf import ServiceBrowser, Zeroconf

from gi.repository import GObject
tempsock = "/tmp/kodikast"

# TODO
# Playlist - if we can vlc:quit after a file, we can do multiple files
#

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def alert(msg):
    parent = None
    md = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.CLOSE, msg)
    md.run()
    md.destroy()

Hosts        = []
MandatoryFudgePeriod = 3;

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

    def __init__(self):
        self.ind = AppIndicator.Indicator.new(
                            "indicator-kodicast",
                            "KodiKast-Red.png",
                            AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
        self.ind.set_icon_theme_path( get_resource_path("./kodikasticons"))
        # icon_image = os.path.dirname(__file__) + "kodikasticons/KodiKast-Red.png"
        self.ind.set_icon( "KodiKast-Red" )
        # need to set this for indicator to be shown
        # print(icon_image)
        # print(self.ind.get_icon_theme_path())
        # print(self.ind.get_icon())
        self.ind.set_status (AppIndicator.IndicatorStatus.ACTIVE)
        self.mode = 0

        # have to give indicator a menu
        self.menu = Gtk.Menu()

        item = Gtk.MenuItem()
        item.set_label("Available Receivers")
        #
        submenu = Gtk.Menu()
        subitem = Gtk.RadioMenuItem(group=None, label="Nowhere")
        # subitem.set_label("Nowhere")
        subitem.set_active(is_active=True)
        subitem.connect("activate", self.handlesubChecks)
        subitem.show()
        submenu.append(subitem)
        submenu.show()
        item.set_submenu( submenu )
        self.SubMenuGroup = subitem
        self.SubMenuRef = submenu
        #
        # self.addReceiverMenu()
        item.show()
        self.menu.append(item)

        item = Gtk.SeparatorMenuItem()
        item.show()
        self.menu.append(item)

        item = Gtk.MenuItem()
        item.set_label("Start Screen Cast")
        item.connect("activate", self.handler_cast_start)
        item.show()
        self.menu.append(item)

        item = Gtk.MenuItem()
        item.set_label("Start File Cast...")
        item.connect("activate", self.handler_cast_file)
        item.show()
        self.menu.append(item)

        item = Gtk.MenuItem()
        item.set_label("Stop Cast")
        item.connect("activate", self.handler_cast_stop)
        item.show()
        self.menu.append(item)

        item = Gtk.SeparatorMenuItem()
        item.show()
        self.menu.append(item)

        # this is for exiting the app
        item = Gtk.MenuItem()
        item.set_label("Exit")
        item.connect("activate", self.handler_menu_exit)
        item.show()
        self.menu.append(item)

        self.menu.show()
        self.ind.set_menu(self.menu)

        GLib.timeout_add_seconds(1, self.handler_timeout)

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
            if (self.KodiTarget == "") or (self.KodiTarget=="Nowhere"):
                alert("No target selected")
                return
            self.streamUrlTo( content, self.KodiTarget )

        time.sleep(0.1) # stops a cpu 100% problem
        return True

    def streamUrlTo(self, uri, hostlist):
        self.mode = 2
        command     = 'cvlc '+uri+' --sout "#transcode{vcodec=h264,scale=1,vb=0}:standard{access=http,mux=ts,ttl=15,dst=:8554/}"'
        print("## Command to exec")
        print(command)
        print("##")
        self.VLCPid = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
        # Not sure about the sleep
        # time.sleep(MandatoryFudgePeriod)

        ## Find my address and compile json to read stream from me
        if socket.gethostname().find('.')>=0:
            thisisme=socket.gethostname()
        else:
            thisisme=socket.gethostbyaddr(socket.gethostname())[0]
        jsonpart  = {'request' : '{"jsonrpc":"2.0", "id":1, "method": "Player.Open","params":{"item":{"file":"http://%s:8554/"}}}' % thisisme }
        jsonstr   = urllib.parse.urlencode(jsonpart) # added parse. as its moved in python3
        # This will have to be for multiple hosts
        streamUrl = 'http://%s:8080/jsonrpc?' % (hostlist)
        streamUrl+= jsonstr
        command   = "/usr/bin/curl -g -H 'Content-Type: application/json' -H 'Accept: application/json' '%s'" % (streamUrl)
        curlProc  = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        output    = curlProc.communicate()[0]
        print(output)

    def handler_cast_start(self, evt):
        if (self.KodiTarget == "") or (self.KodiTarget=="Nowhere"):
            alert("No target selected")
            return

        self.streamUrlTo("screen:// :screen-fps=10 :screen-caching=10 vlc://quit", self.KodiTarget)

    def handler_cast_stop(self, evt=None):
        self.mode = 1
        try:
            os.killpg(os.getpgid(self.VLCPid.pid), signal.SIGTERM)
        except:
            command = 'killall vlc'
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
            output = process.communicate()[0]

    def handler_timeout(self):
        """This will be called every few seconds by the GLib.timeout.
        """
        if self.VLCPid != "":
            try:
                if self.VLCPid.poll()==None:
                    pass
                else:
                    self.mode = 1
            except OSError:
                self.mode = 1
        if self.mode == 0:
          if (self.ind.get_icon() != "KodiKast-Red"):
            self.ind.set_icon("KodiKast-Red")
        elif self.mode == 1:
          if (self.ind.get_icon() != "KodiKast-Grn"):
            self.ind.set_icon("KodiKast-Grn")
        elif self.mode == 2:
            if (self.ind.get_icon() != "KodiKast-Ylw"):
              self.ind.set_icon("KodiKast-Ylw")
        else:
          self.ind.set_icon("KodiKast-Ppl")

        return True

    def main(self):
        #  attempt multiprocess shenanigans
        GObject.idle_add(self.handler_drop_cast_start)
        Gtk.main()

# ############################################################################## Avahi
class AvahiListener(object):
    # Having problems removing - could be pyhton2->3 conversioj rpbos
    target = ""

    def remove_service(self, zeroconf, type, name):
        for host in Hosts:
            if host.get("name")== name:
                info = host

        for itemA in self.target.SubMenuRef.get_children():
            # try:
                # print("label")
                # print(itemA.get_label())
                if itemA.get_label()==info['info'].server:
                    if itemA.get_active():
                        self.target.KodiTarget = ""
                        self.target.mode=0
                    self.target.SubMenuRef.remove(itemA) #itemA.remove()
                    print("Service %s removed" % (info['info'].server,))
            # except:
                # print("Menu Error")

        # print("### REMOVE ###")
        Hosts.remove(info)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        # print name, info.get_name(), info.server,
        # print name, info
        subitem = Gtk.CheckMenuItem()
        subitem = Gtk.RadioMenuItem(group=self.target.SubMenuGroup, label=info.server)
        subitem.connect("activate", self.target.handlesubChecks)
        subitem.set_label(info.server)
        subitem.show()
        self.target.SubMenuRef.append(subitem)
        self.target.SubMenuRef.show()
        Hosts.append({"name": name, "info": info})

    def setTarget(self, targetobj):
        self.target = targetobj

# ############################################################################## Main

if __name__ == "__main__":
    try:
        zeroconf = Zeroconf()
        listener = AvahiListener()
        ind      = IndicatorKodicast()
        # print ind.SubMenuRef
        listener.setTarget(ind);
        # print listener.target
        browser  = ServiceBrowser(zeroconf, "_xbmc-jsonrpc._tcp.local.", listener)
        try:
            open(tempsock,"w").close();
        except:
            print( "socket file not available")
            pass

        ind.main()
    # zeroconf.close()
    finally:
        ind.handler_cast_stop()
