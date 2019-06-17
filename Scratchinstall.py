#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Luglio 2018 - Stefano Salvi stefano@salvi.mn.it
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

## Installati di default (interfaccia grafica)
## python-gi - PyGObject - usato per accedere a GTK

## wget -O adobe-air.sh http://drive.noobslab.com/data/apps/AdobeAir/adobe-air.sh
## chmod +x adobe-air.sh;sudo ./adobe-air.sh
##
## Adobe AIR è fermo alla versione 2.6 e a 32 bit.
## L'installer di Adobe Air è:
## http://airdownload.adobe.com/air/lin/download/2.6/AdobeAIRInstaller.bin
##
## Rimozione:
## sudo apt-get autoremove adobeair edu.media.mit.scratch2editor
##
## Installazione di Scrarch:
## https://scratch.mit.edu/scratch2download/
## Occorre scaricare la versione ".air", disponibile per MAC vecchi OSX.
## Il file da scaricare è  Scrach-<nnn[.n]>.air
## File che contiene l'ultima versione di AIR:
## https://scratch.mit.edu/scratchr2/static/sa/version.xml
## <?xml version="1.0" encoding="utf-8"?>
## <update xmlns="http://ns.adobe.com/air/framework/update/description/2.5">
##     <versionNumber>461</versionNumber>
##     <url>http://cdn.scratch.mit.edu/scratchr2/static/sa/Scratch-461.air</url>
##     <description>Scratch 2 Offline Editor</description>
## </update>
## La versione corrente NON FUNZIONA (penso manchino i dati)
## La funzione funzionante (non so se l'ultima):
## http://cdn.scratch.mit.edu/scratchr2/static/sa/Scratch-442.air
## Risulta che l'ultima funzionante sia la 455
##
## https://wiki.gnome.org/Projects/PyGObject/Threading
##
## Pare che gli errori di GTK nelle applicazioni siano dovuti alla mancanza di gnome-themes-standard per I386
## Vedere anche l'articolo:
## http://forum.debianizzati.org/viewtopic.php?f=15&t=54275
##
## file mancanti:
## Installare
## apt install flashplugin-nonfree-extrasound
## ln -s /usr/lib/flashplugin-nonfree-extrasound/libflashsupport.so /usr/lib/i386-linux-gnu
## ln -s /usr/lib/i386-linux-gnu/libasound.so.2 /usr/lib/i386-linux-gnu/libasound.so
##
## /data1/air/vobs/pchoudhu_apollo_main_lin_2/SDK/unix/nss/libnssckbi.so
## libflashsupport.so
## libasound.so
##

import gi
import os, errno
import os.path
import sys
import threading
import urllib.request
import time
import re
import shlex
import shutil
import subprocess
import argparse

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk, GObject

DESKTOP_FILE = '''[Desktop Entry]
Type=Application
Name=Scratch 2
Comment=Ide visuale per bambini
Exec=/opt/adobe-air-sdk/bin/adl -nodebug /opt/adobe-air-sdk/scratch/META-INF/AIR/application.xml /opt/adobe-air-sdk/scratch
Icon=/opt/adobe-air-sdk/scratch/icons/AppIcon128.png
Terminal=false
NoDisplay=false
StartupNotify=true
Categories=Development;
Keywords=ide;coding;
MimeType=application/x-scratch-project;
'''

class ShowActionDialog(Gtk.Dialog):
    def __init__(self, parent, message):
        Gtk.Dialog.__init__(self, "Installazione", parent, 0)
        self.set_default_size(150, 100)
        self.label = Gtk.Label(message)
        scroll = Gtk.ScrolledWindow ()
        box = self.get_content_area()
        box.set_orientation='vertical'
        box.set_spacing=6;

        box.pack_start(self.label, False, False, 0)
        textbox = Gtk.TextView()
        textbox.set_editable(False)
        self.text = textbox.get_buffer()
        box.pack_start(textbox, False, False, 0)
        self.show_all()

    def add_to_log(self, message):
        if len(message) > 100:
            message = message[:96] + "...\n"
        self.text.insert_at_cursor(message,-1)
        if self.text.get_line_count() > 10:
            start = self.text.get_start_iter()
            end = self.text.get_iter_at_line(1)
            self.text.delete(start, end)

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Installazione di Scratch2")

        self.tempdir = os.path.expanduser('~/scratch2_install_tmp')
        if not os.path.isdir(self.tempdir):
            self.tempdir = os.path.expanduser('~')

        vbox = Gtk.Box(orientation='vertical',spacing=6)
        vbox.set_border_width(10)
        self.add(vbox)

        frame = Gtk.Frame();
        frame.set_label("Adobe AIR SDK")
        vbox1 = Gtk.Box(orientation='vertical',spacing=6)
        frame.add(vbox1)
        vbox.pack_start(frame, False, False, 0)

        hbox = Gtk.Box(spacing=6)
        vbox1.pack_start(hbox, False, False, 0)

        self.airFromNet = Gtk.RadioButton.new_with_label_from_widget(None, "Scarica dalla rete")
        self.airFromNet.connect("toggled", self.on_air_button_toggled)
        hbox.pack_start(self.airFromNet, False, False, 0)

        airFromDisk = Gtk.RadioButton.new_with_label_from_widget(self.airFromNet,"Installa da file")
        # airFromDisk.connect("toggled", self.on_button_toggled, "2")
        hbox.pack_start(airFromDisk, False, False, 0)

        filter = Gtk.FileFilter()
        filter.set_name("tbz2 files")
        filter.add_pattern("*.tbz2")
        self.fileButtonAir = Gtk.FileChooserButton ();
        self.fileButtonAir.set_title("Seleziona l'SDK di Adobe Air")
        self.fileButtonAir.add_filter(filter)
        self.fileButtonAir.set_current_folder(self.tempdir)
        self.fileButtonAir.set_sensitive(False)
        vbox1.pack_start(self.fileButtonAir, False, False, 0)

        frame = Gtk.Frame();
        frame.set_label("Scratch 2.0")
        vbox1 = Gtk.Box(orientation='vertical',spacing=6)
        frame.add(vbox1)
        vbox.pack_start(frame, False, False, 0)

        hbox = Gtk.Box(spacing=6)
        vbox1.pack_start(hbox, False, False, 0)

        self.scratchFromNet = Gtk.RadioButton.new_with_label_from_widget(None, "Scarica dalla rete")
        self.scratchFromNet.connect("toggled", self.on_scratch_button_toggled)
        hbox.pack_start(self.scratchFromNet, False, False, 0)

        scratchFromFile = Gtk.RadioButton.new_with_label_from_widget(self.scratchFromNet, "Installa da file")
        # button2.connect("toggled", self.on_button_toggled, "2")
        hbox.pack_start(scratchFromFile, False, False, 0)

        filter = Gtk.FileFilter()
        filter.set_name("Air files")
        filter.add_pattern("*.air")
        self.fileButtonScratch = Gtk.FileChooserButton()
        self.fileButtonScratch.set_title("Seleziona il pacchetto air con scratch2");
        self.fileButtonScratch.add_filter(filter)
        self.fileButtonScratch.set_current_folder(self.tempdir)
        self.fileButtonScratch.set_sensitive(False)
        vbox1.pack_start(self.fileButtonScratch, False, False, 0)

        self.button = Gtk.Button(label="Installa Scratch 2")
        self.button.connect("clicked", self.on_button_clicked)
        vbox.pack_start(self.button, False, False, 0)

        self.action_dialog = None

        vermsg = check_os()
        if vermsg != None:
            print (vermsg)
            self.error_message(vermsg)
            raise ValueError(vermsg)

    def on_air_button_toggled (self, button):
        self.fileButtonAir.set_sensitive(not button.get_active())

    def on_scratch_button_toggled (self, button):
        self.fileButtonScratch.set_sensitive(not button.get_active())

    def error_message(self, message, isinfo = False):
        if isinfo:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK, "Messaggio:")
        else:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "ERRORE:")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_action_message(self, message):
        if self.action_dialog == None:
            self.action_dialog = ShowActionDialog(self, message)
            self.action_dialog.show()
        else:
            self.action_dialog.label.set_text(message)

    def append_action_message(self, message):
        #import pdb; pdb.set_trace()
        if self.action_dialog == None:
            self.action_dialog = ShowActionDialog(self, "")
            self.action_dialog.show()
        self.action_dialog.add_to_log(message)

    def close_action_message(self):
        if self.action_dialog != None:
           self.action_dialog.destroy()
           self.action_dialog = None

    def create_scratch_downoad_directory(self):
        self.show_action_message("Creo la directory per il download dei pacchetti")
        self.tempdir = os.path.expanduser('~/scratch2_install_tmp')
        try:
            os.makedirs(self.tempdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                return False
        return True

    def download_file(self, url, filename, basemessage):
        GLib.idle_add(self.show_action_message, basemessage)
        try:
            u = urllib.request.urlopen(url)
            f = open(filename, 'wb')
            meta = u.info()
            file_name = url.split('/')[-1]
            file_size = int(u.getheader("Content-Length"))
            basemessage = basemessage + "\nScarico: %s Bytes: %s" % (file_name, file_size)
            GLib.idle_add(self.show_action_message, basemessage)

            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                GLib.idle_add(self.show_action_message, basemessage + "\n" + r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size))

            f.close()
        except BaseException as e:
            print ("download_file - ERRORE:" + str(e))
            GLib.idle_add(self.error_message, "Scaricamneto File Fallito")
            return False
        return True

    def get_url(self, url, basemessage):
        GLib.idle_add(self.show_action_message, basemessage)
        message = "";
        file_name = url.split('/')[-1]
        try:
            u = urllib.request.urlopen(url)
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            basemessage = basemessage + "\nScarico: %s Bytes: %s" % (file_name, file_size)
            GLib.idle_add(self.show_action_message, basemessage)
            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                message += buffer
                GLib.idle_add(self.show_action_message, basemessage + "\n" + r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size))
        except BaseException as e:
            print ("get_url - ERRORE:" + str(e))
            GLib.idle_add(self.error_message, "Scaricamneto Messaggio")
            return None
        return message

    def get_air_installer(self):
        if self.airFromNet.get_active():
            if not self.create_scratch_downoad_directory():
                return False
            self.air_installer_file = self.tempdir + "/AdobeAIRSDK.tbz2"
            return self.download_file("http://airdownload.adobe.com/air/lin/download/2.6/AdobeAIRSDK.tbz2" ,self.air_installer_file ,"Scarico Adobe Air dalla rete")
        else:
            self.air_installer_file = self.fileButtonAir.get_filename()
            if self.air_installer_file == None:
                GLib.idle_add(self.error_message, "Non hai scelto il file con il pacchetto AIR di Scratch")
                return False
            else:
                GLib.idle_add(self.show_action_message, "Installo Air dal file" + self.air_installer_file)
        return True

    def get_scratch_installer(self):
        if self.scratchFromNet.get_active():
            # message = self.get_url("https://scratch.mit.edu/scratchr2/static/sa/version.xml", "Cerco la versione di scratch")
            # if message == None:
            #     return False
            # m = re.search('<versionNumber>([0-9.]*)</versionNumber>.*<url>(.*)</url>', message, re.MULTILINE | re.DOTALL)
            # if m == None:
            #     GLib.idle_add(self.error_message, "Non riesco ad individuare la versione corrente di Scratch")
            #     return False
            # if not self.create_scratch_downoad_directory():
            #     return False
            # GLib.idle_add(self.show_action_message, "Installo la versione " + m.group(1) + " dall'indirizzo " + m.group(2))
            # self.scrathFile = self.tempdir + "/" + m.group(2).split('/')[-1]
            # return self.download_file(m.group(2), self.scrathFile,"Scarico Scratch 2 dalla rete")
            GLib.idle_add(self.show_action_message, "Installo la versione 458 Di Scratch 2")
            self.scrathFile = self.tempdir + "/Scratch-458.0.1.air"
            return self.download_file("https://scratch.mit.edu/scratchr2/static/sa/Scratch-458.0.1.air", self.scrathFile, "Scarico Scratch 2 dalla rete")
        else:
            self.scrathFile = self.fileButtonScratch.get_filename()
            if self.scrathFile == None:
                GLib.idle_add(self.error_message, "Non hai scelto il file con il pacchetto AIR di Scratch")
                return False
            else:
                GLib.idle_add(self.show_action_message, "Installo Scratch2 dal file" + self.scrathFile)
        return True

    def run_installation(self):
        GLib.idle_add(self.show_action_message, "Inizio l'installazione - avvio della parte privilegiata")
        GLib.idle_add(self.append_action_message, "Lancio la sessione in area privilegiata")
        print ("Avvio l'installazione con pkexec")
        # import pdb; pdb.set_trace()
        inst = subprocess.Popen(['/usr/bin/pkexec', os.path.realpath(__file__), '--root-action', '--air-installer=' + self.air_installer_file, '--scratch2-installer=' + self.scrathFile,
            "--xauthority=" + os.environ['XAUTHORITY'] ], stdout=subprocess.PIPE ,stderr=subprocess.STDOUT)
        while True:
            line = inst.stdout.readline().decode('utf-8')
            print (line, end='')
            GLib.idle_add(self.append_action_message, line)
            if line == '' and inst.poll() != None:
                break
        # result = subprocess.Popen(['/usr/bin/pkexec', '/bin/bash', '-c',
        #    'export DISPLAY=:0; XAUTHORITY=' + os.environ['XAUTHORITY'] + '; ' + os.path.realpath(__file__) + ' --root-action --air-installer="' + self.air_installer_file + '" --scratch2-installer="' + self.scrathFile + '"' ],
        #    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        #(out, _) = result.communicate()
        #for char in out:
        #    #for char in result.stdout:
        #    sys.stdout.write(char)
        #    GLib.idle_add(self.append_action_message, char)
        if inst.returncode == 1:
            GLib.idle_add(self.error_message, "Il file SDK di Adobe Air " + self.air_installer_file + " non esiste o non è leggibile")
        elif inst.returncode == 2:
            GLib.idle_add(self.error_message, "Il file di installazione di Scratch2 " + self.scrathFile + " non esiste o non è leggibile")
        elif inst.returncode == 3:
            GLib.idle_add(self.error_message, "La versione del sistema operativo non è supportata")
        elif inst.returncode == 4:
            GLib.idle_add(self.error_message, "Installazione delle dipendenze fallita")
        elif inst.returncode == 5:
            GLib.idle_add(self.error_message, "Installazione di Adobe Air dal file " + self.air_installer_file + " fallita")
        elif inst.returncode == 6:
            GLib.idle_add(self.error_message, "Installazione di Scratch2 dal file " + self.scrathFile + " fallita")
        else:
            GLib.idle_add(self.error_message, "Installazione terminata corettamente", True)
        return inst.returncode == 0

    def install(self):
        if self.get_air_installer() and self.get_scratch_installer() and self.run_installation():
            Gtk.main_quit()
        GLib.idle_add(self.close_action_message)
        GLib.idle_add(self.button.set_sensitive, True)

    def on_button_clicked(self, widget):
        # Il dialog deve essere creato prima dell'inizio del thread
        self.show_action_message("Comincio l'installazione")
        t = threading.Thread(target=self.install)
        self.button.set_sensitive(False)
        t.start()

def check_os():
    with open('/etc/issue', 'r') as myfile:
        data = myfile.read()
    if not data.find('Ubuntu') and not data.find('Mint'):
        return "Il sistema non è né Ubuntu né Mint"
    ver = subprocess.check_output(['/usr/bin/lsb_release', '-rs']).decode("utf-8")
    versions = set(["12.04\n", "14.04\n", "14.04.1\n", "14.04.2\n", "14.04.3\n", "15.04\n", "15.10\n", "16.04\n", "16.04.1\n",
        "13\n", "17\n", "17.1\n", "17.2\n", "17.3\n", "18\n", "18.1\n", "18.04\n"])
    if not ver in versions:
        return "La versione " + ver + " del sistema operativo non è supportata"
    return None

def subprocess_call(command, new_env={}):
    new_env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    print(command)
    return subprocess.call(shlex.split(command), env=new_env)

def real_install(air_installer, scratch2_installer, xauthority):
    if not os.access(air_installer, os.R_OK):
        print("Il file SDK di Adobe Air " + air_installer + " non esiste o non è leggibile")
        sys.exit(1)
    if not os.access(scratch2_installer, os.R_OK):
        print("Il file di installazione di Scratch2 " + scratch2_installer + " non esiste o non è leggibile")
        sys.exit(2)
    print ("Installer di Air: " + air_installer)
    print ("Installer di Scratch: " + scratch2_installer)
    # Rende eseguibile l'installer di Air
    # os.chmod(air_installer, 0o755)
    # Recupera versione e architettura
    ver = subprocess.check_output(['/usr/bin/lsb_release', '-rs']).decode("utf-8")
    arch = subprocess.check_output(['/bin/uname', '-m']).decode("utf-8")

    dependencies = ''

    # import pdb; pdb.set_trace()
    # Cascata di if per le varie versioni/architetture
    if ver == "12.04\n" or ver == "13\n":
        if arch == "x86_64\n":
            dependencies = "ia32-libs lib32nss-mdns libhal-storage1 libgnome-keyring0 libgnome-keyring0 libgtk2.0-0 libxslt1.1 libxml2"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libhal-storage1 libgnome-keyring0 libgnome-keyring0 libgtk2.0-0 libxslt1.1 libxml2"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "14.04.3\n" or ver == "17.3\n":
        if arch == "x86_64\n":
            dependencies = "libxt6:i386 libnspr4-0d:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3-1d:i386 lib32nss-mdns libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "15.04\n":
        if arch == "x86_64\n":
            dependencies = "libxt6:i386 libnspr4-0d:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3-1d:i386 lib32nss-mdns libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "15.10\n":
        if arch == "x86_64\n":
            dependencies = "libxt6:i386 libnspr4-0d:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3-1d:i386 lib32nss-mdns libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "16.04\n" or ver == "18\n":
        if arch == "x86_64\n":
            ## Aggiunti libatk-adaptor e libgail-common
            dependencies = "libatk-adaptor:i386 libgail-common:i386 libxt6:i386 libnspr4-0d:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3-1d:i386 libnss-mdns:i386 libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "16.04.1\n" or ver == "18.1\n":
        if arch == "x86_64\n":
            dependencies = "llibxt6:i386 libnspr4-0d:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3-1d:i386 libnss-mdns:i386 libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    elif ver == "18.04\n":
        if arch == "x86_64\n":
            # dependencies = "libxt6:i386 libnspr4:i386 libgtk2.0-0:i386 libstdc++6:i386 libnss3:i386 libnss-mdns:i386 libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libgnome-keyring0:i386 libxaw7"
            dependencies = "libgtk2.0-0:i386 libstdc++6:i386 libxml2:i386 libxslt1.1:i386 libcanberra-gtk-module:i386 gtk2-engines-murrine:i386 libqt4-qt3support:i386 libgnome-keyring0:i386 libnss-mdns:i386 libnss3:i386"
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/x86_64-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
        else:
            dependencies = "libgtk2.0-0 libxslt1.1 libxml2 libnss3 libxaw7 libgnome-keyring0"
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0 /usr/lib/libgnome-keyring.so.0")
            subprocess_call("ln -sf /usr/lib/i386-linux-gnu/libgnome-keyring.so.0.2.0 /usr/lib/libgnome-keyring.so.0.2.0")
    else:
        print("La versione " + ver + " del sistema operativo non è supportata")
        sys.exit(3)

    environment = { 'DISPLAY':':0', 'XAUTHORITY': xauthority, 'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' }
    subprocess_call("/bin/bash -c env")
    # if subprocess_call("/usr/bin/apt-get -q -y install " + dependencies) != 0:
    if subprocess_call("/usr/bin/apt-get update") != 0:
        print("Installazione delle dipendenze fallita")
        sys.exit(4)
    if subprocess_call("/usr/bin/apt-get -y install " + dependencies) != 0:
        print("Installazione delle dipendenze fallita")
        sys.exit(4)
    # import pdb; pdb.set_trace()
    if "adobe-air-sdk" in os.listdir("/opt"):
        shutil.rmtree("/opt/adobe-air-sdk")
    os.mkdir("/opt/adobe-air-sdk")
    if subprocess_call("/bin/tar jxf " + air_installer + " -C /opt/adobe-air-sdk", environment) != 0:
        print("Installazione di Adobe Air SDK dal file " + air_installer + " fallita")
        sys.exit(5)
    os.mkdir("/opt/adobe-air-sdk/scratch")
    # import pdb; pdb.set_trace()
    if subprocess_call( "/usr/bin/unzip -o " + scratch2_installer + " -d /opt/adobe-air-sdk/scratch/", environment) != 0:
        print("Installazione di Scratch2 dal file " + scratch2_installer + " fallita")
        sys.exit(6)
    try:
        with open("/usr/share/applications/Scratch2.desktop", "w") as f:
            f.write(DESKTOP_FILE)
        os.chmod("/usr/share/applications/Scratch2.desktop", 0o644)
    except Exception as e:
        import pdb; pdb.set_trace()
        print("Installazione di Scratch2 dal file " + scratch2_installer + " fallita")
        sys.exit(6)

    sys.exit(0)



parser = argparse.ArgumentParser(description='Programma di installazione di Scratch 2.')

parser.add_argument('--root-action', action='store_true', help='Forza la parte di root dello script')
parser.add_argument('--air-installer', help='Il percorso dell\'installer di Air')
parser.add_argument('--scratch2-installer', help='Il percorso dell\'installer di Scratch2')
parser.add_argument('--xauthority', help='il percorso del file XAYTHORITY per consentire alle applicazioni desktop di funzionare')

args = parser.parse_args()

if args.root_action:
    if os.geteuid() != 0:
        exit("Devi essere root per eseguire questo script")
    # import pdb; pdb.set_trace()
    vermsg = check_os()
    if vermsg != None:
        exit(vermsg)
    print ("eseguo la parte di root")
    real_install(args.air_installer, args.scratch2_installer, args.xauthority)
else:
    if __name__ == "__main__":
        win = MyWindow()
        win.connect("destroy", Gtk.main_quit)
        GObject.threads_init()
        win.show_all()
        Gtk.main()
