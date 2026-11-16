#!/usr/bin/python
# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    alkisplugin.py
    ---------------------
    Date                 : September 2012
    Copyright            : (C) 2012-2026 by Jürgen Fischer
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

from qgis.PyQt.QtCore import QObject, QSettings, Qt, QPointF, pyqtSignal, QCoreApplication, QMetaObject, QFile, QIODevice, QFileInfo, QDir
from qgis.PyQt.QtWidgets import QMessageBox, QAction, QInputDialog, QProgressBar
from qgis.PyQt.QtGui import QIcon, QColor, QPainter
from qgis.PyQt import QtCore
from qgis.utils import OverrideCursor
from qgis.core import (
    QgsProviderRegistry,
    QgsProviderConnectionException,
    QgsMessageLog,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsPalLayerSettings,
    QgsRectangle,
    QgsCoordinateTransform,
    QgsVectorLayer,
    QgsApplication,
    QgsLayerTreeGroup,
    Qgis,
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
    QgsMarkerSymbol,
    QgsLineSymbol,
    QgsFillSymbol,
    QgsDataSourceUri,
    QgsUnitTypes,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsSettings
)

import os
import re

from .qgisclasses import About, ALKISPointInfo, ALKISPolygonInfo, ALKISOwnerInfo, ALKISSearch, ALKISConf

BASEDIR = os.path.dirname(__file__)

hasProxyTask = False


try:
    from qgis.core import QgsProxyProgressTask
    hasProxyTask = True
except ImportError:
    pass


try:
    import win32api
    USERNAME = win32api.GetUserNameEx(win32api.NameSamCompatible)
except ImportError:
    import getpass
    import socket
    USERNAME = "{}@{}".format(getpass.getuser(), socket.gethostname())


def qDebug(s):
    QtCore.qDebug(s.encode('ascii', 'ignore'))


def logMessage(s):
    QgsMessageLog.logMessage(s, "ALKIS")


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
        self.pwd = ""   # nosec B105
        self.authcfg = ""
        self.signaturkatalog = -1
        self.embedSVGs = False
        self.modellarten = ['DLKM', 'DKKM1000']
        self.footnote = ""
        self.template = ""
        self.templateDirs = []

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
        s.setValue("embedSVGs", self.embedSVGs)
        s.setValue("modellarten", self.modellarten)
        s.setValue("footnote", self.footnote)
        s.setValue("template", self.template)
        s.setValue("templateDirs", self.templateDirs)

        p = QgsProject.instance()
        v, ok = p.readEntry("alkis", "settings/footnote")
        if ok and v != self.footnote:
            p.writeEntry("alkis", "settings/footnote", self.footnote)

        v, ok = p.readEntry("alkis", "settings/template")
        if ok and v != self.template:
            p.writeEntry("alkis", "settings/template", self.template)

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

        self.embedSVGs = s.value("embedSVGs", False, type=bool)

        self.modellarten = s.value("modellarten", ['DLKM', 'DKKM1000'])
        self.footnote = s.value("footnote", "")
        self.template = s.value("template", "")

        self.plugin.db = None

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
        p.writeEntryBool("alkis", "settings/embedSVGs", self.embedSVGs)
        p.writeEntry("alkis", "settings/modellarten", self.modellarten)
        p.writeEntry("alkis", "settings/footnote", self.footnote)
        p.writeEntry("alkis", "settings/template", self.template)

        logMessage("Einstellungen in Projekt gespeichert.")

    def hasSettings(self):
        return len(QgsProject.instance().entryList("alkis", "settings")) > 0

    def removeSettings(self):
        QgsProject.instance().removeEntry("alkis", "settings")

    def load(self):
        self.templateDirs = [QFileInfo(d).canonicalFilePath() for d in QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("templatedirs", [])]

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
            self.embedSVGs, ok = p.readBoolEntry("alkis", "settings/embedSVGs", False)
            self.modellarten, ok = p.readListEntry("alkis", "settings/modellarten", ['DLKM', 'DKKM1000'])
            self.footnote, ok = p.readEntry("alkis", "settings/footnote", "")
            self.template, ok = p.readEntry("alkis", "settings/template", "")

            # logMessage("Einstellungen aus Projekt geladen.")
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

                logMessage("Datenbankeinstellungen aus Punkthervorhebungslayer abgeleitet.")

        if self.template and not self.isSafeTemplate(self.template):
            logMessage(f"Template {self.template} nicht in Vorlageverzeichnissen.")

        self.plugin.pointMarkerLayer = None
        self.plugin.lineMarkerLayer = None
        self.plugin.areaMarkerLayer = None
        self.plugin.db = None

    def isSafeTemplate(self, template):
        template = QFileInfo(template).canonicalFilePath()

        if template.startswith(QDir(BASEDIR).canonicalPath()):
            return True

        for d in self.templateDirs:
            if template.startswith(d):
                return True

        return False


class alkisplugin(QObject):
    showProgress = pyqtSignal(int, int)
    showStatusMessage = pyqtSignal(str)

    themen = (
        {
            'name': "Flurstücke",
            'area': {'min': 0, 'max': 5000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'filter': [
                {'name': "Flächen", 'filter': "NOT layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')"},
                {'name': "Nummern", 'filter': "layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')"},
            ],
            'classes': {
                '2001': 'Bruchstriche',
                '2004': 'Zuordnungspfeil',
                '2005': 'Zuordnungspfeil, abweichender Rechtszustand',
                '2006': 'Strittige Grenze',
                '2008': 'Flurstücksgrenze nicht feststellbar',
                '2028': 'Flurstücksgrenze',
                '2029': 'Flurstücksgrenze, abw. Rechtszustand',
                '3010': 'Flurstücksüberhaken',
                '3020': 'Abgemarkter Grenzpunkt',
                '3021': 'Abgemarkter Grenzpunkt, abw. Rechtszustand',
                '3022': 'Grenzpunkt, Abmarkung zeitweilig ausgesetzt',
                '3024': 'Grenzpunkt ohne spezifizierte Abmarkung',
            },
        },
        {
            'name': "Gebäude",
            'area': {'min': 0, 'max': 10000},
            'outline': {'min': 0, 'max': 3500},
            'line': {'min': 0, 'max': 3500},
            'point': {'min': 0, 'max': 3500},
            'label': {'min': 0, 'max': 3500},
            'filter': [
                {'name': "Laufende Hausnummern", 'filter': "layer='ax_lagebezeichnungmitpseudonummer'"},
                {'name': "Dachform", 'filter': "layer IN ('ax_gebaeude_dachform','ax_bauteil_dachform')"},
                {'name': "Funktion", 'filter': "layer IN ('ax_gebaeude_funktion','ax_bauteil_funktion','ax_turm_funktion')"},
                {'name': "Geschosse", 'filter': "layer IN ('ax_gebaeude_geschosse','ax_bauteil_geschosse')"},
                {'name': "Zustand", 'filter': "layer='ax_gebaeude_zustand'"},
                {'name': "Gebäude", 'filter': "layer NOT IN ('ax_lagebezeichnungmitpseudonummer','ax_gebaeude_dachform','ax_gebaeude_funktion','ax_gebaeude_geschosse','ax_gebaeude_zustand','ax_bauteil_dachform','ax_bauteil_funktion','ax_bauteil_geschosse','ax_turm_funktion')"},
            ],
            'classes': {
                '1301': 'Wohngebäude',
                '1304': 'Anderes Gebäude',
                '1305': 'Mauer',
                '2510': 'Mauer',
                '1309': 'Gebäude für öffentliche Zwecke',
                '1501': 'Aussichtsturm',
                'rn1501': 'Anderes Gebäude',
                '1525': 'Brunnen',
                '2002': 'Zaun',
                '2030': 'Gebäude',
                '2031': 'Anderes Gebäude',
                '2032': 'Gebäude unter der Erdoberfläche',
                '2305': 'Offene Gebäudelinie',
                '2505': 'Öffentliches Gebäude',
                # '2508': 'sonstiges Gebäudeteil',
                '2508': 'aufgeständert',
                '2509': 'Hochhausbauteil',
                '2513': 'Unterirdisch',
                # '2513': 'Schornstein im Gebäude',
                '2514': 'Turm im Gebäude',
                '2515': 'Brunnen',
                '2519': 'Kanal, Im Bau',
                '2623': 'Hochhaus',
                '3300': 'Bank',
                '3302': 'Hotel',
                '3303': 'Jugendherberge',
                '3305': 'Gaststätte',
                '3306': 'Kino',
                '3308': 'Spielcasino',
                '3309': 'Parkhaus',
                '3311': 'Toilette',
                '3312': 'Post',
                '3314': 'Theater',
                '3315': 'Bibliothek',
                '3316': 'Kirche',
                '3317': 'Synagoge',
                '3318': 'Kapelle',
                '3319': 'Moschee',
                '3321': 'Krankenhaus',
                '3323': 'Kindergarten',
                '3324': 'Polizei',
                '3326': 'Feuerwehr',
                '3327': 'Grabhügel (Hügelgrab)',
                '3332': 'Gebäude zum Busbahnhof',
                '3532': 'Denkmal',
                '3334': 'Hallenbad',
                '3336': 'Tiefgarage',
                '3338': 'Apotheke',
                '3521': 'Umformer',
                '3526': 'Großsteingrab (Dolmen), Hünenbett',
                '3529': 'Brunnen / Gasquelle, Mofette / Heilquelle',
                '3534': 'Bildstock',
                '3535': 'Gipfel-/Wegekreuz',
                '3536': 'Meilenstein, historischer Grenzstein',
                '3537': 'Brunnen (Trinkwasserversorgung)',
                '3539': 'Springbrunnen, Zierbrunnen',
                '3540': 'Ziehbrunnen',
                '3580': 'Zaun',

                '2901': 'Geplantes Gebäude (gebaut)',
                '2902': 'Geplantes Gebäude (Bauantrag)',
                '2903': 'Nicht eingemessenes Gebäude',
            },
        },
        {
            'name': "Lagebezeichnungen",
            'area': {'min': 0, 'max': 5000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
        },
        {
            'name': "Politische Grenzen",
            'area': {'min': 0, 'max': None},
            'outline': {'min': 0, 'max': None},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': None},
            'filter': [
                {
                    'name': "Grenzen",
                    'filter': "layer NOT LIKE 'ax_flurstueck%'",
                    'area': {'min': 0, 'max': 10000},
                    'outline': {'min': 0, 'max': 10000},
                    'label': {'min': 0, 'max': 10000},
                },
                {
                    'name': "Flure",
                    'filter': "layer LIKE 'ax_flurstueck_flur%'",
                    'area': {'min': 10000, 'max': 100000},
                    'outline': {'min': 10000, 'max': 50000},
                    'label': {'min': 10000, 'max': 50000},
                },
                {
                    'name': "Gemarkung",
                    'filter': "layer LIKE 'ax_flurstueck_gemarkung%'",
                    'area': {'min': 10000, 'max': 150000},
                    'outline': {'min': 10000, 'max': 150000},
                    'label': {'min': 10000, 'max': 150000},
                },
                {
                    'name': "Gemeinde",
                    'filter': "layer LIKE 'ax_flurstueck_gemeinde%'",
                    'area': {'min': 10000, 'max': 200000},
                    'outline': {'min': 10000, 'max': 200000},
                    'label': {'min': 50000, 'max': 200000},
                },
                {
                    'name': "Kreis",
                    'filter': "layer LIKE 'ax_flurstueck_kreis%'",
                    'area': {'min': 10000, 'max': None},
                    'outline': {'min': 10000, 'max': None},
                    'label': {'min': 200000, 'max': 1000000},
                },
            ],
            'classes': {
                '2010': 'Landkreisgrenze',
                '2012': 'Flurgrenze',
                '2014': 'Gemarkungsgrenze',
                '2016': 'Staatsgrenze',
                '2018': 'Landesgrenze',
                '2020': 'Regierungsbezirksgrenze',
                '2022': 'Gemeindegrenze',
                '2026': 'Verwaltungsbezirksgrenze',
                'pg-flur': 'Flure',
                'pg-gemarkung': 'Gemarkungen',
                'pg-gemeinde': 'Gemeinden',
                'pg-kreis': 'Kreise',
            },
        },
        {
            'name': "Rechtliche Festlegungen",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 25000},
            'line': {'min': 0, 'max': 25000},
            'point': {'min': 0, 'max': 25000},
            'label': {'min': 0, 'max': 25000},
            'classes': {
                '1701': 'Bundesautobahn/-straße',
                '1702': 'Landes-/Staatsstraße',
                'rn1701': 'Bundesautobahn/-straße',
                'rn1702': 'Landes-/Staatsstraße',
                'rn1703': 'Schutzgebiet',
                'rn1704': 'Bau-, Raum-, Bodenordnungsrecht',
            },
        },
        {
            'name': "Topographie",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '2620': 'Damm, Wall, Deich, Graben, Knick, Wallkante',
                '3484': 'Düne, Sand',
                '3601': 'Busch, Hecke, Knick',
                '3625': 'Höhleneingang',
                '3627': 'Felsen, Felsblock, Felsnadel',
                '3629': 'Besonderer topographischer Punkt',
                '3632': 'Busch, Hecke, Knick',
                '3634': 'Felsen, Felsblock, Felsnadel',
            },
        },
        {
            'name': "Verkehr",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1406': 'Begleitfläche',
                '1414': 'Fußgängerzone',
                '1530': 'Brücke, Hochbahn/-straße',
                'rn1530': 'Brücke, Hochbahn/-straße',
                'rn1533': 'Tunnel, Unterführung',
                'rn1535': 'Schleusenkammer',
                '1542': 'Weg',
                'rn1542': 'Weg',
                '1543': 'Wattenweg',
                '1544': 'Anleger',
                'rn1544': 'Anleger',
                '1540': 'Fahrbahn',
                'rn1540': 'Fahrbahn',
                '1808': 'Landeplatz, -bahn, Vorfeld, Rollbahn',
                'rn1808': 'Landeplatz, -bahn, Vorfeld, Rollbahn',
                '2305': 'Durchfahrt, Bauwerk',
                '2533': 'Widerlager',
                '2515': 'Bahnverkehr, Platz',
                '3330': 'S-Bahnhof',
                '3424': 'Fußweg',
                '3426': 'Radweg',
                '3428': 'Rad- und Fußweg',
                '3430': 'Reitweg',
                '3432': 'Parkplatz',
                '3434': 'Rastplatz',
                '3439': 'Segelfluggelände',
                '3541': 'Kommunikationseinrichtung',
                '3542': 'Fernsprechhäuschen',
                '3544': 'Briefkasten',
                '3546': 'Feuermelder',
                '3547': 'Polizeirufsäule',
                '3548': 'Kabelkasten, Schaltkasten',
                '3550': 'Verkehrsampel',
                '3551': 'Freistehende Hinweistafel, -zeichen',
                '3552': 'Wegweiser von besonderer Bedeutung',
                '3553': 'Freistehende Warntafel',
                '3554': 'Haltestelle',
                '3556': 'Kilometerstein',
                '3558': 'Gaslaterne',
                '3559': 'Laterne, elektrisch',
                '3563': 'Säule, Werbefläche',
                '3564': 'Leuchtsäule',
                '3565': 'Fahnenmast',
                '3566': 'Straßensinkkasten',
                '3567': 'Müllbox',
                '3568': 'Kehrichtgrube',
                '3569': 'Uhr',
                '3571': 'Flutlichtmast',
                '3578': 'Haltepunkt',
                '3588': 'Hubschrauberlandeplatz',
                '3590': 'Leuchtfeuer',
                '3645': 'Materialseilbahn',
                '3646': 'Straßenbahngleis',
            },
        },
        {
            'name': "Friedhöfe",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1405': '[1405]',
                '2515': '[2515]',
            },
        },
        {
            'name': "Vegetation",
            'area': {'min': 0, 'max': 25000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1404': 'Brachland, Heide, Moor, Sumpf, Torf',
                '1406': 'Garten',
                '1409': 'Ackerland',
                '1414': 'Wald',
                '1561': 'Schneise',
                '2515': 'Ackerland',
                '2517': 'Wald',
                '3413': 'Gras',
                '3415': 'Park',
                '3421': 'Garten',
                '3440': 'Streuobstacker',
                '3441': 'Streuobstwiese',
                '3444': 'Spargel',
                '3446': 'Baumschule',
                '3448': 'Weingarten',
                '3450': 'Obstplantage',
                '3452': 'Obstbaumplantage',
                '3454': 'Obststrauchplantage',
                '3456': 'Wald',
                '3457': 'Nadelbaum',
                '3458': 'Laubwald',
                '3460': 'Nadelwald',
                '3462': 'Mischwald',
                '3470': 'Mischwald',
                '3474': 'Heide',
                '3476': 'Moor',
                '3478': 'Sumpf',
                '3480': 'Unland',
                '3481': 'Fels',
                '3482': 'Steine, Schotter / Wellenbrecher, Buhne',
                '3484': 'Düne, Sand',
                '3597': 'Nadelbaum',
                '3599': 'Laubbaum',
                '3601': 'Busch, Hecke, Knick',
                '3603': 'Röhricht, Schilf',
                '3605': 'Zierfläche',
                '3607': 'Korbweide',
                '3613': 'Quelle',
            },
        },
        {
            'name': "Landwirtschaftliche Nutzung",
            'area': {'min': 0, 'max': None},
            'outline': {'min': 0, 'max': None},
            'line': {'min': 0, 'max': None},
            'point': {'min': 0, 'max': None},
            'label': {'min': 0, 'max': None},
            'classes': {
            },
        },
        {
            'name': "Gewässer",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 5000},
            'line': {'min': 0, 'max': 5000},
            'point': {'min': 0, 'max': 5000},
            'label': {'min': 0, 'max': 5000},
            'classes': {
                '1410': 'Gewässer',
                '2518': 'Gewässer',
                '3484': 'Düne, Sand',
                '3488': 'Fließgewässer',
                '3490': 'Gewässer',
                '3529': 'Brunnen / Gasquelle, Mofette / Heilquelle',
                '3594': 'Schöpfwerk',
                '3613': 'Quelle',
                '3617': 'Stromschnelle',
                '3619': 'Unterirdisches Fließgewässer',
                '3621': 'Fließgewässer, nicht ständig Wasser führend',
                '3623': 'Höhe des Wasserspiegels',
                '3653': '[3653]',
                'rn1548': 'Fischtreppe, Sicherheitstor, Sperrwerk',
                'rn1550': 'Unterirdisches Gewässer',
            },
        },
        {
            'name': "Industrie und Gewerbe",
            'area': {'min': 0, 'max': 500000, },
            'outline': {'min': 0, 'max': 10000, },
            'line': {'min': 0, 'max': 10000, },
            'point': {'min': 0, 'max': 10000, },
            'label': {'min': 0, 'max': 10000, },
            'classes': {
                '1305': '[1305]',
                'rn1305': '[rn1305]',
                '1306': 'Mast',
                'rn1306': 'Mast',
                'rn1321': 'Vorratsbehälter, Speicherbauwerk unterirdisch',
                'rn1501': '[rn1501]',
                'rn1510': 'Klärbecken',
                '1304': 'Vorratsbehälter, aufgeständert',
                '1401': '[1401]',
                '1403': '[1403]',
                '1404': '[1404]',
                '1501': '[1501]',
                '1510': '[1510]',
                '2031': '[2031]',
                '2515': '[2515]',
                '2524': '[2524]',
                '3401': 'Tankstelle',
                '3403': 'Kraftwerk',
                '3404': 'Umspannstation',
                '3406': 'Stillgelegter Bergbaubetrieb',
                '3407': 'Torf',
                '3501': 'Windrad',
                '3502': 'Solarzellen',
                '3504': 'Mast',
                '3506': 'Antenne / Funkmast',
                '3507': 'Radioteleskop',
                '3508': 'Schornstein, Schlot, Esse',
                '3509': 'Stollenmundloch',
                '3510': 'Schachtöffnung',
                '3511': 'Kran',
                '3512': 'Drehkran',
                '3513': 'Portalkran',
                '3514': 'Laufkran, Brückenlaufkran',
                '3515': 'Portalkran',
                '3517': 'Oberflurhydrant',
                '3518': 'Unterflurhydrant',
                '3519': 'Schieberkappe',
                '3520': 'Einsteigeschacht',
                '3521': 'Umformer',
                '3522': 'Vorratsbehälter',
                '3523': 'Pumpe',
                '3653': 'Wehr',
            },
        },
        {
            'name': "Sport und Freizeit",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '1405': '[1405]',
                '1519': 'Überdachte Tribüne',
                'rn1519': 'Überdachte Tribüne',
                '1520': 'Hart-, Rasenplatz, Spielfeld',
                'rn1520': 'Hart-, Rasenplatz, Spielfeld',
                '1521': 'Rennbahn, Laufbahn, Geläuf',
                'rn1521': 'Rennbahn, Laufbahn, Geläuf',
                '1522': 'Stadion',
                'rn1522': 'Stadion',
                'rn1524': '[1524]',
                '1526': 'Schwimmbecken',
                'rn1526': 'Schwimmbecken',
                '2515': '[2515]',
                '3409': 'Skating',
                '3410': 'Zoo',
                '3411': 'Safaripark, Wildpark',
                '3412': 'Campingplatz',
                '3413': 'Rasen',
                '3415': 'Park',
                '3417': 'Botanischer Garten',
                '3419': 'Kleingarten',
                '3421': 'Garten',
                '3423': 'Spielplatz, Bolzplatz',
                '3424': 'Fußweg',
                '3524': 'Schießanlage',
                '3525': 'Gradierwerk',
            },
        },
        {
            'name': "Wohnbauflächen",
            'area': {'min': 0, 'max': 500000},
            'outline': {'min': 0, 'max': 10000},
            'line': {'min': 0, 'max': 10000},
            'point': {'min': 0, 'max': 10000},
            'label': {'min': 0, 'max': 10000},
            'classes': {
                '1401': 'Wohnbaufläche',
                '2515': '[2515]',
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
        self.toolbar = self.iface.addToolBar("norGIS: ALKIS")
        self.toolbar.setObjectName("norGIS_ALKIS_Toolbar")

        self.importAction = QAction(QIcon("alkis:logo.svg"), "Layer einbinden", self.iface.mainWindow())
        self.importAction.setWhatsThis("ALKIS-Layer einbinden")
        self.importAction.setStatusTip("ALKIS-Layer einbinden")
        self.importAction.triggered.connect(self.run)

        self.searchAction = QAction(QIcon("alkis:find.svg"), "Suchen…", self.iface.mainWindow())
        self.searchAction.setWhatsThis("ALKIS-Beschriftung suchen")
        self.searchAction.setStatusTip("ALKIS-Beschriftung suchen")
        self.searchAction.triggered.connect(self.search)
        self.toolbar.addAction(self.searchAction)

        self.queryOwnerAction = QAction(QIcon("alkis:eigner.svg"), "Flurstücksnachweis", self.iface.mainWindow())
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

        self.confAction = QAction(QIcon("alkis:logo.svg"), "Konfiguration…", self.iface.mainWindow())
        self.confAction.setWhatsThis("Konfiguration der ALKIS-Erweiterung")
        self.confAction.setStatusTip("Konfiguration der ALKIS-Erweiterung")
        self.confAction.triggered.connect(self.conf)

        self.aboutAction = QAction(QIcon("alkis:logo.svg"), "Über…", self.iface.mainWindow())
        self.aboutAction.setWhatsThis("Über die Erweiterung")
        self.aboutAction.setStatusTip("Über die Erweiterung")
        self.aboutAction.triggered.connect(self.about)

        self.iface.addPluginToDatabaseMenu("&ALKIS", self.importAction)
        self.iface.addPluginToDatabaseMenu("&ALKIS", self.confAction)
        self.iface.addPluginToDatabaseMenu("&ALKIS", self.aboutAction)

        ns = QSettings("norBIT", "EDBSgen/PRO")
        if ns.contains("norGISPort") or ns.contains("useTempfile"):
            self.pointInfoAction = QAction(QIcon("alkis:info.svg"), "Flurstücksabfrage (Punkt)", self.iface.mainWindow())
            self.pointInfoAction.triggered.connect(self.setPointInfoTool)
            self.pointInfoAction.setCheckable(True)
            self.toolbar.addAction(self.pointInfoAction)
            self.pointInfoTool = ALKISPointInfo(self)
            self.pointInfoTool.setAction(self.pointInfoAction)

            self.polygonInfoAction = QAction(QIcon("alkis:pinfo.svg"), "Flurstücksabfrage (Polygon)", self.iface.mainWindow())
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
        self.iface.removePluginDatabaseMenu("&ALKIS", self.confAction)
        self.iface.removePluginDatabaseMenu("&ALKIS", self.aboutAction)

        del self.toolbar

        if self.searchAction:
            self.searchAction.deleteLater()
            self.searchAction = None
        if self.importAction:
            self.importAction.deleteLater()
            self.importAction = None
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
            logMessage("Keinen Flächenmarkierungslayer gefunden.")
            return

        if self.areaMarkerLayer in layers or self.areaMarkerLayer.id() in layers:
            QgsProject.instance().removeEntry("alkis", "/areaMarkerLayer")
            self.areaMarkerLayer = None
            self.settings.removeSettings()
            logMessage("ALKIS-Layer entfernt.")

    def conf(self):
        dlg = ALKISConf(self)
        dlg.exec()

    def about(self):
        dlg = About()
        dlg.exec()

    def initLayers(self):
        if self.pointMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/pointMarkerLayer")
            if ok:
                self.pointMarkerLayer = self.mapLayer(layerId)

        if self.pointMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", "Fehler: Punktmarkierungslayer nicht gefunden!")
            return False

        if self.lineMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/lineMarkerLayer")
            if ok:
                self.lineMarkerLayer = self.mapLayer(layerId)

        if self.lineMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", "Fehler: Linienmarkierungslayer nicht gefunden!")
            return False

        return True

    def search(self):
        dlg = ALKISSearch(self)
        dlg.exec()

    def setScale(self, layer, d):
        if d['max'] is None and d['min'] is None:
            return

        if d['max'] is not None:
            layer.setMinimumScale(d['max'])

        if d['min'] is not None:
            layer.setMaximumScale(d['min'])

        try:
            layer.setScaleBasedVisibility(True)
        except AttributeError:
            layer.toggleScaleBasedVisibility(True)

    def categoryLabel(self, d, sn):
        qDebug("categories: %s" % d['classes'])
        if str(sn) in d['classes']:
            return d['classes'][str(sn)]
        else:
            return "(%s)" % sn

    def run(self):
        if self.settings.hasSettings() and QMessageBox.warning(None, "ALKIS", "Im Projekt sind bereits ALKIS-Daten eingebunden.\nNach dem Einbinden werden nur die neuen Layer abfragbar sein.", QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Cancel:
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            try:
                self.alkisimport()
            finally:
                if Qgis.QGIS_VERSION_INT >= 31800:
                    QMetaObject.invokeMethod(self.iface.layerTreeView().model(), 'invalidate', Qt.ConnectionType.QueuedConnection)

                if self.proxyTask:
                    self.proxyTask.finalize(True)
                    self.proxyTask = None

    def progress(self, i, m):
        self.showStatusMessage.emit("%s/%s" % (alkisplugin.themen[i]['name'], m))

        if hasProxyTask:
            if self.proxyTask is None:
                self.proxyTask = QgsProxyProgressTask("Lade ALKIS-Layer…")
                QgsApplication.taskManager().addTask(self.proxyTask)

            self.proxyTask.setProxyProgress(self.step * 100 / self.steps)

        else:
            self.showProgress.emit(self.step, self.steps)
            QCoreApplication.processEvents()

        self.step += 1

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

        try:
            stricharten = []
            maxStrichstaerke = None

            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, r, g, b in db.executeSql(
                (
                    "SELECT abschluss,scheitel,coalesce(strichstaerke/100,0),coalesce(laenge/100,0),coalesce(einzug/100,0),abstand,r,g,b"  # nosec: B608
                    " FROM alkis_linien ln"
                    " LEFT OUTER JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer{0}"
                    " LEFT OUTER JOIN alkis_stricharten_i ON l.strichart=alkis_stricharten_i.stricharten"
                    " LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
                    " LEFT OUTER JOIN alkis_farben ON {1}.farbe=alkis_farben.id"
                    " WHERE ln.signaturnummer='{2}'{3}"
                ).format(
                    "" if kat < 0 else " AND l.katalog=%d" % kat,
                    "ln" if kat < 0 else "l",
                    sn,
                    "" if kat < 0 else " AND ln.katalog=%d" % kat
                )
            ):
                c = QColor(r, g, b)

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
                    raise BaseException("Signaturnummer %s: Stricharten nicht gleich lang (%lf vs %lf)" % (sn, gesamtl0, gesamtl))

                if laenge > 0:
                    if leinzug is None:
                        leinzug = einzug
                    elif leinzug != einzug:
                        # raise BaseException( "Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug) )
                        logMessage("Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug))
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
                        if Qgis.QGIS_VERSION_INT >= 32400:
                            sl.setPlacements(Qgis.MarkerLinePlacement.Interval)
                        else:
                            sl.setPlacement(QgsMarkerLineSymbolLayer.Interval)
                        sl.setIntervalUnit(self.MapUnit)
                        sl.setOffsetAlongLine(einzug)
                        sl.setOffsetAlongLineUnit(self.MapUnit)
                        sl.subSymbol().symbolLayer(0).setSize(abs(strichstaerke))
                        sl.subSymbol().symbolLayer(0).setSizeUnit(self.MapUnit if strichstaerke >= 0 else self.Millimeter)
                        try:
                            sl.subSymbol().symbolLayer(0).setOutlineStyle(Qt.PenStyle.NoPen)
                        except AttributeError:
                            sl.subSymbol().symbolLayer(0).setStrokeStyle(Qt.PenStyle.NoPen)
                        sl.subSymbol().symbolLayer(0).setColor(c)
                        sl.setWidth(strichstaerke)
                        sl.setWidthUnit(self.MapUnit)
                        einzug += abstand
                        sym.appendSymbolLayer(sl)
                else:
                    # Simple line
                    sl = QgsSimpleLineSymbolLayer(c, strichstaerke, Qt.PenStyle.SolidLine)

                    if abstaende:
                        dashvector = []
                        for abstand in abstaende:
                            dashvector.extend([laenge, abstand])
                        sl.setUseCustomDashPattern(True)
                        sl.setCustomDashVector(dashvector)
                        sl.setCustomDashPatternUnit(self.MapUnit)

                    sl.setPenCapStyle(Qt.PenCapStyle.FlatCap if abschluss == "Abgeschnitten" else Qt.PenCapStyle.RoundCap)
                    sl.setPenJoinStyle(Qt.PenJoinStyle.MiterJoin if abschluss == "Spitz" else Qt.PenJoinStyle.RoundJoin)
                    sl.setWidth(abs(strichstaerke))
                    sl.setWidthUnit(self.MapUnit if strichstaerke >= 0 else self.Millimeter)

                    sym.appendSymbolLayer(sl)

            if sym.symbolLayerCount() == 1:
                logMessage(f"Signaturnummer {sn}: Keine Linienarten erzeugt.")
                return False

            if outline:
                sym.deleteSymbolLayer(0)
            else:
                sl = QgsSimpleLineSymbolLayer(QColor(0, 0, 0, 0), maxStrichstaerke * 1.01, Qt.PenStyle.SolidLine)
                sl.setWidthUnit(self.MapUnit)
                sym.changeSymbolLayer(0, sl)

            return True

        except QgsProviderConnectionException as e:
            logMessage(f"Signaturnummer {sn}: Linienarten konnten nicht abgefragt werden. [{e}]")
            return False

    def alkisimport(self):
        self.settings.loadSettings()

        (db, conninfo) = self.opendb()
        if db is None:
            return

        modelle = self.settings.modellarten
        katalog = self.settings.signaturkatalog
        embedSVGs = self.settings.embedSVGs

        self.iface.mapCanvas().setRenderFlag(False)

        svgpath = os.path.abspath(os.path.join(BASEDIR, "svg"))
        qs = QgsSettings()
        svgpaths = QgsApplication.svgPaths()
        if svgpath not in svgpaths:
            svgpaths.append(svgpath)
            qs.setValue("svg/searchPathsForSVG", svgpaths)
        layeropts = QgsVectorLayer.LayerOptions(False, False)

        self.shortnames = [self.shortName(lyr) for lyr in QgsProject.instance().mapLayers().values() if self.shortName(lyr)]

        def addgroupsns(root=QgsProject.instance().layerTreeRoot()):
            for c in root.children():
                if not isinstance(c, QgsLayerTreeGroup):
                    continue
                sn = c.customProperty("wmsShortName")
                if sn and sn not in self.shortnames:
                    self.shortnames.append(sn)
                addgroupsns(c)

        addgroupsns()

        self.alkisGroup = self.addGroup("ALKIS", False)

        markerGroup = self.addGroup("Markierungen", False, self.alkisGroup)

        if not hasProxyTask:
            if hasattr(self.iface.mainWindow(), "showProgress"):
                self.showProgress.connect(self.iface.mainWindow().showProgress)
            else:
                self.showProgress.connect(self.doShowProgress)
        self.showStatusMessage.connect(self.iface.mainWindow().showStatusMessage)

        if self.epsg > 100000:
            try:
                rows = db.executeSql("SELECT proj4text FROM spatial_ref_sys WHERE srid=%d" % self.epsg)  # nosec: B608
                if len(rows) == 1:
                    crs = QgsCoordinateReferenceSystem()
                    crs.createFromProj4(rows[0][0])
                    if crs.authid() == "":
                        crs.saveAsUserCrs("ALKIS %d" % self.epsg)
                    else:
                        QMessageBox.critical(None, "ALKIS", f"Konnte Projektion für SRID {self.epsg} nicht zuweisen: {rows[0][0]}")

            except QgsProviderConnectionException as e:
                QMessageBox.critical(None, "ALKIS", f"Fehler: {e}")
                return

        self.steps = 0
        for d in alkisplugin.themen:
            self.steps += 6 * len(d.get('filter', [1]))

        self.step = 0

        nGroups = 0
        iThema = -1
        for d in alkisplugin.themen:
            iThema += 1
            t = d['name']

            if 'filter' not in d:
                d['filter'] = [{'name': None, 'filter': None}]

            themeGroup = self.addGroup(t, False, self.alkisGroup)

            nSubGroups = 0

            qDebug("Thema: %s" % t)

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

                self.progress(iThema, "Flächen")

                try:
                    r = QgsCategorizedSymbolRenderer("sn_flaeche")
                    r.deleteAllCategories()

                    n = 0
                    for sn, c0, c1, c2 in db.executeSql(
                        (
                            "SELECT signaturnummer,r,g,b"  # nosec: B608
                            " FROM alkis_flaechen"
                            " JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                            " WHERE EXISTS ("
                            "SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer"
                            "){1}"
                            " ORDER BY darstellungsprioritaet DESC"
                        ).format(
                            where,
                            "" if katalog < 0 else " AND alkis_flaechen.katalog=%d" % katalog
                        )
                    ):
                        sym = QgsFillSymbol()
                        sym.setColor(QColor(c0, c1, c2))
                        try:
                            sym.symbolLayer(0).setBorderStyle(Qt.PenStyle.NoPen)
                        except AttributeError:
                            sym.symbolLayer(0).setStrokeStyle(Qt.PenStyle.NoPen)

                        r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                        n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            "Flächen (%s)" % t,
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
                except QgsProviderConnectionException as e:
                    QMessageBox.critical(None, "ALKIS", f"Fehler: {e}")
                    break

                self.progress(iThema, "Grenzen")

                try:
                    r = QgsCategorizedSymbolRenderer("sn_randlinie")
                    r.deleteAllCategories()

                    n = 0
                    for sn, in db.executeSql(
                        (
                            "SELECT"  # nosec: B608
                            " signaturnummer"
                            " FROM alkis_linien"
                            " WHERE EXISTS ("
                            "SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_randlinie=alkis_linien.signaturnummer"
                            "){1}"
                            " ORDER BY darstellungsprioritaet"
                        ).format(
                            where,
                            "" if katalog < 0 else " AND alkis_linien.katalog=%d" % katalog,
                        )
                    ):
                        sym = QgsFillSymbol()
                        if self.setStricharten(db, sym, katalog, sn, True):
                            r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                            n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            "Grenzen (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        layer.setFeatureBlendMode(QPainter.CompositionMode.CompositionMode_Source)
                        self.setScale(layer, f['outline'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                except QgsProviderConnectionException as e:
                    QMessageBox.critical(None, "ALKIS", f"Fehler: {e}")
                    break

                self.progress(iThema, "Linien")

                try:
                    r = QgsCategorizedSymbolRenderer("signaturnummer")
                    r.setUsingSymbolLevels(True)
                    r.deleteAllCategories()

                    n = 0
                    for sn, in db.executeSql(
                        (
                            "SELECT signaturnummer"  # nosec: B608
                            " FROM alkis_linien"
                            " WHERE EXISTS ("
                            "SELECT * FROM po_lines WHERE {0} AND po_lines.signaturnummer=alkis_linien.signaturnummer"
                            "){1}"
                            " ORDER BY darstellungsprioritaet ASC"
                        ).format(
                            where,
                            "" if katalog < 0 else " AND alkis_linien.katalog=%d" % katalog,
                        )
                    ):
                        sym = QgsLineSymbol()
                        if self.setStricharten(db, sym, katalog, sn, False):
                            for i in range(0, sym.symbolLayerCount()):
                                sym.symbolLayer(i).setRenderingPass(n)

                            r.addCategory(QgsRendererCategory(sn, sym, self.categoryLabel(d, sn)))
                            n += 1

                    if n > 0:
                        layer = QgsVectorLayer(
                            "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTILINESTRING srid=%d table=%s.po_lines (line) sql=%s" % (conninfo, self.epsg, self.quotedschema(), where),
                            "Linien (%s)" % t,
                            "postgres", layeropts
                        )
                        layer.setReadOnly()
                        self.setRenderer(layer, r)
                        layer.setFeatureBlendMode(QPainter.CompositionMode.CompositionMode_Source)
                        self.setScale(layer, f['line'])
                        self.refreshLayer(layer)

                        self.addLayer(layer, thisGroup)

                        nLayers += 1
                    else:
                        del r
                except QgsProviderConnectionException as e:
                    QMessageBox.critical(None, "ALKIS", f"Fehler: {e}")
                    break

                self.progress(iThema, "Punkte")

                kat = max([1, katalog])

                try:
                    r = QgsCategorizedSymbolRenderer("signaturnummer")
                    r.deleteAllCategories()

                    n = 0
                    for sn, in db.executeSql(f"SELECT DISTINCT signaturnummer FROM po_points WHERE {where}"):  # nosec: B608
                        svg = os.path.abspath(os.path.join(BASEDIR, "svg", "alkis%s_%d.svg" % (sn, kat)))

                        x, y, w = 0, 0, 1
                        bounds = db.executeSql("SELECT x0,y0,x1,y1 FROM alkis_punkte WHERE katalog=%d AND signaturnummer='%s'" % (kat, sn))  # nosec: B608
                        if len(bounds) == 1:
                            x = (bounds[0][0] + bounds[0][2]) / 2
                            y = (bounds[0][1] + bounds[0][3]) / 2
                            w = bounds[0][2] - bounds[0][0]
                            # h = bounds[0][3] - bounds[0][1]
                        elif sn in alkisplugin.exts:
                            x = (alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx']) / 2
                            y = (alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy']) / 2
                            w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
                            # h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']

                        if embedSVGs:
                            svgfile = QFile(svg)
                            if svgfile.open(QIODevice.OpenModeFlag.ReadOnly):
                                svg = "base64:" + svgfile.readAll().toBase64().data().decode("utf-8")
                                svgfile.close()

                        symlayer = QgsSvgMarkerSymbolLayer(svg)
                        symlayer.setOutputUnit(self.MapUnit)
                        symlayer.setSize(w)
                        symlayer.setOffset(QPointF(-x, -y))

                        sym = QgsMarkerSymbol()
                        sym.setOutputUnit(self.MapUnit)
                        sym.setSize(w)

                        sym.changeSymbolLayer(0, symlayer)

                        if hasattr(sym, "setDataDefinedAngle"):
                            sym.setDataDefinedAngle(QgsProperty.fromField("drehwinkel_grad"))
                        else:
                            symlayer.setDataDefinedProperty("angle", "drehwinkel_grad")

                        r.addCategory(QgsRendererCategory("%s" % sn, sym, self.categoryLabel(d, sn)))
                        n += 1

                    qDebug("classes: %d" % n)
                    if n > 0:
                        layer = QgsVectorLayer(
                            "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOINT srid=%d table=\"(SELECT ogc_fid,gml_id,thema,layer,signaturnummer,-drehwinkel_grad AS drehwinkel_grad,point FROM %s.po_points WHERE %s)\" (point) sql=" % (conninfo, self.epsg, self.quotedschema().replace('"', '\\"'), where),  # nosec: B608
                            "Punkte (%s)" % t,
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

                except QgsProviderConnectionException as e:
                    QMessageBox.critical(None, "ALKIS", e)
                    break

                n = 0
                labelGroup = None
                layer = None
                for i in range(2):
                    geom = "point" if i == 0 else "line"
                    geomtype = "MULTIPOINT" if i == 0 else "MULTILINESTRING"

                    try:
                        rows = db.executeSql("SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL" % (where, geom))  # nosec: B608

                        self.progress(iThema, "Beschriftungen (%d)" % (i + 1))

                        if len(rows) == 0 or rows[0][0] == 0:
                            continue

                    except QgsProviderConnectionException as e:
                        QMessageBox.critical(None, "ALKIS", f"Fehler: {e}")
                        continue

                    if n == 1:
                        labelGroup = self.addGroup("Beschriftungen", False, thisGroup)
                        self.addLayer(layer, labelGroup)
                        layer = None

                    uri = (
                        "{0} estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type={1} srid={2} table="  # nosec: B608
                        "\"("
                        "SELECT"
                        " ogc_fid"
                        ",layer"
                        # FIXME: Faktor 1.3225 empirisch bestimmt (QGIS: Schriftgröße mit ascent/decent; ALKIS: reine Schriftgröße)
                        ",CASE WHEN grad_pt<0 THEN abs(s.grad_pt) ELSE 0.25*coalesce(skalierung,1)*s.grad_pt*1.3225 END AS tsize"
                        ",CASE WHEN grad_pt<0 THEN 'Point' ELSE 'MapUnit' END AS tunit"
                        ",text"
                        ",CASE coalesce(po_labels.horizontaleausrichtung,s.horizontaleausrichtung)"
                        " WHEN 'linksbündig' THEN 'Left'"
                        " WHEN 'rechtsbündig' THEN 'Right'"
                        " ELSE 'Center'"
                        " END AS halign"
                        ",CASE coalesce(po_labels.vertikaleausrichtung,s.vertikaleausrichtung)"
                        " WHEN 'oben' THEN 'Cap'"
                        " WHEN 'Basis' THEN 'Base'"
                        " ELSE 'Half'"
                        " END AS valign"
                        ",coalesce(s.art,'Arial'::text) AS family"
                        ",CASE WHEN s.stil LIKE '%Kursiv%' THEN 1 ELSE 0 END AS italic"
                        ",CASE WHEN s.stil LIKE '%Fett%' THEN 1 ELSE 0 END AS bold"
                        ",coalesce(sperrung_pt*0.25,0) AS fontsperrung"
                        ",replace(f.umn,' ',',') AS tcolor"
                        ",CASE WHEN grad_pt<0 THEN 0 ELSE 1 END AS tshow"
                        ",{3}"
                        " FROM {7}.po_labels"
                        " LEFT OUTER JOIN {7}.alkis_schriften s ON po_labels.signaturnummer=s.signaturnummer{4}"
                        " LEFT OUTER JOIN {7}.alkis_farben f ON s.farbe=f.id"
                        " WHERE {5}"
                        ")\" ({6}) sql="
                    ).format(
                        conninfo, geomtype, self.epsg,
                        "point,st_x(point) AS tx,st_y(point) AS ty,drehwinkel_grad AS tangle" if geom == "point" else "line",
                        "" if katalog < 0 else " AND s.katalog=%d" % katalog,
                        where,
                        geom,
                        self.quotedschema().replace('"', '\\"')
                    )

                    qDebug("URI: %s" % uri)

                    layer = QgsVectorLayer(
                        uri,
                        "Beschriftungen (%s)" % t,
                        "postgres", layeropts
                    )
                    layer.setReadOnly()

                    self.setScale(layer, f['label'])

                    sym = QgsMarkerSymbol() if geom == "point" else QgsLineSymbol()
                    if geom == "point":
                        sym.setSize(0.0)
                    else:
                        sym.changeSymbolLayer(0, QgsSimpleLineSymbolLayer(Qt.GlobalColor.black, 0.0, Qt.PenStyle.NoPen))
                    self.setRenderer(layer, QgsSingleSymbolRenderer(sym))
                    self.refreshLayer(layer)

                    lyr = QgsPalLayerSettings()
                    lyr.fieldName = "text"
                    lyr.isExpression = False
                    lyr.enabled = True
                    # lyr.displayAll = True
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

                    lyr.upsidedownLabels = QgsPalLayerSettings.ShowAll
                    lyr.scaleVisibility = True

                    if geom == "point":
                        lyr.placement = QgsPalLayerSettings.AroundPoint
                    else:
                        lyr.placement = QgsPalLayerSettings.Curved
                        lyr.placementFlags = QgsPalLayerSettings.AboveLine

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
                    else:
                        c.setProperty(QgsPalLayerSettings.LinePlacementOptions, QgsProperty.fromExpression("CASE WHEN valign='Cap' THEN 'AL' WHEN valign='Base' THEN 'BL' ELSE 'OL' END"))

                    c.setProperty(QgsPalLayerSettings.LabelRotation, QgsProperty.fromExpression("-tangle"))
                    c.setProperty(QgsPalLayerSettings.AlwaysShow, QgsProperty.fromField("tshow"))
                    lyr.setDataDefinedProperties(c)

                    layer.setLabeling(QgsVectorLayerSimpleLabeling(lyr))
                    layer.setLabelsEnabled(True)

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
                "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOINT srid=%d table=%s.po_labels (point) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                "Punktmarkierung",
                "postgres", layeropts
            )

            sym = QgsMarkerSymbol()
            sym.setColor(Qt.GlobalColor.yellow)
            sym.setSize(20.0)
            sym.setOutputUnit(self.Millimeter)
            try:
                sym.setAlpha(0.5)
            except AttributeError:
                sym.setOpacity(0.5)
            self.setRenderer(self.pointMarkerLayer, QgsSingleSymbolRenderer(sym))

            self.addLayer(self.pointMarkerLayer, markerGroup)

            self.lineMarkerLayer = QgsVectorLayer(
                "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTILINESTRING srid=%d table=%s.po_labels (line) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                "Linienmarkierung",
                "postgres", layeropts
            )

            sym = QgsLineSymbol()
            sym.setColor(Qt.GlobalColor.yellow)
            try:
                sym.setAlpha(0.5)
            except AttributeError:
                sym.setOpacity(0.5)
            sym.setWidth(2)
            self.setRenderer(self.lineMarkerLayer, QgsSingleSymbolRenderer(sym))
            self.addLayer(self.lineMarkerLayer, markerGroup)

            self.areaMarkerLayer = QgsVectorLayer(
                "%s estimatedmetadata=true checkPrimaryKeyUnicity=0 key='ogc_fid' type=MULTIPOLYGON srid=%d table=%s.po_polygons (polygon) sql=false" % (conninfo, self.epsg, self.quotedschema()),
                "Flächenmarkierung",
                "postgres", layeropts
            )

            sym = QgsFillSymbol()
            sym.setColor(Qt.GlobalColor.yellow)
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

            for lyr in ['Punktmarkierung', 'Linienmarkierung', 'Flächenmarkierung']:
                try:
                    restrictedLayers.index(lyr)
                except ValueError:
                    restrictedLayers.append(lyr)

            QgsProject.instance().writeEntry("WMSRestrictedLayers", "/", restrictedLayers)

            if Qgis.QGIS_VERSION_INT >= 32600:
                QgsProject.instance().setFlag(Qgis.ProjectFlag.TrustStoredLayerStatistics)
            else:
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
                qDebug("connected")
            else:
                qDebug("not connected")
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

            uri = QgsDataSourceUri()
            if service:
                uri.setConnection(service, dbname, uid, pwd)
            else:
                uri.setConnection(host, port, dbname, uid, pwd)

            authcfg = self.settings.authcfg
            if authcfg:
                uri.setAuthConfigId(authcfg)
            conninfo = uri.connectionInfo(False)

        else:
            uid = None
            pwd = None
            uri = QgsDataSourceUri(conninfo)

        conninfo0 = conninfo

        if conninfo0 == self.conninfo and self.db and schema == self.schema:
            try:
                rows = self.db.executeSql("SELECT 1")
                if len(rows) == 1:
                    return (self.db, self.conninfo)
            except QgsProviderConnectionException:
                pass
            logMessage("Bestehende Verbindung nicht verfügbar - wird neu verbunden")
            self.db = None

        conninfo = uri.connectionInfo(True)

        md = QgsProviderRegistry.instance().providerMetadata("postgres")

        try:
            db = md.createConnection(conninfo, {})

            db.executeSql(f"SELECT set_config('search_path', {self.quotedvalue(schema)} || ',' ||current_setting('search_path'), false)")

            rows = db.executeSql("SELECT current_schema()")
            if len(rows) < 1:
                QMessageBox.warning(None, "ALKIS", f"Fehler: Aktiviertes Schema {schema} konnte nicht abgefragt werden!")
            elif rows[0][0] != schema:
                QMessageBox.warning(None, "ALKIS", f"Fehler: Schema {schema} wurde nicht aktiviert [noch aktiv: {rows[0][0]}]")

            rows = db.executeSql("SELECT " + " AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['gema_shl', 'eignerart', 'bestand', 'flurst']]))
            buchZugriff = len(rows) == 1 and rows[0][0]
            self.queryOwnerAction.setVisible(buchZugriff)

            rows = db.executeSql(f"SELECT find_srid({self.quotedvalue(schema)}::text,'ax_flurstueck'::text,'wkb_geometry'::text)")
            if len(rows) == 0:
                QMessageBox.warning(None, "ALKIS", f"Fehler: Keine Daten im Schema {schema} gefunden!")
                return (None, None)

            self.epsg = rows[0][0]
            self.schema = schema
            self.db = db
            self.conninfo = conninfo0

            return (self.db, self.conninfo)
        except QgsProviderConnectionException as e:
            logMessage(f"Datenbankfehler: {e}")
            QMessageBox.warning(None, "ALKIS", f"Fehler: Fehler bei Datenbankverbindung [{e}]!")
            return (None, None)

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
            QMessageBox.warning(None, "ALKIS", "Fehler: Punktmarkierungslayer nicht gefunden!")
            return

        self.pointMarkerLayer.setSubsetString("false")

        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", "Fehler: Flächenmarkierungslayer nicht gefunden!")
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
            QMessageBox.warning(None, "ALKIS", "Fehler: Flächenmarkierungslayer nicht gefunden!")
            return fs

        (db, conninfo) = self.opendb()
        if db is None:
            return fs

        try:
            for gmlid, flsnr in db.executeSql(
                "SELECT "  # nosec: B608
                "gml_id"
                ",alkis_flsnr(ax_flurstueck)"
                " FROM ax_flurstueck"
                " WHERE endet IS NULL"
                " AND (%s)" % " AND ".join(where)
            ):
                fs.append({'gmlid': gmlid, 'flsnr': flsnr})

        except QgsProviderConnectionException as e:
            QMessageBox.critical(None, "Fehler", f"Konnte Flurstücke nicht abfragen [{e}]")

        return fs

    def highlight(self, where='', fs=[], zoomTo=False, add=False):
        if not self.areaMarkerLayer:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.mapLayer(layerId)

        if not self.areaMarkerLayer:
            QMessageBox.warning(None, "ALKIS", "Fehler: Flächenmarkierungslayer nicht gefunden!")
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

        if zoomTo:
            try:
                rows = db.executeSql("SELECT st_extent(wkb_geometry),count(*) FROM ax_flurstueck WHERE gml_id IN ('" + "','".join(gmlids) + "')")  # nosec: B608
                if len(rows) == 1 and rows[0][1] > 0:
                    self.zoomToExtent(rows[0][0], self.areaMarkerLayer.crs())
            except QgsProviderConnectionException:
                pass

        return fs

    def zoomToExtent(self, bb, crs):
        if bb is None:
            return

        bb = bb[4:-1]
        (p0, p1) = bb.split(",")
        (x0, y0) = p0.split(" ")
        (x1, y1) = p1.split(" ")
        qDebug("x0:%s y0:%s x1:%s y1:%s" % (x0, y0, x1, y1))
        rect = QgsRectangle(float(x0), float(y0), float(x1), float(y1))

        if not isinstance(crs, QgsCoordinateReferenceSystem):
            epsg = crs
            crs = QgsCoordinateReferenceSystem(epsg)

            if not crs.isValid():
                QMessageBox.critical(None, "ALKIS", "Ungültiges Koordinatensystem %d" % epsg)
                return

        rect = self.transform(rect, crs, self.destinationCrs())

        qDebug("rect:%s" % rect.toString())

        self.iface.mapCanvas().setExtent(rect)
        self.iface.mapCanvas().refresh()

    def getschema(self):
        (db, conninfo) = self.opendb()
        if db is None:
            return None
        return self.schema

    def quotedvalue(self, v):
        return "'" + v.replace("'", "''") + "'"

    def quotedschema(self):
        return '"{}"'.format(self.schema.replace('"', '""'))

    def getepsg(self):
        (db, conninfo) = self.opendb()
        if db is None:
            return None
        return self.epsg

    def shortName(self, layer):
        return layer.serverProperties().shortName() if hasattr(layer, "serverProperties") and hasattr(layer.serverProperties(), 'shortName') else layer.shortName()

    def setShortName(self, layer):
        idx = 0
        while True:
            sn = "alkis{0}".format(idx)
            if sn not in self.shortnames:
                break
            idx += 1

        self.shortnames.append(sn)

        if hasattr(layer, "serverProperties") and hasattr(layer.serverProperties(), 'setShortName'):
            layer.serverProperties().setShortName(sn)
        else:
            layer.setShortName(sn)

    def addGroup(self, name, expand=True, parent=None):
        if parent is None:
            parent = self.iface.layerTreeView().layerTreeModel().rootGroup()

        grp = parent.addGroup(name)
        grp.setExpanded(expand)

        idx = 0
        while True:
            sn = "alkis{0}".format(idx)
            if sn not in self.shortnames:
                break
            idx += 1

        self.shortnames.append(sn)

        grp.setCustomProperty("wmsShortName", sn)

        return grp

    def addLayer(self, layer, grp):
        if not self.shortName(layer):
            self.setShortName(layer)

        QgsProject.instance().addMapLayer(layer, False)

        grp.insertLayer(0, layer)

    def refreshLayer(self, layer):
        node = QgsProject.instance().layerTreeRoot().findLayer(layer)
        self.iface.layerTreeView().layerTreeModel().refreshLayerLegend(node)

    def setGroupExpanded(self, grp, expanded):
        grp.setExpanded(expanded)

    def setGroupVisible(self, grp, visible):
        if hasattr(grp, 'setItemVisibilityChecked'):
            grp.setItemVisibilityChecked(visible)
        else:
            grp.setVisible(Qt.Checked if visible else Qt.Unchecked)

    def removeGroup(self, grp):
        grp.parent().removeChildNode(grp)

    def mapLayer(self, layerId):
        return QgsProject.instance().mapLayer(layerId)

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

        try:
            rows = db.executeSql("SELECT has_table_privilege(current_user, 'postnas_search_logging', 'INSERT')")
            if len(rows) < 1 or not rows[0][0]:
                qDebug("Einfügerecht zur Protokollierung fehlt.")
                return True
        except QgsProviderConnectionException:
            try:
                db.executeSql("CREATE TABLE postnas_search_logging(datum timestamp without time zone NOT NULL, username text NOT NULL, requestType text, search text, result text[])")
                qDebug("Protokolltabelle angelegt.")
            except QgsProviderConnectionException:
                qDebug("Protokolltabelle konnte nicht angelegt werden.")
                return True

        qDebug("Protokollierung aktiv.")
        try:
            rows = db.executeSql(f"SELECT 1 FROM information_schema.columns WHERE table_schema={self.quotedvalue(self.settings.schema)} AND table_name='postnas_search_logging' AND column_name='aktenzeichen'")  # nosec: B608
            if len(rows) == 1:
                with OverrideCursor(Qt.CursorShape.ArrowCursor):
                    az, ok = QInputDialog.getText(None, "Grund der Abfrage", "Aktenzeichen:", text=self.az)
                    if not ok:
                        return False

                    self.az = az

                    db.executeSql(
                        "INSERT INTO postnas_search_logging(datum, username, requestType, search, result, aktenzeichen) VALUES (now(),{},{},{},{},{})".format(  # nosec: B608
                            self.quotedvalue(USERNAME),
                            self.quotedvalue(requestType),
                            self.quotedvalue(search),
                            self.quotedvalue("{%s}" % ",".join(result)),
                            self.quotedvalue(self.az)
                        )
                    )
            else:
                db.executeSql(
                    "INSERT INTO postnas_search_logging(datum, username, requestType, search, result) VALUES (now(),{},{},{},{})".format(  # nosec: B608
                        self.quotedvalue(USERNAME),
                        self.quotedvalue(requestType),
                        self.quotedvalue(search),
                        self.quotedvalue("{%s}" % ",".join(result)),
                    )
                )

        except QgsProviderConnectionException as e:
            logMessage(f"Protokolleintrag konnte nicht vorgenommen werden [{e}]")
            return False

        return True
