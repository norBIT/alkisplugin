# -*- coding: utf-8 -*-

"""
***************************************************************************
    __init__.py
    ---------------------
    Date                 : September 2012
    Copyright            : (C) 2012-2014 by Jürgen Fischer
    Email                : jef at norbit dot de
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from __future__ import absolute_import


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
  from .alkisplugin import alkisplugin
  return alkisplugin(iface)
