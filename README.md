# Lukecast

The new name for KodiKast. As Kodi 18 will be Leia....

A small python script to provide a system indicator in GNOME or Ubuntu with appindicator extensions (sigh) to stream video, or your screen to zeroconf recognised Kodi instances.

## Installation

Clone the git, or download the .py file. 
If you want a pretty looking menu icon system, you need the sub directory with icons to be next to the python file.
A desktop launcher which **only** supports drag and drop is there.

### Dependencies

Requires the python zeroconf library, you can install it with 

```pip install zeroconf```

(Or your equivalent, just make sure your python3 can find it)

As of 17.10+ you will need TopIcons or KStatusNotifierItem/AppIndicator gnome extension.
it *may* work with the Ubuntu fork fornappindicators.

## Usage

- Add the python file "lukecast.py" to your startup-items, and place the ".desktop" file somewhere.

+ Reboot, or start the python manually

+ Open the Lukecast menu and select a "receiver" from the submenu

+ Now either 
	+ drop a file on the desktop file
	+ Choose from the menu to stream your screen
	+ Choose from the menu to stream a file (presents a dialog)
	
## Disclaimers

This is *pretty* hacky. It was a quick'n'dirty solution to allow me to stream my screen to several different Kodi systems. I expanded it to video files and tidied it a little bit, but its still not a great example of coding.

## Limitations

Tested on Ubuntu 16.10, 17.04 with python3
Additionally 17.10 Ubuntu-Gnome.
