#!/usr/bin/python
# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    alkisplugin.py
    ---------------------
    Date                 : September 2012
    Copyright            : (C) 2012-2020 by Jürgen Fischer
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
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import str
from builtins import range
try:
    from builtins import unicode
except ImportError:
    unicode = str

from io import open

import sip
for c in ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]:
    sip.setapi(c, 2)

try:
    from qgis.PyQt.QtCore import QObject, QSettings, Qt, QPointF, pyqtSignal, QCoreApplication
    from qgis.PyQt.QtWidgets import QApplication, QMessageBox, QAction, QFileDialog, QInputDialog, QProgressBar
    from qgis.PyQt.QtGui import QIcon, QColor, QPainter
    from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
    from qgis.PyQt import QtCore
except ImportError:
    from PyQt5.QtCore import QObject, QSettings, Qt, QPointF, pyqtSignal, QCoreApplication
    from PyQt5.QtWidgets import QApplication, QMessageBox, QAction, QFileDialog, QInputDialog, QProgressBar
    from PyQt5.QtGui import QIcon, QColor, QPainter
    from PyQt5.QtSql import QSqlDatabase, QSqlQuery
    from PyQt5 import QtCore

from tempfile import mkstemp

import os
import re

try:
    import sys
    BASEDIR = os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))
except TypeError:
    BASEDIR = os.path.dirname(__file__)

qgisAvailable = False
authAvailable = False
hasBlendSource = False
hasProxyTask = False

try:
    import qgis.core
    qgisAvailable = True
except ImportError:
    qgisAvailable = False

if qgisAvailable:
    from qgis.core import QgsMessageLog, QgsProject, QgsCoordinateReferenceSystem, QgsPalLayerSettings, QgsCredentials, QgsRectangle, QgsCoordinateTransform, QgsVectorLayer, QgsApplication

    if hasattr(qgis.core, "QGis"):
        from qgis.core import (
            QGis as Qgis,
            QgsWKBTypes as QgsWkbTypes,
            QgsDataDefined,
            QgsDataSourceURI as QgsDataSourceUri,
            QgsMapLayerRegistry,
            QgsMarkerLineSymbolLayerV2 as QgsMarkerLineSymbolLayer,
            QgsSymbolV2 as QgsSymbol,
            QgsSimpleLineSymbolLayerV2 as QgsSimpleLineSymbolLayer,
            QgsCategorizedSymbolRendererV2 as QgsCategorizedSymbolRenderer,
            QgsRendererCategoryV2 as QgsRendererCategory,
            QgsSvgMarkerSymbolLayerV2 as QgsSvgMarkerSymbolLayer,
            QgsSingleSymbolRendererV2 as QgsSingleSymbolRenderer,
            QgsLineSymbolV2 as QgsLineSymbol,
            QgsMapRenderer,
        )

        authAvailable = hasattr(QgsDataSourceUri, 'setAuthConfigId')
        hasBlendSource = hasattr(QgsMapRenderer, "BlendSource")
        qgis3 = False
    else:
        from qgis.core import (
            QgsWkbTypes,
            QgsProperty,
            QgsPropertyCollection,
            QgsVectorLayerSimpleLabeling,
            QgsMarkerLineSymbolLayer,
            QgsSymbol,
            QgsSimpleLineSymbolLayer,
            QgsCategorizedSymbolRenderer,
            QgsRendererCategory,
            QgsSvgMarkerSymbolLayer,
            QgsSingleSymbolRenderer,
            QgsLineSymbol,
            QgsDataSourceUri,
            QgsUnitTypes,
            QgsTextFormat,
            QgsTextBufferSettings,
            QgsSettings
        )
        authAvailable = True
        hasBlendSource = True
        qgis3 = True

        try:
            from qgis.core import QgsProxyProgressTask
            hasProxyTask = True
        except ImportError:
            pass

    from .qgisclasses import About, ALKISPointInfo, ALKISPolygonInfo, ALKISOwnerInfo, ALKISSearch, ALKISConf

try:
    import win32api
    USERNAME = win32api.GetUserNameEx(win32api.NameSamCompatible)
except ImportError:
    import getpass
    import socket
    USERNAME = u"{}@{}".format(getpass.getuser(), socket.gethostname())

try:
    import mapscript
    from mapscript import fromstring
    mapscriptAvailable = True
except ImportError:
    mapscriptAvailable = False


def qDebug(s):
    QtCore.qDebug(s.encode('ascii', 'ignore'))


def logMessage(s):
    if qgisAvailable:
        QgsMessageLog.logMessage(s, "ALKIS")
    else:
        QtCore.qWarning(s.encode("utf-8"))


class alkissettings(QObject):
    def __init__(self, plugin):
        QObject.__init__(self)

        self.plugin = plugin

        self.service = ""
        self.host = ""
        self.port = "5432"
        self.dbname = ""
        self.schema = "public"
        self.uid = ""
        self.pwd = ""
        self.authcfg = ""
        self.signaturkatalog = -1
        self.modellarten = ['DLKM', 'DKKM1000']
        self.footnote = ""
        self.umnpath = BASEDIR
        self.umntemplate = ""

        self.load()

        if plugin.iface:
            plugin.iface.projectRead.connect(self.load)
            plugin.iface.newProjectCreated.connect(self.load)

    def saveSettings(self):
        s = QSettings("norBIT", "norGIS-ALKIS-Erweiterung")
        s.setValue("service", self.service)
        s.setValue("host", self.host)
        s.setValue("port", self.port)
        s.setValue("dbname", self.dbname)
        s.setValue("schema", self.schema)
        s.setValue("uid", self.uid)
        s.setValue("pwd", self.pwd)
        s.setValue("authcfg", self.authcfg)
        s.setValue("signaturkatalog", self.signaturkatalog)
        s.setValue("modellarten", self.modellarten)
        s.setValue("footnote", self.footnote)
        s.setValue("umnpath", self.umnpath)
        s.setValue("umntemplate", self.umntemplate)

        logMessage("Einstellungen gespeichert.")

    def loadSettings(self):
        s = QSettings("norBIT", "norGIS-ALKIS-Erweiterung")
        self.service = s.value("service")
        self.host = s.value("host", "")
        self.port = s.value("port", "5432")
        self.dbname = s.value("dbname", "")
        self.schema = s.value("schema", "public")
        self.uid = s.value("uid", "")
        self.pwd = s.value("pwd", "")
        self.authcfg = s.value("authcfg", "")

        try:
            self.signaturkatalog = int(s.value("signaturkatalog", -1))
        except Exception:
            self.signaturkatalog = -1

        self.modellarten = s.value("modellarten", ['DLKM', 'DKKM1000'])
        self.footnote = s.value("footnote", "")
        self.umnpath = s.value("umnpath", BASEDIR)
        self.umntemplate = s.value("umntemplate", "")

        if self.plugin.db and self.plugin.db.isOpen():
            self.plugin.db.close()

    def saveToProject(self):
        p = QgsProject.instance()
        p.writeEntry("alkis", "settings/service", self.service)
        p.writeEntry("alkis", "settings/host", self.host)
        p.writeEntry("alkis", "settings/port", self.port)
        p.writeEntry("alkis", "settings/dbname", self.dbname)
        p.writeEntry("alkis", "settings/schema", self.schema)
        p.writeEntry("alkis", "settings/uid", self.uid)
        p.writeEntry("alkis", "settings/pwd", self.pwd)
        p.writeEntry("alkis", "settings/authcfg", self.authcfg)
        p.writeEntry("alkis", "settings/signaturkatalog", self.signaturkatalog)
        p.writeEntry("alkis", "settings/modellarten", self.modellarten)
        p.writeEntry("alkis", "settings/footnote", self.footnote)
        p.writeEntry("alkis", "settings/umnpath", self.umnpath)
        p.writeEntry("alkis", "settings/umntemplate", self.umntemplate)

        logMessage(u"Einstellungen in Projekt gespeichert.")

    def hasSettings(self):
        return len(QgsProject.instance().entryList("alkis", "settings")) > 0

    def removeSettings(self):
        QgsProject.instance().removeEntry("alkis", "settings")

    def load(self):
        if not qgisAvailable:
            self.loadSettings()
            return

        p = QgsProject.instance()
        if len(p.entryList("alkis", "settings")) > 0:
            self.service, ok = p.readEntry("alkis", "settings/service", "")
            self.host, ok = p.readEntry("alkis", "settings/host", "")
            self.port, ok = p.readEntry("alkis", "settings/port", "5432")
            self.dbname, ok = p.readEntry("alkis", "settings/dbname", "")
            self.schema, ok = p.readEntry("alkis", "settings/schema", "public")
            self.uid, ok = p.readEntry("alkis", "settings/uid", "")
            self.pwd, ok = p.readEntry("alkis", "settings/pwd", "")
            self.authcfg, ok = p.readEntry("alkis", "settings/authcfg", "")
            self.signaturkatalog, ok = p.readNumEntry("alkis", "settings/signaturkatalog", -1)
            self.modellarten, ok = p.readListEntry("alkis", "settings/modellarten", ['DLKM', 'DKKM1000'])
            self.footnote, ok = p.readEntry("alkis", "settings/footnote", "")
            self.umnpath, ok = p.readEntry("alkis", "settings/umnpath", BASEDIR)
            self.umntemplate, ok = p.readEntry("alkis", "settings/umntemplate", "")

            # logMessage(u"Einstellungen aus Projekt geladen.")
        else:
            self.loadSettings()

            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/pointMarkerLayer")
            pml = self.plugin.mapLayer(layerId) if ok else None
            if pml:
                uri = QgsDataSourceUri(pml.source())
                self.service = uri.service()
                self.host = uri.host()
                self.port = uri.port()
                self.dbname = uri.database()
                self.schema = uri.schema()
                self.uid = uri.username()
                self.pwd = uri.password()
                self.authcfg = uri.authConfigId()

                logMessage(u"Datenbankeinstellungen aus Punkthervorhebungslayer abgeleitet.")

        self.plugin.pointMarkerLayer = None
        self.plugin.lineMarkerLayer = None
        self.plugin.areaMarkerLayer = None

        if self.plugin.db and self.plugin.db.isOpen():
            self.plugin.db.close()


class alkisplugin(QObject):
    showProgress = pyqtSignal(int, int)
    showStatusMessage = pyqtSignal(str)

    themen = (
        {
            'name': u"Flurstücke",
            'area': {'min': 0, 'max': 5000},
            'outline': {'min': 0, 'max': 5000, 'umntemplate': 1, },
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'filter': [
                {'name': u"Flächen", 'filter': "NOT layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')"},
                {'name': u"Nummern", 'filter': "layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')"},
            ],
            'classes': {
                '2001': u'Bruchstriche',
                '2004': u'Zuordnungspfeil',
                '2005': u'Zuordnungspfeil, abweichender Rechtszustand',
                '2006': u'Strittige Grenze',
                '2008': u'Flurstücksgrenze nicht feststellbar',
                '2028': u'Flurstücksgrenze',
                '2029': u'Flurstücksgrenze, abw. Rechtszustand',
                '3010': u'Flurstücksüberhaken',
                '3020': u'Abgemarkter Grenzpunkt',
                '3021': u'Abgemarkter Grenzpunkt, abw. Rechtszustand',
                '3022': u'Grenzpunkt, Abmarkung zeitweilig ausgesetzt',
                '3024': u'Grenzpunkt ohne spezifizierte Abmarkung',
            },
        },
        {
            'name': u"Gebäude",
            'area': {'min': 0, 'max': 10000},
            'outline': {'min': 0, 'max': 3500},
            'line': {'min': 0, 'max': 3500},
            'point': {'min': 0, 'max': 3500},
            'label': {'min': 0, 'max': 3500},
            'filter': [
                {'name': u"Laufende Hausnummern", 'filter': "layer='ax_lagebezeichnungmitpseudonummer'"},
                {'name': u"Dachform", 'filter': "layer IN ('ax_gebaeude_dachform','ax_bauteil_dachform')"},
                {'name': u"Funktion", 'filter': "layer IN ('ax_gebaeude_funktion','ax_bauteil_funktion','ax_turm_funktion')"},
                {'name': u"Geschosse", 'filter': "layer IN ('ax_gebaeude_geschosse','ax_bauteil_geschosse')"},
                {'name': u"Zustand", 'filter': "layer='ax_gebaeude_zustand'"},
                {'name': u"Gebäude", 'filter': "layer NOT IN ('ax_lagebezeichnungmitpseudonummer','ax_gebaeude_dachform','ax_gebaeude_funktion','ax_gebaeude_geschosse','ax_gebaeude_zustand','ax_bauteil_dachform','ax_bauteil_funktion','ax_bauteil_geschosse','ax_turm_funktion')"},
            ],
            'classes': {
                '1301': u'Wohngebäude',
                '1304': u'Anderes Gebäude',
                '1305': u'Mauer',
                '2510': u'Mauer',
                '1309': u'Gebäude für öffentliche Zwecke',
                '1501': u'Aussichtsturm',
                'rn1501': u'Anderes Gebäude',
                '1525': u'Brunnen',
                '2002': u'Zaun',
                '2030': u'Gebäude',
                '2031': u'Anderes Gebäude',
                '2032': u'Gebäude unter der Erdoberfläche',
                '2305': u'Offene Gebäudelinie',
                '2505': u'Öffentliches Gebäude',
                # '2508': u'sonstiges Gebäudeteil',
                '2508': u'aufgeständert',
                '2509': u'Hochhausbauteil',
                '2513': u'Unterirdisch',
                # '2513': u'Schornstein im Gebäude',
                '2514': u'Turm im Gebäude',
                '2515': u'Brunnen',
                '2519': u'Kanal, Im Bau',
                '2623': u'Hochhaus',
                '3300': u'Bank',
                '3302': u'Hotel',
                '3303': u'Jugendherberge',
                '3305': u'Gaststätte',
                '3306': u'Kino',
                '3308': u'Spielcasino',
                '3309': u'Parkhaus',
                '3311': u'Toilette',
                '3312': u'Post',
                '3314': u'Theater',
                '3315': u'Bibliothek',
                '3316': u'Kirche',
                '3317': u'Synagoge',
                '3318': u'Kapelle',
                '3319': u'Moschee',
                '3321': u'Krankenhaus',
                '3323': u'Kindergarten',
                '3324': u'Polizei',
                '3326': u'Feuerwehr',
                '3327': u'Grabhügel (Hügelgrab)',
                '3332': u'Gebäude zum Busbahnhof',
                '3532': u'Denkmal',
                '3334': u'Hallenbad',
                '3336': u'Tiefgarage',
                '3338': u'Apotheke',
                '3521': u'Umformer',
                '3526': u'Großsteingrab (Dolmen), Hünenbett',
                '3529': u'Brunnen / Gasquelle, Mofette / Heilquelle',
                '3534': u'Bildstock',
                '3535': u'Gipfel-/Wegekreuz',
                '3536': u'Meilenstein, historischer Grenzstein',
                '3537': u'Brunnen (Trinkwasserversorgung)',
                '3539': u'Springbrunnen, Zierbrunnen',
                '3540': u'Ziehbrunnen',
                '3580': u'Zaun',

                '2901': u'Geplantes Gebäude (gebaut)',
                '2902': u'Geplantes Gebäude (Bauantrag)',
                '2903': u'Nicht eingemessenes Gebäude',
            },
        },
        {
            'name': u"Lagebezeichnungen",
            'area': {'min': 0, 'max': 5000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
        },
        {
            'name': u"Politische Grenzen",
            'area': {'min': 0, 'max': None},
            'outline': {'min': 0, 'max': None},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': None},
            'filter': [
                {
                    'name': u"Grenzen",
                    'filter': "layer NOT LIKE 'ax_flurstueck%'",
                    'area': {'min': 0, 'max': 10000},
                    'outline': {'min': 0, 'max': 10000},
                    'label': {'min': 0, 'max': 10000},
                },
                {
                    'name': u"Flure",
                    'filter': "layer LIKE 'ax_flurstueck_flur%'",
                    'area': {'min': 10000, 'max': 100000},
                    'outline': {'min': 10000, 'max': 50000},
                    'label': {'min': 10000, 'max': 50000},
                },
                {
                    'name': u"Gemarkung",
                    'filter': "layer LIKE 'ax_flurstueck_gemarkung%'",
                    'area': {'min': 10000, 'max': 150000},
                    'outline': {'min': 10000, 'max': 150000},
                    'label': {'min': 10000, 'max': 150000},
                },
                {
                    'name': u"Gemeinde",
                    'filter': "layer LIKE 'ax_flurstueck_gemeinde%'",
                    'area': {'min': 10000, 'max': 200000},
                    'outline': {'min': 10000, 'max': 200000},
                    'label': {'min': 50000, 'max': 200000},
                },
                {
                    'name': u"Kreis",
                    'filter': "layer LIKE 'ax_flurstueck_kreis%'",
                    'area': {'min': 10000, 'max': None},
                    'outline': {'min': 10000, 'max': None},
                    'label': {'min': 200000, 'max': 1000000},
                },
            ],
            'classes': {
                '2010': u'Landkreisgrenze',
                '2012': u'Flurgrenze',
                '2014': u'Gemarkungsgrenze',
                '2016': u'Staatsgrenze',
                '2018': u'Landesgrenze',
                '2020': u'Regierungsbezirksgrenze',
                '2022': u'Gemeindegrenze',
                '2026': u'Verwaltungsbezirksgrenze',
                'pg-flur': u'Flure',
                'pg-gemarkung': u'Gemarkungen',
                'pg-gemeinde': u'Gemeinden',
                'pg-kreis': u'Kreise',
            },
        },
        {
            'name': u"Rechtliche Festlegungen",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 25000},
            'line': {'min': 0, 'max': 25000},
            'point': {'min': 0, 'max': 25000},
            'label': {'min': 0, 'max': 25000},
            'classes': {
                '1701': u'Bundesautobahn/-straße',
                '1702': u'Landes-/Staatsstraße',
                'rn1701': u'Bundesautobahn/-straße',
                'rn1702': u'Landes-/Staatsstraße',
                'rn1703': u'Schutzgebiet',
                'rn1704': u'Bau-, Raum-, Bodenordnungsrecht',
            },
        },
        {
            'name': u"Topographie",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '2620': u'Damm, Wall, Deich, Graben, Knick, Wallkante',
                '3484': u'Düne, Sand',
                '3601': u'Busch, Hecke, Knick',
                '3625': u'Höhleneingang',
                '3627': u'Felsen, Felsblock, Felsnadel',
                '3629': u'Besonderer topographischer Punkt',
                '3632': u'Busch, Hecke, Knick',
                '3634': u'Felsen, Felsblock, Felsnadel',
            },
        },
        {
            'name': u"Verkehr",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1406': u'Begleitfläche',
                '1414': u'Fußgängerzone',
                '1530': u'Brücke, Hochbahn/-straße',
                'rn1530': u'Brücke, Hochbahn/-straße',
                'rn1533': u'Tunnel, Unterführung',
                'rn1535': u'Schleusenkammer',
                '1542': u'Weg',
                'rn1542': u'Weg',
                '1543': u'Wattenweg',
                '1544': u'Anleger',
                'rn1544': u'Anleger',
                '1540': u'Fahrbahn',
                'rn1540': u'Fahrbahn',
                '1808': u'Landeplatz, -bahn, Vorfeld, Rollbahn',
                'rn1808': u'Landeplatz, -bahn, Vorfeld, Rollbahn',
                '2305': u'Durchfahrt, Bauwerk',
                '2533': u'Widerlager',
                '2515': u'Bahnverkehr, Platz',
                '3330': u'S-Bahnhof',
                '3424': u'Fußweg',
                '3426': u'Radweg',
                '3428': u'Rad- und Fußweg',
                '3430': u'Reitweg',
                '3432': u'Parkplatz',
                '3434': u'Rastplatz',
                '3439': u'Segelfluggelände',
                '3541': u'Kommunikationseinrichtung',
                '3542': u'Fernsprechhäuschen',
                '3544': u'Briefkasten',
                '3546': u'Feuermelder',
                '3547': u'Polizeirufsäule',
                '3548': u'Kabelkasten, Schaltkasten',
                '3550': u'Verkehrsampel',
                '3551': u'Freistehende Hinweistafel, -zeichen',
                '3552': u'Wegweiser von besonderer Bedeutung',
                '3553': u'Freistehende Warntafel',
                '3554': u'Haltestelle',
                '3556': u'Kilometerstein',
                '3558': u'Gaslaterne',
                '3559': u'Laterne, elektrisch',
                '3563': u'Säule, Werbefläche',
                '3564': u'Leuchtsäule',
                '3565': u'Fahnenmast',
                '3566': u'Straßensinkkasten',
                '3567': u'Müllbox',
                '3568': u'Kehrichtgrube',
                '3569': u'Uhr',
                '3571': u'Flutlichtmast',
                '3578': u'Haltepunkt',
                '3588': u'Hubschrauberlandeplatz',
                '3590': u'Leuchtfeuer',
                '3645': u'Materialseilbahn',
                '3646': u'Straßenbahngleis',
            },
        },
        {
            'name': u"Friedhöfe",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1405': u'[1405]',
                '2515': u'[2515]',
            },
        },
        {
            'name': u"Vegetation",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1404': u'Brachland, Heide, Moor, Sumpf, Torf',
                '1406': u'Garten',
                '1409': u'Ackerland',
                '1414': u'Wald',
                '1561': u'Schneise',
                '2515': u'Ackerland',
                '2517': u'Wald',
                '3413': u'Gras',
                '3415': u'Park',
                '3421': u'Garten',
                '3440': u'Streuobstacker',
                '3441': u'Streuobstwiese',
                '3444': u'Spargel',
                '3446': u'Baumschule',
                '3448': u'Weingarten',
                '3450': u'Obstplantage',
                '3452': u'Obstbaumplantage',
                '3454': u'Obststrauchplantage',
                '3456': u'Wald',
                '3457': u'Nadelbaum',
                '3458': u'Laubwald',
                '3460': u'Nadelwald',
                '3462': u'Mischwald',
                '3470': u'Mischwald',
                '3474': u'Heide',
                '3476': u'Moor',
                '3478': u'Sumpf',
                '3480': u'Unland',
                '3481': u'Fels',
                '3482': u'Steine, Schotter / Wellenbrecher, Buhne',
                '3484': u'Düne, Sand',
                '3597': u'Nadelbaum',
                '3599': u'Laubbaum',
                '3601': u'Busch, Hecke, Knick',
                '3603': u'Röhricht, Schilf',
                '3605': u'Zierfläche',
                '3607': u'Korbweide',
                '3613': u'Quelle',
            },
        },
        {
            'name': u"Landwirtschaftliche Nutzung",
            'area': {'min': 0, 'max': None},
            'outline': {'min': 0, 'max': None},
            'line': {'min': 0, 'max': None},
            'point': {'min': 0, 'max': None},
            'label': {'min': 0, 'max': None},
            'classes': {
            },
        },
        {
            'name': u"Gewässer",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1410': u'Gewässer',
                '2518': u'Gewässer',
                '3484': u'Düne, Sand',
                '3488': u'Fließgewässer',
                '3490': u'Gewässer',
                '3529': u'Brunnen / Gasquelle, Mofette / Heilquelle',
                '3594': u'Schöpfwerk',
                '3613': u'Quelle',
                '3617': u'Stromschnelle',
                '3619': u'Unterirdisches Fließgewässer',
                '3621': u'Fließgewässer, nicht ständig Wasser führend',
                '3623': u'Höhe des Wasserspiegels',
                '3653': u'[3653]',
                'rn1548': u'Fischtreppe, Sicherheitstor, Sperrwerk',
                'rn1550': u'Unterirdisches Gewässer',
            },
        },
        {
            'name': u"Industrie und Gewerbe",
            'area': {'min': 0, 'max': 500000, },
            'outline': {'min': 0, 'max': 10000, },
            'line': {'min': 0, 'max': 10000, },
            'point': {'min': 0, 'max': 10000, },
            'label': {'min': 0, 'max': 10000, },
            'classes': {
                '1305': u'[1305]',
                'rn1305': u'[rn1305]',
                '1306': u'Mast',
                'rn1306': u'Mast',
                'rn1321': u'Vorratsbehälter, Speicherbauwerk unterirdisch',
                'rn1501': u'[rn1501]',
                'rn1510': u'Klärbecken',
                '1304': u'Vorratsbehälter, aufgeständert',
                '1401': u'[1401]',
                '1403': u'[1403]',
                '1404': u'[1404]',
                '1501': u'[1501]',
                '1510': u'[1510]',
                '2031': u'[2031]',
                '2515': u'[2515]',
                '2524': u'[2524]',
                '3401': u'Tankstelle',
                '3403': u'Kraftwerk',
                '3404': u'Umspannstation',
                '3406': u'Stillgelegter Bergbaubetrieb',
                '3407': u'Torf',
                '3501': u'Windrad',
                '3502': u'Solarzellen',
                '3504': u'Mast',
                '3506': u'Antenne / Funkmast',
                '3507': u'Radioteleskop',
                '3508': u'Schornstein, Schlot, Esse',
                '3509': u'Stollenmundloch',
                '3510': u'Schachtöffnung',
                '3511': u'Kran',
                '3512': u'Drehkran',
                '3513': u'Portalkran',
                '3514': u'Laufkran, Brückenlaufkran',
                '3515': u'Portalkran',
                '3517': u'Oberflurhydrant',
                '3518': u'Unterflurhydrant',
                '3519': u'Schieberkappe',
                '3520': u'Einsteigeschacht',
                '3521': u'Umformer',
                '3522': u'Vorratsbehälter',
                '3523': u'Pumpe',
                '3653': u'Wehr',
            },
        },
        {
            'name': u"Sport und Freizeit",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '1405': u'[1405]',
                '1519': u'Überdachte Tribüne',
                'rn1519': u'Überdachte Tribüne',
                '1520': u'Hart-, Rasenplatz, Spielfeld',
                'rn1520': u'Hart-, Rasenplatz, Spielfeld',
                '1521': u'Rennbahn, Laufbahn, Geläuf',
                'rn1521': u'Rennbahn, Laufbahn, Geläuf',
                '1522': u'Stadion',
                'rn1522': u'Stadion',
                'rn1524': u'[1524]',
                '1526': u'Schwimmbecken',
                'rn1526': u'Schwimmbecken',
                '2515': u'[2515]',
                '3409': u'Skating',
                '3410': u'Zoo',
                '3411': u'Safaripark, Wildpark',
                '3412': u'Campingplatz',
                '3413': u'Rasen',
                '3415': u'Park',
                '3417': u'Botanischer Garten',
                '3419': u'Kleingarten',
                '3421': u'Garten',
                '3423': u'Spielplatz, Bolzplatz',
                '3424': u'Fußweg',
                '3524': u'Schießanlage',
                '3525': u'Gradierwerk',
            },
        },
        {
            'name': u"Wohnbauflächen",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '1401': u'Wohnbaufläche',
                '2515': u'[2515]',
            },
        },
    )

    exts = {
        '3010': {'minx': -0.6024, 'miny': 0, 'maxx': 0.6171, 'maxy': 2.2309},
        '3011': {'minx': -0.6216, 'miny': -1.0061, 'maxx': 0.6299, 'maxy': 1.2222},
        '3020': {'minx': -0.8459, 'miny': -0.8475, 'maxx': 0.8559, 'maxy': 0.8569},
        '3021': {'minx': -0.8459, 'miny': -0.8475, 'maxx': 0.8559, 'maxy': 0.8569},
        '3022': {'minx': -0.8722, 'miny': -0.8628, 'maxx': 0.8617, 'maxy': 0.8415},
        '3023': {'minx': -0.8722, 'miny': -0.8628, 'maxx': 0.8617, 'maxy': 0.8415},
        '3024': {'minx': -0.7821, 'miny': -0.7727, 'maxx': 0.7588, 'maxy': 0.7721},
        '3025': {'minx': -0.7821, 'miny': -0.7727, 'maxx': 0.7588, 'maxy': 0.7721},
        '3300': {'minx': -2.6223, 'miny': -2.6129, 'maxx': 2.601, 'maxy': 2.5987},
        '3302': {'minx': -2.5251, 'miny': -2.5107, 'maxx': 2.5036, 'maxy': 2.5163},
        '3303': {'minx': -3.4963, 'miny': -3.0229, 'maxx': 3.4825, 'maxy': 3.0199},
        '3305': {'minx': -2.5129, 'miny': -2.5091, 'maxx': 2.5156, 'maxy': 2.5179},
        '3306': {'minx': -2.5064, 'miny': -2.5046, 'maxx': 2.5224, 'maxy': 2.5227},
        '3308': {'minx': -2.4464, 'miny': -2.4446, 'maxx': 2.5817, 'maxy': 2.5817},
        '3309': {'minx': -2.5322, 'miny': -3.1229, 'maxx': 2.5288, 'maxy': 3.1051},
        '3311': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3312': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3314': {'minx': -2.7808, 'miny': -3.0312, 'maxx': 2.8638, 'maxy': 3.0117},
        '3315': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3316': {'minx': -2.7685, 'miny': -5.0168, 'maxx': 2.7791, 'maxy': 5.0062},
        '3317': {'minx': -1.5189, 'miny': -1.7538, 'maxx': 1.5364, 'maxy': 1.7565},
        '3318': {'minx': -0.8139, 'miny': -1.5046, 'maxx': 0.8234, 'maxy': 1.5017},
        '3319': {'minx': -2.1918, 'miny': -2.5922, 'maxx': 2.1569, 'maxy': 2.5962},
        '3320': {'minx': -2.7685, 'miny': -2.5016, 'maxx': 2.7791, 'maxy': 2.5028},
        '3321': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3323': {'minx': -2.5322, 'miny': -3.1229, 'maxx': 2.5288, 'maxy': 3.1051},
        '3324': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3326': {'minx': -2.5251, 'miny': -2.5107, 'maxx': 2.5036, 'maxy': 2.5163},
        '3328': {'minx': -2.7822, 'miny': -2.7729, 'maxx': 2.7656, 'maxy': 2.7617},
        '3330': {'minx': -2.7822, 'miny': -2.7729, 'maxx': 2.7656, 'maxy': 2.7617},
        '3332': {'minx': -2.7825, 'miny': -2.7731, 'maxx': 2.7653, 'maxy': 2.7614},
        '3334': {'minx': -2.5322, 'miny': -3.1229, 'maxx': 2.5288, 'maxy': 3.1051},
        '3336': {'minx': -2.5322, 'miny': -3.1229, 'maxx': 2.5288, 'maxy': 3.2195},
        '3338': {'minx': -2.5064, 'miny': -2.5046, 'maxx': 2.5224, 'maxy': 2.5227},
        '3340': {'minx': -2.5322, 'miny': -2.5228, 'maxx': 2.5288, 'maxy': 2.5044},
        '3342': {'minx': -2.5064, 'miny': -2.5046, 'maxx': 2.5224, 'maxy': 2.5227},
        '3343': {'minx': -2.0122, 'miny': -2.0122, 'maxx': 2.0126, 'maxy': 2.0027},
        '3401': {'minx': -1.9675, 'miny': -2.6149, 'maxx': 1.96, 'maxy': 2.6196},
        '3402': {'minx': -3.7939, 'miny': -3.5892, 'maxx': 3.8046, 'maxy': 3.5886},
        '3403': {'minx': -3.6978, 'miny': -3.6799, 'maxx': 3.7045, 'maxy': 3.6842},
        '3404': {'minx': -3.6978, 'miny': -3.6799, 'maxx': 3.7045, 'maxy': 3.6842},
        '3405': {'minx': -4.1785, 'miny': -3.8158, 'maxx': 4.3008, 'maxy': 3.9871},
        '3406': {'minx': -4.2746, 'miny': -3.9971, 'maxx': 4.3678, 'maxy': 3.8105},
        '3407': {'minx': -6.2567, 'miny': -2.2569, 'maxx': 6.2643, 'maxy': 2.2639},
        '3409': {'minx': -3.7075, 'miny': -3.6981, 'maxx': 3.695, 'maxy': 3.6888},
        '3410': {'minx': -3.6816, 'miny': -3.6797, 'maxx': 3.6887, 'maxy': 3.6844},
        '3411': {'minx': -3.7075, 'miny': -3.6981, 'maxx': 3.695, 'maxy': 3.6888},
        '3412': {'minx': -3.8813, 'miny': -3.8719, 'maxx': 3.3302, 'maxy': 3.8636},
        '3413': {'minx': -1.2257, 'miny': -0.2181, 'maxx': 1.2166, 'maxy': 0.2127},
        '3415': {'minx': -5.0815, 'miny': -2.5197, 'maxx': 4.9078, 'maxy': 3.1702},
        '3417': {'minx': -3.6945, 'miny': -3.6889, 'maxx': 3.6754, 'maxy': 3.6978},
        '3419': {'minx': -2.6093, 'miny': -3.2037, 'maxx': 2.6138, 'maxy': 3.2091},
        '3421': {'minx': -1.0193, 'miny': -0.9064, 'maxx': 1.0043, 'maxy': 0.9118},
        '3423': {'minx': -3.6945, 'miny': -3.6889, 'maxx': 3.6754, 'maxy': 3.6978},
        '3424': {'minx': -2.5193, 'miny': -2.5137, 'maxx': 2.5093, 'maxy': 2.5134},
        '3426': {'minx': -2.5193, 'miny': -2.5137, 'maxx': 2.5093, 'maxy': 2.5134},
        '3428': {'minx': -2.5193, 'miny': -2.5137, 'maxx': 2.5093, 'maxy': 2.5134},
        '3430': {'minx': -2.5193, 'miny': -2.5137, 'maxx': 2.5093, 'maxy': 2.5134},
        '3432': {'minx': -2.5193, 'miny': -2.9017, 'maxx': 2.5093, 'maxy': 2.5895},
        '3434': {'minx': -2.5193, 'miny': -2.8235, 'maxx': 2.5093, 'maxy': 2.6663},
        '3436': {'minx': -6.0195, 'miny': -6.1918, 'maxx': 6.0061, 'maxy': 6.0214},
        '3438': {'minx': -6.2697, 'miny': -6.2641, 'maxx': 6.2508, 'maxy': 6.2528},
        '3439': {'minx': -6.2697, 'miny': -6.2641, 'maxx': 6.2508, 'maxy': 6.2528},
        '3440': {'minx': -1.1856, 'miny': -2.0168, 'maxx': 1.1925, 'maxy': 2.1807},
        '3441': {'minx': -2.6945, 'miny': -2.0062, 'maxx': 2.5297, 'maxy': 2.1914},
        '3442': {'minx': -1.2818, 'miny': -1.3142, 'maxx': 1.2894, 'maxy': 1.326},
        '3444': {'minx': -0.5701, 'miny': -1.5137, 'maxx': 0.5529, 'maxy': 1.5608},
        '3446': {'minx': -1.9144, 'miny': -2.0137, 'maxx': 1.6907, 'maxy': 2.1838},
        '3448': {'minx': -0.175, 'miny': -1.5, 'maxx': 0.175, 'maxy': 1.5},
        '3450': {'minx': -2.2109, 'miny': -2.0168, 'maxx': 2.202, 'maxy': 2.1807},
        '3452': {'minx': -1.1856, 'miny': -2.0168, 'maxx': 1.1925, 'maxy': 2.1807},
        '3454': {'minx': -0.9292, 'miny': -0.929, 'maxx': 0.9335, 'maxy': 0.935},
        '3456': {'minx': -4.1028, 'miny': -2.7517, 'maxx': 3.4036, 'maxy': 2.7596},
        '3458': {'minx': -2.0507, 'miny': -1.6767, 'maxx': 1.8776, 'maxy': 1.6959},
        '3460': {'minx': -1.8905, 'miny': -2.1752, 'maxx': 1.6503, 'maxy': 2.664},
        '3462': {'minx': -3.4608, 'miny': -2.6966, 'maxx': 3.2266, 'maxy': 2.6765},
        '3470': {'minx': -2.7435, 'miny': -2.1025, 'maxx': 2.7393, 'maxy': 2.7579},
        '3472': {'minx': -0.8011, 'miny': -0.7704, 'maxx': 0.8041, 'maxy': 0.7516},
        '3474': {'minx': -1.4221, 'miny': -0.9636, 'maxx': 1.4072, 'maxy': 0.9686},
        '3476': {'minx': -1.562, 'miny': -0.8073, 'maxx': 1.5577, 'maxy': 0.8058},
        '3478': {'minx': -4.0053, 'miny': -0.5438, 'maxx': 4.0176, 'maxy': 0.5458},
        '3480': {'minx': -1.8193, 'miny': -2.0137, 'maxx': 1.9459, 'maxy': 2.0013},
        '3481': {'minx': -1.8905, 'miny': -1.8808, 'maxx': 1.94, 'maxy': 1.9043},
        '3482': {'minx': -2.115, 'miny': -1.6314, 'maxx': 2.1682, 'maxy': 1.6038},
        '3483': {'minx': -1.9026, 'miny': -1.3693, 'maxx': 1.8312, 'maxy': 1.2484},
        '3484': {'minx': -2.1193, 'miny': -1.5137, 'maxx': 2.1316, 'maxy': 1.5153},
        '3486': {'minx': -1.506, 'miny': -1.5182, 'maxx': 1.517, 'maxy': 1.5108},
        '3488': {'minx': -3.044, 'miny': -0.7478, 'maxx': 3.0241, 'maxy': 0.7514},
        '3490': {'minx': -2.5057, 'miny': -0.6882, 'maxx': 2.5873, 'maxy': 0.6518},
        '3501': {'minx': -2.852, 'miny': -3.5574, 'maxx': 2.8258, 'maxy': 3.3221},
        '3502': {'minx': -1.6984, 'miny': -2.1752, 'maxx': 1.6797, 'maxy': 2.1846},
        '3503': {'minx': -3.044, 'miny': -2.787, 'maxx': 3.0564, 'maxy': 3.0227},
        '3504': {'minx': -1.1216, 'miny': -1.1104, 'maxx': 1.0953, 'maxy': 1.0957},
        '3506': {'minx': -1.4583, 'miny': -2.6887, 'maxx': 1.4677, 'maxy': 2.5699},
        '3507': {'minx': -2.262, 'miny': -3.2279, 'maxx': 2.0229, 'maxy': 3.2312},
        '3508': {'minx': -1.6984, 'miny': -1.6767, 'maxx': 1.6797, 'maxy': 1.6959},
        '3509': {'minx': -1.7693, 'miny': -1.6387, 'maxx': 1.7702, 'maxy': 1.6422},
        '3510': {'minx': -1.9093, 'miny': -1.3037, 'maxx': 1.9211, 'maxy': 1.2908},
        '3511': {'minx': -1.7945, 'miny': -2.5606, 'maxx': 1.6809, 'maxy': 2.6044},
        '3512': {'minx': -1.6342, 'miny': -2.6059, 'maxx': 1.5504, 'maxy': 2.6056},
        '3513': {'minx': -3.012, 'miny': -2.6059, 'maxx': 3.0234, 'maxy': 2.6056},
        '3514': {'minx': -5.031, 'miny': -2.6284, 'maxx': 5.0211, 'maxy': 2.6067},
        '3515': {'minx': -1.4443, 'miny': -2.1887, 'maxx': 1.4495, 'maxy': 2.1938},
        '3516': {'minx': -1.1536, 'miny': -1.2009, 'maxx': 1.1919, 'maxy': 1.2106},
        '3517': {'minx': -1.442, 'miny': -2.1074, 'maxx': 1.4517, 'maxy': 2.0914},
        '3518': {'minx': -2.0956, 'miny': -0.8475, 'maxx': 2.091, 'maxy': 0.8569},
        '3519': {'minx': -0.8652, 'miny': -0.8611, 'maxx': 0.8687, 'maxy': 0.8432},
        '3520': {'minx': -1.6021, 'miny': -1.6089, 'maxx': 1.6146, 'maxy': 1.6033},
        '3521': {'minx': -1.8585, 'miny': -1.8581, 'maxx': 1.8427, 'maxy': 1.8583},
        '3522': {'minx': -1.6129, 'miny': -1.6037, 'maxx': 1.6037, 'maxy': 1.6084},
        '3523': {'minx': -1.6982, 'miny': -2.3567, 'maxx': 1.7123, 'maxy': 2.3709},
        '3524': {'minx': -3.2045, 'miny': -3.1951, 'maxx': 3.1883, 'maxy': 3.1947},
        '3525': {'minx': -4.4542, 'miny': -3.0362, 'maxx': 4.4509, 'maxy': 3.0297},
        '3526': {'minx': -2.5315, 'miny': -1.5408, 'maxx': 2.5294, 'maxy': 1.557},
        '3527': {'minx': -1.8906, 'miny': -1.9033, 'maxx': 1.8752, 'maxy': 1.9052},
        '3528': {'minx': -2.5315, 'miny': -1.5408, 'maxx': 2.5294, 'maxy': 1.557},
        '3529': {'minx': -1.3458, 'miny': -1.3596, 'maxx': 1.3546, 'maxy': 1.3491},
        '3531': {'minx': -1.7623, 'miny': -1.6767, 'maxx': 1.7774, 'maxy': 1.6959},
        '3532': {'minx': -1.4739, 'miny': -2.4473, 'maxx': 1.4845, 'maxy': 2.4416},
        '3533': {'minx': -1.2176, 'miny': -2.1752, 'maxx': 1.2247, 'maxy': 2.002},
        '3534': {'minx': -0.8973, 'miny': -2.0168, 'maxx': 0.901, 'maxy': 2.2035},
        '3535': {'minx': -1.2176, 'miny': -2.0168, 'maxx': 1.2247, 'maxy': 2.021},
        '3536': {'minx': -0.9421, 'miny': -1.4366, 'maxx': 0.9527, 'maxy': 1.4322},
        '3537': {'minx': -1.6094, 'miny': -1.6037, 'maxx': 1.6072, 'maxy': 1.6084},
        '3539': {'minx': -1.8585, 'miny': -2.0846, 'maxx': 1.8752, 'maxy': 1.9541},
        '3540': {'minx': -1.6663, 'miny': -3.0589, 'maxx': 1.7436, 'maxy': 3.1911},
        '3541': {'minx': -2.6083, 'miny': -1.5952, 'maxx': 2.6148, 'maxy': 1.5943},
        '3542': {'minx': -2.5954, 'miny': -1.6089, 'maxx': 2.5957, 'maxy': 1.6033},
        '3543': {'minx': -1.6342, 'miny': -0.4532, 'maxx': 1.6471, 'maxy': 0.4546},
        '3544': {'minx': -1.1216, 'miny': -0.6118, 'maxx': 1.0953, 'maxy': 0.5916},
        '3545': {'minx': -2.6081, 'miny': -1.6037, 'maxx': 2.6151, 'maxy': 1.6084},
        '3546': {'minx': -2.6093, 'miny': -1.6037, 'maxx': 2.6138, 'maxy': 1.6084},
        '3547': {'minx': -2.6093, 'miny': -1.6037, 'maxx': 2.6138, 'maxy': 1.6084},
        '3548': {'minx': -1.09, 'miny': -1.1536, 'maxx': 1.0947, 'maxy': 1.0528},
        '3549': {'minx': -1.5061, 'miny': -3.8749, 'maxx': 1.5488, 'maxy': 3.9066},
        '3550': {'minx': -0.8652, 'miny': -3.2855, 'maxx': 0.8687, 'maxy': 3.29},
        '3551': {'minx': -1.6021, 'miny': -2.6059, 'maxx': 1.6146, 'maxy': 2.6056},
        '3552': {'minx': -0.8652, 'miny': -2.8552, 'maxx': 1.2218, 'maxy': 2.7724},
        '3553': {'minx': -1.0894, 'miny': -3.3082, 'maxx': 1.1595, 'maxy': 3.4053},
        '3554': {'minx': -2.7696, 'miny': -2.764, 'maxx': 2.778, 'maxy': 2.7704},
        '3556': {'minx': -1.5061, 'miny': -1.5636, 'maxx': 1.5488, 'maxy': 1.557},
        '3557': {'minx': -1.0254, 'miny': -3.3535, 'maxx': 1.0303, 'maxy': 3.3605},
        '3558': {'minx': -1.0894, 'miny': -3.3764, 'maxx': 1.1595, 'maxy': 3.361},
        '3559': {'minx': -1.3137, 'miny': -3.648, 'maxx': 1.322, 'maxy': 3.5547},
        '3560': {'minx': -2.852, 'miny': -3.1495, 'maxx': 2.9226, 'maxy': 3.1477},
        '3561': {'minx': -2.9481, 'miny': -3.4217, 'maxx': 2.9568, 'maxy': 3.3167},
        '3562': {'minx': -2.0956, 'miny': -0.5978, 'maxx': 2.091, 'maxy': 0.6056},
        '3563': {'minx': -1.6094, 'miny': -1.6037, 'maxx': 1.6072, 'maxy': 1.6084},
        '3564': {'minx': -1.6021, 'miny': -1.6089, 'maxx': 1.6465, 'maxy': 1.6033},
        '3565': {'minx': -1.3778, 'miny': -3.1045, 'maxx': 1.3871, 'maxy': 3.0086},
        '3566': {'minx': -1.1216, 'miny': -0.6118, 'maxx': 1.0953, 'maxy': 0.5916},
        '3567': {'minx': -2.0964, 'miny': -1.0945, 'maxx': 2.0902, 'maxy': 1.1116},
        '3568': {'minx': -2.115, 'miny': -1.1104, 'maxx': 2.1037, 'maxy': 1.0957},
        '3569': {'minx': -1.3458, 'miny': -1.3596, 'maxx': 1.3546, 'maxy': 1.3491},
        '3570': {'minx': -3.1081, 'miny': -1.1104, 'maxx': 3.025, 'maxy': 1.0957},
        '3571': {'minx': -1.3137, 'miny': -1.3143, 'maxx': 1.322, 'maxy': 1.303},
        '3572': {'minx': -1.5701, 'miny': -1.6089, 'maxx': 1.5821, 'maxy': 1.6033},
        '3573': {'minx': -29.7675, 'miny': -6.0952, 'maxx': 29.7664, 'maxy': 6.0919},
        '3574': {'minx': -2.7693, 'miny': -2.7637, 'maxx': 2.7783, 'maxy': 2.7707},
        '3576': {'minx': -2.5193, 'miny': -2.5137, 'maxx': 2.5093, 'maxy': 2.5134},
        '3578': {'minx': -1.6094, 'miny': -1.6037, 'maxx': 1.6072, 'maxy': 1.6084},
        '3579': {'minx': -0.8011, 'miny': -0.8158, 'maxx': 0.8042, 'maxy': 0.8201},
        '3580': {'minx': -0.09, 'miny': 0, 'maxx': 0.09, 'maxy': 0.6},
        '3583': {'minx': -1.2177, 'miny': -2.8099, 'maxx': 1.1925, 'maxy': 2.794},
        '3584': {'minx': -1.3884, 'miny': -2.6038, 'maxx': 1.4728, 'maxy': 2.5162},
        '3585': {'minx': -0.5127, 'miny': -0.5212, 'maxx': 0.514, 'maxy': 0.5002},
        '3586': {'minx': -1.0254, 'miny': -0.5212, 'maxx': 1.0303, 'maxy': 0.5002},
        '3587': {'minx': -3.3968, 'miny': -3.3761, 'maxx': 3.3866, 'maxy': 3.3847},
        '3588': {'minx': -3.5973, 'miny': -3.1348, 'maxx': 3.674, 'maxy': 3.2307},
        '3589': {'minx': -0.596, 'miny': -2.5968, 'maxx': 0.5914, 'maxy': 2.5006},
        '3590': {'minx': -2.879, 'miny': -3.0183, 'maxx': 2.8637, 'maxy': 2.4292},
        '3592': {'minx': -1.6214, 'miny': -0.6027, 'maxx': 1.5952, 'maxy': 0.6006},
        '3593': {'minx': -10.1131, 'miny': -2.0983, 'maxx': 10.1004, 'maxy': 2.1007},
        '3594': {'minx': -1.8137, 'miny': -2.0983, 'maxx': 1.8228, 'maxy': 2.1007},
        '3595': {'minx': -2.07, 'miny': -0.6027, 'maxx': 2.116, 'maxy': 0.6006},
        '3596': {'minx': -0.5965, 'miny': -1.8446, 'maxx': 0.5909, 'maxy': 1.8491},
        '3597': {'minx': -1.4611, 'miny': -2.2794, 'maxx': 1.4651, 'maxy': 2.5843},
        '3599': {'minx': -1.2398, 'miny': -2.2796, 'maxx': 1.2349, 'maxy': 2.1731},
        '3601': {'minx': -0.731, 'miny': -0.6744, 'maxx': 0.7457, 'maxy': 0.7336},
        '3603': {'minx': -1.5253, 'miny': -1.6223, 'maxx': 1.5298, 'maxy': 2.0915},
        '3605': {'minx': -0.6314, 'miny': -1.2045, 'maxx': 0.6523, 'maxy': 1.2072},
        '3607': {'minx': -1.4611, 'miny': -1.3958, 'maxx': 1.4651, 'maxy': 1.4498},
        '3609': {'minx': -1.3971, 'miny': -2.0303, 'maxx': 1.4963, 'maxy': 2.0077},
        '3613': {'minx': -0.5064, 'miny': -0.5045, 'maxx': 0.5203, 'maxy': 0.5169},
        '3615': {'minx': -2.9032, 'miny': -0.852, 'maxx': 2.9048, 'maxy': 0.8523},
        '3617': {'minx': -9.4081, 'miny': -2.5062, 'maxx': 9.4305, 'maxy': 2.498},
        '3619': {'minx': -3.6365, 'miny': -0.6045, 'maxx': 3.6361, 'maxy': 0.6216},
        '3621': {'minx': -3.7565, 'miny': -0.6045, 'maxx': 3.7768, 'maxy': 0.6216},
        '3623': {'minx': -1.5253, 'miny': -1.4865, 'maxx': 1.5298, 'maxy': 1.4739},
        '3625': {'minx': -2.0064, 'miny': -1.9762, 'maxx': 2.0183, 'maxy': 1.9929},
        '3627': {'minx': -2.807, 'miny': -2.5968, 'maxx': 2.8379, 'maxy': 2.7521},
        '3629': {'minx': -0.5064, 'miny': -0.5045, 'maxx': 0.5203, 'maxy': 0.5169},
        '3631': {'minx': -0.15, 'miny': -0.15, 'maxx': 0.15, 'maxy': 0.15},
        '3632': {'minx': -0.09, 'miny': -1, 'maxx': 0.09, 'maxy': 1},
        '3634': {'minx': -1.7176, 'miny': -1.5998, 'maxx': 1.7572, 'maxy': 1.749},
        '3636': {'minx': -3.3518, 'miny': -0.852, 'maxx': 3.3662, 'maxy': 0.8523},
        '3637': {'minx': -1.9739, 'miny': -1.9623, 'maxx': 0.3762, 'maxy': 1.9607},
        '3638': {'minx': -2.1982, 'miny': -0.852, 'maxx': 2.2146, 'maxy': 0.8523},
        '3640': {'minx': -2.1021, 'miny': -2.0983, 'maxx': 2.1168, 'maxy': 2.1007},
        '3641': {'minx': -2.3584, 'miny': -2.3475, 'maxx': 2.346, 'maxy': 2.3574},
        '3642': {'minx': -0.596, 'miny': -0.6027, 'maxx': 0.5914, 'maxy': 0.6006},
        '3643': {'minx': -0.09, 'miny': -0.5, 'maxx': 0.09, 'maxy': 0.5},
        '3644': {'minx': -1.5253, 'miny': -0.6027, 'maxx': 1.5298, 'maxy': 0.6007},
        '3645': {'minx': -0.596, 'miny': -0.852, 'maxx': 0.5914, 'maxy': 0.8523},
        '3646': {'minx': -0.596, 'miny': -0.6027, 'maxx': 0.5914, 'maxy': 0.6007},
        '3647': {'minx': -0.3076, 'miny': -0.6027, 'maxx': 0.3017, 'maxy': 0.6007},
        '3648': {'minx': -0.8524, 'miny': -0.6027, 'maxx': 0.8495, 'maxy': 0.6006},
        '3649': {'minx': -2.0058, 'miny': -0.6027, 'maxx': 2.019, 'maxy': 0.6007},
        '3650': {'minx': -0.596, 'miny': -0.6027, 'maxx': 0.5914, 'maxy': 0.6006},
        '3651': {'minx': -1.4932, 'miny': -0.784, 'maxx': 1.4651, 'maxy': 0.829},
        '3653': {'minx': -3.0314, 'miny': -0.6027, 'maxx': 3.0038, 'maxy': 0.6006},
        '3701': {'minx': -1.4931, 'miny': -2.2569, 'maxx': 1.4333, 'maxy': 2.8576},
        '3703': {'minx': -1.2048, 'miny': -1.1919, 'maxx': 1.2052, 'maxy': 1.197},
        '3705': {'minx': -1.6855, 'miny': -1.6904, 'maxx': 1.6927, 'maxy': 1.6822},
        '3707': {'minx': -3.0314, 'miny': -3.0047, 'maxx': 3.0038, 'maxy': 3.0153},
        '3709': {'minx': -1.6855, 'miny': -1.6904, 'maxx': 1.6927, 'maxy': 1.6822},
    }

    defcrs = "EPSG:4326 EPSG:4647 EPSG:31466 EPSG:31467 EPSG:31468 EPSG:25832 EPSG:25833"

    def __init__(self, iface):
        QObject.__init__(self)
        self.iface = iface
        self.pointMarkerLayer = None
        self.lineMarkerLayer = None
        self.areaMarkerLayer = None
        self.alkisGroup = None
        self.proxyTask = None

        self.db = None
        self.conninfo = None

        self.az = None

        self.settings = alkissettings(self)

        if not qgisAvailable:
            return

        if hasattr(QgsSymbol, "MapUnit"):
            self.MapUnit = QgsSymbol.MapUnit
            self.Millimeter = QgsSymbol.MM
            self.PointGeometry = Qgis.Point
            self.LineGeometry = Qgis.Line
            self.PolygonGeometry = Qgis.Polygon
        else:
            self.MapUnit = QgsUnitTypes.RenderMapUnits
            self.Millimeter = QgsUnitTypes.RenderMillimeters
            self.PointGeometry = QgsWkbTypes.PointGeometry
            self.LineGeometry = QgsWkbTypes.LineGeometry
            self.PolygonGeometry = QgsWkbTypes.PolygonGeometry

    def initGui(self):
        self.toolbar = self.iface.addToolBar(u"norGIS: ALKIS")
        self.toolbar.setObjectName("norGIS_ALKIS_Toolbar")

        self.importAction = QAction(QIcon("alkis:logo.svg"), "Layer einbinden", self.iface.mainWindow())
        self.importAction.setWhatsThis("ALKIS-Layer einbinden")
        self.importAction.setStatusTip("ALKIS-Layer einbinden")
        self.importAction.triggered.connect(self.run)

        if mapscriptAvailable:
            self.umnAction = QAction(QIcon("alkis:logo.svg"), u"UMN-Mapdatei erzeugen…", self.iface.mainWindow())
            self.umnAction.setWhatsThis("UMN-Mapserver-Datei erzeugen")
            self.umnAction.setStatusTip("UMN-Mapserver-Datei erzeugen")
            self.umnAction.triggered.connect(self.mapfile)
        else:
            self.umnAction = None

        self.searchAction = QAction(QIcon("alkis:find.svg"), u"Suchen…", self.iface.mainWindow())
        self.searchAction.setWhatsThis("ALKIS-Beschriftung suchen")
        self.searchAction.setStatusTip("ALKIS-Beschriftung suchen")
        self.searchAction.triggered.connect(self.search)
        self.toolbar.addAction(self.searchAction)

        self.queryOwnerAction = QAction(QIcon("alkis:eigner.svg"), u"Flurstücksnachweis", self.iface.mainWindow())
        self.queryOwnerAction.triggered.connect(self.setQueryOwnerTool)
        self.queryOwnerAction.setCheckable(True)
        self.toolbar.addAction(self.queryOwnerAction)
        self.queryOwnerInfoTool = ALKISOwnerInfo(self)
        self.queryOwnerInfoTool.setAction(self.queryOwnerAction)

        self.clearAction = QAction(QIcon("alkis:clear.svg"), "Hervorhebungen entfernen", self.iface.mainWindow())
        self.clearAction.setWhatsThis("Hervorhebungen entfernen")
        self.clearAction.setStatusTip("Hervorhebungen entfernen")
        self.clearAction.triggered.connect(self.clearHighlight)
        self.toolbar.addAction(self.clearAction)

        self.confAction = QAction(QIcon("alkis:logo.svg"), u"Konfiguration…", self.iface.mainWindow())
        self.confAction.setWhatsThis("Konfiguration der ALKIS-Erweiterung")
        self.confAction.setStatusTip("Konfiguration der ALKIS-Erweiterung")
        self.confAction.triggered.connect(self.conf)

        self.aboutAction = QAction(QIcon("alkis:logo.svg"), u"Über...", self.iface.mainWindow())
        self.aboutAction.setWhatsThis(u"Über die Erweiterung")
        self.aboutAction.setStatusTip(u"Über die Erweiterung")
        self.aboutAction.triggered.connect(self.about)

        self.iface.addPluginToDatabaseMenu("&ALKIS", self.importAction)
        if self.umnAction:
            self.iface.addPluginToDatabaseMenu("&ALKIS", self.umnAction)
        self.iface.addPluginToDatabaseMenu("&ALKIS", self.confAction)
        self.iface.addPluginToDatabaseMenu("&ALKIS", self.aboutAction)

        ns = QSettings("norBIT", "EDBSgen/PRO")
        if ns.contains("norGISPort"):
            self.pointInfoAction = QAction(QIcon("alkis:info.svg"), u"Flurstücksabfrage (Punkt)", self.iface.mainWindow())
            self.pointInfoAction.triggered.connect(self.setPointInfoTool)
            self.pointInfoAction.setCheckable(True)
            self.toolbar.addAction(self.pointInfoAction)
            self.pointInfoTool = ALKISPointInfo(self)
            self.pointInfoTool.setAction(self.pointInfoAction)

            self.polygonInfoAction = QAction(QIcon("alkis:pinfo.svg"), u"Flurstücksabfrage (Polygon)", self.iface.mainWindow())
            self.polygonInfoAction.triggered.connect(self.setPolygonInfoTool)
            self.polygonInfoAction.setCheckable(True)
            self.toolbar.addAction(self.polygonInfoAction)
            self.polygonInfoTool = ALKISPolygonInfo(self)
            self.polygonInfoTool.setAction(self.polygonInfoAction)
        else:
            self.pointInfoTool = None
            self.polygonInfoTool = None

        if not self.register():
            self.iface.mainWindow().initializationCompleted.connect(self.register)

        try:
            QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(self.layersRemoved)
        except NameError:
            QgsProject.instance().layersWillBeRemoved.connect(self.layersRemoved)

    def unload(self):
        self.iface.removePluginDatabaseMenu("&ALKIS", self.importAction)
        if self.umnAction:
            self.iface.removePluginDatabaseMenu("&ALKIS", self.umnAction)
        self.iface.removePluginDatabaseMenu("&ALKIS", self.confAction)
        self.iface.removePluginDatabaseMenu("&ALKIS", self.aboutAction)

        del self.toolbar

        if self.searchAction:
            self.searchAction.deleteLater()
            self.searchAction = None
        if self.importAction:
            self.importAction.deleteLater()
            self.importAction = None
        if self.umnAction:
            self.umnAction.deleteLater()
            self.umnAction = None
        if self.confAction:
            self.confAction.deleteLater()
            self.confAction = None
        if self.aboutAction:
            self.aboutAction.deleteLater()
            self.aboutAction = None

        if self.clearAction:
            self.clearAction.deleteLater()
            self.clearAction = None

        if self.queryOwnerInfoTool:
            self.queryOwnerInfoTool.deleteLater()
            self.queryOwnerInfoTool = None

        if self.pointInfoTool is not None:
            self.pointInfoTool.deleteLater()
            self.pointInfoTool = None

        if self.polygonInfoTool is not None:
            self.polygonInfoTool.deleteLater()
            self.polygonInfoTool = None

        try:
            QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.layersRemoved)
        except NameError:
            QgsProject.instance().layersWillBeRemoved.disconnect(self.layersRemoved)

    def layersRemoved(self, layers):
        if self.pointMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/pointMarkerLayer")
            if ok:
                self.pointMarkerLayer = self.mapLayer(layerId)

        if self.pointMarkerLayer is not None and (self.pointMarkerLayer in layers or self.pointMarkerLayer.id() in layers):
            self.pointMarkerLayer = None
            QgsProject.instance().removeEntry("alkis", "/pointMarkerLayer")

        if self.lineMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/lineMarkerLayer")
            if ok:
                self.lineMarkerLayer = self.mapLayer(layerId)

        if self.lineMarkerLayer is not None and (self.lineMarkerLayer in layers or self.lineMarkerLayer.id() in layers):
            self.lineMarkerLayer = None
            QgsProject.instance().removeEntry("alkis", "/lineMarkerLayer")

        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            logMessage(u"Keinen Flächenmarkierungslayer gefunden.")
            return

        if self.areaMarkerLayer in layers or self.areaMarkerLayer.id() in layers:
            QgsProject.instance().removeEntry("alkis", "/areaMarkerLayer")
            self.areaMarkerLayer = None
            self.settings.removeSettings()
            logMessage(u"ALKIS-Layer entfernt.")

    def conf(self):
        dlg = ALKISConf(self)
        dlg.exec_()

    def about(self):
        dlg = About()
        dlg.exec_()

    def initLayers(self):
        if self.pointMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/pointMarkerLayer")
            if ok:
                self.pointMarkerLayer = self.mapLayer(layerId)

        if self.pointMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Punktmarkierungslayer nicht gefunden!")
            return False

        if self.lineMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/lineMarkerLayer")
            if ok:
                self.lineMarkerLayer = self.mapLayer(layerId)

        if self.lineMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Linienmarkierungslayer nicht gefunden!")
            return False

        return True

    def search(self):
        dlg = ALKISSearch(self)
        dlg.exec_()

    def setScale(self, layer, d):
        if qgis3:
            kmin, kmax = 'max', 'min'
        else:
            kmin, kmax = 'min', 'max'

        if d[kmin] is None and d[kmax] is None:
            return

        if d[kmin] is not None:
            layer.setMinimumScale(d[kmin])

        if d[kmax] is not None:
            layer.setMaximumScale(d[kmax])

        try:
            layer.setScaleBasedVisibility(True)
        except AttributeError:
            layer.toggleScaleBasedVisibility(True)

    def setUMNScale(self, layer, d):
        if d.get('umntemplate', 0):
            template = self.settings.umntemplate
            if template:
                layer.template = template
                layer.tolerance = 1
                layer.toleranceunits = mapscript.MS_PIXELS
        if d['min'] is None and d['max'] is None:
            return

        if d['min'] is not None:
            layer.minscaledenom = d['min']

        if d['max'] is not None:
            layer.maxscaledenom = d['max']

    def categoryLabel(self, d, sn):
        qDebug(u"categories: %s" % d['classes'])
        if str(sn) in d['classes']:
            return d['classes'][str(sn)]
        else:
            return "(%s)" % sn

    def run(self):
        if self.settings.hasSettings() and QMessageBox.warning(None, "ALKIS", u"Im Projekt sind bereits ALKIS-Daten eingebunden.\nNach dem Einbinden werden nur die neuen Layer abfragbar sein.", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.alkisimport()
        finally:
            QApplication.restoreOverrideCursor()

            if self.proxyTask:
                self.proxyTask.finalize(True)
                self.proxyTask = None

    def progress(self, i, m, s):
        self.showStatusMessage.emit(u"%s/%s" % (alkisplugin.themen[i]['name'], m))

        if hasProxyTask:
            if self.proxyTask is None:
                self.proxyTask = QgsProxyProgressTask(u"Lade ALKIS-Layer…")
                QgsApplication.taskManager().addTask(self.proxyTask)

            self.proxyTask.setProxyProgress((i * 5 + s) / (len(alkisplugin.themen) * 5) * 100)

        else:
            self.showProgress.emit(i * 5 + s, len(alkisplugin.themen) * 5)
            QCoreApplication.processEvents()

    def doShowProgress(self, i, n):
        b = self.iface.mainWindow().findChild(QProgressBar, "mProgressBar")
        if b is None:
            return

        if i >= n:
            b.reset()
            b.hide()
        else:
            if not b.isVisible():
                b.show()

            b.setMaximum(n)
            b.setValue(i)

    def setStricharten(self, db, sym, kat, sn, outline):
        lqry = QSqlQuery(db)

        sql = (u"SELECT abschluss,scheitel,coalesce(strichstaerke/100,0),coalesce(laenge/100,0),coalesce(einzug/100,0),abstand,r,g,b"
               u" FROM alkis_linien ln"
               u" LEFT OUTER JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer{0}"
               u" LEFT OUTER JOIN alkis_stricharten_i ON l.strichart=alkis_stricharten_i.stricharten"
               u" LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
               u" LEFT OUTER JOIN alkis_farben ON {1}.farbe=alkis_farben.id"
               u" WHERE ln.signaturnummer='{2}'{3}").format(
                   "" if kat < 0 else u" AND l.katalog=%d" % kat,
                   u"ln" if kat < 0 else u"l",
                   sn,
                   "" if kat < 0 else u" AND ln.katalog=%d" % kat
        )

        if lqry.exec_(sql):
            stricharten = []

            maxStrichstaerke = None

            while lqry.next():
                try:
                    abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, c = \
                        lqry.value(0), lqry.value(1), float(lqry.value(2)), \
                        float(lqry.value(3)), float(lqry.value(4)), lqry.value(5), \
                        QColor(int(lqry.value(6)), int(lqry.value(7)), lqry.value(8))
                except TypeError as e:
                    logMessage(u"Signaturnummer %s: Ausnahme %s\nSQL:%s" % (sn, str(e), sql))
                    continue

                if maxStrichstaerke is None or abs(strichstaerke) > abs(maxStrichstaerke):
                    maxStrichstaerke = strichstaerke

                if abstaende:
                    if abstaende.startswith("{") and abstaende.endswith("}"):
                        abstaende = [float(x) / 100 for x in abstaende[1:-1].split(",")]
                    else:
                        abstaende = [float(abstaende) / 100]
                else:
                    abstaende = []

                gesamtl = 0
                for abstand in abstaende:
                    gesamtl += laenge + abstand

                stricharten.append([abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c])

            gesamtl0 = None
            leinzug = None
            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c in stricharten:
                if gesamtl0 is None:
                    gesamtl0 = gesamtl
                elif gesamtl0 != gesamtl:
                    raise BaseException(u"Signaturnummer %s: Stricharten nicht gleich lang (%lf vs %lf)" % (sn, gesamtl0, gesamtl))

                if laenge > 0:
                    if leinzug is None:
                        leinzug = einzug
                    elif leinzug != einzug:
                        # raise BaseException( u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug) )
                        logMessage(u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug))
                        return False

            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c in stricharten:
                if abstaende and laenge == 0:
                    # Marker line
                    if leinzug:
                        if einzug > leinzug:
                            einzug -= leinzug
                        else:
                            einzug += gesamtl - leinzug

                    for abstand in abstaende:
                        sl = QgsMarkerLineSymbolLayer(False, gesamtl)
                        sl.setPlacement(QgsMarkerLineSymbolLayer.Interval)
                        sl.setIntervalUnit(self.MapUnit)
                        sl.setOffsetAlongLine(einzug)
                        sl.setOffsetAlongLineUnit(self.MapUnit)
                        sl.subSymbol().symbolLayer(0).setSize(abs(strichstaerke))
                        sl.subSymbol().symbolLayer(0).setSizeUnit(self.MapUnit if strichstaerke >= 0 else self.Millimeter)
                        try:
                            sl.subSymbol().symbolLayer(0).setOutlineStyle(Qt.NoPen)
                        except AttributeError:
                            sl.subSymbol().symbolLayer(0).setStrokeStyle(Qt.NoPen)
                        sl.subSymbol().symbolLayer(0).setColor(c)
                        sl.setWidth(strichstaerke)
                        sl.setWidthUnit(self.MapUnit)
                        einzug += abstand
                        sym.appendSymbolLayer(sl)
                else:
                    # Simple line
                    sl = QgsSimpleLineSymbolLayer(c, strichstaerke, Qt.SolidLine)

                    if abstaende:
                        dashvector = []
                        for abstand in abstaende:
                            dashvector.extend([laenge, abstand])
                        sl.setUseCustomDashPattern(True)
                        sl.setCustomDashVector(dashvector)
                        sl.setCustomDashPatternUnit(self.MapUnit)

                    sl.setPenCapStyle(Qt.FlatCap if abschluss == "Abgeschnitten" else Qt.RoundCap)
                    sl.setPenJoinStyle(Qt.MiterJoin if abschluss == "Spitz" else Qt.RoundJoin)
                    sl.setWidth(abs(strichstaerke))
                    sl.setWidthUnit(self.MapUnit if strichstaerke >= 0 else self.Millimeter)

                    sym.appendSymbolLayer(sl)

            if sym.symbolLayerCount() == 1:
                logMessage(u"Signaturnummer %s: Keine Linienarten erzeugt." % sn)
                return False

            if outline:
                sym.deleteSymbolLayer(0)
            else:
                sl = QgsSimpleLineSymbolLayer(QColor(0, 0, 0, 0) if hasBlendSource else Qt.white, maxStrichstaerke * 1.01, Qt.SolidLine)
                sl.setWidthUnit(self.MapUnit)
                sym.changeSymbolLayer(0, sl)
        else:
            logMessage(u"Signaturnummer %s: Linienarten konnten nicht abgefragt werden.\nSQL:%s\nFehler:%s" % (sn, sql, lqry.lastError().text()))
            return False

        return True

    def alkisimport(self):
        self.settings.loadSettings()

        (db, conninfo) = self.opendb()
        if db is None:
            return

        modelle = self.settings.modellarten
        katalog = self.settings.signaturkatalog

        self.iface.mapCanvas().setRenderFlag(False)

        qry = QSqlQuery(db)
        qry2 = QSqlQuery(db)

        svgpath = os.path.abspath(os.path.join(BASEDIR, "svg"))
        if qgis3:
            qs = QgsSettings()
            svgpaths = QgsApplication.svgPaths()
            if svgpath not in svgpaths:
                svgpaths.append(svgpath)
                qs.setValue("svg/searchPathsForSVG", svgpaths)
            layeropts = QgsVectorLayer.LayerOptions(False, False)
        else:
            qs = QSettings("QGIS", "QGIS2")
            svgpaths = qs.value("svg/searchPathsForSVG", "", type=unicode).split("|")
            if not svgpath.upper() in list(map(unicode.upper, svgpaths)):
                svgpaths.append(svgpath)
                qs.setValue("svg/searchPathsForSVG", u"|".join(svgpaths))
            layeropts = False

        self.alkisGroup = self.addGroup("ALKIS", False)

        markerGroup = self.addGroup("Markierungen", False, self.alkisGroup)

        if not hasProxyTask:
            if hasattr(self.iface.mainWindow(), "showProgress"):
                self.showProgress.connect(self.iface.mainWindow().showProgress)
            else:
                self.showProgress.connect(self.doShowProgress)
        self.showStatusMessage.connect(self.iface.mainWindow().showStatusMessage)

        if self.epsg > 100000:
            if qry.exec_("SELECT proj4text FROM spatial_ref_sys WHERE srid=%d" % self.epsg) and qry.next():
                crs = QgsCoordinateReferenceSystem()
                crs.createFromProj4(qry.value(0))
                if crs.authid() == "":
                    crs.saveAsUserCRS("ALKIS %d" % self.epsg)
                else:
                    QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), qry.executedQuery()))
            else:
                QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), qry.executedQuery()))
                return

        nGroups = 0
        iThema = -1
        for d in alkisplugin.themen:
            iThema += 1
            t = d['name']

            if 'filter' not in d:
                d['filter'] = [{'name': None, 'filter': None}]

            themeGroup = self.addGroup(t, False, self.alkisGroup)

            nSubGroups = 0

            qDebug(u"Thema: %s" % t)

            for f in d['filter']:
                name = f.get('name', t)
                tname = t

                for k in ['area', 'outline', 'line', 'point', 'label']:
                    if k not in f:
                        f[k] = d[k]

                nLayers = 0
                if len(d['filter']) > 1:
                    thisGroup = self.addGroup(name, False, themeGroup)
                else:
                    thisGroup = themeGroup

                where = "thema='%s'" % t

                if len(modelle) > 0:
                    where += " AND modell && ARRAY['%s']::varchar[]" % "','".join(modelle)

                if f.get('name', None):
                    tname += " / " + f['name']

                if f.get('filter', None):
                    where += " AND (%s)" % f['filter']

                self.progress(iThema, u"Flächen", 0)

                sql = (u"SELECT signaturnummer,r,g,b"
                       u" FROM alkis_flaechen"
                       u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                       u" WHERE EXISTS ("
                       u"SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer"
                       u"){1}"
                       u" ORDER BY darstellungsprioritaet DESC"
                       ).format(
                           where,
                           "" if katalog < 0 else " AND alkis_flaechen.katalog=%d" % katalog
                )

                # qDebug( u"SQL: %s" % sql )
                if qry.exec_(sql):
                    r = QgsCategorizedSymbolRenderer("sn_flaeche")
                    r.deleteAllCategories()

                    n = 0
                    while qry.next():
                        sym = QgsSymbol.defaultSymbol(self.PolygonGeometry)

                        sn = qry.value(0)
                        sym.setColor(QColor(int(qry.value(1)), int(qry.value(2)), int(qry.value(3))))
                        try:
                            sym.symbolLayer(0).setBorderStyle(Qt.NoPen)
                        except AttributeError:
                            sym.symbolLayer(0).setStrokeStyle(Qt.NoPen)

                        r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                        n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            u"Flächen (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        self.setScale(layer, f['area'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                else:
                    QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                    break

                self.progress(iThema, "Grenzen", 1)

                sql = (u"SELECT"
                       u" signaturnummer"
                       u" FROM alkis_linien"
                       u" WHERE EXISTS ("
                       u"SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_randlinie=alkis_linien.signaturnummer"
                       u"){1}"
                       u" ORDER BY darstellungsprioritaet"
                       ).format(
                           where,
                           "" if katalog < 0 else " AND alkis_linien.katalog=%d" % katalog,
                )

                # qDebug( u"SQL: %s" % sql )
                if qry.exec_(sql):
                    r = QgsCategorizedSymbolRenderer("sn_randlinie")
                    r.deleteAllCategories()

                    n = 0
                    while qry.next():
                        sym = QgsSymbol.defaultSymbol(self.PolygonGeometry)
                        sn = qry.value(0)

                        if self.setStricharten(db, sym, katalog, sn, True):
                            r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                            n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            u"Grenzen (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        if hasBlendSource:
                            layer.setFeatureBlendMode(QPainter.CompositionMode_Source)
                        self.setScale(layer, f['outline'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                else:
                    QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                    break

                self.progress(iThema, "Linien", 2)

                sql = (u"SELECT signaturnummer"
                       u" FROM alkis_linien"
                       u" WHERE EXISTS ("
                       u"SELECT * FROM po_lines WHERE {0} AND po_lines.signaturnummer=alkis_linien.signaturnummer"
                       u"){1}"
                       u" ORDER BY darstellungsprioritaet ASC"
                       ).format(
                           where,
                           "" if katalog < 0 else u" AND alkis_linien.katalog=%d" % katalog,
                )

                # qDebug( u"SQL: %s" % sql )
                if qry.exec_(sql):
                    r = QgsCategorizedSymbolRenderer("signaturnummer")
                    r.setUsingSymbolLevels(True)
                    r.deleteAllCategories()

                    n = 0
                    while qry.next():
                        sym = QgsSymbol.defaultSymbol(self.LineGeometry)
                        sn = qry.value(0)

                        if self.setStricharten(db, sym, katalog, sn, False):
                            for i in range(0, sym.symbolLayerCount()):
                                sym.symbolLayer(i).setRenderingPass(n)

                            r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                            n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTILINESTRING srid=%d table=%s.po_lines (line) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            u"Linien (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        if hasBlendSource:
                            layer.setFeatureBlendMode(QPainter.CompositionMode_Source)
                        layer.setFeatureBlendMode(QPainter.CompositionMode_Source)
                        self.setScale(layer, f['line'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                else:
                    QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                    break

                self.progress(iThema, "Punkte", 3)

                kat = max([1, katalog])

                sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE %s" % where
                # qDebug( u"SQL: %s" % sql )
                if qry.exec_(sql):
                    r = QgsCategorizedSymbolRenderer("signaturnummer")
                    r.deleteAllCategories()

                    n = 0
                    while qry.next():
                        sn = qry.value(0)

                        if qgis3:
                            svg = os.path.abspath(os.path.join(BASEDIR, "svg", "alkis%s_%d.svg" % (sn, kat)))
                        else:
                            svg = "alkis%s_%d.svg" % (sn, kat)

                        x, y, w = 0, 0, 1
                        if qry2.exec_("SELECT x0,y0,x1,y1 FROM alkis_punkte WHERE katalog=%d AND signaturnummer='%s'" % (kat, sn)) and qry2.next():
                            x = (qry2.value(0) + qry2.value(2)) / 2
                            y = (qry2.value(1) + qry2.value(3)) / 2
                            w = qry2.value(2) - qry2.value(0)
                            # h = qry2.value(3) - qry2.value(1)
                        elif sn in alkisplugin.exts:
                            x = (alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx']) / 2
                            y = (alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy']) / 2
                            w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
                            # h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']

                        symlayer = QgsSvgMarkerSymbolLayer(svg)
                        symlayer.setOutputUnit(self.MapUnit)
                        symlayer.setSize(w)
                        symlayer.setOffset(QPointF(-x, -y))

                        sym = QgsSymbol.defaultSymbol(self.PointGeometry)
                        sym.setOutputUnit(self.MapUnit)
                        sym.setSize(w)

                        sym.changeSymbolLayer(0, symlayer)

                        if hasattr(sym, "setDataDefinedAngle"):
                            try:
                                sym.setDataDefinedAngle(QgsProperty.fromField("drehwinkel_grad"))
                            except NameError:
                                sym.setDataDefinedAngle(QgsDataDefined("drehwinkel_grad"))
                        else:
                            symlayer.setDataDefinedProperty("angle", "drehwinkel_grad")

                        r.addCategory(QgsRendererCategory("%s" % sn, sym, self.categoryLabel(d, sn)))
                        n += 1

                    qDebug(u"classes: %d" % n)
                    if n > 0:
                        layer = QgsVectorLayer(
                            u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOINT srid=%d table=\"(SELECT ogc_fid,gml_id,thema,layer,signaturnummer,-drehwinkel_grad AS drehwinkel_grad,point FROM %s.po_points WHERE %s)\" (point) sql=" % (conninfo, self.epsg, self.quotedschema().replace('"', '\\"'), where),
                            u"Punkte (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        self.setScale(layer, f['point'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                else:
                    QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                    break

                n = 0
                labelGroup = None
                layer = None
                for i in range(2):
                    geom = "point" if i == 0 else "line"
                    geomtype = "MULTIPOINT" if i == 0 else "MULTILINESTRING"

                    if not qry.exec_("SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL" % (where, geom)):
                        QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                        continue

                    self.progress(iThema, "Beschriftungen (%d)" % (i + 1), 4 + i)

                    if not qry.next() or int(qry.value(0)) == 0:
                        continue

                    if n == 1:
                        labelGroup = self.addGroup("Beschriftungen", False, thisGroup)
                        self.addLayer(layer, labelGroup)
                        layer = None

                    uri = (
                        u"{0} estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type={1} srid={2} table="
                        u"\"("
                        u"SELECT"
                        u" ogc_fid"
                        u",layer"
                        # FIXME: Faktor 1.3225 empirisch bestimmt (QGIS: Schriftgröße mit ascent/decent; ALKIS: reine Schriftgröße)
                        u",CASE WHEN grad_pt<0 THEN abs(s.grad_pt) ELSE 0.25*coalesce(skalierung,1)*s.grad_pt*1.3225 END AS tsize"
                        u",CASE WHEN grad_pt<0 THEN 'Point' ELSE 'MapUnit' END AS tunit"
                        u",text"
                        u",CASE coalesce(po_labels.horizontaleausrichtung,s.horizontaleausrichtung)"
                        u" WHEN 'linksbündig' THEN 'Left'"
                        u" WHEN 'rechtsbündig' THEN 'Right'"
                        u" ELSE 'Center'"
                        u" END AS halign"
                        u",CASE coalesce(po_labels.vertikaleausrichtung,s.vertikaleausrichtung)"
                        u" WHEN 'oben' THEN 'Cap'"
                        u" WHEN 'Basis' THEN 'Base'"
                        u" ELSE 'Half'"
                        u" END AS valign"
                        u",coalesce(s.art,'Arial'::text) AS family"
                        u",CASE WHEN s.stil LIKE '%Kursiv%' THEN 1 ELSE 0 END AS italic"
                        u",CASE WHEN s.stil LIKE '%Fett%' THEN 1 ELSE 0 END AS bold"
                        u",coalesce(sperrung_pt*0.25,0) AS fontsperrung"
                        u",replace(f.umn,' ',',') AS tcolor"
                        u",CASE WHEN grad_pt<0 THEN 0 ELSE 1 END AS tshow"
                        u",{3}"
                        u" FROM {7}.po_labels"
                        u" LEFT OUTER JOIN {7}.alkis_schriften s ON po_labels.signaturnummer=s.signaturnummer{4}"
                        u" LEFT OUTER JOIN {7}.alkis_farben f ON s.farbe=f.id"
                        u" WHERE {5}"
                        u")\" ({6}) sql="
                    ).format(
                        conninfo, geomtype, self.epsg,
                        u"point,st_x(point) AS tx,st_y(point) AS ty,drehwinkel_grad AS tangle" if geom == "point" else "line",
                        "" if katalog < 0 else " AND s.katalog=%d" % katalog,
                        where,
                        geom,
                        self.quotedschema().replace(u'"', u'\\"')
                    )

                    qDebug(u"URI: %s" % uri)

                    layer = QgsVectorLayer(
                        uri,
                        u"Beschriftungen (%s)" % t,
                        "postgres", layeropts
                    )
                    layer.setReadOnly()
                    self.setShortName(layer)

                    self.setScale(layer, f['label'])

                    sym = QgsSymbol.defaultSymbol(self.PointGeometry if geom == "point" else self.LineGeometry)
                    if geom == "point":
                        sym.setSize(0.0)
                    else:
                        sym.changeSymbolLayer(0, QgsSimpleLineSymbolLayer(Qt.black, 0.0, Qt.NoPen))
                    self.setRenderer(layer, QgsSingleSymbolRenderer(sym))
                    self.refreshLayer(layer)

                    lyr = QgsPalLayerSettings()
                    lyr.fieldName = "text"
                    lyr.isExpression = False
                    lyr.enabled = True
                    # lyr.displayAll = True
                    if qgis3:
                        tf = QgsTextFormat()
                        tf.font().setPointSizeF(2.5)
                        tf.font().setFamily("Arial")
                        tf.setSizeUnit(self.MapUnit)

                        bs = QgsTextBufferSettings()
                        bs.setEnabled(True)
                        bs.setSize(0.125)
                        bs.setSizeUnit(self.MapUnit)
                        tf.setBuffer(bs)

                        lyr.setFormat(tf)
                    else:
                        lyr.textFont.setPointSizeF(2.5)
                        lyr.textFont.setFamily("Arial")
                        lyr.fontSizeInMapUnits = True

                        lyr.bufferSizeInMapUnits = True
                        lyr.bufferSize = 0.125
                        lyr.bufferDraw = True

                    lyr.upsidedownLabels = QgsPalLayerSettings.ShowAll
                    lyr.scaleVisibility = True

                    if geom == "point":
                        lyr.placement = QgsPalLayerSettings.AroundPoint
                    else:
                        lyr.placement = QgsPalLayerSettings.Curved
                        lyr.placementFlags = QgsPalLayerSettings.AboveLine

                    if qgis3:
                        c = QgsPropertyCollection()
                        c.setProperty(QgsPalLayerSettings.Size, QgsProperty.fromField("tsize"))
                        c.setProperty(QgsPalLayerSettings.FontSizeUnit, QgsProperty.fromField("tunit"))
                        c.setProperty(QgsPalLayerSettings.Family, QgsProperty.fromField("family"))
                        c.setProperty(QgsPalLayerSettings.Italic, QgsProperty.fromField("italic"))
                        c.setProperty(QgsPalLayerSettings.Bold, QgsProperty.fromField("bold"))
                        c.setProperty(QgsPalLayerSettings.Hali, QgsProperty.fromField("halign"))
                        c.setProperty(QgsPalLayerSettings.Vali, QgsProperty.fromField("valign"))
                        c.setProperty(QgsPalLayerSettings.Color, QgsProperty.fromField("tcolor"))
                        c.setProperty(QgsPalLayerSettings.FontLetterSpacing, QgsProperty.fromField("fontsperrung"))
                        if geom == "point":
                            c.setProperty(QgsPalLayerSettings.PositionX, QgsProperty.fromField("tx"))
                            c.setProperty(QgsPalLayerSettings.PositionY, QgsProperty.fromField("ty"))

                        c.setProperty(QgsPalLayerSettings.LabelRotation, QgsProperty.fromExpression("-tangle"))
                        c.setProperty(QgsPalLayerSettings.AlwaysShow, QgsProperty.fromField("tshow"))
                        lyr.setDataDefinedProperties(c)

                        layer.setLabeling(QgsVectorLayerSimpleLabeling(lyr))
                        layer.setLabelsEnabled(True)
                    else:
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, False, "", "tsize")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.FontSizeUnit, True, False, "", "tunit")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Family, True, False, "", "family")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Italic, True, False, "", "italic")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Bold, True, False, "", "bold")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Hali, True, False, "", "halign")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Vali, True, False, "", "valign")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Color, True, False, "", "tcolor")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.FontLetterSpacing, True, False, "", "fontsperrung")
                        if geom == "point":
                            lyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, "", "tx")
                            lyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, "", "ty")

                        lyr.setDataDefinedProperty(QgsPalLayerSettings.Rotation, True, False, "", "tangle")
                        lyr.setDataDefinedProperty(QgsPalLayerSettings.AlwaysShow, True, False, "", "tshow")

                        lyr.writeToLayer(layer)

                    self.refreshLayer(layer)

                    if labelGroup:
                        self.addLayer(layer, labelGroup)
                        layer = None

                    n += 1
                    nLayers += 1

                if layer is not None:
                    self.addLayer(layer, thisGroup)

                if nLayers > 0:
                    self.setGroupExpanded(thisGroup, False)
                    nSubGroups += 1
                elif thisGroup != themeGroup:
                    self.removeGroup(thisGroup)

            if nSubGroups > 0:
                nGroups += 1
            else:
                self.removeGroup(themeGroup)

        if nGroups > 0:
            self.setGroupExpanded(self.alkisGroup, False)
            self.setGroupVisible(self.alkisGroup, False)

            self.pointMarkerLayer = QgsVectorLayer(
                u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOINT srid=%d table=%s.po_labels (point) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                u"Punktmarkierung",
                "postgres", layeropts
            )

            sym = QgsSymbol.defaultSymbol(self.PointGeometry)
            sym.setColor(Qt.yellow)
            sym.setSize(20.0)
            sym.setOutputUnit(self.Millimeter)
            try:
                sym.setAlpha(0.5)
            except AttributeError:
                sym.setOpacity(0.5)
            self.setRenderer(self.pointMarkerLayer, QgsSingleSymbolRenderer(sym))

            self.addLayer(self.pointMarkerLayer, markerGroup)

            self.lineMarkerLayer = QgsVectorLayer(
                u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTILINESTRING srid=%d table=%s.po_labels (line) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                u"Linienmarkierung",
                "postgres", layeropts
            )

            sym = QgsLineSymbol()
            sym.setColor(Qt.yellow)
            try:
                sym.setAlpha(0.5)
            except AttributeError:
                sym.setOpacity(0.5)
            sym.setWidth(2)
            self.setRenderer(self.lineMarkerLayer, QgsSingleSymbolRenderer(sym))
            self.addLayer(self.lineMarkerLayer, markerGroup)

            self.areaMarkerLayer = QgsVectorLayer(
                u"%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                u"Flächenmarkierung",
                "postgres", layeropts
            )

            sym = QgsSymbol.defaultSymbol(self.PolygonGeometry)
            sym.setColor(Qt.yellow)
            try:
                sym.setAlpha(0.5)
            except AttributeError:
                sym.setOpacity(0.5)
            self.setRenderer(self.areaMarkerLayer, QgsSingleSymbolRenderer(sym))
            self.addLayer(self.areaMarkerLayer, markerGroup)

            QgsProject.instance().writeEntry("alkis", "/pointMarkerLayer", self.pointMarkerLayer.id())
            QgsProject.instance().writeEntry("alkis", "/lineMarkerLayer", self.lineMarkerLayer.id())
            QgsProject.instance().writeEntry("alkis", "/areaMarkerLayer", self.areaMarkerLayer.id())

            restrictedLayers, ok = QgsProject.instance().readListEntry("WMSRestrictedLayers", "/", [])

            for l in [u'Punktmarkierung', u'Linienmarkierung', u'Flächenmarkierung']:
                try:
                    restrictedLayers.index(l)
                except ValueError:
                    restrictedLayers.append(l)

            QgsProject.instance().writeEntry("WMSRestrictedLayers", "/", restrictedLayers)

            if qgis3:
                QgsProject.instance().setTrustLayerMetadata(True)

            self.settings.saveToProject()
        else:
            self.removeGroup(self.alkisGroup)

        self.iface.mapCanvas().setRenderFlag(True)

        self.showStatusMessage.emit(str(""))

    def setPointInfoTool(self):
        self.iface.mapCanvas().setMapTool(self.pointInfoTool)

    def setPolygonInfoTool(self):
        self.iface.mapCanvas().setMapTool(self.polygonInfoTool)

    def setQueryOwnerTool(self):
        self.iface.mapCanvas().setMapTool(self.queryOwnerInfoTool)

    def register(self):
        edbsgen = self.iface.mainWindow().findChild(QObject, "EDBSQuery")
        if edbsgen:
            if edbsgen.received.connect(self.message):
                qDebug(u"connected")
            else:
                qDebug(u"not connected")
        else:
            return False

    def opendb(self, conninfo=None):
        schema = self.settings.schema

        if not conninfo:
            service = self.settings.service
            host = self.settings.host
            port = self.settings.port
            dbname = self.settings.dbname
            uid = self.settings.uid
            pwd = self.settings.pwd

            if qgisAvailable:
                uri = QgsDataSourceUri()
                if service:
                    uri.setConnection(service, dbname, uid, pwd)
                else:
                    uri.setConnection(host, port, dbname, uid, pwd)

                if authAvailable:
                    authcfg = self.settings.authcfg
                    if authcfg:
                        uri.setAuthConfigId(authcfg)
                    conninfo = uri.connectionInfo(False)
                else:
                    conninfo = uri.connectionInfo()
            else:
                conninfo = ""
                if service:
                    conninfo = "service={} ".format(service)
                if host:
                    conninfo += "host={} ".format(host)
                if port:
                    conninfo += "port={} ".format(port)
                if dbname:
                    conninfo += "dbname={} ".format(dbname)
                if uid:
                    conninfo += "user={} ".format(uid)
                if pwd:
                    conninfo += "password={} ".format(pwd)

                conninfo = conninfo.strip()

        else:
            uid = None
            pwd = None
            uri = QgsDataSourceUri(conninfo)

        conninfo0 = conninfo

        if conninfo0 == self.conninfo and self.db and self.db.isOpen() and schema == self.schema:
            return (self.db, self.conninfo)

        if authAvailable:
            conninfo = uri.connectionInfo(True)

        QSqlDatabase.removeDatabase("ALKIS")
        db = QSqlDatabase.addDatabase("QPSQL", "ALKIS")
        db.setConnectOptions(conninfo)

        if not db.open() and qgisAvailable:
            while not db.open():
                ok, uid, pwd = QgsCredentials.instance().get(conninfo0, uid, pwd, u"Datenbankverbindung schlug fehl [%s]" % db.lastError().text())
                if not ok:
                    return (None, None)

                uri.setUsername(uid)
                uri.setPassword(pwd)
                conninfo = uri.connectionInfo(False) if authAvailable else uri.connectionInfo()
                db.setConnectOptions(conninfo)

            QgsCredentials.instance().put(conninfo0, uid, pwd)

        if db.isOpen() and qgisAvailable:
            qry = QSqlQuery(db)
            if not qry.prepare("SELECT set_config('search_path', quote_ident(?)||','||current_setting('search_path'), false)"):
                QMessageBox.warning(None, "ALKIS", u"Fehler: Konnte Schema-Aktivierung nicht vorbereiten [{}]!".format(qry.lastError().text()))

            qry.addBindValue(schema)

            if not qry.exec_():
                QMessageBox.warning(None, "ALKIS", u"Fehler: Schema {} konnte nicht aktiviert werden [{}]!".format(schema, qry.lastError().text()))
            elif not qry.exec_("SELECT current_schema()") or not qry.next():
                QMessageBox.warning(None, "ALKIS", u"Fehler: Aktiviertes Schema {} konnte nicht abgefragt werden [{}]!".format(schema, qry.lastError().text()))
            elif qry.value(0) != schema:
                QMessageBox.warning(None, "ALKIS", u"Fehler: Schema {} wurde nicht aktiviert [noch aktiv: {}]!".format(schema, qry.value(0)))

            sql = u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['gema_shl', 'eignerart', 'bestand', 'flurst']])
            buchZugriff = qry.exec_(sql) and qry.next() and qry.value(0)

            self.queryOwnerAction.setVisible(buchZugriff)

            if qry.exec_(u"SELECT find_srid('{}'::text,'ax_flurstueck'::text,'wkb_geometry'::text)".format(schema.replace("'", "''"))) and qry.next():
                self.epsg = int(qry.value(0))
            else:
                QMessageBox.warning(None, "ALKIS", u"Fehler: Keine Daten im Schema {} gefunden!".format(schema))
                return (None, None)

            self.schema = schema

        self.db = db
        self.conninfo = conninfo0

        return (db, self.conninfo)

    def message(self, msg):
        if msg.startswith("ALKISDRAW"):
            (prefix, hatch, window, qry) = msg.split(' ', 3)
            if qry.startswith("ids:"):
                self.highlight(where="gml_id in (%s)" % qry[4:], zoomTo=True)
            elif qry.startswith("where:"):
                self.highlight(where=qry[6:], zoomTo=True)
            elif qry.startswith("select "):
                self.highlight(where="gml_id in (%s)" % qry, zoomTo=True)

    def clearHighlight(self):
        if self.pointMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/pointMarkerLayer")
            if ok:
                self.pointMarkerLayer = self.mapLayer(layerId)

        if self.pointMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Punktmarkierungslayer nicht gefunden!")
            return

        self.pointMarkerLayer.setSubsetString("false")

        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")
            return

        self.areaMarkerLayer.setSubsetString("false")
        # currentLayer = self.iface.activeLayer()
        self.iface.mapCanvas().refresh()

    def highlighted(self):
        if self.areaMarkerLayer is not None:
            m = re.search("layer='ax_flurstueck' AND gml_id IN \\('(.*)'\\)", self.areaMarkerLayer.subsetString())
            if m:
                return m.group(1).split("','")

        return []

    def retrieve(self, where):
        if not isinstance(where, list):
            where = [where]

        fs = []

        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")
            return fs

        (db, conninfo) = self.opendb()
        if db is None:
            return fs

        qry = QSqlQuery(db)

        if not qry.exec_(
                u"SELECT "
                u"gml_id"
                u",alkis_flsnr(ax_flurstueck)"
                u" FROM ax_flurstueck"
                u" WHERE endet IS NULL"
                u" AND (%s)" % u" AND ".join(where)
        ):
            QMessageBox.critical(None, "Fehler", u"Konnte Abfrage nicht ausführen.\nSQL:%s\nFehler:%s" % (qry.lastQuery(), qry.lastError().text()))
            return fs

        qDebug(qry.lastQuery())

        while qry.next():
            fs.append({'gmlid': qry.value(0), 'flsnr': qry.value(1)})

        return fs

    def highlight(self, where='', fs=[], zoomTo=False, add=False):
        if not self.areaMarkerLayer:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if not self.areaMarkerLayer:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")
            return []

        if (fs and where) or (not fs and not where):
            raise BaseException("fs xor where")

        if not fs:
            fs = self.retrieve(where)

        gmlids = set()
        for e in fs:
            gmlids.add(e['gmlid'])

        if add:
            gmlids = gmlids | set(self.highlighted())

        self.areaMarkerLayer.setSubsetString("layer='ax_flurstueck' AND gml_id IN ('" + "','".join(gmlids) + "')")

        # currentLayer = self.iface.activeLayer()

        self.iface.mapCanvas().refresh()

        (db, conninfo) = self.opendb()
        if db is None:
            return fs

        qry = QSqlQuery(db)
        if zoomTo and qry.exec_(u"SELECT st_extent(wkb_geometry),count(*) FROM ax_flurstueck WHERE gml_id IN ('" + "','".join(gmlids) + "')") and qry.next() and qry.value(1) > 0:
            self.zoomToExtent(qry.value(0), self.areaMarkerLayer.crs())

        return fs

    def zoomToExtent(self, bb, crs):
        if bb is None:
            return

        bb = bb[4:-1]
        (p0, p1) = bb.split(",")
        (x0, y0) = p0.split(" ")
        (x1, y1) = p1.split(" ")
        qDebug(u"x0:%s y0:%s x1:%s y1:%s" % (x0, y0, x1, y1))
        rect = QgsRectangle(float(x0), float(y0), float(x1), float(y1))

        if not isinstance(crs, QgsCoordinateReferenceSystem):
            epsg = crs
            crs = QgsCoordinateReferenceSystem(epsg)

            if not crs.isValid():
                QMessageBox.critical(None, "ALKIS", u"Ungültiges Koordinatensystem %d" % epsg)
                return

        rect = self.transform(rect, crs, self.destinationCrs())

        qDebug(u"rect:%s" % rect.toString())

        self.iface.mapCanvas().setExtent(rect)
        self.iface.mapCanvas().refresh()

    def setLayerData(self, layer, data):
        if int(sys.version[0]) < 3:
            layer.data = data.encode("utf-8")
        else:
            layer.data = data

    def setLayerMetaData(self, layer, k, v):
        if int(sys.version[0]) < 3:
            layer.setMetaData(k, v.encode("utf-8"))
        else:
            layer.setMetaData(k, v)

    def setClassName(self, c, name):
        if int(sys.version[0]) < 3:
            c.name = name.encode("utf-8")
        else:
            c.name = name

    def mapfile(self, conninfo=None, dstfile=None):
        try:
            if qgisAvailable:
                QApplication.setOverrideCursor(Qt.WaitCursor)

            self.settings.loadSettings()
            (db, conninfo) = self.opendb(conninfo)
            if db is None or not db.isOpen():
                if not qgisAvailable:
                    raise BaseException("Database connection failed.")
                return

            qry = QSqlQuery(db)
            qry2 = QSqlQuery(db)

            if dstfile is None:
                if not self.iface or not self.iface:
                    raise BaseException("Destination file missing.")

                try:
                    QApplication.setOverrideCursor(Qt.ArrowCursor)
                    dstfile = QFileDialog.getSaveFileName(None, "Mapfiledateinamen angeben", "", "UMN-Mapdatei (*.map)")
                finally:
                    QApplication.restoreOverrideCursor()

                if dstfile is None:
                    return

                if isinstance(dstfile, tuple):
                    dstfile = dstfile[0]

            if qgisAvailable:
                if hasattr(self.iface.mainWindow(), "showProgress"):
                    self.showProgress.connect(self.iface.mainWindow().showProgress)
                else:
                    self.showProgress.connect(self.doShowProgress)
                self.showStatusMessage.connect(self.iface.mainWindow().showStatusMessage)

            if not self.iface:
                if not qry.prepare("SELECT set_config('search_path', quote_ident(?)||','||current_setting('search_path'), false)"):
                    raise BaseException("Could not prepare search path update [{}]".format(qry.lastError().text()))

                qry.addBindValue(self.settings.schema)
                self.schema = self.settings.schema

                if not qry.exec_():
                    raise BaseException("Could not set search path.")

            mapobj = mapscript.mapObj()
            mapobj.name = "ALKIS"
            mapobj.setFontSet(os.path.join(BASEDIR, "fonts", "fonts.txt"))

            mapobj.outputformat.driver = "GD/PNG"
            mapobj.outputformat.imagemode = mapscript.MS_IMAGEMODE_RGB

            mapobj.legend.label.type = mapscript.MS_TRUETYPE
            mapobj.legend.label.font = 'arial'

            mapobj.maxsize = 20480
            mapobj.setSize(400, 400)
            try:
                mapobj.web.metadata.set(u"wms_title", "ALKIS")
                mapobj.web.metadata.set(u"wms_enable_request", "*")
                mapobj.web.metadata.set(u"wfs_enable_request", "*")
                mapobj.web.metadata.set(u"ows_enable_request", "*")
                mapobj.web.metadata.set(u"wms_feature_info_mime_type", "text/html")
                mapobj.web.metadata.set(u"wms_encoding", "UTF-8")
            except AttributeError:
                mapobj.web.metadata[u"wms_title"] = "ALKIS"
                mapobj.web.metadata[u"wms_enable_request"] = "*"
                mapobj.web.metadata[u"wfs_enable_request"] = "*"
                mapobj.web.metadata[u"ows_enable_request"] = "*"
                mapobj.web.metadata[u"wms_feature_info_mime_type"] = "text/html"
                mapobj.web.metadata[u"wms_encoding"] = "UTF-8"

            symbol = mapscript.symbolObj("0")
            symbol.inmapfile = True
            symbol.type = mapscript.MS_SYMBOL_ELLIPSE
            symbol.filled = mapscript.MS_TRUE
            line = mapscript.lineObj()
            p = mapscript.pointObj()
            p.x = 1
            p.y = 1
            line.add(p)
            if line.add(p) != mapscript.MS_SUCCESS:
                raise BaseException("failed to add point %d" % p)

            if symbol.setPoints(line) != 2:
                raise BaseException("failed to add all %d points" % line.numpoints)

            if mapobj.symbolset.appendSymbol(symbol) < 0:
                raise BaseException("symbol not added.")

            if qry.exec_(u"SELECT st_extent(wkb_geometry),find_srid('{}'::text,'ax_flurstueck'::text,'wkb_geometry'::text) FROM ax_flurstueck".format(self.settings.schema)) and qry.next():
                bb = qry.value(0)[4:-1]
                (p0, p1) = bb.split(",")
                (x0, y0) = p0.split(" ")
                (x1, y1) = p1.split(" ")
                self.epsg = int(qry.value(1))
                if self.epsg > 100000:
                    if qry.exec_("SELECT proj4text FROM spatial_ref_sys WHERE srid=%d" % self.epsg) and qry.next():
                        crs = qry.value(0)
                        mapobj.setProjection(crs)
                else:
                    crs = "init=epsg:%d" % self.epsg
                    mapobj.setProjection(crs)
                mapobj.setExtent(float(x0), float(y0), float(x1), float(y1))
            else:
                crs = "init=epsg:%d" % self.epsg

            modelle = self.settings.modellarten
            katalog = self.settings.signaturkatalog

            missing = {}
            symbols = {}

            iThema = -1
            iLayer = 0
            for d in alkisplugin.themen:
                iThema += 1
                thema = d['name']

                if 'filter' not in d:
                    d['filter'] = [{'name': None, 'filter': None}]

                qDebug(u"Thema: %s" % thema)

                for f in d['filter']:
                    name = f.get('name', thema)
                    tname = thema

                    where = u"thema='%s'" % thema
                    if len(modelle) > 0:
                        where += u" AND modell && ARRAY['%s']::varchar[]" % "','".join(modelle)

                    if f.get('name', None):
                        tname += u" / " + f['name']

                    if f.get('filter', None):
                        where += u" AND (%s)" % f['filter']

                    for k in ['area', 'outline', 'line', 'point', 'label']:
                        if k not in f:
                            f[k] = d[k]

                    self.progress(iThema, u"Flächen", 0)

                    # 1 Polylinien
                    # 1.1 Flächen
                    # 1.2 Randlinien
                    # 2 Linien
                    # 3 Punkte
                    # 4 Beschriftungen

                    group = []
                    layer = None
                    sprio = None
                    minprio = None
                    maxprio = None
                    nclasses = None

                    layer = mapscript.layerObj(mapobj)
                    layer.name = "l%d" % iLayer
                    layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                    iLayer += 1

                    self.setLayerData(layer, u"geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_flaeche AS signaturnummer FROM %s.po_polygons WHERE %s AND NOT sn_flaeche IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg))
                    layer.classitem = "signaturnummer"
                    layer.setProjection(crs)
                    layer.connectiontype = mapscript.MS_POSTGIS
                    layer.connection = conninfo
                    layer.symbolscaledenom = 1000
                    layer.setProcessing("CLOSE_CONNECTION=DEFER")
                    layer.type = mapscript.MS_LAYER_POLYGON
                    layer.sizeunits = mapscript.MS_INCHES
                    layer.status = mapscript.MS_OFF
                    layer.tileitem = None
                    self.setLayerMetaData(layer, u"norGIS_label", (u"ALKIS / %s / Flächen" % tname))
                    self.setLayerMetaData(layer, u"wms_layer_group", (u"/%s" % tname))
                    self.setLayerMetaData(layer, u"wms_title", u"Flächen")
                    self.setLayerMetaData(layer, u"wfs_title", u"Flächen")
                    self.setLayerMetaData(layer, u"gml_geom_type", "multipolygon")
                    self.setLayerMetaData(layer, u"gml_geometries", "geom")
                    self.setLayerMetaData(layer, u"gml_featureid", "ogc_fid")
                    self.setLayerMetaData(layer, u"gml_include_items", "all")
                    self.setLayerMetaData(layer, u"wms_srs", alkisplugin.defcrs)
                    self.setLayerMetaData(layer, u"wfs_srs", alkisplugin.defcrs)
                    self.setUMNScale(layer, f['area'])

                    sql = (u"SELECT DISTINCT"
                           u" signaturnummer,umn,darstellungsprioritaet,alkis_flaechen.name"
                           u" FROM alkis_flaechen"
                           u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                           u" WHERE EXISTS ("
                           u"SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer"
                           u"){1}"
                           u" ORDER BY darstellungsprioritaet"
                           ).format(
                               where,
                               "" if katalog < 0 else " AND katalog=%d" % katalog
                    )
                    # qDebug( "SQL: %s" % sql )

                    if qry.exec_(sql):
                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        while qry.next():
                            sn = qry.value(0)
                            color = qry.value(1)
                            prio = qry.value(2)
                            name = qry.value(3)

                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            self.setClassName(cl, d['classes'].get(sn, name))

                            style = mapscript.styleObj()
                            if color:
                                r, g, b = color.split(" ")
                                style.color.setRGB(int(r), int(g), int(b))
                            else:
                                style.color.setRGB(0, 0, 0)

                            cl.insertStyle(style)

                            nclasses += 1
                            sprio += prio
                            if not minprio or prio < minprio:
                                minprio = prio
                            if not maxprio or prio > maxprio:
                                maxprio = prio

                    else:
                        QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                        break

                    if layer.numclasses > 0:
                        self.setLayerMetaData(layer, "norGIS_zindex", "%d" % (sprio / nclasses))
                        self.setLayerMetaData(layer, "norGIS_minprio", "%d" % minprio)
                        self.setLayerMetaData(layer, "norGIS_maxprio", "%d" % maxprio)

                        group.append(layer.name)
                    else:
                        mapobj.removeLayer(layer.index)

                    self.progress(iThema, "Grenzen", 1)

                    #
                    # 1.2 Randlinien
                    #
                    layer = mapscript.layerObj(mapobj)
                    layer.name = "l%d" % iLayer
                    layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                    iLayer += 1
                    self.setLayerData(layer, u"geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_randlinie AS signaturnummer FROM %s.po_polygons WHERE %s AND NOT polygon IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg))
                    layer.classitem = "signaturnummer"
                    layer.setProjection(crs)
                    layer.connection = conninfo
                    layer.connectiontype = mapscript.MS_POSTGIS
                    layer.setProcessing("CLOSE_CONNECTION=DEFER")
                    # layer.symbolscaledenom = 1000
                    layer.sizeunits = mapscript.MS_METERS
                    layer.type = mapscript.MS_LAYER_POLYGON
                    layer.status = mapscript.MS_OFF
                    layer.tileitem = None
                    self.setLayerMetaData(layer, "norGIS_label", u"ALKIS / %s / Grenzen" % tname)
                    self.setLayerMetaData(layer, u"wms_layer_group", u"/%s" % tname)
                    self.setLayerMetaData(layer, u"wms_title", u"Grenzen")
                    self.setLayerMetaData(layer, u"wfs_title", u"Grenzen")
                    self.setLayerMetaData(layer, u"gml_geom_type", "multiline")
                    self.setLayerMetaData(layer, u"gml_geometries", "geom")
                    self.setLayerMetaData(layer, u"gml_featureid", "ogc_fid")
                    self.setLayerMetaData(layer, u"gml_include_items", "all")
                    self.setLayerMetaData(layer, u"wms_srs", alkisplugin.defcrs)
                    self.setLayerMetaData(layer, u"wfs_srs", alkisplugin.defcrs)
                    self.setUMNScale(layer, f['outline'])

                    sql = (u"SELECT DISTINCT"
                           u" ln.signaturnummer,umn,darstellungsprioritaet,ln.name"
                           u" FROM alkis_linien ln{0}"
                           u" LEFT OUTER JOIN alkis_farben f ON {1}.farbe=f.id"
                           u" WHERE EXISTS ("
                           u"SELECT * FROM po_polygons WHERE {2} AND po_polygons.sn_randlinie=ln.signaturnummer"
                           u"){3}"
                           u" ORDER BY darstellungsprioritaet"
                           ).format(
                               "" if katalog < 0 else u" LEFT OUTER JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer AND l.katalog=%d" % katalog,
                               "ln" if katalog < 0 else "l",
                               where,
                               "" if katalog < 0 else " AND ln.katalog=%d" % katalog
                    )

                    # qDebug( "SQL: %s" % sql )
                    if qry.exec_(sql):
                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        while qry.next():
                            sn = qry.value(0)
                            color = qry.value(1)
                            prio = qry.value(2)
                            name = qry.value(3)

                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            self.setClassName(cl, d['classes'].get(sn, name))

                            if not self.addLineStyles(db, cl, katalog, sn, color, True):
                                layer.removeClass(layer.numclasses - 1)

                            nclasses += 1
                            sprio += prio
                            if not minprio or prio < minprio:
                                minprio = prio
                            if not maxprio or prio > maxprio:
                                maxprio = prio

                    else:
                        QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                        break

                    if layer.numclasses > 0:
                        self.setLayerMetaData(layer, "norGIS_zindex", "%d" % (sprio / nclasses))
                        self.setLayerMetaData(layer, "norGIS_minprio", "%d" % minprio)
                        self.setLayerMetaData(layer, "norGIS_maxprio", "%d" % maxprio)

                        group.append(layer.name)
                    else:
                        mapobj.removeLayer(layer.index)

                    self.progress(iThema, "Linien", 2)

                    #
                    # 2 Linien
                    #
                    layer = mapscript.layerObj(mapobj)
                    layer.name = "l%d" % iLayer
                    layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                    iLayer += 1
                    self.setLayerData(layer, u"geom FROM (SELECT ogc_fid,gml_id,line AS geom,signaturnummer FROM %s.po_lines WHERE %s AND NOT line IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg))
                    layer.classitem = "signaturnummer"
                    layer.setProjection(crs)
                    layer.connection = conninfo
                    layer.connectiontype = mapscript.MS_POSTGIS
                    layer.setProcessing("CLOSE_CONNECTION=DEFER")
                    # layer.symbolscaledenom = 1000
                    layer.sizeunits = mapscript.MS_METERS
                    layer.type = mapscript.MS_LAYER_LINE
                    layer.status = mapscript.MS_OFF
                    layer.tileitem = None
                    self.setLayerMetaData(layer, "norGIS_label", u"ALKIS / %s / Linien" % tname)
                    self.setLayerMetaData(layer, u"wms_layer_group", u"/%s" % tname)
                    self.setLayerMetaData(layer, u"wms_title", u"Linien")
                    self.setLayerMetaData(layer, u"wfs_title", u"Linien")
                    self.setLayerMetaData(layer, u"gml_geom_type", "multiline")
                    self.setLayerMetaData(layer, u"gml_geometries", "geom")
                    self.setLayerMetaData(layer, u"gml_featureid", "ogc_fid")
                    self.setLayerMetaData(layer, u"gml_include_items", "all")
                    self.setLayerMetaData(layer, u"wms_srs", alkisplugin.defcrs)
                    self.setLayerMetaData(layer, u"wfs_srs", alkisplugin.defcrs)
                    self.setUMNScale(layer, f['line'])

                    sql = (u"SELECT DISTINCT"
                           u" ln.signaturnummer,umn,darstellungsprioritaet,ln.name"
                           u" FROM alkis_linien ln{0}"
                           u" JOIN alkis_farben f ON {1}.farbe=f.id"
                           u" WHERE EXISTS ("
                           u"SELECT * FROM po_lines WHERE {2} AND po_lines.signaturnummer=ln.signaturnummer"
                           u"){3}"
                           u" ORDER BY darstellungsprioritaet"
                           ).format(
                               "" if katalog < 0 else u" JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer AND l.katalog=%d" % katalog,
                               "ln" if katalog < 0 else "l",
                               where,
                               "" if katalog < 0 else u" AND ln.katalog=%d" % katalog
                    )
                    # qDebug( "SQL: %s" % sql )
                    if qry.exec_(sql):
                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        while qry.next():
                            sn = qry.value(0)
                            color = qry.value(1)
                            prio = qry.value(2)
                            name = qry.value(3)

                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            self.setClassName(cl, d['classes'].get(sn, name))

                            if not self.addLineStyles(db, cl, katalog, sn, color, False):
                                layer.removeClass(layer.numclasses - 1)

                            nclasses += 1
                            sprio += prio
                            if not minprio or prio < minprio:
                                minprio = prio
                            if not maxprio or prio > maxprio:
                                maxprio = prio

                        # style caching (https://github.com/mapserver/mapserver/issues/4612) berücksichtigen
                        haveMultipleStyles = False
                        for i in range(layer.numclasses):
                            cl = layer.getClass(i)
                            if cl.numstyles > 0:
                                haveMultipleStyles = True
                                break

                        if haveMultipleStyles:
                            nStyles = 0
                            for i in range(layer.numclasses):
                                cl = layer.getClass(i)
                                for j in range(nStyles):
                                    cl.insertStyle(mapscript.styleObj(), 0)   # Leeren Style einfügen
                                nStyles += cl.numstyles

                    else:
                        QMessageBox.critical(None, "ALKIS", u"Fehler: %s\nSQL: %s" % (qry.lastError().text(), sql))
                        break

                    if layer.numclasses > 0:
                        self.setLayerMetaData(layer, "norGIS_zindex", "%d" % (sprio / nclasses))
                        self.setLayerMetaData(layer, "norGIS_minprio", "%d" % minprio)
                        self.setLayerMetaData(layer, "norGIS_maxprio", "%d" % maxprio)

                        group.append(layer.name)
                    else:
                        n = mapobj.numlayers
                        mapobj.removeLayer(layer.index)
                        if n == mapobj.numlayers:
                            raise BaseException("No layer removed")

                    #
                    # 3 Punkte (TODO: Darstellungspriorität)
                    #

                    layer = mapscript.layerObj(mapobj)
                    layer.name = "l%d" % iLayer
                    layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                    iLayer += 1
                    self.setLayerData(layer, u"geom FROM (SELECT ogc_fid,gml_id,point AS geom,drehwinkel_grad,signaturnummer FROM %s.po_points WHERE %s AND NOT point IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg))
                    layer.classitem = "signaturnummer"
                    layer.setProjection(crs)
                    layer.connection = conninfo
                    layer.connectiontype = mapscript.MS_POSTGIS
                    layer.setProcessing("CLOSE_CONNECTION=DEFER")
                    layer.symbolscaledenom = 1000
                    layer.sizeunits = mapscript.MS_METERS
                    layer.type = mapscript.MS_LAYER_POINT
                    layer.status = mapscript.MS_OFF
                    layer.tileitem = None
                    self.setLayerMetaData(layer, "norGIS_label", u"ALKIS / %s / Punkte" % tname)
                    self.setLayerMetaData(layer, u"wms_layer_group", u"/%s" % tname)
                    self.setLayerMetaData(layer, u"wms_title", u"Punkte")
                    self.setLayerMetaData(layer, u"wfs_title", u"Punkte")
                    self.setLayerMetaData(layer, u"gml_geom_type", "multipoint")
                    self.setLayerMetaData(layer, u"gml_geometries", "geom")
                    self.setLayerMetaData(layer, u"gml_featureid", "ogc_fid")
                    self.setLayerMetaData(layer, u"gml_include_items", "all")
                    self.setLayerMetaData(layer, u"wms_srs", alkisplugin.defcrs)
                    self.setLayerMetaData(layer, u"wfs_srs", alkisplugin.defcrs)
                    self.setUMNScale(layer, f['point'])

                    self.progress(iThema, "Punkte", 3)

                    kat = max([1, katalog])

                    sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE (%s)" % where
                    # qDebug( "SQL: %s" % sql )
                    if qry.exec_(sql):
                        while qry.next():
                            sn = qry.value(0)
                            if not sn:
                                logMessage(u"Leere Signaturnummer in po_points:%s" % thema)
                                continue

                            path = os.path.abspath(os.path.join(BASEDIR, "svg", "alkis%s_%d.svg" % (sn, kat)))

                            if "norGIS_alkis%s_%d" % (sn, kat) not in symbols and not os.path.isfile(path):
                                if sn != '6000':
                                    logMessage("Symbol alkis%s_%d.svg nicht gefunden" % (sn, kat))
                                    missing["norGIS_alkis%s" % sn] = 1
                                continue

                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            self.setClassName(cl, d['classes'].get(sn, "(%s)" % sn))

                            x, y, h = 0, 0, 1
                            if qry2.exec_("SELECT x0,y0,x1,y1 FROM alkis_punkte WHERE katalog=%d AND signaturnummer='%s'" % (kat, sn)) and qry2.next():
                                x = (qry2.value(0) + qry2.value(2)) / 2
                                y = (qry2.value(1) + qry2.value(3)) / 2
                                w = qry2.value(2) - qry2.value(0)
                                h = qry2.value(3) - qry2.value(1)
                            elif sn not in alkisplugin.exts:
                                x = (alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx']) / 2
                                y = (alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy']) / 2
                                w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
                                h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']

                            if "norGIS_alkis%s_%d" % (sn, kat) not in symbols:
                                fd, tempname = mkstemp()
                                os.close(fd)

                                symbolf = open(tempname, "w", encoding="utf-8")
                                symbolf.write(u"SYMBOLSET SYMBOL TYPE SVG NAME \"norGIS_alkis{0}_{1}\" IMAGE \"{2}/alkis{0}_{1}.svg\" ANCHORPOINT {3} {4} END END".format(
                                    sn,
                                    kat,
                                    self.settings.umnpath + "/svg",
                                    0.5 + x / w,
                                    0.5 + y / h,
                                ))
                                symbolf.close()

                                tempsymbolset = mapscript.symbolSetObj(tempname)

                                os.unlink(tempname)

                                sym = tempsymbolset.getSymbolByName("norGIS_alkis%s_%d" % (sn, kat))
                                sym.inmapfile = True
                                if mapobj.symbolset.appendSymbol(sym) < 0:
                                    raise BaseException("symbol not added.")

                                del tempsymbolset
                                symbols["norGIS_alkis%s_%d" % (sn, kat)] = 1

                            stylestring = "STYLE ANGLE [drehwinkel_grad] SIZE %lf SYMBOL \"norGIS_alkis%s_%d\" MINSIZE 1 END" % (h, sn, kat)
                            style = fromstring(stylestring)
                            cl.insertStyle(style)

                    if layer.numclasses > 0:
                        group.append(layer.name)
                    else:
                        mapobj.removeLayer(layer.index)

                    #
                    # 4 Beschriftungen (TODO: Darstellungspriorität)
                    #

                    lgroup = []

                    for j in range(2):
                        geom = "point" if j == 0 else "line"

                        if not qry.exec_("SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL" % (where, geom)) or not qry.next() or qry.value(0) == 0:
                            continue

                        self.progress(iThema, "Beschriftungen (%d)" % (j + 1), 4 + j)

                        layer = mapscript.layerObj(mapobj)
                        layer.name = "l%d" % iLayer
                        layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                        iLayer += 1
                        self.setLayerMetaData(layer, u"norGIS_label", u"ALKIS / %s / Beschriftungen" % tname)
                        self.setLayerMetaData(layer, u"wms_layer_group", u"/%s" % tname)
                        self.setLayerMetaData(layer, u"wms_title", u"Beschriftungen (%s)" % ("Punkte" if j == 0 else "Linien"))
                        self.setLayerMetaData(layer, u"wfs_title", u"Beschriftungen (%s)" % ("Punkte" if j == 0 else "Linien"))
                        self.setLayerMetaData(layer, u"gml_geom_type", "multipoint")
                        self.setLayerMetaData(layer, u"gml_geometries", "geom")
                        self.setLayerMetaData(layer, u"gml_featureid", "ogc_fid")
                        self.setLayerMetaData(layer, u"gml_include_items", "all")
                        self.setLayerMetaData(layer, u"wms_srs", alkisplugin.defcrs)
                        self.setLayerMetaData(layer, u"wfs_srs", alkisplugin.defcrs)
                        self.setLayerMetaData(layer, u"norGIS_zindex", "999")
                        self.setUMNScale(layer, f['label'])

                        data = (u"geom FROM (SELECT"
                                u" ogc_fid"
                                u",gml_id"
                                u",text"
                                u",f.umn AS color_umn"
                                u",lower(art) || coalesce('-'||effekt,'') ||"
                                u"CASE"
                                u" WHEN stil='Kursiv' THEN '-italic'"
                                u" WHEN stil='Fett' THEN '-bold'"
                                u" WHEN stil='Fett, Kursiv' THEN '-bold-italic'"
                                u" ELSE ''"
                                u" END || CASE"
                                u" WHEN coalesce(fontsperrung,0)=0 THEN ''"
                                u" ELSE '-'||(fontsperrung/0.25)::int"
                                u" END AS font_umn"
                                u",0.25/0.0254*skalierung*grad_pt AS size_umn"
                                )

                        lwhere = where
                        if geom == "point":
                            data += (u",CASE coalesce(l.vertikaleausrichtung,s.vertikaleausrichtung) "
                                     u" WHEN 'oben' THEN 'L'"
                                     u" WHEN 'Basis' THEN 'U'"
                                     u" ELSE 'C'"
                                     u" END || CASE coalesce(l.horizontaleausrichtung,s.horizontaleausrichtung)"
                                     u" WHEN 'linksbündig' THEN 'L'"
                                     u" WHEN 'rechtsbündig' THEN 'R'"
                                     u" ELSE 'C'"
                                     u" END AS position_umn"
                                     u",drehwinkel_grad"
                                     u",point AS geom"
                                     )
                            lwhere += " AND point IS NOT NULL"
                        else:
                            data += u",st_offsetcurve(line,0.125*skalierung*grad_pt,'') AS geom"
                            lwhere += " AND line IS NOT NULL"

                        data += (u" FROM {0}.po_labels l"
                                 u" JOIN {0}.alkis_schriften s ON s.signaturnummer=l.signaturnummer{1}"
                                 u" JOIN {0}.alkis_farben f ON s.farbe=f.id"
                                 u" WHERE {2}"
                                 u") AS foo USING UNIQUE ogc_fid USING SRID={3}"
                                 ).format(
                                     self.quotedschema(),
                                     "" if katalog < 0 else " AND s.katalog=%d" % katalog,
                                     lwhere,
                                     self.epsg)

                        self.setLayerData(layer, data)

                        cl = mapscript.classObj(layer)
                        label = mapscript.labelObj()

                        if geom == "point":
                            label.type = mapscript.MS_TRUETYPE
                            label.setBinding(mapscript.MS_LABEL_BINDING_COLOR, "color_umn")
                            label.setBinding(mapscript.MS_LABEL_BINDING_FONT, "font_umn")
                            label.setBinding(mapscript.MS_LABEL_BINDING_ANGLE, "drehwinkel_grad")
                            label.setBinding(mapscript.MS_LABEL_BINDING_SIZE, "size_umn")
                            label.setBinding(mapscript.MS_LABEL_BINDING_POSITION, "position_umn")
                            label.buffer = 2
                            label.force = mapscript.MS_TRUE
                            label.partials = mapscript.MS_TRUE
                            label.antialias = mapscript.MS_TRUE
                            label.outlinecolor.setRGB(255, 255, 255)
                            label.mindistance = -1
                            label.minfeaturesize = -1
                            label.shadowsizex = 0
                            label.shadowsizey = 0
                            # label.minsize = 4
                            # label.maxsize = 256
                            label.minfeaturesize = -1
                            label.priority = 10
                        else:
                            label.updateFromString("""
    LABEL
    ANGLE FOLLOW
    ANTIALIAS TRUE
    FONT [font_umn]
    SIZE [size_umn]
    BUFFER 2
    COLOR [color_umn]
    FORCE TRUE
    OFFSET 0 0
    OUTLINECOLOR 255 255 255
    PRIORITY 10
    SHADOWSIZE 0 0
    TYPE TRUETYPE
    END
    """)

                        cl.addLabel(label)

                        layer.labelitem = "text"
                        layer.setProjection(crs)

                        layer.connection = conninfo
                        layer.connectiontype = mapscript.MS_POSTGIS
                        layer.setProcessing("CLOSE_CONNECTION=DEFER")
                        layer.symbolscaledenom = 1000
                        # layer.labelminscaledenom = 0
                        # layer.labelmaxscaledenom = 2000
                        layer.sizeunits = mapscript.MS_INCHES
                        layer.type = mapscript.MS_LAYER_POINT if mapscript.MS_VERSION_MAJOR > 6 else mapscript.MS_LAYER_ANNOTATION
                        layer.status = mapscript.MS_OFF
                        layer.tileitem = None

                        lgroup.append(layer.name)

            self.reorderLayers(mapobj)

            self.showProgress.emit(len(alkisplugin.themen) * 5, len(alkisplugin.themen) * 5)

            mapobj.save(dstfile)

            if self.settings.umnpath != BASEDIR:
                os.rename(dstfile, dstfile + ".bak")
                i = open(dstfile + ".bak", "r", encoding="utf-8")
                o = open(dstfile, "w", encoding="utf-8")

                for l in i:
                    if 'FONTSET "' in l:
                        o.write(u'  FONTSET "%s/fonts/fonts.txt"\n' % self.settings.umnpath)
                    else:
                        o.write(l)

                o.close()
                i.close()

                os.remove(dstfile + ".bak")

        finally:
            if qgisAvailable:
                QApplication.restoreOverrideCursor()

    def addLineStyles(self, db, cl, kat, sn, c, outline):
        assert cl.numstyles == 0

        sql = (u"SELECT abschluss,scheitel,coalesce(strichstaerke/100,0),coalesce(laenge/100,0),coalesce(einzug/100,0),abstand{0}"
               u" FROM alkis_linie l"
               u" LEFT OUTER JOIN alkis_stricharten_i ON l.strichart=alkis_stricharten_i.stricharten"
               u" LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
               u"{1}"
               u" WHERE l.signaturnummer='{2}'{3}"
               ).format(
                   "" if kat < 0 else ",r,g,b",
                   "" if kat < 0 else " LEFT OUTER JOIN alkis_farben ON l.farbe=alkis_farben.id",
                   sn,
                   "" if kat < 0 else " AND l.katalog=%d" % kat
        )

        lqry = QSqlQuery(db)
        if lqry.exec_(sql):
            stricharten = []

            maxStrichstaerke = None

            while lqry.next():
                abschluss, scheitel, strichstaerke, laenge, einzug, abstaende = \
                    lqry.value(0), lqry.value(1), float(lqry.value(2)), \
                    float(lqry.value(3)), float(lqry.value(4)), lqry.value(5)

                if kat >= 0:
                    c = [int(lqry.value(6)), int(lqry.value(7)), int(lqry.value(8))]

                if maxStrichstaerke is None or abs(strichstaerke) > abs(maxStrichstaerke):
                    maxStrichstaerke = strichstaerke

                if abstaende:
                    if abstaende.startswith("{") and abstaende.endswith("}"):
                        abstaende = [float(x) / 100 for x in abstaende[1:-1].split(",")]
                    else:
                        abstaende = [float(abstaende) / 100]
                else:
                    abstaende = []

                gesamtl = 0
                for abstand in abstaende:
                    gesamtl += laenge + abstand

                stricharten.append([abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c])

            gesamtl0 = None
            leinzug = None
            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c in stricharten:
                if gesamtl0 is None:
                    gesamtl0 = gesamtl
                elif gesamtl0 != gesamtl:
                    raise BaseException(u"Signaturnummer %s: Stricharten nicht gleich lang (%lf vs %lf)" % (sn, gesamtl0, gesamtl))

                if laenge > 0:
                    if leinzug is None:
                        leinzug = einzug
                    elif leinzug != einzug:
                        # raise BaseException( u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug) )
                        logMessage(u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug))
                        return False

            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl, c in stricharten:
                if abstaende and laenge == 0:
                    # Marker line
                    if leinzug:
                        if einzug > leinzug:
                            einzug -= leinzug
                        else:
                            einzug += gesamtl - leinzug

                    style = mapscript.styleObj()

                    s = "STYLE SYMBOL 0 PATTERN "
                    for abstand in abstaende:
                        s += "0 %s " % str(abstand)
                    s += "END END"
                    style.updateFromString(s)

                    style.initialgap = einzug
                else:
                    # Simple line
                    style = mapscript.styleObj()

                    if abstaende:
                        dashvector = []
                        for abstand in abstaende:
                            dashvector.extend([laenge, abstand])

                        style.updateFromString("STYLE SYMBOL 0 PATTERN %s END END" % (' '.join([str(x) for x in dashvector])))

                style.linecap = mapscript.MS_CJC_SQUARE if abschluss == "Abgeschnitten" else mapscript.MS_CJC_ROUND
                style.linejoin = mapscript.MS_CJC_MITER if abschluss == "Spitz" else mapscript.MS_CJC_ROUND
                if strichstaerke < 0:
                    style.sizeunits = mapscript.MS_PIXELS
                    style.width = abs(strichstaerke)
                    style.size = abs(strichstaerke)
                else:
                    style.width = strichstaerke
                    style.size = strichstaerke

                if isinstance(c, list):
                    r, g, b = c
                else:
                    r, g, b = c.split(" ")
                if outline:
                    style.outlinecolor.setRGB(int(r), int(g), int(b))
                else:
                    style.color.setRGB(int(r), int(g), int(b))

                cl.insertStyle(style)

            if cl.numstyles == 0:
                logMessage(u"Signaturnummer %s: Keine Linienarten erzeugt." % sn)
                return False

            if not outline:
                style = mapscript.styleObj()
                style.color.setRGB(255, 255, 255)
                style.opacity = 0
                style.width = maxStrichstaerke * 1.01
                cl.insertStyle(style, 0)
        else:
            logMessage(u"Signaturnummer %s: Linienarten konnten nicht abgefragt werden.\nSQL:%s\nFehler:%s" % (sn, lqry.lastQuery(), lqry.lastError().text()))
            return False

        return True

    def reorderLayers(self, mapobj):
        layers = {}
        idx = {}
        for i in range(mapobj.numlayers):
            layer = mapobj.getLayer(i)
            self.setLayerMetaData(layer, "norGIS_oldindex", "%d" % i)

            zindex = int(layer.metadata.get("norGIS_zindex") or '-1')

            if layer.type not in layers:
                layers[layer.type] = {}

            if zindex not in layers[layer.type]:
                layers[layer.type][zindex] = []

            layers[layer.type][zindex].append(i)
            idx[i] = i

        order = []
        for t in [mapscript.MS_LAYER_RASTER, mapscript.MS_LAYER_POLYGON, mapscript.MS_LAYER_LINE, mapscript.MS_LAYER_POINT, mapscript.MS_LAYER_ANNOTATION]:
            if t not in layers:
                continue

            keys = list(layers[t].keys())
            keys.sort()
            for z in keys:
                order.extend(layers[t][z])

        for i in range(mapobj.numlayers):
            oidx = order.pop(0)
            j = idx[oidx]
            del idx[oidx]

            layer = mapobj.getLayer(j)
            mapobj.removeLayer(j)

            if mapobj.insertLayer(layer, i if i < mapobj.numlayers else -1) < 0:
                raise BaseException(u"Konnte Layer %d nicht wieder hinzufügen" % i)

            for k in list(idx.keys()):
                if idx[k] >= i and idx[k] < j:
                    idx[k] += 1

    def getschema(self):
        (db, conninfo) = self.opendb()
        if db is None:
            return None
        return self.schema

    def quotedschema(self):
        return u'"{}"'.format(self.schema.replace(u'"', u'""'))

    def getepsg(self):
        (db, conninfo) = self.opendb()
        if db is None:
            return None
        return self.epsg

    def setShortName(self, layer):
        (idx, ok) = QgsProject.instance().readNumEntry("alkis", "/shortNameIndex")
        layer.setShortName("alkis{}".format(idx))
        idx += 1
        QgsProject.instance().writeEntry("alkis", "/shortNameIndex", idx)

    def addGroup(self, name, expand=True, parent=None):
        if not qgis3:
            return self.iface.legendInterface().addGroup(name, expand, parent)

        if parent:
            grp = parent.addGroup(name)
        else:
            grp = QgsProject.instance().layerTreeRoot().addGroup(name)

        grp.setExpanded(expand)

        return grp

    def addLayer(self, layer, grp):
        if qgis3:
            QgsProject.instance().addMapLayer(layer, False)
            grp.insertLayer(0, layer)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(layer, True)
            self.iface.legendInterface().moveLayer(layer, grp)

    def refreshLayer(self, layer):
        if qgis3:
            node = QgsProject.instance().layerTreeRoot().findLayer(layer)
            self.iface.layerTreeView().layerTreeModel().refreshLayerLegend(node)
        else:
            self.iface.legendInterface().refreshLayerSymbology(layer)

    def setGroupExpanded(self, grp, expanded):
        if hasattr(self.iface, "legendInterface"):
            self.iface.legendInterface().setGroupExpanded(grp, expanded)
        else:
            grp.setExpanded(expanded)

    def setGroupVisible(self, grp, visible):
        if hasattr(self.iface, "legendInterface"):
            self.iface.legendInterface().setGroupVisible(grp, visible)
        else:
            grp.setItemVisibilityChecked(visible)

    def removeGroup(self, grp):
        if hasattr(self.iface, "legendInterface"):
            self.iface.legendInterface().removeGroup(grp)
        else:
            grp.parent().removeChildNode(grp)

    def mapLayer(self, layerId):
        if qgis3:
            return QgsProject.instance().mapLayer(layerId)
        else:
            return QgsMapLayerRegistry.instance().mapLayer(layerId)

    def setRenderer(self, layer, r):
        if hasattr(layer, "setRendererV2"):
            layer.setRendererV2(r)
        else:
            layer.setRenderer(r)

    def destinationCrs(self):
        if hasattr(QgsProject, "crs"):
            return QgsProject.instance().crs()

        c = self.iface.mapCanvas()
        if not hasattr(c, 'hasCrsTransformEnabled') or c.hasCrsTransformEnabled():
            try:
                return c.mapSettings().destinationCrs()
            except AttributeError:
                return c.mapRenderer().destinationCrs()

        return None

    def transform(self, o, src=None, dst=None):
        if src is None:
            src = self.destinationCrs()
        if dst is None:
            if self.areaMarkerLayer is None:
                (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
                if ok:
                    self.areaMarkerLayer = self.mapLayer(layerId)

            if self.areaMarkerLayer is not None:
                dst = self.areaMarkerLayer.crs()

        if src and dst and src != dst:
            if not hasattr(self.iface.mapCanvas(), 'hasCrsTransformEnabled'):
                t = QgsCoordinateTransform(src, dst, QgsProject.instance())
            else:
                t = QgsCoordinateTransform(src, dst)

            if t:
                if hasattr(o, "transform"):
                    o.transform(t)
                else:
                    o = t.transform(o)

        return o

    def logQuery(self, requestType, search, result):
        (db, conninfo) = self.opendb()
        if db is None:
            return

        qry = QSqlQuery(db)

        if qry.exec_("SELECT has_table_privilege(current_user, 'postnas_search_logging', 'INSERT')"):
            if not qry.next() or not qry.value(0):
                qDebug(u"Einfügerecht zur Protokollierung fehlt.")
                return True

            qDebug(u"Protokollierung aktiv.")

        elif qry.exec_("CREATE TABLE postnas_search_logging(datum timestamp without time zone NOT NULL, username text NOT NULL, requestType text, search text, result text[])"):
            qDebug(u"Protokolltabelle angelegt.")

        else:
            qDebug(u"Protokolltabelle konnte nicht angelegt werden.")
            return True

        mitAZ = qry.exec_("SELECT 1 FROM information_schema.columns WHERE table_schema='{}' AND table_name='postnas_search_logging' AND column_name='aktenzeichen'".format(self.settings.schema.replace("'", "''"))) and qry.next()

        if mitAZ:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            az, ok = QInputDialog.getText(None, u"Grund der Abfrage", u"Aktenzeichen:", text=self.az)
            QApplication.restoreOverrideCursor()
            if not ok:
                return False

            self.az = az

        if not qry.prepare("INSERT INTO postnas_search_logging(datum, username, requestType, search, result{}) VALUES (now(),?,?,?,?{})".format(
            ', aktenzeichen' if mitAZ else '',
            ',?' if mitAZ else ''
        )):
            logMessage(u"Protokolleintrag konnte nicht vorbereitet werden")
            return False

        qry.addBindValue(USERNAME)
        qry.addBindValue(requestType)
        qry.addBindValue(search)
        qry.addBindValue(u"{%s}" % u",".join(result))
        if mitAZ:
            qry.addBindValue(self.az)

        if not qry.exec_():
            logMessage(u"Protokolleintrag konnte nicht ergänzt werden")
            return False

        return True


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        p = alkisplugin(QCoreApplication.instance())
        p.mapfile(None, sys.argv[1])
    else:
        print('Fehler: alkisplugin.py "dstfile.map"')
