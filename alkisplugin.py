#!/usr/bin/python
# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    alkisplugin.py
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


import sip
for c in [ "QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant" ]:
        sip.setapi(c,2)

from PyQt4.QtCore import QObject, QSettings, Qt, QPointF, pyqtSignal, QCoreApplication
from PyQt4.QtGui import QApplication, QIcon, QMessageBox, QAction, QColor, QFileDialog, QPainter
from PyQt4.QtSql import QSqlDatabase, QSqlQuery, QSqlError, QSql
from PyQt4 import QtCore

from tempfile import NamedTemporaryFile
import os, sys

BASEDIR = os.path.dirname( unicode(__file__,sys.getfilesystemencoding()) )

try:
        from qgis.core import *
        from qgis.gui import *
        qgisAvailable = True
except:
        qgisAvailable = False

if qgisAvailable:
        from qgisclasses import Info, About, ALKISPointInfo, ALKISPolygonInfo, ALKISOwnerInfo, ALKISSearch, ALKISConf

try:
        import mapscript
        from mapscript import fromstring
        mapscriptAvailable = True
        mapscript.MS_SYMBOL_CARTOLINE = -1
except:
        mapscriptAvailable = False

def qDebug(s):
        QtCore.qDebug( s.encode('ascii', 'ignore') )

def logMessage(s):
    if qgisAvailable:
        QgsMessageLog.logMessage( s, "ALKIS" )
    else:
        QtCore.qWarning( s.encode( "utf-8" ) )

class alkisplugin(QObject):
        showProgress = pyqtSignal(int,int)
        showStatusMessage = pyqtSignal(str)

        themen = (
                {
                        'name'   : u"Flurstücke",
                        'area'   : { 'min':0, 'max':5000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
                        'filter' : [
                            { 'name': u"Flächen", 'filter': "NOT layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')" },
                            { 'name': u"Nummern", 'filter': "layer IN ('ax_flurstueck_nummer','ax_flurstueck_zuordnung','ax_flurstueck_zuordnung_pfeil')" },
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
                        'name'   : u"Gebäude",
                        'area'   : { 'min':0, 'max':3500 },
                        'outline': { 'min':0, 'max':3500 },
                        'line'   : { 'min':0, 'max':3500 },
                        'point'  : { 'min':0, 'max':3500 },
                        'label'  : { 'min':0, 'max':3500 },
                        'classes': {
                            '1301': u'Wohngebäude',
                            '1304': u'Anderes Gebäude',
                            '1305': u'[1305]',
                            '1309': u'Gebäude für öffentliche Zwecke',
                            '1501': u'Aussichtsturm',
                            'rn1501': u'Anderes Gebäude',
                            '1525': u'Brunnen',
                            '2031': u'Anderes Gebäude',
                            '2032': u'Gebäude unter der Erdoberfläche',
                            '2305': u'Offene Gebäudelinie',
                            '2505': u'Öffentliches Gebäude',
                            '2513': u'Schornstein im Gebäude',
                            '2514': u'Turm im Gebäude',
                            '2515': u'Brunnen',
                            '2519': u'Kanal, Im Bau',
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
                        },
                },
                {
                        'name'   : u"Lagebezeichnungen",
                        'area'   : { 'min':0, 'max':5000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
                },
                {
                        'name'   : u"Rechtliche Festlegungen",
                        'area'   : { 'min':0, 'max':500000 },
                        'outline': { 'min':0, 'max':25000 },
                        'line'   : { 'min':0, 'max':25000 },
                        'point'  : { 'min':0, 'max':25000 },
                        'label'  : { 'min':0, 'max':25000 },
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
                        'name'   : u"Verkehr",
                        'area'   : { 'min':0, 'max':25000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
                        'classes': {
                            '1406': u'[1406]',
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
                        'name'   : u"Friedhöfe",
                        'area'   : { 'min':0, 'max':25000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
                        'classes': {
                            '1405': u'[1405]',
                            '2515': u'[2515]',
                        },
                },
                {
                        'name'   : u"Vegetation",
                        'area'   : { 'min':0, 'max':25000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
                        'classes': {
                            '1404': u'Brachland, Heide, Moor, Sumpf, Torf',
                            '1406': u'Garten',
                            '1414': u'Wald',
                            '2515': u'[2515]',
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
                        'name'   : u"Landwirtschaftliche Nutzung",
                        'area'   : { 'min':0, 'max':None },
                        'outline': { 'min':0, 'max':None },
                        'line'   : { 'min':0, 'max':None },
                        'point'  : { 'min':0, 'max':None },
                        'label'  : { 'min':0, 'max':None },
                        'classes': {
                        },
                },
                {
                        'name'   : u"Gewässer",
                        'area'   : { 'min':0, 'max':500000, },
                        'outline': { 'min':0, 'max':5000, },
                        'line'   : { 'min':0, 'max':5000, },
                        'point'  : { 'min':0, 'max':5000, },
                        'label'  : { 'min':0, 'max':5000, },
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
                        'name'   : u"Politische Grenzen",
                        'area'   : { 'min':0, 'max':5000, },
                        'outline': { 'min':0, 'max':5000, },
                        'line'   : { 'min':0, 'max':100000, },
                        'point'  : { 'min':0, 'max':5000, },
                        'label'  : { 'min':0, 'max':5000, },
                        'classes': {
                            '2010': u'Landkreisgrenze',
                            '2012': u'Flurgrenze',
                            '2014': u'Gemarkungsgrenze',
                            '2016': u'Staatsgrenze',
                            '2018': u'Landesgrenze',
                            '2020': u'Regierungsbezirksgrenze',
                            '2022': u'Gemeindegrenze',
                            '2026': u'Verwaltungsbezirksgrenze',
                        },
                },
                {
                        'name'   : u"Industrie und Gewerbe",
                        'area'   : { 'min':0, 'max':500000, },
                        'outline': { 'min':0, 'max':10000, },
                        'line'   : { 'min':0, 'max':10000, },
                        'point'  : { 'min':0, 'max':10000, },
                        'label'  : { 'min':0, 'max':10000, },
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
                        'name'   : u"Sport und Freizeit",
                        'area'   : { 'min':0, 'max':500000, },
                        'outline': { 'min':0, 'max':10000, },
                        'line'   : { 'min':0, 'max':10000, },
                        'point'  : { 'min':0, 'max':10000, },
                        'label'  : { 'min':0, 'max':10000, },
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
                        'name'   : u"Wohnbauflächen",
                        'area'   : { 'min':0, 'max':500000, },
                        'outline': { 'min':0, 'max':10000, },
                        'line'   : { 'min':0, 'max':10000, },
                        'point'  : { 'min':0, 'max':10000, },
                        'label'  : { 'min':0, 'max':10000, },
                        'classes': {
                            '1401': u'Wohnbaufläche',
                            '2515': u'[2515]',
                        },
                },
                {
                        'name'   : u"Topographie",
                        'area'   : { 'min':0, 'max':500000, },
                        'outline': { 'min':0, 'max':10000, },
                        'line'   : { 'min':0, 'max':10000, },
                        'point'  : { 'min':0, 'max':10000, },
                        'label'  : { 'min':0, 'max':10000, },
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
                }
        )

        exts = {
                '3010': { 'minx':-0.6024,       'miny':0,       'maxx':0.6171,  'maxy':2.2309 },
                '3011': { 'minx':-0.6216,       'miny':-1.0061, 'maxx':0.6299,  'maxy':1.2222 },
                '3020': { 'minx':-0.8459,       'miny':-0.8475, 'maxx':0.8559,  'maxy':0.8569 },
                '3021': { 'minx':-0.8459,       'miny':-0.8475, 'maxx':0.8559,  'maxy':0.8569 },
                '3022': { 'minx':-0.8722,       'miny':-0.8628, 'maxx':0.8617,  'maxy':0.8415 },
                '3023': { 'minx':-0.8722,       'miny':-0.8628, 'maxx':0.8617,  'maxy':0.8415 },
                '3024': { 'minx':-0.7821,       'miny':-0.7727, 'maxx':0.7588,  'maxy':0.7721 },
                '3025': { 'minx':-0.7821,       'miny':-0.7727, 'maxx':0.7588,  'maxy':0.7721 },
                '3300': { 'minx':-2.6223,       'miny':-2.6129, 'maxx':2.601,   'maxy':2.5987 },
                '3302': { 'minx':-2.5251,       'miny':-2.5107, 'maxx':2.5036,  'maxy':2.5163 },
                '3303': { 'minx':-3.4963,       'miny':-3.0229, 'maxx':3.4825,  'maxy':3.0199 },
                '3305': { 'minx':-2.5129,       'miny':-2.5091, 'maxx':2.5156,  'maxy':2.5179 },
                '3306': { 'minx':-2.5064,       'miny':-2.5046, 'maxx':2.5224,  'maxy':2.5227 },
                '3308': { 'minx':-2.4464,       'miny':-2.4446, 'maxx':2.5817,  'maxy':2.5817 },
                '3309': { 'minx':-2.5322,       'miny':-3.1229, 'maxx':2.5288,  'maxy':3.1051 },
                '3311': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3312': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3314': { 'minx':-2.7808,       'miny':-3.0312, 'maxx':2.8638,  'maxy':3.0117 },
                '3315': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3316': { 'minx':-2.7685,       'miny':-5.0168, 'maxx':2.7791,  'maxy':5.0062 },
                '3317': { 'minx':-1.5189,       'miny':-1.7538, 'maxx':1.5364,  'maxy':1.7565 },
                '3318': { 'minx':-0.8139,       'miny':-1.5046, 'maxx':0.8234,  'maxy':1.5017 },
                '3319': { 'minx':-2.1918,       'miny':-2.5922, 'maxx':2.1569,  'maxy':2.5962 },
                '3320': { 'minx':-2.7685,       'miny':-2.5016, 'maxx':2.7791,  'maxy':2.5028 },
                '3321': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3323': { 'minx':-2.5322,       'miny':-3.1229, 'maxx':2.5288,  'maxy':3.1051 },
                '3324': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3326': { 'minx':-2.5251,       'miny':-2.5107, 'maxx':2.5036,  'maxy':2.5163 },
                '3328': { 'minx':-2.7822,       'miny':-2.7729, 'maxx':2.7656,  'maxy':2.7617 },
                '3330': { 'minx':-2.7822,       'miny':-2.7729, 'maxx':2.7656,  'maxy':2.7617 },
                '3332': { 'minx':-2.7825,       'miny':-2.7731, 'maxx':2.7653,  'maxy':2.7614 },
                '3334': { 'minx':-2.5322,       'miny':-3.1229, 'maxx':2.5288,  'maxy':3.1051 },
                '3336': { 'minx':-2.5322,       'miny':-3.1229, 'maxx':2.5288,  'maxy':3.2195 },
                '3338': { 'minx':-2.5064,       'miny':-2.5046, 'maxx':2.5224,  'maxy':2.5227 },
                '3340': { 'minx':-2.5322,       'miny':-2.5228, 'maxx':2.5288,  'maxy':2.5044 },
                '3342': { 'minx':-2.5064,       'miny':-2.5046, 'maxx':2.5224,  'maxy':2.5227 },
                '3343': { 'minx':-2.0122,       'miny':-2.0122, 'maxx':2.0126,  'maxy':2.0027 },
                '3401': { 'minx':-1.9675,       'miny':-2.6149, 'maxx':1.96,    'maxy':2.6196 },
                '3402': { 'minx':-3.7939,       'miny':-3.5892, 'maxx':3.8046,  'maxy':3.5886 },
                '3403': { 'minx':-3.6978,       'miny':-3.6799, 'maxx':3.7045,  'maxy':3.6842 },
                '3404': { 'minx':-3.6978,       'miny':-3.6799, 'maxx':3.7045,  'maxy':3.6842 },
                '3405': { 'minx':-4.1785,       'miny':-3.8158, 'maxx':4.3008,  'maxy':3.9871 },
                '3406': { 'minx':-4.2746,       'miny':-3.9971, 'maxx':4.3678,  'maxy':3.8105 },
                '3407': { 'minx':-6.2567,       'miny':-2.2569, 'maxx':6.2643,  'maxy':2.2639 },
                '3409': { 'minx':-3.7075,       'miny':-3.6981, 'maxx':3.695,   'maxy':3.6888 },
                '3410': { 'minx':-3.6816,       'miny':-3.6797, 'maxx':3.6887,  'maxy':3.6844 },
                '3411': { 'minx':-3.7075,       'miny':-3.6981, 'maxx':3.695,   'maxy':3.6888 },
                '3412': { 'minx':-3.8813,       'miny':-3.8719, 'maxx':3.3302,  'maxy':3.8636 },
                '3413': { 'minx':-1.2257,       'miny':-0.2181, 'maxx':1.2166,  'maxy':0.2127 },
                '3415': { 'minx':-5.0815,       'miny':-2.5197, 'maxx':4.9078,  'maxy':3.1702 },
                '3417': { 'minx':-3.6945,       'miny':-3.6889, 'maxx':3.6754,  'maxy':3.6978 },
                '3419': { 'minx':-2.6093,       'miny':-3.2037, 'maxx':2.6138,  'maxy':3.2091 },
                '3421': { 'minx':-1.0193,       'miny':-0.9064, 'maxx':1.0043,  'maxy':0.9118 },
                '3423': { 'minx':-3.6945,       'miny':-3.6889, 'maxx':3.6754,  'maxy':3.6978 },
                '3424': { 'minx':-2.5193,       'miny':-2.5137, 'maxx':2.5093,  'maxy':2.5134 },
                '3426': { 'minx':-2.5193,       'miny':-2.5137, 'maxx':2.5093,  'maxy':2.5134 },
                '3428': { 'minx':-2.5193,       'miny':-2.5137, 'maxx':2.5093,  'maxy':2.5134 },
                '3430': { 'minx':-2.5193,       'miny':-2.5137, 'maxx':2.5093,  'maxy':2.5134 },
                '3432': { 'minx':-2.5193,       'miny':-2.9017, 'maxx':2.5093,  'maxy':2.5895 },
                '3434': { 'minx':-2.5193,       'miny':-2.8235, 'maxx':2.5093,  'maxy':2.6663 },
                '3436': { 'minx':-6.0195,       'miny':-6.1918, 'maxx':6.0061,  'maxy':6.0214 },
                '3438': { 'minx':-6.2697,       'miny':-6.2641, 'maxx':6.2508,  'maxy':6.2528 },
                '3439': { 'minx':-6.2697,       'miny':-6.2641, 'maxx':6.2508,  'maxy':6.2528 },
                '3440': { 'minx':-1.1856,       'miny':-2.0168, 'maxx':1.1925,  'maxy':2.1807 },
                '3441': { 'minx':-2.6945,       'miny':-2.0062, 'maxx':2.5297,  'maxy':2.1914 },
                '3442': { 'minx':-1.2818,       'miny':-1.3142, 'maxx':1.2894,  'maxy':1.326 },
                '3444': { 'minx':-0.5701,       'miny':-1.5137, 'maxx':0.5529,  'maxy':1.5608 },
                '3446': { 'minx':-1.9144,       'miny':-2.0137, 'maxx':1.6907,  'maxy':2.1838 },
                '3448': { 'minx':-0.175,        'miny':-1.5,    'maxx':0.175,   'maxy':1.5 },
                '3450': { 'minx':-2.2109,       'miny':-2.0168, 'maxx':2.202,   'maxy':2.1807 },
                '3452': { 'minx':-1.1856,       'miny':-2.0168, 'maxx':1.1925,  'maxy':2.1807 },
                '3454': { 'minx':-0.9292,       'miny':-0.929,  'maxx':0.9335,  'maxy':0.935 },
                '3456': { 'minx':-4.1028,       'miny':-2.7517, 'maxx':3.4036,  'maxy':2.7596 },
                '3458': { 'minx':-2.0507,       'miny':-1.6767, 'maxx':1.8776,  'maxy':1.6959 },
                '3460': { 'minx':-1.8905,       'miny':-2.1752, 'maxx':1.6503,  'maxy':2.664 },
                '3462': { 'minx':-3.4608,       'miny':-2.6966, 'maxx':3.2266,  'maxy':2.6765 },
                '3470': { 'minx':-2.7435,       'miny':-2.1025, 'maxx':2.7393,  'maxy':2.7579 },
                '3472': { 'minx':-0.8011,       'miny':-0.7704, 'maxx':0.8041,  'maxy':0.7516 },
                '3474': { 'minx':-1.4221,       'miny':-0.9636, 'maxx':1.4072,  'maxy':0.9686 },
                '3476': { 'minx':-1.562,        'miny':-0.8073, 'maxx':1.5577,  'maxy':0.8058 },
                '3478': { 'minx':-4.0053,       'miny':-0.5438, 'maxx':4.0176,  'maxy':0.5458 },
                '3480': { 'minx':-1.8193,       'miny':-2.0137, 'maxx':1.9459,  'maxy':2.0013 },
                '3481': { 'minx':-1.8905,       'miny':-1.8808, 'maxx':1.94,    'maxy':1.9043 },
                '3482': { 'minx':-2.115,        'miny':-1.6314, 'maxx':2.1682,  'maxy':1.6038 },
                '3483': { 'minx':-1.9026,       'miny':-1.3693, 'maxx':1.8312,  'maxy':1.2484 },
                '3484': { 'minx':-2.1193,       'miny':-1.5137, 'maxx':2.1316,  'maxy':1.5153 },
                '3486': { 'minx':-1.506,        'miny':-1.5182, 'maxx':1.517,   'maxy':1.5108 },
                '3488': { 'minx':-3.044,        'miny':-0.7478, 'maxx':3.0241,  'maxy':0.7514 },
                '3490': { 'minx':-2.5057,       'miny':-0.6882, 'maxx':2.5873,  'maxy':0.6518 },
                '3501': { 'minx':-2.852,        'miny':-3.5574, 'maxx':2.8258,  'maxy':3.3221 },
                '3502': { 'minx':-1.6984,       'miny':-2.1752, 'maxx':1.6797,  'maxy':2.1846 },
                '3503': { 'minx':-3.044,        'miny':-2.787,  'maxx':3.0564,  'maxy':3.0227 },
                '3504': { 'minx':-1.1216,       'miny':-1.1104, 'maxx':1.0953,  'maxy':1.0957 },
                '3506': { 'minx':-1.4583,       'miny':-2.6887, 'maxx':1.4677,  'maxy':2.5699 },
                '3507': { 'minx':-2.262,        'miny':-3.2279, 'maxx':2.0229,  'maxy':3.2312 },
                '3508': { 'minx':-1.6984,       'miny':-1.6767, 'maxx':1.6797,  'maxy':1.6959 },
                '3509': { 'minx':-1.7693,       'miny':-1.6387, 'maxx':1.7702,  'maxy':1.6422 },
                '3510': { 'minx':-1.9093,       'miny':-1.3037, 'maxx':1.9211,  'maxy':1.2908 },
                '3511': { 'minx':-1.7945,       'miny':-2.5606, 'maxx':1.6809,  'maxy':2.6044 },
                '3512': { 'minx':-1.6342,       'miny':-2.6059, 'maxx':1.5504,  'maxy':2.6056 },
                '3513': { 'minx':-3.012,        'miny':-2.6059, 'maxx':3.0234,  'maxy':2.6056 },
                '3514': { 'minx':-5.031,        'miny':-2.6284, 'maxx':5.0211,  'maxy':2.6067 },
                '3515': { 'minx':-1.4443,       'miny':-2.1887, 'maxx':1.4495,  'maxy':2.1938 },
                '3516': { 'minx':-1.1536,       'miny':-1.2009, 'maxx':1.1919,  'maxy':1.2106 },
                '3517': { 'minx':-1.442,        'miny':-2.1074, 'maxx':1.4517,  'maxy':2.0914 },
                '3518': { 'minx':-2.0956,       'miny':-0.8475, 'maxx':2.091,   'maxy':0.8569 },
                '3519': { 'minx':-0.8652,       'miny':-0.8611, 'maxx':0.8687,  'maxy':0.8432 },
                '3520': { 'minx':-1.6021,       'miny':-1.6089, 'maxx':1.6146,  'maxy':1.6033 },
                '3521': { 'minx':-1.8585,       'miny':-1.8581, 'maxx':1.8427,  'maxy':1.8583 },
                '3522': { 'minx':-1.6129,       'miny':-1.6037, 'maxx':1.6037,  'maxy':1.6084 },
                '3523': { 'minx':-1.6982,       'miny':-2.3567, 'maxx':1.7123,  'maxy':2.3709 },
                '3524': { 'minx':-3.2045,       'miny':-3.1951, 'maxx':3.1883,  'maxy':3.1947 },
                '3525': { 'minx':-4.4542,       'miny':-3.0362, 'maxx':4.4509,  'maxy':3.0297 },
                '3526': { 'minx':-2.5315,       'miny':-1.5408, 'maxx':2.5294,  'maxy':1.557 },
                '3527': { 'minx':-1.8906,       'miny':-1.9033, 'maxx':1.8752,  'maxy':1.9052 },
                '3528': { 'minx':-2.5315,       'miny':-1.5408, 'maxx':2.5294,  'maxy':1.557 },
                '3529': { 'minx':-1.3458,       'miny':-1.3596, 'maxx':1.3546,  'maxy':1.3491 },
                '3531': { 'minx':-1.7623,       'miny':-1.6767, 'maxx':1.7774,  'maxy':1.6959 },
                '3532': { 'minx':-1.4739,       'miny':-2.4473, 'maxx':1.4845,  'maxy':2.4416 },
                '3533': { 'minx':-1.2176,       'miny':-2.1752, 'maxx':1.2247,  'maxy':2.002 },
                '3534': { 'minx':-0.8973,       'miny':-2.0168, 'maxx':0.901,   'maxy':2.2035 },
                '3535': { 'minx':-1.2176,       'miny':-2.0168, 'maxx':1.2247,  'maxy':2.021 },
                '3536': { 'minx':-0.9421,       'miny':-1.4366, 'maxx':0.9527,  'maxy':1.4322 },
                '3537': { 'minx':-1.6094,       'miny':-1.6037, 'maxx':1.6072,  'maxy':1.6084 },
                '3539': { 'minx':-1.8585,       'miny':-2.0846, 'maxx':1.8752,  'maxy':1.9541 },
                '3540': { 'minx':-1.6663,       'miny':-3.0589, 'maxx':1.7436,  'maxy':3.1911 },
                '3541': { 'minx':-2.6083,       'miny':-1.5952, 'maxx':2.6148,  'maxy':1.5943 },
                '3542': { 'minx':-2.5954,       'miny':-1.6089, 'maxx':2.5957,  'maxy':1.6033 },
                '3543': { 'minx':-1.6342,       'miny':-0.4532, 'maxx':1.6471,  'maxy':0.4546 },
                '3544': { 'minx':-1.1216,       'miny':-0.6118, 'maxx':1.0953,  'maxy':0.5916 },
                '3545': { 'minx':-2.6081,       'miny':-1.6037, 'maxx':2.6151,  'maxy':1.6084 },
                '3546': { 'minx':-2.6093,       'miny':-1.6037, 'maxx':2.6138,  'maxy':1.6084 },
                '3547': { 'minx':-2.6093,       'miny':-1.6037, 'maxx':2.6138,  'maxy':1.6084 },
                '3548': { 'minx':-1.09,         'miny':-1.1536, 'maxx':1.0947,  'maxy':1.0528 },
                '3549': { 'minx':-1.5061,       'miny':-3.8749, 'maxx':1.5488,  'maxy':3.9066 },
                '3550': { 'minx':-0.8652,       'miny':-3.2855, 'maxx':0.8687,  'maxy':3.29 },
                '3551': { 'minx':-1.6021,       'miny':-2.6059, 'maxx':1.6146,  'maxy':2.6056 },
                '3552': { 'minx':-0.8652,       'miny':-2.8552, 'maxx':1.2218,  'maxy':2.7724 },
                '3553': { 'minx':-1.0894,       'miny':-3.3082, 'maxx':1.1595,  'maxy':3.4053 },
                '3554': { 'minx':-2.7696,       'miny':-2.764,  'maxx':2.778,   'maxy':2.7704 },
                '3556': { 'minx':-1.5061,       'miny':-1.5636, 'maxx':1.5488,  'maxy':1.557 },
                '3557': { 'minx':-1.0254,       'miny':-3.3535, 'maxx':1.0303,  'maxy':3.3605 },
                '3558': { 'minx':-1.0894,       'miny':-3.3764, 'maxx':1.1595,  'maxy':3.361 },
                '3559': { 'minx':-1.3137,       'miny':-3.648,  'maxx':1.322,   'maxy':3.5547 },
                '3560': { 'minx':-2.852,        'miny':-3.1495, 'maxx':2.9226,  'maxy':3.1477 },
                '3561': { 'minx':-2.9481,       'miny':-3.4217, 'maxx':2.9568,  'maxy':3.3167 },
                '3562': { 'minx':-2.0956,       'miny':-0.5978, 'maxx':2.091,   'maxy':0.6056 },
                '3563': { 'minx':-1.6094,       'miny':-1.6037, 'maxx':1.6072,  'maxy':1.6084 },
                '3564': { 'minx':-1.6021,       'miny':-1.6089, 'maxx':1.6465,  'maxy':1.6033 },
                '3565': { 'minx':-1.3778,       'miny':-3.1045, 'maxx':1.3871,  'maxy':3.0086 },
                '3566': { 'minx':-1.1216,       'miny':-0.6118, 'maxx':1.0953,  'maxy':0.5916 },
                '3567': { 'minx':-2.0964,       'miny':-1.0945, 'maxx':2.0902,  'maxy':1.1116 },
                '3568': { 'minx':-2.115,        'miny':-1.1104, 'maxx':2.1037,  'maxy':1.0957 },
                '3569': { 'minx':-1.3458,       'miny':-1.3596, 'maxx':1.3546,  'maxy':1.3491 },
                '3570': { 'minx':-3.1081,       'miny':-1.1104, 'maxx':3.025,   'maxy':1.0957 },
                '3571': { 'minx':-1.3137,       'miny':-1.3143, 'maxx':1.322,   'maxy':1.303 },
                '3572': { 'minx':-1.5701,       'miny':-1.6089, 'maxx':1.5821,  'maxy':1.6033 },
                '3573': { 'minx':-29.7675,      'miny':-6.0952, 'maxx':29.7664, 'maxy':6.0919 },
                '3574': { 'minx':-2.7693,       'miny':-2.7637, 'maxx':2.7783,  'maxy':2.7707 },
                '3576': { 'minx':-2.5193,       'miny':-2.5137, 'maxx':2.5093,  'maxy':2.5134 },
                '3578': { 'minx':-1.6094,       'miny':-1.6037, 'maxx':1.6072,  'maxy':1.6084 },
                '3579': { 'minx':-0.8011,       'miny':-0.8158, 'maxx':0.8042,  'maxy':0.8201 },
                '3580': { 'minx':-0.09,         'miny':-0.3,    'maxx':0.09,    'maxy':0.3 },
                '3583': { 'minx':-1.2177,       'miny':-2.8099, 'maxx':1.1925,  'maxy':2.794 },
                '3584': { 'minx':-1.3884,       'miny':-2.6038, 'maxx':1.4728,  'maxy':2.5162 },
                '3585': { 'minx':-0.5127,       'miny':-0.5212, 'maxx':0.514,   'maxy':0.5002 },
                '3586': { 'minx':-1.0254,       'miny':-0.5212, 'maxx':1.0303,  'maxy':0.5002 },
                '3587': { 'minx':-3.3968,       'miny':-3.3761, 'maxx':3.3866,  'maxy':3.3847 },
                '3588': { 'minx':-3.5973,       'miny':-3.1348, 'maxx':3.674,   'maxy':3.2307 },
                '3589': { 'minx':-0.596,        'miny':-2.5968, 'maxx':0.5914,  'maxy':2.5006 },
                '3590': { 'minx':-2.879,        'miny':-3.0183, 'maxx':2.8637,  'maxy':2.4292 },
                '3592': { 'minx':-1.6214,       'miny':-0.6027, 'maxx':1.5952,  'maxy':0.6006 },
                '3593': { 'minx':-10.1131,      'miny':-2.0983, 'maxx':10.1004, 'maxy':2.1007 },
                '3594': { 'minx':-1.8137,       'miny':-2.0983, 'maxx':1.8228,  'maxy':2.1007 },
                '3595': { 'minx':-2.07,         'miny':-0.6027, 'maxx':2.116,   'maxy':0.6006 },
                '3596': { 'minx':-0.5965,       'miny':-1.8446, 'maxx':0.5909,  'maxy':1.8491 },
                '3597': { 'minx':-1.4611,       'miny':-2.2794, 'maxx':1.4651,  'maxy':2.5843 },
                '3599': { 'minx':-1.2398,       'miny':-2.2796, 'maxx':1.2349,  'maxy':2.1731 },
                '3601': { 'minx':-0.731,        'miny':-0.6744, 'maxx':0.7457,  'maxy':0.7336 },
                '3603': { 'minx':-1.5253,       'miny':-1.6223, 'maxx':1.5298,  'maxy':2.0915 },
                '3605': { 'minx':-0.6314,       'miny':-1.2045, 'maxx':0.6523,  'maxy':1.2072 },
                '3607': { 'minx':-1.4611,       'miny':-1.3958, 'maxx':1.4651,  'maxy':1.4498 },
                '3609': { 'minx':-1.3971,       'miny':-2.0303, 'maxx':1.4963,  'maxy':2.0077 },
                '3613': { 'minx':-0.5064,       'miny':-0.5045, 'maxx':0.5203,  'maxy':0.5169 },
                '3615': { 'minx':-2.9032,       'miny':-0.852,  'maxx':2.9048,  'maxy':0.8523 },
                '3617': { 'minx':-9.4081,       'miny':-2.5062, 'maxx':9.4305,  'maxy':2.498 },
                '3619': { 'minx':-3.6365,       'miny':-0.6045, 'maxx':3.6361,  'maxy':0.6216 },
                '3621': { 'minx':-3.7565,       'miny':-0.6045, 'maxx':3.7768,  'maxy':0.6216 },
                '3623': { 'minx':-1.5253,       'miny':-1.4865, 'maxx':1.5298,  'maxy':1.4739 },
                '3625': { 'minx':-2.0064,       'miny':-1.9762, 'maxx':2.0183,  'maxy':1.9929 },
                '3627': { 'minx':-2.807,        'miny':-2.5968, 'maxx':2.8379,  'maxy':2.7521 },
                '3629': { 'minx':-0.5064,       'miny':-0.5045, 'maxx':0.5203,  'maxy':0.5169 },
                '3631': { 'minx':-0.15,         'miny':-0.15,   'maxx':0.15,    'maxy':0.15 },
                '3632': { 'minx':-0.09,         'miny':-1,      'maxx':0.09,    'maxy':1 },
                '3634': { 'minx':-1.7176,       'miny':-1.5998, 'maxx':1.7572,  'maxy':1.749 },
                '3636': { 'minx':-3.3518,       'miny':-0.852,  'maxx':3.3662,  'maxy':0.8523 },
                '3637': { 'minx':-1.9739,       'miny':-1.9623, 'maxx':0.3762,  'maxy':1.9607 },
                '3638': { 'minx':-2.1982,       'miny':-0.852,  'maxx':2.2146,  'maxy':0.8523 },
                '3640': { 'minx':-2.1021,       'miny':-2.0983, 'maxx':2.1168,  'maxy':2.1007 },
                '3641': { 'minx':-2.3584,       'miny':-2.3475, 'maxx':2.346,   'maxy':2.3574 },
                '3642': { 'minx':-0.596,        'miny':-0.6027, 'maxx':0.5914,  'maxy':0.6006 },
                '3643': { 'minx':-0.09,         'miny':-0.5,    'maxx':0.09,    'maxy':0.5 },
                '3644': { 'minx':-1.5253,       'miny':-0.6027, 'maxx':1.5298,  'maxy':0.6007 },
                '3645': { 'minx':-0.596,        'miny':-0.852,  'maxx':0.5914,  'maxy':0.8523 },
                '3646': { 'minx':-0.596,        'miny':-0.6027, 'maxx':0.5914,  'maxy':0.6007 },
                '3647': { 'minx':-0.3076,       'miny':-0.6027, 'maxx':0.3017,  'maxy':0.6007 },
                '3648': { 'minx':-0.8524,       'miny':-0.6027, 'maxx':0.8495,  'maxy':0.6006 },
                '3649': { 'minx':-2.0058,       'miny':-0.6027, 'maxx':2.019,   'maxy':0.6007 },
                '3650': { 'minx':-0.596,        'miny':-0.6027, 'maxx':0.5914,  'maxy':0.6006 },
                '3651': { 'minx':-1.4932,       'miny':-0.784,  'maxx':1.4651,  'maxy':0.829 },
                '3653': { 'minx':-3.0314,       'miny':-0.6027, 'maxx':3.0038,  'maxy':0.6006 },
                '3701': { 'minx':-1.4931,       'miny':-2.2569, 'maxx':1.4333,  'maxy':2.8576 },
                '3703': { 'minx':-1.2048,       'miny':-1.1919, 'maxx':1.2052,  'maxy':1.197 },
                '3705': { 'minx':-1.6855,       'miny':-1.6904, 'maxx':1.6927,  'maxy':1.6822 },
                '3707': { 'minx':-3.0314,       'miny':-3.0047, 'maxx':3.0038,  'maxy':3.0153 },
                '3709': { 'minx':-1.6855,       'miny':-1.6904, 'maxx':1.6927,  'maxy':1.6822 },
        }

        BLOCKS = {
                # Flächen
                'alkis1301': { 'symbol': "0" },
                'alkis1304': { 'symbol': "0" },
                'alkis1305': { 'symbol': "0" },
                'alkis1306': { 'symbol': "0" },
                'alkis1309': { 'symbol': "0" },
                'alkis1401': { 'symbol': "0" },
                'alkis1403': { 'symbol': "0" },
                'alkis1404': { 'symbol': "0" },
                'alkis1405': { 'symbol': "0" },
                'alkis1406': { 'symbol': "0" },
                'alkis1409': { 'symbol': "0" },
                'alkis1410': { 'symbol': "0" },
                'alkis1414': { 'symbol': "0" },
                'alkis1501': { 'symbol': "0" },
                'alkis1510': { 'symbol': "0" },
                'alkis1519': { 'symbol': "0" },
                'alkis1520': { 'symbol': "0" },
                'alkis1521': { 'symbol': "0" }, # NRW
                'alkis1522': { 'symbol': "0" }, # NRW
                'alkis1523': { 'symbol': "0" }, # NRW
                'alkis1525': { 'symbol': "0" }, # NRW
                'alkis1526': { 'symbol': "0" },
                'alkis1532': { 'symbol': "0" }, # NRW
                'alkis1542': { 'symbol': "0" }, # NRW
                'alkis1540': { 'symbol': "0" },
                'alkis1701': { 'symbol': "0" },
                'alkis1702': { 'symbol': "0" },
                'alkis1808': { 'symbol': "0" },
                'alkis1530': { 'symbol': "0" },

                'alkis1502': { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 10, 5 ], },

                'alkisrn1305': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1306': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1321': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1330': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color': [153,153,153], },
                'alkisrn1501': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1510': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1519': [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 1, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 20, 10 ], 'filled': 1, },
                        ],
                'alkisrn1520': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1521': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color': [81,0,0], },
                'alkisrn1524': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color': [153,153,153], },
                'alkisrn1525': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1526': { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color': [0,204,204], },
                'alkisrn1530': [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 1, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 20, 10 ], 'filled': 1, 'color': [81,0,0], },
                        ],
                'alkisrn1531': [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 2, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 10, 5 ], 'filled': 1, },
                        ],
                'alkisrn1535'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'size': 2, 'color':  [127,127,127], },
                'alkisrn1540'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [153,153,153], },
                'alkisrn1542'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [153,153,153], },
                'alkisrn1548'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [153,153,153], },
                'alkisrn1550'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [153,153,153], },
                'alkisrn1551'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1560'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [0,255,0], },
                'alkisrn1562'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [0,0,255], },
                'alkisrn1701'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1702'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkisrn1703'  : [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 3, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color': [ 255,255,255 ], 'size': 3, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'gap':40, 'pattern': [ 10, 40 ], 'filled': 1, },
                        ],
                'alkisrn1704'  : [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 3, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 3, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 40, 10 ], 'filled': 1, },
                        ],
                'alkisrn1705'  : [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 3, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 3, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 40, 10 ], 'filled': 1, },
                        ],
                'alkisrn1740'  : [
                                { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'size': 3, 'points': [1, 1], 'filled': 1, 'color': [ 255,255,255 ], },
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'size': 3, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 40, 10 ], 'filled': 1, },
                        ],
                'alkisrn1808'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'color':  [153,153,153], },

                # Linien
                'alkis2001'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2002'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2003'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, },
                'alkis2004'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, }, # Pfeilspitze wird in Ableitungsregeln behandelt.
                'alkis2005'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 204, 204, 204 ], 'size': 2, 'linecap': mapscript.MS_CJC_TRIANGLE, }, # NRW
                'alkis2006'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 6, 1 ], }, # NRW
                'alkis2008'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 20, 10 ], },

                'alkis2010'  : [
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 10, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND,  'pattern': [ 35, 25, ], },
                                { 'character': "&#14;", 'color':  [ 242, 127, 255 ], 'size': 9, 'gap': 11, },
                        ],

                'alkis2012'  : [
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 5, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND,  'pattern': [ 25, 30, ], },
                                { 'character': "&#14;", 'color':  [ 242, 127, 255 ], 'size': 5, 'gap': 10, },
                        ],

                'alkis2014'  : [
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 3, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND,  'pattern': [ 25, 30, ], },
                                { 'character': "&#14;", 'color':  [ 242, 127, 255 ], 'size': 3, 'gap':8, },
                        ],

                'alkis2016'  : [ #2016
                                { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 9, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND,  'pattern': [ 50, 90, ], },
                                { 'character': "&#14;", 'color':  [ 242, 127, 255 ], 'size': 9, 'gap':25, },
                        ],

                'alkis2018': [ #2016
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 7, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'gap':900, 'pattern': [ 800, 350, 800, 900 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 7, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'pattern': [ 10, 2840 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 7, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'gap':450,  },
                ],

                #'alkis2020'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2020': [
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'gap':1200, 'pattern': [ 700, 300, 700, 1200 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'pattern': [ 10, 440, 10, 2440 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'gap':375,  },
                ],

                'alkis2022': [
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 4, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'gap':500, 'pattern': [ 500, 500 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 4, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'pattern': [ 10, 990 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 4, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'gap':250,  },
                ],

                'alkis2026': [
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'gap':1650, 'pattern': [ 700, 300, 700, 1650 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'pattern': [ 10, 440, 10, 440, 10, 2440 ],  },
                        { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 242, 127, 255 ], 'size': 6, 'linecap': mapscript.MS_CJC_ROUND, 'linejoin': mapscript.MS_CJC_ROUND, 'gap':375,  },
                ],

                'alkis2028'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2029'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 204, 204, 204 ], 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, }, # NRW
                'alkis2030'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 10, 5 ], },
                'alkis2031'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 10, 5 ], },
                'alkis2032'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 1, 1 ], },
                'alkis2305'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 10, 5 ], },
                'alkis2505'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2506'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 153, 153, 153 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, 'pattern': [ 35, 35 ],  },
                'alkis2507'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2512'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 1, 1 ], },
                'alkis2513'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_ROUND, }, # NRW
                'alkis2514'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, 'size': 2 },
                'alkis2515'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2517'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2518'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2523'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 1, 1 ], },
                'alkis2510'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, }, # NRW
                'alkis2519'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 204, 204 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 7, 1 ], }, # NRW
                'alkis2520'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 204, 204 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 4, 2 ],  }, # NRW
                'alkis2524'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2525'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, },
                'alkis2527'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 153, 153, 153 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, },
                'alkis2530'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 127, 127, 127 ], 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, },
                'alkis2533'  : { 'type': mapscript.MS_SYMBOL_ELLIPSE, 'points': [1, 1], 'filled': 1, },
                'alkis2535'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 81, 0, 0 ], 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 20, 32 ], }, # NRW
                'alkis2560'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 204, 204 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER,  'pattern': [ 35, 35 ], }, # NRW
                'alkis2592'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 204, 204 ], 'size': 1, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, }, # NRW
                'alkis2623'  : { 'type': mapscript.MS_SYMBOL_CARTOLINE, 'color':  [ 0, 0, 0 ], 'size': 2, 'linecap': mapscript.MS_CJC_BUTT, 'linejoin': mapscript.MS_CJC_MITER, },      # NRW
        } if mapscriptAvailable else {}

        defcrs = "EPSG:4326 EPSG:4647 EPSG:31466 EPSG:31467 EPSG:31468 EPSG:25832 EPSG:25833"

        def __init__(self, iface):
                QObject.__init__(self)
                self.iface = iface
                self.pointMarkerLayer = None
                self.lineMarkerLayer = None
                self.areaMarkerLayer = None
                self.alkisGroup = None

        def initGui(self):
                self.toolbar = self.iface.addToolBar( u"norGIS: ALKIS" )
                self.toolbar.setObjectName( "norGIS_ALKIS_Toolbar" )

                self.importAction = QAction( QIcon( "alkis:logo.svg" ), "Layer einbinden", self.iface.mainWindow())
                self.importAction.setWhatsThis("ALKIS-Layer einbinden")
                self.importAction.setStatusTip("ALKIS-Layer einbinden")
                self.importAction.triggered.connect( self.alkisimport )

                if mapscriptAvailable:
                        self.umnAction = QAction( QIcon( "alkis:logo.svg" ), "UMN-Mapdatei erzeugen...", self.iface.mainWindow())
                        self.umnAction.setWhatsThis("UMN-Mapserver-Datei erzeugen")
                        self.umnAction.setStatusTip("UMN-Mapserver-Datei erzeugen")
                        self.umnAction.triggered.connect(self.mapfile)
                else:
                        self.umnAction = None

                self.searchAction = QAction( QIcon( "alkis:find.png" ), "Suchen...", self.iface.mainWindow())
                self.searchAction.setWhatsThis("ALKIS-Beschriftung suchen")
                self.searchAction.setStatusTip("ALKIS-Beschriftung suchen")
                self.searchAction.triggered.connect(self.search)
                self.toolbar.addAction( self.searchAction )

                self.queryOwnerAction = QAction( QIcon( "alkis:eigner.png" ), u"Flurstücksnachweis", self.iface.mainWindow())
                self.queryOwnerAction.triggered.connect( self.setQueryOwnerTool )
                self.toolbar.addAction( self.queryOwnerAction )
                self.queryOwnerInfoTool = ALKISOwnerInfo( self )

                self.clearAction = QAction( QIcon( "alkis:clear.png" ), "Hervorhebungen entfernen", self.iface.mainWindow())
                self.clearAction.setWhatsThis("Hervorhebungen entfernen")
                self.clearAction.setStatusTip("Hervorhebungen entfernen")
                self.clearAction.triggered.connect(self.clearHighlight)
                self.toolbar.addAction( self.clearAction )

                self.confAction = QAction( QIcon("alkis:logo.svg" ), "Konfiguration...", self.iface.mainWindow())
                self.confAction.setWhatsThis("Konfiguration der ALKIS-Erweiterung")
                self.confAction.setStatusTip("Konfiguration der ALKIS-Erweiterung")
                self.confAction.triggered.connect(self.conf)

                self.aboutAction = QAction( QIcon("alkis:logo.svg" ), u"Über...", self.iface.mainWindow())
                self.aboutAction.setWhatsThis(u"Über die Erweiterung")
                self.aboutAction.setStatusTip(u"Über die Erweiterung")
                self.aboutAction.triggered.connect(self.about)

                if hasattr(self.iface, "addPluginToDatabaseMenu"):
                        self.iface.addPluginToDatabaseMenu("&ALKIS", self.importAction)
                        if self.umnAction:
                            self.iface.addPluginToDatabaseMenu("&ALKIS", self.umnAction)
                        self.iface.addPluginToDatabaseMenu("&ALKIS", self.confAction)
                        self.iface.addPluginToDatabaseMenu("&ALKIS", self.aboutAction)
                else:
                        self.iface.addPluginToMenu("&ALKIS", self.importAction)
                        self.iface.addPluginToMenu("&ALKIS", self.umnAction)
                        self.iface.addPluginToMenu("&ALKIS", self.confAction)
                        self.iface.addPluginToMenu("&ALKIS", self.aboutAction)

                ns = QSettings( "norBIT", "EDBSgen/PRO" )
                if ns.contains( "norGISPort" ):
                        self.pointInfoAction = QAction( QIcon( "alkis:info.png" ), u"Flurstücksabfrage (Punkt)", self.iface.mainWindow())
                        self.pointInfoAction.activated.connect( self.setPointInfoTool )
                        self.toolbar.addAction( self.pointInfoAction )
                        self.pointInfoTool = ALKISPointInfo( self )

                        self.polygonInfoAction = QAction( QIcon( "alkis:pinfo.png" ), u"Flurstücksabfrage (Polygon)", self.iface.mainWindow())
                        self.polygonInfoAction.activated.connect( self.setPolygonInfoTool )
                        self.toolbar.addAction( self.polygonInfoAction )
                        self.polygonInfoTool = ALKISPolygonInfo( self )
                else:
                        self.pointInfoTool = None
                        self.polygonInfoTool = None

                if not self.register():
                        self.iface.mainWindow().initializationCompleted.connect( self.register )

        def unload(self):
                if hasattr(self.iface, "removePluginDatabaseMenu"):
                        self.iface.removePluginDatabaseMenu("&ALKIS", self.importAction)
                        if self.umnAction:
                            self.iface.removePluginDatabaseMenu("&ALKIS", self.umnAction)
                        self.iface.removePluginDatabaseMenu("&ALKIS", self.confAction)
                        self.iface.removePluginDatabaseMenu("&ALKIS", self.aboutAction)
                else:
                        self.iface.removePluginMenu("&ALKIS", self.importAction)
                        if self.umnAction:
                            self.iface.removePluginMenu("&ALKIS", self.umnAction)
                        self.iface.removePluginMenu("&ALKIS", self.confAction)
                        self.iface.removePluginMenu("&ALKIS", self.aboutAction)

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

                if not self.pointInfoTool is None:
                        self.pointInfoTool.deleteLater()
                        self.pointInfoTool = None

                if not self.polygonInfoTool is None:
                        self.polygonInfoTool.deleteLater()
                        self.polygonInfoTool = None

        def conf(self):
                dlg = ALKISConf(self)
                dlg.exec_()

        def about(self):
                dlg = About()
                dlg.exec_()

        def initLayers(self):
                if not self.pointMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/pointMarkerLayer" )
                        if ok:
                                self.pointMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.pointMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Punktmarkierungslayer nicht gefunden!" )
                        return False

                if not self.lineMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/lineMarkerLayer" )
                        if ok:
                                self.lineMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.lineMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Linienmarkierungslayer nicht gefunden!" )
                        return False

                return True

        def search(self):
                dlg = ALKISSearch(self)
                dlg.exec_()

        def setScale(self, layer, d):
                if d['min'] is None and d['max'] is None:
                        return

                if not d['min'] is None: layer.setMinimumScale(d['min'])
                if not d['max'] is None: layer.setMaximumScale(d['max'])

                try:
                    layer.setScaleBasedVisibility(True)
                except:
                    layer.toggleScaleBasedVisibility(True)

        def setUMNScale(self, layer, d):
                if d['min'] is None and d['max'] is None:
                        return

                if not d['min'] is None: layer.minscaledenom = d['min']
                if not d['max'] is None: layer.maxscaledenom = d['max']

        def categoryLabel(self, d, sn):
                qDebug( u"categories: %s" % d['classes'] )
                if d['classes'].has_key(unicode(sn)):
                        return d['classes'][unicode(sn)]
                else:
                        return "(%s)" % sn

        def run(self):
                QApplication.setOverrideCursor( Qt.WaitCursor )
                try:
                        self.alkisimport()
                finally:
                        QApplication.restoreOverrideCursor()

        def progress(self,i,m,s):
                self.showStatusMessage.emit( u"%s/%s" % (alkisplugin.themen[i]['name'],m) )
                self.showProgress.emit( i*5+s, len(alkisplugin.themen)*5 )
                QCoreApplication.processEvents()

        def setStricharten(self, db, sym, sn, c, outline):
            lqry = QSqlQuery(db)

            if hasattr(QgsMarkerLineSymbolLayerV2, "setOffsetAlongLine"):
                if lqry.exec_( "SELECT abschluss,scheitel,coalesce(strichstaerke/100,0),coalesce(laenge/100,0),coalesce(einzug/100,0),abstand"
                               " FROM alkis_linie"
                               " LEFT OUTER JOIN alkis_stricharten_i ON alkis_linie.strichart=alkis_stricharten_i.stricharten"
                               " LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
                               " WHERE alkis_linie.signaturnummer='%s'" % sn ):
                    stricharten = []

                    maxStrichstaerke = -1

                    while lqry.next():
                        abschluss, scheitel, strichstaerke, laenge, einzug, abstaende = \
                            lqry.value(0), lqry.value(1), float(lqry.value(2)), \
                            float(lqry.value(3)), float(lqry.value(4)), lqry.value(5)

                        if strichstaerke > maxStrichstaerke:
                            maxStrichstaerke = strichstaerke

                        if abstaende:
                            if abstaende.startswith("{") and abstaende.endswith("}"):
                                abstaende = map ( lambda x: float(x)/100, abstaende[1:-1].split(",") )
                            else:
                                abstaende = [ float(abstaende)/100 ]
                        else:
                            abstaende = []

                        gesamtl = 0
                        for abstand in abstaende:
                            gesamtl += laenge + abstand

                        stricharten.append( [ abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl ] )

                    gesamtl0 = None
                    leinzug = None
                    for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl in stricharten:
                        if gesamtl0 is None:
                            gesamtl0 = gesamtl
                        elif gesamtl0 <> gesamtl:
                            raise BaseException( u"Signaturnummer %s: Stricharten nicht gleich lang (%lf vs %lf)" % (sn, gesamtl0, gesamtl) )

                        if laenge>0:
                            if leinzug is None:
                                leinzug = einzug
                            elif leinzug<>einzug:
                                #raise BaseException( u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug) )
                                logMessage( u"Signaturnummer %s: Linienstricharten mit unterschiedlichen Einzügen (%lf vs %lf)" % (sn, leinzug, einzug) )
                                return False

                    for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, gesamtl in stricharten:
                        if abstaende and laenge==0:
                            # Marker line
                            if leinzug:
                                if einzug > leinzug:
                                    einzug -= leinzug
                                else:
                                    einzug += gesamtl - leinzug

                            for abstand in abstaende:
                                sl = QgsMarkerLineSymbolLayerV2( False, gesamtl )
                                sl.setPlacement( QgsMarkerLineSymbolLayerV2.Interval )
                                sl.setIntervalUnit( QgsSymbolV2.MapUnit )
                                sl.setOffsetAlongLine( einzug )
                                sl.setOffsetAlongLineUnit( QgsSymbolV2.MapUnit )
                                sl.subSymbol().symbolLayer(0).setSize( strichstaerke )
                                sl.subSymbol().symbolLayer(0).setSizeUnit( QgsSymbolV2.MapUnit )
                                sl.subSymbol().symbolLayer(0).setOutlineStyle( Qt.NoPen )
                                sl.subSymbol().symbolLayer(0).setColor( c )
                                sl.setWidth( strichstaerke )
                                sl.setWidthUnit( QgsSymbolV2.MapUnit )
                                einzug += abstand
                                sym.appendSymbolLayer( sl )
                        else:
                            # Simple line
                            sl = QgsSimpleLineSymbolLayerV2( c, strichstaerke, Qt.SolidLine )

                            if abstaende:
                                dashvector = []
                                for abstand in abstaende:
                                    dashvector.extend( [laenge, abstand] )
                                sl.setUseCustomDashPattern( True )
                                sl.setCustomDashVector( dashvector )
                                sl.setCustomDashPatternUnit( QgsSymbolV2.MapUnit )

                            sl.setPenCapStyle( Qt.FlatCap if abschluss == "Abgeschnitten" else Qt.RoundCap )
                            sl.setPenJoinStyle( Qt.MiterJoin if abschluss == "Spitz" else Qt.RoundJoin )
                            sl.setWidth( strichstaerke )
                            sl.setWidthUnit( QgsSymbolV2.MapUnit )

                            sym.appendSymbolLayer( sl )

                    if sym.symbolLayerCount() == 1:
                        logMessage( u"Signaturnummer %s: Keine Linienarten erzeugt." % sn )
                        return False

                    if outline:
                        sym.deleteSymbolLayer(0)
                    else:
                        sl = QgsSimpleLineSymbolLayerV2( QColor( 0, 0, 0, 0 ) if hasattr(QgsMapRenderer, "BlendSource") else Qt.white, maxStrichstaerke*1.01, Qt.SolidLine )
                        sl.setWidthUnit( QgsSymbolV2.MapUnit )
                        sym.changeSymbolLayer(0, sl)
                else:
                    logMessage( u"Signaturnummer %s: Linienarten konnten nicht abgefragt werden.\nSQL:%s\nFehler:%s" % (sn, lqry.lastQuery(), lqry.lastError().text() ) )
                    return False
            elif lqry.exec_( "SELECT coalesce(strichstaerke/100,0)"
                             " FROM alkis_linie"
                             " LEFT OUTER JOIN alkis_stricharten_i ON alkis_linie.strichart=alkis_stricharten_i.stricharten"
                             " LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
                             " WHERE alkis_linie.signaturnummer='%s'" % sn ) and lqry.next():

                if sym.type() == QgsSymbolV2.Fill:
                    sym.changeSymbolLayer( 0, QgsSimpleFillSymbolLayerV2( c, Qt.NoBrush, c, Qt.SolidLine, float(lqry.value(0)) ) )
                else:
                    sym.setWidth( float(lqry.value(0)) )
                    sym.setColor( c )

                sym.setOutputUnit( QgsSymbolV2.MapUnit )
            else:
                logMessage( u"Signaturnummer %s: Linienarten konnten nicht abgefragt werden.\nSQL:%s\nFehler:%s" % (sn, lqry.lastQuery(), lqry.lastError().text() ) )
                return False

            return True

        def alkisimport(self):
                (db,conninfo) = self.opendb()
                if db is None:
                        return

                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                modelle = s.value( "modellarten", ['DLKM','DKKM1000'] )

                self.iface.mapCanvas().setRenderFlag( False )

                qry = QSqlQuery(db)

                qs = QSettings( "QGIS", "QGIS2" )
                svgpaths = qs.value( "svg/searchPathsForSVG", "", type=str ).split("|")
                svgpath = os.path.abspath( os.path.join( BASEDIR, "svg" ) )
                if not svgpath.upper() in map(unicode.upper, svgpaths):
                        svgpaths.append( svgpath )
                        qs.setValue( "svg/searchPathsForSVG", u"|".join( svgpaths ) )

                self.alkisGroup = self.iface.legendInterface().addGroup( "ALKIS", False )

                markerGroup = self.iface.legendInterface().addGroup( "Markierungen", False, self.alkisGroup )

                self.showProgress.connect( self.iface.mainWindow().showProgress )
                self.showStatusMessage.connect( self.iface.mainWindow().showStatusMessage )

                if qry.exec_( "SELECT find_srid('','po_points', 'point')" ) and qry.next():
                        epsg = qry.value(0)
                        if epsg>100000:
                                if qry.exec_( "SELECT proj4text FROM spatial_ref_sys WHERE srid=%d" % epsg ) and qry.next():
                                        crs = QgsCoordinateReferenceSystem()
                                        crs.createFromProj4( qry.value(0) )
                                        if crs.authid() == "":
                                                crs.saveAsUserCRS( "ALKIS %d" % epsg )
                                else:
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                else:
                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                        return

                nGroups = 0
                iThema = -1
                for d in alkisplugin.themen:
                        iThema += 1
                        t = d['name']
                        thisGroup = self.iface.legendInterface().addGroup( t, False, self.alkisGroup )
                        nLayers = 0

                        qDebug( u"Thema: %s" % t )

                        where = "thema='%s'" % t

                        if len(modelle)>0:
                            where += " AND modell && ARRAY['%s']::varchar[]" % "','".join( modelle )

                        self.progress(iThema, u"Flächen", 0)

                        sql = (u"SELECT signaturnummer,r,g,b FROM alkis_flaechen"
                               u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                               u" WHERE EXISTS (SELECT * FROM po_polygons WHERE %s"
                               u" AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer)"
                               u" ORDER BY darstellungsprioritaet DESC") % where
                        #qDebug( u"SQL: %s" % sql )
                        if qry.exec_( sql ):
                                r = QgsCategorizedSymbolRendererV2( "sn_flaeche" )
                                r.deleteAllCategories()

                                n = 0
                                while qry.next():
                                        sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )

                                        sn = qry.value(0)
                                        sym.setColor( QColor( int(qry.value(1)), int(qry.value(2)), int(qry.value(3)) ) )

                                        r.addCategory( QgsRendererCategoryV2( sn, sym, self.categoryLabel(d, sn) ) )
                                        n += 1

                                if n>0:
                                        layer = self.iface.addVectorLayer(
                                                u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=%d table=po_polygons (polygon) sql=%s" % (conninfo, epsg, where),
                                                u"Flächen (%s)" % t,
                                                "postgres" )
                                        layer.setReadOnly()
                                        layer.setRendererV2( r )
                                        self.setScale( layer, d['area'] )
                                        self.iface.legendInterface().refreshLayerSymbology( layer )
                                        self.iface.legendInterface().moveLayer( layer, thisGroup )
                                        nLayers += 1
                                else:
                                        del r
                        else:
                                QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                break

                        self.progress(iThema, "Grenzen", 1)

                        sql = (u"SELECT"
                               u" signaturnummer,r,g,b"
                               u" FROM alkis_linien"
                               u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
                               u" WHERE EXISTS (SELECT * FROM po_polygons WHERE %s"
                               u" AND po_polygons.sn_randlinie=alkis_linien.signaturnummer)"
                               u" ORDER BY darstellungsprioritaet" ) % where
                        #qDebug( u"SQL: %s" % sql )
                        if qry.exec_(sql):
                                r = QgsCategorizedSymbolRendererV2( "sn_randlinie" )
                                r.deleteAllCategories()

                                n = 0
                                while qry.next():
                                        sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )
                                        sn = qry.value(0)

                                        if self.setStricharten( db, sym, sn, QColor( int(qry.value(1)), int(qry.value(2)), int(qry.value(3)) ), True ):
                                            r.addCategory( QgsRendererCategoryV2( sn, sym, self.categoryLabel(d, sn) ) )
                                            n += 1

                                if n>0:
                                        layer = self.iface.addVectorLayer(
                                                u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=%d table=po_polygons (polygon) sql=%s" % (conninfo, epsg, where),
                                                u"Grenzen (%s)" % t,
                                                "postgres" )
                                        layer.setReadOnly()
                                        layer.setRendererV2( r )
                                        if hasattr(QgsMapRenderer, "BlendSource"):
                                                layer.setFeatureBlendMode( QPainter.CompositionMode_Source )
                                        self.setScale( layer, d['outline'] )
                                        self.iface.legendInterface().refreshLayerSymbology( layer )
                                        self.iface.legendInterface().moveLayer( layer, thisGroup )
                                        nLayers += 1
                                else:
                                        del r
                        else:
                                QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                break

                        self.progress(iThema, "Linien", 2)

                        sql = (u"SELECT"
                               u" signaturnummer,r,g,b"
                               u" FROM alkis_linien"
                               u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
                               u" WHERE EXISTS (SELECT * FROM po_lines WHERE %s"
                               u" AND po_lines.signaturnummer=alkis_linien.signaturnummer)"
                               u" ORDER BY darstellungsprioritaet ASC" ) % where
                        #qDebug( u"SQL: %s" % sql )
                        if qry.exec_( sql ):
                                r = QgsCategorizedSymbolRendererV2( "signaturnummer" )
                                r.setUsingSymbolLevels( True )
                                r.deleteAllCategories()

                                n = 0
                                while qry.next():
                                        sym = QgsSymbolV2.defaultSymbol( QGis.Line )
                                        sn = qry.value(0)

                                        if self.setStricharten( db, sym, sn, QColor( int(qry.value(1)), int(qry.value(2)), int(qry.value(3)) ), False ):
                                            for i in range(0,sym.symbolLayerCount()):
                                                sym.symbolLayer(i).setRenderingPass(n)

                                            r.addCategory( QgsRendererCategoryV2( sn, sym, self.categoryLabel(d, sn) ) )
                                            n += 1

                                if n>0:
                                        layer = self.iface.addVectorLayer(
                                                        u"%s estimatedmetadata=true key='ogc_fid' type=MULTILINESTRING srid=%d table=po_lines (line) sql=%s" % (conninfo, epsg, where),
                                                        u"Linien (%s)" % t,
                                                        "postgres" )
                                        layer.setReadOnly()
                                        layer.setRendererV2( r )
                                        if hasattr(QgsMapRenderer, "BlendSource"):
                                                layer.setFeatureBlendMode( QPainter.CompositionMode_Source )
                                        layer.setFeatureBlendMode( QPainter.CompositionMode_Source )
                                        self.setScale( layer, d['line'] )
                                        self.iface.legendInterface().refreshLayerSymbology( layer )
                                        self.iface.legendInterface().moveLayer( layer, thisGroup )
                                        nLayers += 1
                                else:
                                        del r
                        else:
                                QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                break

                        self.progress(iThema, "Punkte", 3)

                        sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE %s" % where
                        #qDebug( u"SQL: %s" % sql )
                        if qry.exec_( sql ):
                                r = QgsCategorizedSymbolRendererV2( "signaturnummer" )
                                r.deleteAllCategories()
                                r.setRotationField( "drehwinkel_grad" )

                                n = 0
                                while qry.next():
                                        sn = qry.value(0)
                                        svg = "alkis%s.svg" % sn
                                        if alkisplugin.exts.has_key(sn):
                                                x = ( alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx'] ) / 2
                                                y = ( alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy'] ) / 2
                                                w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
                                                h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']
                                        else:
                                                x = 0
                                                y = 0
                                                w = 1
                                                h = 1

                                        symlayer = QgsSvgMarkerSymbolLayerV2( svg )
                                        symlayer.setOutputUnit( QgsSymbolV2.MapUnit )
                                        qDebug( u"symlayer.setSize %s:%f" % (sn, w) )
                                        symlayer.setSize( w )
                                        symlayer.setOffset( QPointF( -x, -y ) )

                                        sym = QgsSymbolV2.defaultSymbol( QGis.Point )
                                        sym.setOutputUnit( QgsSymbolV2.MapUnit )
                                        qDebug( u"sym.setSize %s:%f" % (sn, w) )
                                        sym.setSize( w )

                                        sym.changeSymbolLayer( 0, symlayer )
                                        r.addCategory( QgsRendererCategoryV2( "%s" % sn, sym, self.categoryLabel(d, sn) ) )
                                        n += 1

                                qDebug( u"classes: %d" % n )
                                if n>0:
                                        layer = self.iface.addVectorLayer(
                                                        u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=%d table=\"(SELECT ogc_fid,gml_id,thema,layer,signaturnummer,-drehwinkel_grad AS drehwinkel_grad,point FROM po_points WHERE %s)\" (point) sql=" % (conninfo, epsg, where),
                                                        u"Punkte (%s)" % t,
                                                        "postgres" )
                                        layer.setReadOnly()
                                        layer.setRendererV2( r )
                                        self.setScale( layer, d['point'] )
                                        self.iface.legendInterface().refreshLayerSymbology( layer )
                                        self.iface.legendInterface().moveLayer( layer, thisGroup )
                                        nLayers += 1
                                else:
                                        del r
                        else:
                                QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                break

                        n = 0
                        labelGroup = -1
                        for i in range(2):
                                geom = "point" if i==0 else "line"
                                geomtype = "MULTIPOINT" if i==0 else "MULTILINESTRING"

                                if not qry.exec_( "SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL" % (where,geom) ):
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                        continue

                                self.progress(iThema, "Beschriftungen (%d)" % (i+1), 4+i)

                                if not qry.next() or int(qry.value(0))==0:
                                        continue

                                if n==1:
                                        labelGroup = self.iface.legendInterface().addGroup( "Beschriftungen", False, thisGroup )
                                        self.iface.legendInterface().moveLayer( layer, labelGroup )

                                uri = (
                                        u"{0} estimatedmetadata=true key='ogc_fid' type={1} srid={2} table="
                                        u"\"("
                                        u"SELECT"
                                        u" ogc_fid"
                                        u",(size_umn*0.0254)::float8 AS tsize"
                                        u",text"
                                        u",CASE"
                                        u" WHEN horizontaleausrichtung='linksbündig' THEN 'Left'"
                                        u" WHEN horizontaleausrichtung='zentrisch' THEN 'Center'"
                                        u" WHEN horizontaleausrichtung='rechtsbündig' THEN 'Right'"
                                        u" END AS halign"
                                        u",CASE"
                                        u" WHEN vertikaleausrichtung='oben' THEN 'Top'"
                                        u" WHEN vertikaleausrichtung='Mitte' THEN 'Half'"
                                        u" WHEN vertikaleausrichtung='Basis' THEN 'Bottom'"
                                        u" END AS valign"
                                        u",'Arial'::text AS family"
                                        u",CASE WHEN font_umn LIKE '%italic%' THEN 1 ELSE 0 END AS italic"
                                        u",CASE WHEN font_umn LIKE '%bold%' THEN 1 ELSE 0 END AS bold"
                                        u",fontsperrung"
                                        u",split_part(color_umn,' ',1) AS r"
                                        u",split_part(color_umn,' ',2) AS g"
                                        u",split_part(color_umn,' ',3) AS b"
                                        u",{3}"
                                        u"{6}"
                                        u" FROM po_labels"
                                        u" WHERE {4}"
                                        u")\" ({5}) sql="
                                        ).format(
                                            conninfo, geomtype, epsg,
                                            u"point,st_x(point) AS tx,st_y(point) AS ty,drehwinkel_grad AS tangle" if geom=="point" else "line",
                                            where, geom, "" if len(modelle)==0 else ",modell"
                                        )

                                qDebug( u"URI: %s" % uri )

                                layer = self.iface.addVectorLayer( uri, u"Beschriftungen (%s)" % t, "postgres" )
                                layer.setReadOnly()

                                self.setScale( layer, d['label'] )

                                sym = QgsSymbolV2.defaultSymbol( QGis.Point if geom=="point" else QGis.Line )
                                if geom=="point":
                                    sym.setSize( 0.0 )
                                else:
                                    sym.changeSymbolLayer( 0, QgsSimpleLineSymbolLayerV2( Qt.black, 0.0, Qt.NoPen ) )
                                layer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
                                self.iface.legendInterface().refreshLayerSymbology( layer )
                                self.iface.legendInterface().moveLayer( layer, thisGroup )

                                lyr = QgsPalLayerSettings()
                                lyr.fieldName = "text"
                                lyr.isExpression = False
                                lyr.enabled = True
                                lyr.fontSizeInMapUnits = True
                                lyr.textFont.setPointSizeF( 2.5 )
                                lyr.textFont.setFamily( "Arial" )
                                lyr.bufferSizeInMapUnits = True
                                lyr.bufferSize = 0.25
                                lyr.displayAll = True
                                lyr.upsidedownLabels = QgsPalLayerSettings.ShowAll
                                lyr.scaleVisibility = True
                                if geom == "point":
                                    lyr.placement = QgsPalLayerSettings.AroundPoint
                                else:
                                    lyr.placement = QgsPalLayerSettings.Curved
                                    lyr.placementFlags = QgsPalLayerSettings.AboveLine

                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Size, True, False, "", "tsize" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Family, True, False, "", "family" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Italic, True, False, "", "italic" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Bold, True, False, "", "bold" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Hali, True, False, "", "halign" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Vali, True, False, "", "valign" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.Color, True, True, "color_rgb(r,g,b)", "" )
                                lyr.setDataDefinedProperty( QgsPalLayerSettings.FontLetterSpacing, True, False, "", "fontsperrung" )
                                if geom == "point":
                                    lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionX, True, False, "", "tx" )
                                    lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionY, True, False, "", "ty" )
                                    lyr.setDataDefinedProperty( QgsPalLayerSettings.Rotation, True, False, "", "tangle" )
                                lyr.writeToLayer( layer )

                                self.iface.legendInterface().refreshLayerSymbology( layer )

                                if labelGroup!=-1:
                                        self.iface.legendInterface().moveLayer( layer, labelGroup )

                                n += 1
                                nLayers += 1

                        if nLayers > 0:
                                self.iface.legendInterface().setGroupExpanded( thisGroup, False )
                                nGroups += 1
                        else:
                                self.iface.legendInterface().removeGroup( thisGroup )

                if nGroups > 0:
                        self.iface.legendInterface().setGroupExpanded( self.alkisGroup, False )
                        self.iface.legendInterface().setGroupVisible( self.alkisGroup, False )

                        self.pointMarkerLayer = self.iface.addVectorLayer(
                                                u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=%d table=po_labels (point) sql=false" % (conninfo,epsg),
                                                u"Punktmarkierung",
                                                "postgres" )

                        sym = QgsSymbolV2.defaultSymbol( QGis.Point )
                        sym.setColor( Qt.yellow )
                        sym.setSize( 20.0 )
                        sym.setOutputUnit( QgsSymbolV2.MM )
                        sym.setAlpha( 0.5 )
                        self.pointMarkerLayer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
                        self.iface.legendInterface().moveLayer( self.pointMarkerLayer, markerGroup )

                        self.lineMarkerLayer = self.iface.addVectorLayer(
                                                u"%s estimatedmetadata=true key='ogc_fid' type=MULTILINESTRING srid=%d table=po_labels (line) sql=false" % (conninfo,epsg),
                                                u"Linienmarkierung",
                                                "postgres" )

                        sym = QgsLineSymbolV2()
                        sym.setColor( Qt.yellow )
                        sym.setAlpha( 0.5 )
                        sym.setWidth( 2 )
                        self.lineMarkerLayer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
                        self.iface.legendInterface().moveLayer( self.lineMarkerLayer, markerGroup )

                        self.areaMarkerLayer = self.iface.addVectorLayer(
                                                u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=%d table=po_polygons (polygon) sql=false" % (conninfo,epsg),
                                                u"Flächenmarkierung",
                                                "postgres" )

                        sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )
                        sym.setColor( Qt.yellow )
                        sym.setAlpha( 0.5 )
                        self.areaMarkerLayer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
                        self.iface.legendInterface().moveLayer( self.areaMarkerLayer, markerGroup )

                        QgsProject.instance().writeEntry( "alkis", "/pointMarkerLayer", self.pointMarkerLayer.id() )
                        QgsProject.instance().writeEntry( "alkis", "/lineMarkerLayer", self.lineMarkerLayer.id() )
                        QgsProject.instance().writeEntry( "alkis", "/areaMarkerLayer", self.areaMarkerLayer.id() )

                        restrictedLayers, ok = QgsProject.instance().readListEntry( "WMSRestrictedLayers", "/", [] )

                        for l in [u'Punktmarkierung', u'Linienmarkierung', u'Flächenmarkierung']:
                            try:
                                restrictedLayers.index(l)
                            except:
                                restrictedLayers.append(l)

                        QgsProject.instance().writeEntry( "WMSRestrictedLayers", "/", restrictedLayers )
                else:
                        self.iface.legendInterface().removeGroup( self.alkisGroup )

                self.iface.mapCanvas().setRenderFlag( True )

        def setPointInfoTool(self):
                self.iface.mapCanvas().setMapTool( self.pointInfoTool )

        def setPolygonInfoTool(self):
                self.iface.mapCanvas().setMapTool( self.polygonInfoTool )

        def setQueryOwnerTool(self):
                self.iface.mapCanvas().setMapTool( self.queryOwnerInfoTool )

        def register(self):
                edbsgen = self.iface.mainWindow().findChild( QObject, "EDBSQuery" )
                if edbsgen:
                        if edbsgen.received.connect( self.message ):
                                qDebug( u"connected" )
                        else:
                                qDebug( u"not connected" )
                else:
                        return False

        def opendb(self,conninfo=None):
                if not conninfo:
                        s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )

                        service = s.value( "service", "" )
                        host = s.value( "host", "" )
                        port = s.value( "port", "5432" )
                        dbname = s.value( "dbname", "" )
                        uid = s.value( "uid", "" )
                        pwd = s.value( "pwd", "" )

                        uri = QgsDataSourceURI()
                        if service:
                                uri.setConnection( service, dbname, uid, pwd )
                        else:
                                uri.setConnection( host, port, dbname, uid, pwd )

                        conninfo0 = uri.connectionInfo()
                else:
                        uid = None
                        pwd = None

                QSqlDatabase.removeDatabase( "ALKIS" )
                db = QSqlDatabase.addDatabase( "QPSQL", "ALKIS" )
                db.setConnectOptions( conninfo0 )
                conninfo = conninfo0

                if not db.open() and qgisAvailable:
                        uri = QgsDataSourceURI()
                        if service:
                                uri.setConnection( service, dbname, uid, pwd )
                        else:
                                uri.setConnection( host, port, dbname, uid, pwd )

                        while not db.open():
                                (ok, uid, pwd) = QgsCredentials.instance().get( conninfo0, uid, pwd, u"Datenbankverbindung schlug fehl [%s]" % db.lastError().text() )
                                if not ok:
                                        return (None,None)

                                uri.setUsername(uid)
                                uri.setPassword(pwd)
                                conninfo = uri.connectionInfo()
                                db.setConnectOptions( conninfo )

                        QgsCredentials.instance().put( conninfo0, uid, pwd )
                        conninfo = conninfo0

                return (db,conninfo)

        def message(self, msg):
                if msg.startswith("ALKISDRAW"):
                        (prefix,hatch,window,qry) = msg.split(' ', 3)
#                       qDebug( u"prefix:%s hatch:%s window:%s qry:%s" % (prefix,hatch,window,qry) )
                        if qry.startswith("ids:"):
                                self.highlight( "gml_id in (%s)" % qry[4:], True )
                        elif qry.startswith("where:"):
                                self.highlight( qry[6:], True )
                        elif qry.startswith("select "):
                                self.highlight( "gml_id in (%s)" % qry, True )
#                       else:
#                               qDebug( u"ALKIS: Ignorierte Nachricht:%s" % msg )
#               else:
#                       qDebug( u"ALKIS: Ignorierte Nachricht:%s" % msg )

        def clearHighlight(self):
                if not self.pointMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/pointMarkerLayer" )
                        if ok:
                                self.pointMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.pointMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Punktmarkierungslayer nicht gefunden!\n" )
                        return

                self.pointMarkerLayer.setSubsetString( "false" )

                if not self.areaMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.areaMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )
                        return

                self.areaMarkerLayer.setSubsetString( "false" )
                currentLayer = self.iface.activeLayer()
                self.iface.mapCanvas().refresh()

        def highlight(self, where, zoomTo=False):
                fs = []

                if not self.areaMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.areaMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )
                        return fs

                (db,conninfo) = self.opendb()
                if db is None:
                        return fs

                qry = QSqlQuery(db)


                if not qry.exec_(
                        u"SELECT "
                        u"gml_id"
                        u",to_char(land::int,'fm00') || to_char(gemarkungsnummer::int,'fm0000') || "
                        u"'-' || to_char(coalesce(flurnummer,0),'fm000') ||"
                        u"'-' || to_char(zaehler,'fm00000') || '/' || CASE WHEN gml_id LIKE 'DESN%%' THEN substring(flurstueckskennzeichen,15,4) ELSE to_char(coalesce(nenner::int,0),'fm000') END"
                        u" FROM ax_flurstueck"
                        u" WHERE endet IS NULL"
                        u" AND (%s)" % where
                        ):
                        QMessageBox.critical( None, "Fehler", u"Konnte Abfrage nicht ausführen.\nSQL:%s\nFehler:%s" % ( qry.lastQuery(), qry.lastError().text() ) )
                        return fs

                qDebug( qry.lastQuery() )

                while qry.next():
                        fs.append( { 'gmlid': qry.value(0), 'flsnr':qry.value(1) } )

                if len(fs)==0:
                        return fs


                gmlids = []
                for e in fs:
                        gmlids.append( e['gmlid'] )

                self.areaMarkerLayer.setSubsetString( "layer='ax_flurstueck' AND gml_id IN ('" + "','".join( gmlids ) + "')" )

                currentLayer = self.iface.activeLayer()

                self.iface.mapCanvas().refresh()

                if zoomTo and qry.exec_( u"SELECT find_srid('','ax_flurstueck', 'wkb_geometry')" ) and qry.next():
                    crs = qry.value(0)

                    if qry.exec_( u"SELECT st_extent(wkb_geometry) FROM ax_flurstueck WHERE gml_id IN ('" + "','".join( gmlids ) + "')" ) and qry.next():
                        self.zoomToExtent( qry.value(0), crs )

                return fs

        def zoomToExtent( self, bb, epsg ):
                bb = bb[4:-1]
                (p0,p1) = bb.split(",")
                (x0,y0) = p0.split(" ")
                (x1,y1) = p1.split(" ")
                qDebug( u"x0:%s y0:%s x1:%s y1:%s" % (x0, y0, x1, y1) )
                rect = QgsRectangle( float(x0), float(y0), float(x1), float(y1) )

                c = self.iface.mapCanvas()
                if c.hasCrsTransformEnabled():
                    try:
                      t = QgsCoordinateTransform( QgsCoordinateReferenceSystem(epsg), c.mapSettings().destinationCrs() )
                    except:
                      t = QgsCoordinateTransform( QgsCoordinateReferenceSystem(epsg), c.mapRenderer().destinationCrs() )
                    rect = t.transform( rect )

                qDebug( u"rect:%s" % rect.toString() )

                self.iface.mapCanvas().setExtent( rect )
                self.iface.mapCanvas().refresh()


        def mapfile(self,conninfo=None,dstfile=None):
                (db,conninfo) = self.opendb(conninfo)
                if db is None:
                        return

                if dstfile is None:
                        dstfile = QFileDialog.getSaveFileName( None, "Mapfiledateinamen angeben", "", "UMN-Mapdatei (*.map)" )
                        if dstfile is None:
                                return

                if self.iface:
                        self.showProgress.connect( self.iface.mainWindow().showProgress )
                        self.showStatusMessage.connect( self.iface.mainWindow().showStatusMessage )

                mapobj = mapscript.mapObj()
                mapobj.name = "ALKIS"
                mapobj.setFontSet( os.path.abspath( os.path.join( BASEDIR, "fonts", "fonts.txt" ) ) )

                mapobj.outputformat.driver = "GD/PNG"
                mapobj.outputformat.imagemode = mapscript.MS_IMAGEMODE_RGB

                mapobj.maxsize = 20480;
                mapobj.web.metadata.set( u"wms_title", "ALKIS" )
                mapobj.web.metadata.set( u"wms_enable_request", "*" )
                mapobj.web.metadata.set( u"wfs_enable_request", "*" )
                mapobj.web.metadata.set( u"ows_enable_request", "*" )

                qry = QSqlQuery(db)

                if qry.exec_( "SELECT st_extent(wkb_geometry),find_srid('','ax_flurstueck','wkb_geometry') FROM ax_flurstueck" ) and qry.next():
                        bb = qry.value(0)[4:-1]
                        (p0,p1) = bb.split(",")
                        (x0,y0) = p0.split(" ")
                        (x1,y1) = p1.split(" ")
                        epsg = qry.value(1)
                        mapobj.setProjection( "init=epsg:%d" % epsg )
                        mapobj.setExtent( float(x0), float(y0), float(x1), float(y1) )

                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                modelle = s.value( "modellarten", ['DLKM','DKKM1000'] )

                missing = {}
                symbols = {}

                nGroups = 0
                iThema = -1
                iLayer = 0
                for d in alkisplugin.themen:
                        iThema += 1
                        thema = d['name']

                        if not d.has_key('filter'):
                                d['filter'] = [ { 'name':None, 'filter': None } ]

                        tgroup = []

                        nLayers = 0

                        qDebug( u"Thema: %s" % thema )

                        for f in d['filter']:
                                name = f.get('name', thema)
                                tname = thema

                                where = "thema='%s'" % thema

                                if len(modelle)>0:
                                    where += " AND modell && ARRAY['%s']::varchar[]" % "','".join( modelle )

                                if f.get('name',None):
                                        tname += " / " + f['name']

                                if f.get('filter',None):
                                        where += " AND (%s)" % f['filter']

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

                                sql = u"SELECT find_srid('','po_points', 'point')"
                                if qry.exec_( sql ) and qry.next():
                                        epsg = qry.value(0)
                                else:
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), sql) )
                                        break

                                layer = mapscript.layerObj(mapobj)
                                layer.name = "l%d" % iLayer
                                iLayer += 1

                                layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_flaeche AS signaturnummer FROM po_polygons WHERE %s AND NOT sn_flaeche IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg) ).encode("utf-8")
                                layer.classitem = "signaturnummer"
                                layer.setProjection( "init=epsg:%d" % epsg )
                                layer.connectiontype = mapscript.MS_POSTGIS
                                layer.connection = conninfo
                                layer.symbolscaledenom = 1000
                                layer.setProcessing( "CLOSE_CONNECTION=DEFER" )
                                layer.type = mapscript.MS_LAYER_POLYGON
                                layer.sizeunits = mapscript.MS_INCHES
                                layer.status = mapscript.MS_DEFAULT
                                layer.tileitem = None
                                layer.setMetaData( u"norGIS_label", (u"ALKIS / %s / Flächen" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_layer_group", (u"/%s" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_title", u"Flächen".encode("utf-8") )
                                layer.setMetaData( u"wfs_title", u"Flächen".encode("utf-8") )
                                layer.setMetaData( u"gml_geom_type", "multipolygon" )
                                layer.setMetaData( u"gml_geometries", "geom" )
                                layer.setMetaData( u"gml_featureid", "ogc_fid" )
                                layer.setMetaData( u"gml_include_items", "all" )
                                layer.setMetaData( u"wms_srs", alkisplugin.defcrs )
                                layer.setMetaData( u"wfs_srs", alkisplugin.defcrs )
                                self.setUMNScale( layer, d['area'] )

                                sql = (u"SELECT"
                                       u" signaturnummer,umn,darstellungsprioritaet,alkis_flaechen.name"
                                       u" FROM alkis_flaechen"
                                       u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                                       u" WHERE EXISTS (SELECT * FROM po_polygons WHERE %s AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer)"
                                       u" ORDER BY darstellungsprioritaet" ) % where
                                #qDebug( "SQL: %s" % sql )
                                if qry.exec_( sql ):
                                        sprio = 0
                                        nclasses = 0
                                        minprio = None
                                        maxprio = None

                                        while qry.next():
                                                sn = qry.value( 0 )
                                                color = qry.value( 1 )
                                                prio = qry.value( 2 )
                                                names = qry.value( 3 )

                                                cl = mapscript.classObj(layer)
                                                cl.setExpression( sn )
                                                cl.name = d['classes'].get(sn, "(%s)" % sn).encode("utf-8")

                                                if not self.insertStylesFromBlock( layerclass=cl, map=mapobj, name="alkis%s" % sn, color=color ):
                                                        layer.removeClass( layer.numclasses - 1 )
                                                        missing["alkis%s" % sn] = 1
                                                        continue

                                                nclasses += 1
                                                sprio += prio
                                                if not minprio or prio < minprio:
                                                        minprio = prio
                                                if not maxprio or prio > maxprio:
                                                        maxprio = prio

                                else:
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                        break

                                if layer.numclasses > 0:
                                        layer.setMetaData( "norGIS_zindex", "%d" % (sprio / nclasses) )
                                        layer.setMetaData( "norGIS_minprio", "%d" % minprio )
                                        layer.setMetaData( "norGIS_maxprio", "%d" % maxprio )

                                        group.append( layer.name )
                                else:
                                        mapobj.removeLayer( layer.index )


                                self.progress(iThema, "Grenzen", 1)

                                #
                                # 1.2 Randlinien
                                #
                                layer = mapscript.layerObj(mapobj)
                                layer.name = "l%d" % iLayer
                                iLayer += 1
                                layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_randlinie AS signaturnummer FROM po_polygons WHERE %s AND NOT polygon IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg) ).encode("utf-8")
                                layer.classitem = "signaturnummer"
                                layer.setProjection( "init=epsg:%d" % epsg )
                                layer.connection = conninfo
                                layer.connectiontype = mapscript.MS_POSTGIS
                                layer.setProcessing( "CLOSE_CONNECTION=DEFER" )
                                #layer.symbolscaledenom = 1000
                                #layer.sizeunits = mapscript.MS_INCHES
                                layer.type = mapscript.MS_LAYER_LINE
                                layer.status = mapscript.MS_DEFAULT
                                layer.tileitem = None
                                layer.setMetaData( "norGIS_label", (u"ALKIS / %s / Grenzen" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_layer_group", (u"/%s" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_title", u"Grenzen" )
                                layer.setMetaData( u"wfs_title", u"Grenzen" )
                                layer.setMetaData( u"gml_geom_type", "multiline" )
                                layer.setMetaData( u"gml_geometries", "geom" )
                                layer.setMetaData( u"gml_featureid", "ogc_fid" )
                                layer.setMetaData( u"gml_include_items", "all" )
                                layer.setMetaData( u"wms_srs", alkisplugin.defcrs )
                                layer.setMetaData( u"wfs_srs", alkisplugin.defcrs )
                                self.setUMNScale( layer, d['outline'] )

                                sql = (u"SELECT"
                                       u" signaturnummer,umn,darstellungsprioritaet,alkis_linien.name"
                                       u" FROM alkis_linien"
                                       u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
                                       u" WHERE EXISTS (SELECT * FROM po_polygons WHERE %s AND po_polygons.sn_randlinie=alkis_linien.signaturnummer)"
                                       u" ORDER BY darstellungsprioritaet" ) % where
                                #qDebug( "SQL: %s" % sql )
                                if qry.exec_( sql ):
                                        sprio = 0
                                        nclasses = 0
                                        minprio = None
                                        maxprio = None

                                        while qry.next():
                                                sn = qry.value( 0 )
                                                color  = qry.value( 1 )
                                                prio = qry.value( 2 )
                                                names = qry.value( 3 )

                                                cl = mapscript.classObj( layer )
                                                cl.setExpression( sn )
                                                cl.name = d['classes'].get(sn, "(%s)" % sn).encode("utf-8")

                                                if not self.insertStylesFromBlock(layerclass=cl, map=mapobj, name="alkis%s" % sn, color=color ):
                                                        layer.removeClass( layer.numclasses-1 )

                                                nclasses += 1
                                                sprio += prio
                                                if not minprio or prio < minprio:
                                                        minprio = prio
                                                if not maxprio or prio > maxprio:
                                                        maxprio = prio

                                else:
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                        break

                                if layer.numclasses > 0:
                                        layer.setMetaData( "norGIS_zindex", "%d" % (sprio / nclasses) )
                                        layer.setMetaData( "norGIS_minprio", "%d" % minprio )
                                        layer.setMetaData( "norGIS_maxprio", "%d" % maxprio )

                                        group.append( layer.name )
                                else:
                                        mapobj.removeLayer( layer.index )

                                self.progress(iThema, "Linien", 2)

                                #
                                # 2 Linien
                                #
                                layer = mapscript.layerObj(mapobj)
                                layer.name = "l%d" % iLayer
                                iLayer += 1
                                layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,line AS geom,signaturnummer FROM po_lines WHERE %s AND NOT line IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg)).encode("utf-8")
                                layer.classitem = "signaturnummer"
                                layer.setProjection( "init=epsg:%d" % epsg )
                                layer.connection = conninfo
                                layer.connectiontype = mapscript.MS_POSTGIS
                                layer.setProcessing( "CLOSE_CONNECTION=DEFER" )
                                #layer.symbolscaledenom = 1000
                                #layer.sizeunits = mapscript.MS_PIXELS
                                layer.type = mapscript.MS_LAYER_LINE
                                layer.status = mapscript.MS_DEFAULT
                                layer.tileitem = None
                                layer.setMetaData( "norGIS_label", (u"ALKIS / %s / Linien" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_layer_group", (u"/%s" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_title", u"Linien" )
                                layer.setMetaData( u"wfs_title", u"Linien" )
                                layer.setMetaData( u"gml_geom_type", "multiline" )
                                layer.setMetaData( u"gml_geometries", "geom" )
                                layer.setMetaData( u"gml_featureid", "ogc_fid" )
                                layer.setMetaData( u"gml_include_items", "all" )
                                layer.setMetaData( u"wms_srs", alkisplugin.defcrs )
                                layer.setMetaData( u"wfs_srs", alkisplugin.defcrs )
                                self.setUMNScale( layer, d['line'] )

                                sql = (u"SELECT"
                                       u" signaturnummer,umn,darstellungsprioritaet,alkis_linien.name"
                                       u" FROM alkis_linien"
                                       u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
                                       u" WHERE EXISTS (SELECT * FROM po_lines WHERE %s AND po_lines.signaturnummer=alkis_linien.signaturnummer)"
                                       u" ORDER BY darstellungsprioritaet" ) % where
                                #qDebug( "SQL: %s" % sql )
                                if qry.exec_( sql ):
                                        sprio = 0
                                        nclasses = 0
                                        minprio = None
                                        maxprio = None

                                        while qry.next():
                                                sn = qry.value( 0 )
                                                color  = qry.value( 1 )
                                                prio = qry.value( 2 )
                                                names = qry.value( 3 )

                                                cl = mapscript.classObj( layer )
                                                cl.setExpression( sn )
                                                cl.name = d['classes'].get(sn, "(%s)" % sn).encode("utf-8")

                                                if not self.insertStylesFromBlock(layerclass=cl, map=mapobj, name="alkis%s" % sn, color=color ):
                                                        layer.removeClass( layer.numclasses-1 )

                                                nclasses += 1
                                                sprio += prio;
                                                if not minprio or prio < minprio:
                                                        minprio = prio
                                                if not maxprio or prio > maxprio:
                                                        maxprio = prio

                                else:
                                        QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
                                        break

                                if layer.numclasses > 0:
                                        layer.setMetaData( "norGIS_zindex", "%d" % (sprio / nclasses) )
                                        layer.setMetaData( "norGIS_minprio", "%d" % minprio )
                                        layer.setMetaData( "norGIS_maxprio", "%d" % maxprio )

                                        group.append( layer.name )
                                else:
                                        n = mapobj.numlayers
                                        mapobj.removeLayer( layer.index )
                                        if n == mapobj.numlayers:
                                                raise BaseException( "No layer removed" )

                                #
                                # 3 Punkte (TODO: Darstellungspriorität)
                                #

                                layer = mapscript.layerObj(mapobj)
                                layer.name = "l%d" % iLayer
                                iLayer += 1
                                layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,point AS geom,drehwinkel_grad,signaturnummer FROM po_points WHERE %s AND NOT point IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg)).encode("utf-8")
                                layer.classitem = "signaturnummer"
                                layer.setProjection( "init=epsg:%d" % epsg )
                                layer.connection = conninfo
                                layer.connectiontype = mapscript.MS_POSTGIS
                                layer.setProcessing( "CLOSE_CONNECTION=DEFER" )
                                layer.symbolscaledenom = 1000
                                layer.sizeunits = mapscript.MS_METERS
                                layer.type = mapscript.MS_LAYER_POINT
                                layer.status = mapscript.MS_DEFAULT
                                layer.tileitem = None
                                layer.setMetaData( "norGIS_label", (u"ALKIS / %s / Punkte" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_layer_group", (u"/%s" % tname).encode("utf-8") )
                                layer.setMetaData( u"wms_title", u"Punkte" )
                                layer.setMetaData( u"wfs_title", u"Punkte" )
                                layer.setMetaData( u"gml_geom_type", "multipoint" )
                                layer.setMetaData( u"gml_geometries", "geom" )
                                layer.setMetaData( u"gml_featureid", "ogc_fid" )
                                layer.setMetaData( u"gml_include_items", "all" )
                                layer.setMetaData( u"wms_srs", alkisplugin.defcrs )
                                layer.setMetaData( u"wfs_srs", alkisplugin.defcrs )
                                self.setUMNScale( layer, d['point'] )

                                self.progress(iThema, "Punkte", 3)

                                sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE (%s)" % where
                                #qDebug( "SQL: %s" % sql )
                                if qry.exec_( sql ):
                                        while qry.next():
                                                sn = qry.value(0)
                                                if not sn:
                                                        logMessage( u"Leere Signaturnummer in po_points:%s" % thema )
                                                        continue

                                                path = os.path.abspath( os.path.join( BASEDIR, "svg", "alkis%s.svg" % sn ) )

                                                if not symbols.has_key( "norGIS_alkis%s" % sn ) and not os.path.isfile( path ):
                                                        logMessage( "Symbol alkis%s.svg nicht gefunden" % sn )
                                                        missing[ "norGIS_alkis%s" % sn ] = 1
                                                        continue

                                                cl = mapscript.classObj( layer )
                                                cl.setExpression( sn )
                                                cl.name = d['classes'].get(sn, "(%s)" % sn).encode("utf-8")

                                                if alkisplugin.exts.has_key(sn):
                                                        x = ( alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx'] ) / 2
                                                        y = ( alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy'] ) / 2
                                                        w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
                                                        h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']
                                                else:
                                                        x, y, w, h = 0, 0, 1, 1

                                                if not symbols.has_key( "norGIS_alkis%s" % sn ):
                                                        f = NamedTemporaryFile(delete=False)
                                                        tempname = f.name
                                                        f.write( "SYMBOLSET SYMBOL TYPE SVG NAME \"norGIS_alkis%s\" IMAGE \"%s\" END END" % ( sn, path) )
                                                        f.close()

                                                        tempsymbolset = mapscript.symbolSetObj( tempname )
                                                        os.unlink( tempname )

                                                        sym = tempsymbolset.getSymbolByName( "norGIS_alkis%s" % sn )
                                                        sym.inmapfile = True
                                                        if mapobj.symbolset.appendSymbol(sym) < 0:
                                                             raise BaseException( "symbol not added." )

                                                        del tempsymbolset
                                                        symbols[ "norGIS_alkis%s" % sn ] = 1

                                                stylestring = "STYLE ANGLE [drehwinkel_grad] OFFSET %lf %lf SIZE %lf SYMBOL \"norGIS_alkis%s\" MINSIZE 1 END" % (x, y, h, sn )
                                                style = fromstring( stylestring )
                                                cl.insertStyle( style )

                                if layer.numclasses > 0:
                                        group.append( layer.name )
                                else:
                                        mapobj.removeLayer( layer.index )

                                #
                                # 4 Beschriftungen (TODO: Darstellungspriorität)
                                #

                                lgroup = []

                                for j in range(2):
                                        geom = "point" if j==0 else "line"

                                        if not qry.exec_( "SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL" % (where,geom) ) or not qry.next() or qry.value(0) == 0:
                                                continue

                                        self.progress(iThema, "Beschriftungen (%d)" % (j+1), 4+j)

                                        layer = mapscript.layerObj(mapobj)
                                        layer.name = "l%d" % iLayer
                                        iLayer += 1
                                        layer.setMetaData( "norGIS_label", (u"ALKIS / %s / Beschriftungen" % tname).encode("utf-8") )
                                        layer.setMetaData( u"wms_layer_group", (u"/%s" % tname).encode("utf-8") )
                                        layer.setMetaData( u"wms_title", u"Beschriftungen (%s)" % ("Punkte" if j==0 else "Linien") )
                                        layer.setMetaData( u"wfs_title", u"Beschriftungen (%s)" % ("Punkte" if j==0 else "Linien") )
                                        layer.setMetaData( u"gml_geom_type", "multipoint" )
                                        layer.setMetaData( u"gml_geometries", "geom" )
                                        layer.setMetaData( u"gml_featureid", "ogc_fid" )
                                        layer.setMetaData( u"gml_include_items", "all" )
                                        layer.setMetaData( u"wms_srs", alkisplugin.defcrs )
                                        layer.setMetaData( u"wfs_srs", alkisplugin.defcrs )
                                        layer.setMetaData( u"norGIS_zindex", "999" )
                                        self.setUMNScale( layer, d['label'] )

                                        if geom=="point":
                                            layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,text,point AS geom,drehwinkel_grad,color_umn,font_umn,size_umn,alignment_dxf AS alignment FROM po_labels l WHERE %s AND NOT point IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg)).encode("utf-8")
                                            layer.classitem = "alignment"

                                            positions = {
                                                        -1: mapscript.MS_AUTO,
                                                         1: mapscript.MS_LR,
                                                         2: mapscript.MS_LC,
                                                         3: mapscript.MS_LL,
                                                         4: mapscript.MS_CR,
                                                         5: mapscript.MS_CC,
                                                         6: mapscript.MS_CL,
                                                         7: mapscript.MS_UR,
                                                         8: mapscript.MS_UC,
                                                         9: mapscript.MS_UL,
                                                    }

                                            for pos in [ 1, 2, 3, 4, 5, 6, 7, 8, 9, -1 ]:
                                                cl = mapscript.classObj( layer )

                                                if pos >= 0:
                                                        cl.setExpression( "%d" % pos )
                                                        #cl.name = u"Beschriftungen %s %d" % (geom,pos)
                                                else:
                                                        #cl.name = u"Beschriftungen %s AUTO" % geom
                                                        pass

                                                label = mapscript.labelObj()
                                                label.position = positions[ pos ]
                                                label.type = mapscript.MS_TRUETYPE
                                                label.setBinding( mapscript.MS_LABEL_BINDING_COLOR, "color_umn" )
                                                label.setBinding( mapscript.MS_LABEL_BINDING_FONT, "font_umn" )
                                                label.setBinding( mapscript.MS_LABEL_BINDING_ANGLE, "drehwinkel_grad" )
                                                label.setBinding( mapscript.MS_LABEL_BINDING_SIZE, "size_umn" )
                                                label.buffer = 2
                                                label.force = mapscript.MS_TRUE
                                                label.partials = mapscript.MS_TRUE
                                                label.antialias = mapscript.MS_TRUE
                                                label.outlinecolor.setRGB( 255, 255, 255 )
                                                label.mindistance = -1
                                                label.minfeaturesize = -1
                                                label.shadowsizex = 0
                                                label.shadowsizey = 0
                                                #label.minsize = 4
                                                #label.maxsize = 256
                                                label.minfeaturesize = -1
                                                label.priority = 10

                                                cl.addLabel( label )
                                        else:
                                            layer.data = (u"geom FROM (SELECT ogc_fid,gml_id,text,st_offsetcurve(line,size_umn*0.0127,'') AS geom,color_umn,font_umn,size_umn FROM po_labels l WHERE %s AND NOT line IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (where,epsg)).encode("utf-8")

                                            cl = mapscript.classObj( layer )

                                            label = mapscript.labelObj()
                                            label.updateFromString( """
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
""" )

                                            cl.addLabel( label )

                                        layer.labelitem = "text"
                                        layer.setProjection( "init=epsg:%d" % epsg )

                                        layer.connection = conninfo
                                        layer.connectiontype = mapscript.MS_POSTGIS
                                        layer.setProcessing( "CLOSE_CONNECTION=DEFER" )
                                        layer.symbolscaledenom = 1000
                                        #layer.labelminscaledenom = 0
                                        #layer.labelmaxscaledenom = 2000
                                        layer.sizeunits = mapscript.MS_INCHES
                                        layer.type = mapscript.MS_LAYER_ANNOTATION
                                        layer.status = mapscript.MS_DEFAULT
                                        layer.tileitem = None


                                        lgroup.append( layer.name )

                self.reorderLayers( mapobj )

                self.showProgress.emit( len(alkisplugin.themen)*5, len(alkisplugin.themen)*5 )

                mapobj.save(dstfile)

        def styleFromBlock(self,**kwargs):
                mapobj = kwargs.get('map',None)
                symbolset = kwargs.get('symbolset',None)
                name = kwargs.get('name',None)
                color0 = kwargs.get('color',None)
                angle = kwargs.get('angle',None)
                cl = kwargs.get('class',None)
                minsize = kwargs.get('minsize',None)
                size = kwargs.get('size',None)
                maxsize = kwargs.get('maxsize',None)

                if minsize: minsize = int(minsize)
                if size: size = int(size)
                if maxsize: maxsize = int(maxsize)

                if not mapobj: raise BaseException( "map undefined" )
                if not name: raise BaseException( "name undefined" )

                symname0 = "norGIS_%s" % name
                name = name.lower()

                if not symbolset:
                        symbolset = mapobj.symbolset
                        inmapfile = True
                else:
                        inmapfile = False

                blocks = []
                styles = []

                if not alkisplugin.BLOCKS.has_key(name):
                        logMessage( u" Keine Daten für Symbol |%s| gefunden." % name )
                        return None

                b = alkisplugin.BLOCKS[name]

                if isinstance(b,list):
                        blocks = b
                else:
                        blocks = [ b ]

                i=0
                for block in blocks:
                        color = block.get('color', color0)

                        style = mapscript.styleObj()

                        if not block.has_key('symbol'):
                                symname = symname0
                                if i > 0: symname += "#%d" % i
                                i += 1

                                index = symbolset.index( symname )
                                if index >= 0: symbolset.removeSymbol( index )

                                symbol = mapscript.symbolObj( symname )
                                symbol.inmapfile = inmapfile
                                symbol.type = block.get('type', mapscript.MS_SYMBOL_TRUETYPE)

                                if symbol.type == mapscript.MS_SYMBOL_TRUETYPE:
                                        if not block.get('character',None): raise BaseException( "character for %s not defined" % name )

                                        symbol.character = block['character']
                                        symbol.antialias = block.get('antialias', mapscript.MS_TRUE)
                                        symbol.filled = mapscript.MS_TRUE if block.get('filled',0) else mapscript.MS_FALSE
                                        symbol.font = block.get('font', "webgis")

                                        if block.has_key('position'):
                                                raise BaseException( u"symbol.position not supported in mapscript 6" )

                                elif symbol.type == mapscript.MS_SYMBOL_VECTOR or \
                                      symbol.type == mapscript.MS_SYMBOL_ELLIPSE:

                                        symbol.filled = mapscript.MS_TRUE if block.get('filled',0) else mapscript.MS_FALSE

                                        if block.has_key('points'):
                                                line = mapscript.lineObj()
                                                p = mapscript.pointObj()

                                                i = 0
                                                while i+1 < len( block['points'] ):
                                                        p.x = block['points'][i]
                                                        p.y = block['points'][i+1]

                                                        if line.add( p ) != mapscript.MS_SUCCESS:
                                                                raise BaseException( "failed to add point %d" % i )

                                                        i += 2

                                                if symbol.setPoints( line ) != line.numpoints:
                                                        raise BaseException( "failed to add all %d points" % line.numpoints )

                                elif symbol.type == mapscript.MS_SYMBOL_CARTOLINE:

                                        #  SYMBOL
                                        #    NAME "schraff"
                                        #    TYPE VECTOR
                                        #    POINTS
                                        #      0 1
                                        #      1 0
                                        #    END
                                        #  END

                                        if block.has_key('pattern'):
                                                style.updateFromString( "STYLE PATTERN %s END END" % ( ' '.join( map( lambda x : str(x), block['pattern'] ) ) ) )

                                elif symbol.type == mapscript.MS_SYMBOL_HATCH:
                                        logMessage( u"Hatch!" )
                                        continue
                                else:
                                        logMessage( u"symbol type %d not supported." % symbol.type )
                                        continue

                                if symbolset.appendSymbol(symbol) < 0:
                                        raise BaseException( "symbol not added." )

                        else:
                                symname = block['symbol']

                        if color:
                                if isinstance(color,list):
                                        r, g, b = color
                                else:
                                        r, g, b = color.split(" ")
                                style.color.setRGB( int(r), int(g), int(b) )
                        else:
                                style.color.setRGB(0,0,0)

                        if block.has_key('minsize'):
                                style.minsize = block['minsize']
                        elif minsize:
                                style.minsize = minsize

                        if block.has_key('maxsize'):
                                style.maxsize = block['maxsize']
                        elif maxsize:
                                style.maxsize = maxsize

                        if block.has_key('size') or size: style.size = block.get('size',size)
                        style.offsetx = block.get('offsetx',0)
                        style.offsety = block.get('offsety',0)
                        if block.has_key('angle'): style.angle = block['angle']

                        if block.has_key('linecap'): style.linecap = block['linecap']
                        if block.has_key('linejoin'): style.linejoin = block['linejoin']
                        if block.has_key('linejoinmaxsize'): style.linejoinmaxsize = block['linejoinmaxsize']

                        style.opacity = block.get('opacity',100)

                        if angle: style.setBinding( mapscript.MS_STYLE_BINDING_ANGLE, angle )

                        if symname != "0":
                                style.symbolname = symname

                        styles.append( style )

                return styles

        def insertStylesFromBlock(self,**kwargs):
                cl = kwargs.get('layerclass', None)
                if not cl:
                        raise BaseException( "layerclass undefined" )

                del kwargs['layerclass']

                styles = self.styleFromBlock(**kwargs)

                if not styles:
                        return 0

                for style in styles:
                        cl.insertStyle( style )

                return 1

        def reorderLayers(self,mapobj):
                layers = {}
                idx = {}
                for i in range(mapobj.numlayers):
                        layer = mapobj.getLayer(i)
                        layer.setMetaData( "norGIS_oldindex", "%d" % i )

                        zindex = layer.metadata.get( "norGIS_zindex" ) or -1

                        if not layers.has_key( layer.type ):
                                layers[ layer.type ] = {}

                        if not layers[ layer.type ].has_key( zindex ):
                                layers[ layer.type ][ zindex ] = []

                        layers[ layer.type ][ zindex ].append( i )
                        idx[i] = i

                order = []
                for t in [ mapscript.MS_LAYER_RASTER, mapscript.MS_LAYER_POLYGON, mapscript.MS_LAYER_LINE, mapscript.MS_LAYER_POINT, mapscript.MS_LAYER_ANNOTATION ]:
                        if not layers.has_key( t ):
                                continue

                        keys = layers[t].keys()
                        keys.sort()
                        for z in keys:
                                order.extend( layers[t][z] )

                for i in range(mapobj.numlayers):
                        oidx = order.pop(0)
                        j = idx[oidx]
                        del idx[oidx]

                        l = mapobj.getLayer(j)
                        mapobj.removeLayer(j)

                        if mapobj.insertLayer( l, i if i<mapobj.numlayers else -1 ) < 0:
                                raise BaseException( u"Konnte Layer %d nicht wieder hinzufügen" % i )

                        for k in idx.keys():
                                if idx[k]>=i and idx[k]<j:
                                        idx[k] += 1

if __name__ == '__main__':
        import sys
        if len(sys.argv) == 2:
                p = alkisplugin( QCoreApplication.instance() )
                p.mapfile(None,sys.argv[1])
        else:
                print 'Fehler: alkisplugin.py "dstfile.map"'
