# -*- coding: utf-8 -*-

import resources

def name():
  return u"ALKIS-Einbindung"

def description():
  return u"Dies Plugin dient zur Einbindung von ALKIS-Layern."

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.8"

def authorName():
  return u"Jürgen E. Fischer <jef@norbit.de>"

def icon():
    return ":/plugins/alkis/logo.png"

def classFactory(iface):
  from alkisplugin import alkisplugin
  return alkisplugin(iface)
