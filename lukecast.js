#!/usr/bin/env gjs

const GLib         = imports.gi.GLib;
const Gio          = imports.gi.Gio;
const AppIndicator = imports.gi.AppIndicator3;
// const Avahi = imports.gi.avahiClient;

// Check for dependents
let [res, out, err, status] = GLib.spawn_command_line_sync('which cvlc');
const VLCavailable = out;

(function(Gtk) {'use strict';
    Gtk.init(null);

    function DisplayError(errstr) {
    const win = new Gtk.Window({ // create a new Window
      type: Gtk.WindowType.TOPLEVEL, // as top-level
      window_position: Gtk.WindowPosition.CENTER // centered on the screen
    });

    win.set_default_size(200, 80);
    win.add(new Gtk.Label({
      label: 'Error : ' + errstr
    }));

    win.connect('show', () => {
      win.set_keep_above(true);
      Gtk.main();
    });

    win.connect('destroy', () => Gtk.main_quit());
    win.show_all();
    }

    function get_resource_path(rel_path) {
    return "/home/gaz/Desktop/lukecast/"+rel_path;
    // TODO
    }
    // Check for dependencies
    if (VLCavailable === "") {
    DisplayError("VLC is not installed.");
    }
    let indicator = AppIndicator.Indicator.new("indicator-lukecast", "KodiKast-Red.png", AppIndicator.IndicatorCategory.SYSTEM_SERVICES);

    indicator.set_icon_theme_path(get_resource_path("kodikasticons/"));
    indicator.set_icon("KodiKast-Red");
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE);
    let mode = 0;

    var menu = new Gtk.Menu();
    let item = new Gtk.MenuItem();
    item.set_label("Available Receivers");
    let submenu = new Gtk.Menu();
    let subitem = new Gtk.RadioMenuItem();
    subitem.set_label("Nowhere");
    subitem.set_active({"is_active": "True"});
    subitem.connect("activate", handlesubChecks); // ??
    subitem.show();
    submenu.append(subitem);
    submenu.show();
    item.set_submenu(submenu);
    let SubMenuGroup = subitem;
    let SubMenuRef = submenu;
    item.show();
    menu.append(item);

    function addMenuItem(menuobj, labelstr, handlerfunc) {
        let item = new Gtk.MenuItem();
        item.set_label(labelstr);
        item.connect("activate", handlerfunc);
        item.show();
        menuobj.append(item);
    }
    function addMenuSep(menuobj) {
        let item = new Gtk.SeparatorMenuItem();
        item.show();
        menuobj.append(item);
    }
    addMenuSep(menu);
    addMenuItem(menu, "Start Screen Cast", handler_cast_start);
    addMenuItem(menu, "Start File Cast...", handler_cast_file);
    addMenuItem(menu, "Stop Case", handler_cast_stop);
    addMenuSep(menu);
    addMenuItem(menu, "Exit", handler_menu_exit);

    menu.show();
    indicator.set_menu(menu);
    GLib.timeout_add_seconds(1, 1, handler_timeout)
    // ************************

    function handlesubChecks() {}
    function handler_cast_start() {}
    function handler_cast_file() {}
    function handler_cast_stop() {}
    function handler_menu_exit() {
        loop.quit();
        Gtk.main_quit();
    }
    function handler_timeout() {}

    let ServiceBrowser = Gio.DBusProxy.new_for_bus(
        Gio.BusType.SYSTEM,
        Gio.DBusProxyFlags.NONE,
        [],
        "org.kodi.scanner",
        "/org/freedesktop/Avahi/Server",
        "org.freedesktop.Avahi",
        [],
        function(cb){ print("ere"); }
    );

    ServiceBrowser.connectSignal("ItemNew", function(proxy) {
        let newName = proxy.name;
        print("Found " + newName);
    });

    let loop = new GLib.MainLoop(null, false);
    loop.run();
    // Gtk.main();

}(imports.gi.Gtk));
