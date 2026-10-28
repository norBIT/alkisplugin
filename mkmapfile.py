#!/usr/bin/python
# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    mkmapfile.py
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

try:
    import sip
    if sip.SIP_VERSION >> 16 < 5:
        for c in ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]:
            sip.setapi(c, 2)
except ModuleNotFoundError:
    pass

from tempfile import mkstemp

import os
import sys
import optparse


import mapscript
from mapscript import fromstring

import psycopg

BASEDIR = os.path.dirname(__file__)


def qDebug(s):
    print(s, file=sys.stderr)


def logMessage(s):
    print(s, file=sys.stdout)


def logError(s):
    print(s, file=sys.stderr)


class mkmapfile():
    themen = (
        {
            'name': "Flurstücke",
            'area': {'min': 0, 'max': 5000},
            'outline': {'min': 0, 'max': 5000, 'umntemplate': 1, },
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

    def __init__(self, opts):
        self.umntemplates = opts.template
        self.modelle = opts.modellarten.split(',')
        self.katalog = self.signaturkatalog
        self.schema = self.schema

    def setScale(self, layer, d):
        if d.get('umntemplate', 0):
            template = self.umntemplate
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

    def setLayerMetaData(self, layer, k, v):
        if hasattr(layer, "setMetaData"):
            layer.setMetaData(k, v)
        else:
            layer.metadata.set(k, v)

    def mapfile(self, conninfo, dstfile):
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('search_path', quote_ident(%s)||','||current_setting('search_path'), false)", (self.schema,))

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
                    mapobj.web.metadata.set("wms_title", "ALKIS")
                    mapobj.web.metadata.set("wms_enable_request", "*")
                    mapobj.web.metadata.set("wfs_enable_request", "*")
                    mapobj.web.metadata.set("ows_enable_request", "*")
                    mapobj.web.metadata.set("wms_feature_info_mime_type", "text/html")
                    mapobj.web.metadata.set("wms_encoding", "UTF-8")
                except AttributeError:
                    mapobj.web.metadata["wms_title"] = "ALKIS"
                    mapobj.web.metadata["wms_enable_request"] = "*"
                    mapobj.web.metadata["wfs_enable_request"] = "*"
                    mapobj.web.metadata["ows_enable_request"] = "*"
                    mapobj.web.metadata["wms_feature_info_mime_type"] = "text/html"
                    mapobj.web.metadata["wms_encoding"] = "UTF-8"

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

                cur.execute("SELECT *,proj4text FROM (SELECT st_extent(wkb_geometry) AS bb,find_srid(%s::text,'ax_flurstueck'::text,'wkb_geometry'::text) AS srid FROM ax_flurstueck) AS a LEFT JOIN spat_ref_sys USING (srid)", (self.schema,))

                for r in cur:
                    bb = r[0][4:-1]
                    (p0, p1) = bb.split(",")
                    (x0, y0) = p0.split(" ")
                    (x1, y1) = p1.split(" ")
                    self.epsg = r[1]
                    if self.epsg > 100000:
                        mapobj.setProjection(r[2])
                    else:
                        crs = "init=epsg:%d" % self.epsg
                        mapobj.setProjection(crs)
                    mapobj.setExtent(float(x0), float(y0), float(x1), float(y1))
                    break
                else:
                    crs = "init=epsg:%d" % self.epsg

                modelle = self.modellarten
                katalog = self.signaturkatalog

                missing = {}
                symbols = {}

                self.steps = 0
                for d in mkmapfile.themen:
                    self.steps += 6 * len(d.get('filter', [1]))

                self.step = 0

                iThema = -1
                iLayer = 0
                for d in mkmapfile.themen:
                    iThema += 1
                    thema = d['name']

                    if 'filter' not in d:
                        d['filter'] = [{'name': None, 'filter': None}]

                    qDebug("Thema: %s" % thema)

                    for f in d['filter']:
                        name = f.get('name', thema)
                        tname = thema

                        where = "thema='%s'" % thema
                        if len(modelle) > 0:
                            where += " AND modell && ARRAY['%s']::varchar[]" % "','".join(modelle)

                        if f.get('name', None):
                            tname += " / " + f['name']

                        if f.get('filter', None):
                            where += " AND (%s)" % f['filter']

                        for k in ['area', 'outline', 'line', 'point', 'label']:
                            if k not in f:
                                f[k] = d[k]

                        self.progress(iThema, "Flächen")

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

                        layer.data = "geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_flaeche AS signaturnummer FROM %s.po_polygons WHERE %s AND NOT sn_flaeche IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg)  # nosec: B608
                        layer.classitem = "signaturnummer"
                        layer.setProjection(crs)
                        layer.connectiontype = mapscript.MS_POSTGIS
                        layer.connection = conninfo
                        layer.symbolscaledenom = 1000
                        if hasattr(layer, "setProcessing"):
                            layer.setProcessing("CLOSE_CONNECTION=DEFER")
                        else:
                            layer.setProcessingKey("CLOSE_CONNECTION", "DEFER")
                        layer.type = mapscript.MS_LAYER_POLYGON
                        layer.sizeunits = mapscript.MS_INCHES
                        layer.status = mapscript.MS_OFF
                        layer.tileitem = None
                        self.setLayerMetaData(layer, "norGIS_label", ("ALKIS / %s / Flächen" % tname))
                        self.setLayerMetaData(layer, "wms_layer_group", ("/%s" % tname))
                        self.setLayerMetaData(layer, "wms_title", "Flächen")
                        self.setLayerMetaData(layer, "wfs_title", "Flächen")
                        self.setLayerMetaData(layer, "gml_geom_type", "multipolygon")
                        self.setLayerMetaData(layer, "gml_geometries", "geom")
                        self.setLayerMetaData(layer, "gml_featureid", "ogc_fid")
                        self.setLayerMetaData(layer, "gml_include_items", "all")
                        self.setLayerMetaData(layer, "wms_srs", mkmapfile.defcrs)
                        self.setLayerMetaData(layer, "wfs_srs", mkmapfile.defcrs)
                        self.setScale(layer, f['area'])

                        sql = ("SELECT DISTINCT"  # nosec: B608
                               " signaturnummer,umn,darstellungsprioritaet,alkis_flaechen.name"
                               " FROM alkis_flaechen"
                               " JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
                               " WHERE EXISTS ("
                               "SELECT * FROM po_polygons WHERE {0} AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer"
                               "){1}"
                               " ORDER BY darstellungsprioritaet"
                               ).format(
                                   where,
                                   "" if katalog < 0 else " AND katalog=%d" % katalog
                        )
                        # qDebug( "SQL: %s" % sql )

                        cur.execute(sql)

                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        for sn, color, prio, name in cur:
                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            cl.name = d['classes'].get(sn, name)

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

                        if nclasses == 0:
                            logError("Keine Klassen gefunden")
                            break

                        if layer.numclasses > 0:
                            self.setLayerMetaData(layer, "norGIS_zindex", "%d" % (sprio / nclasses))
                            self.setLayerMetaData(layer, "norGIS_minprio", "%d" % minprio)
                            self.setLayerMetaData(layer, "norGIS_maxprio", "%d" % maxprio)

                            group.append(layer.name)
                        else:
                            mapobj.removeLayer(layer.index)

                        self.progress(iThema, "Grenzen")

                        #
                        # 1.2 Randlinien
                        #
                        layer = mapscript.layerObj(mapobj)
                        layer.name = "l%d" % iLayer
                        layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                        iLayer += 1
                        layer.data = "geom FROM (SELECT ogc_fid,gml_id,polygon AS geom,sn_randlinie AS signaturnummer FROM %s.po_polygons WHERE %s AND NOT polygon IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg)  # nosec: B608
                        layer.classitem = "signaturnummer"
                        layer.setProjection(crs)
                        layer.connection = conninfo
                        layer.connectiontype = mapscript.MS_POSTGIS
                        if hasattr(layer, "setProcessing"):
                            layer.setProcessing("CLOSE_CONNECTION=DEFER")
                        else:
                            layer.setProcessingKey("CLOSE_CONNECTION", "DEFER")
                        # layer.symbolscaledenom = 1000
                        layer.sizeunits = mapscript.MS_METERS
                        layer.type = mapscript.MS_LAYER_POLYGON
                        layer.status = mapscript.MS_OFF
                        layer.tileitem = None
                        self.setLayerMetaData(layer, "norGIS_label", "ALKIS / %s / Grenzen" % tname)
                        self.setLayerMetaData(layer, "wms_layer_group", "/%s" % tname)
                        self.setLayerMetaData(layer, "wms_title", "Grenzen")
                        self.setLayerMetaData(layer, "wfs_title", "Grenzen")
                        self.setLayerMetaData(layer, "gml_geom_type", "multiline")
                        self.setLayerMetaData(layer, "gml_geometries", "geom")
                        self.setLayerMetaData(layer, "gml_featureid", "ogc_fid")
                        self.setLayerMetaData(layer, "gml_include_items", "all")
                        self.setLayerMetaData(layer, "wms_srs", mkmapfile.defcrs)
                        self.setLayerMetaData(layer, "wfs_srs", mkmapfile.defcrs)
                        self.setScale(layer, f['outline'])

                        sql = (
                            "SELECT DISTINCT"  # nosec: B608
                            " ln.signaturnummer,umn,darstellungsprioritaet,ln.name"
                            " FROM alkis_linien ln{0}"
                            " LEFT OUTER JOIN alkis_farben f ON {1}.farbe=f.id"
                            " WHERE EXISTS ("
                            "SELECT * FROM po_polygons WHERE {2} AND po_polygons.sn_randlinie=ln.signaturnummer"
                            "){3}"
                            " ORDER BY darstellungsprioritaet"
                        ).format(
                            "" if katalog < 0 else " LEFT OUTER JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer AND l.katalog=%d" % katalog,
                            "ln" if katalog < 0 else "l",
                            where,
                            "" if katalog < 0 else " AND ln.katalog=%d" % katalog
                        )

                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        cur.execute(sql)

                        for sn, color, prio, name in cur:
                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            cl.name = d['classes'].get(sn, name)

                            if not self.addLineStyles(conn, cl, katalog, sn, color, True):
                                layer.removeClass(layer.numclasses - 1)

                            nclasses += 1
                            sprio += prio
                            if not minprio or prio < minprio:
                                minprio = prio
                            if not maxprio or prio > maxprio:
                                maxprio = prio
                            break
                        else:
                            logError("Fehler: Kein Klassen gefunden\nSQL: %s" % (sql))
                            break

                        if layer.numclasses > 0:
                            self.setLayerMetaData(layer, "norGIS_zindex", "%d" % (sprio / nclasses))
                            self.setLayerMetaData(layer, "norGIS_minprio", "%d" % minprio)
                            self.setLayerMetaData(layer, "norGIS_maxprio", "%d" % maxprio)

                            group.append(layer.name)
                        else:
                            mapobj.removeLayer(layer.index)

                        self.progress(iThema, "Linien")

                        #
                        # 2 Linien
                        #
                        layer = mapscript.layerObj(mapobj)
                        layer.name = "l%d" % iLayer
                        layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                        iLayer += 1
                        layer.data = "geom FROM (SELECT ogc_fid,gml_id,line AS geom,signaturnummer FROM %s.po_lines WHERE %s AND NOT line IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg)  # nosec: B608
                        layer.classitem = "signaturnummer"
                        layer.setProjection(crs)
                        layer.connection = conninfo
                        layer.connectiontype = mapscript.MS_POSTGIS
                        if hasattr(layer, "setProcessing"):
                            layer.setProcessing("CLOSE_CONNECTION=DEFER")
                        else:
                            layer.setProcessingKey("CLOSE_CONNECTION", "DEFER")
                        # layer.symbolscaledenom = 1000
                        layer.sizeunits = mapscript.MS_METERS
                        layer.type = mapscript.MS_LAYER_LINE
                        layer.status = mapscript.MS_OFF
                        layer.tileitem = None
                        self.setLayerMetaData(layer, "norGIS_label", "ALKIS / %s / Linien" % tname)
                        self.setLayerMetaData(layer, "wms_layer_group", "/%s" % tname)
                        self.setLayerMetaData(layer, "wms_title", "Linien")
                        self.setLayerMetaData(layer, "wfs_title", "Linien")
                        self.setLayerMetaData(layer, "gml_geom_type", "multiline")
                        self.setLayerMetaData(layer, "gml_geometries", "geom")
                        self.setLayerMetaData(layer, "gml_featureid", "ogc_fid")
                        self.setLayerMetaData(layer, "gml_include_items", "all")
                        self.setLayerMetaData(layer, "wms_srs", mkmapfile.defcrs)
                        self.setLayerMetaData(layer, "wfs_srs", mkmapfile.defcrs)
                        self.setScale(layer, f['line'])

                        sql = (
                            "SELECT DISTINCT"  # nosec: B608
                            " ln.signaturnummer,umn,darstellungsprioritaet,ln.name"
                            " FROM alkis_linien ln{0}"
                            " JOIN alkis_farben f ON {1}.farbe=f.id"
                            " WHERE EXISTS ("
                            "SELECT * FROM po_lines WHERE {2} AND po_lines.signaturnummer=ln.signaturnummer"
                            "){3}"
                            " ORDER BY darstellungsprioritaet"
                        ).format(
                            "" if katalog < 0 else " JOIN alkis_linie l ON ln.signaturnummer=l.signaturnummer AND l.katalog=%d" % katalog,
                            "ln" if katalog < 0 else "l",
                            where,
                            "" if katalog < 0 else " AND ln.katalog=%d" % katalog
                        )

                        sprio = 0
                        nclasses = 0
                        minprio = None
                        maxprio = None

                        cur.execute(sql)

                        for sn, color, prio, name in cur:
                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            cl.name = d['classes'].get(sn, name)

                            if not self.addLineStyles(conn, cl, katalog, sn, color, False):
                                layer.removeClass(layer.numclasses - 1)

                            nclasses += 1
                            sprio += prio
                            if not minprio or prio < minprio:
                                minprio = prio
                            if not maxprio or prio > maxprio:
                                maxprio = prio

                        if nclasses == 0:
                            logError("Kein Klassen gefunden\nSQL: %s" % (sql))
                            break

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
                        layer.data = "geom FROM (SELECT ogc_fid,gml_id,point AS geom,drehwinkel_grad,signaturnummer FROM %s.po_points WHERE %s AND NOT point IS NULL) AS foo USING UNIQUE ogc_fid USING SRID=%d" % (self.quotedschema(), where, self.epsg)  # nosec: B608
                        layer.classitem = "signaturnummer"
                        layer.setProjection(crs)
                        layer.connection = conninfo
                        layer.connectiontype = mapscript.MS_POSTGIS
                        if hasattr(layer, "setProcessing"):
                            layer.setProcessing("CLOSE_CONNECTION=DEFER")
                        else:
                            layer.setProcessingKey("CLOSE_CONNECTION", "DEFER")
                        layer.symbolscaledenom = 1000
                        layer.sizeunits = mapscript.MS_METERS
                        layer.type = mapscript.MS_LAYER_POINT
                        layer.status = mapscript.MS_OFF
                        layer.tileitem = None
                        self.setLayerMetaData(layer, "norGIS_label", "ALKIS / %s / Punkte" % tname)
                        self.setLayerMetaData(layer, "wms_layer_group", "/%s" % tname)
                        self.setLayerMetaData(layer, "wms_title", "Punkte")
                        self.setLayerMetaData(layer, "wfs_title", "Punkte")
                        self.setLayerMetaData(layer, "gml_geom_type", "multipoint")
                        self.setLayerMetaData(layer, "gml_geometries", "geom")
                        self.setLayerMetaData(layer, "gml_featureid", "ogc_fid")
                        self.setLayerMetaData(layer, "gml_include_items", "all")
                        self.setLayerMetaData(layer, "wms_srs", mkmapfile.defcrs)
                        self.setLayerMetaData(layer, "wfs_srs", mkmapfile.defcrs)
                        self.setScale(layer, f['point'])

                        self.progress(iThema, "Punkte")

                        kat = max([1, katalog])

                        sql = "SELECT DISTINCT signaturnummer FROM po_points WHERE (%s)" % where  # nosec: B608
                        # qDebug( "SQL: %s" % sql )
                        cur.execute(sql)

                        for sn, in cur:
                            if not sn:
                                logMessage("Leere Signaturnummer in po_points:%s" % thema)
                                continue

                            path = os.path.abspath(os.path.join(BASEDIR, "svg", "alkis%s_%d.svg" % (sn, kat)))

                            if "norGIS_alkis%s_%d" % (sn, kat) not in symbols and not os.path.isfile(path):
                                if sn != '6000':
                                    logMessage("Symbol alkis%s_%d.svg nicht gefunden" % (sn, kat))
                                    missing["norGIS_alkis%s" % sn] = 1
                                continue

                            cl = mapscript.classObj(layer)
                            cl.setExpression(sn)
                            cl.name = d['classes'].get(sn, "(%s)" % sn)

                            x, y, h = 0, 0, 1
                            with conn.cursor() as cur:
                                cur.execute("SELECT x0,y0,x1,y1 FROM alkis_punkte WHERE katalog=%s AND signaturnummer=%s", (kat, sn))

                                for x0, y0, x1, y1 in cur:
                                    x = (x0 + x1) / 2
                                    y = (y0 + y1) / 2
                                    w = x1 - x0
                                    h = y1 - y0
                                    break
                                else:
                                    if sn not in mkmapfile.exts:
                                        x = (mkmapfile.exts[sn]['minx'] + mkmapfile.exts[sn]['maxx']) / 2
                                        y = (mkmapfile.exts[sn]['miny'] + mkmapfile.exts[sn]['maxy']) / 2
                                        w = mkmapfile.exts[sn]['maxx'] - mkmapfile.exts[sn]['minx']
                                        h = mkmapfile.exts[sn]['maxy'] - mkmapfile.exts[sn]['miny']

                            if "norGIS_alkis%s_%d" % (sn, kat) not in symbols:
                                fd, tempname = mkstemp()
                                os.close(fd)

                                symbolf = open(tempname, "w", encoding="utf-8")
                                symbolf.write("SYMBOLSET SYMBOL TYPE SVG NAME \"norGIS_alkis{0}_{1}\" IMAGE \"{2}/alkis{0}_{1}.svg\" ANCHORPOINT {3} {4} END END".format(
                                    sn,
                                    kat,
                                    self.svgpath + "/svg",
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

                            cur.execute("SELECT count(*) FROM po_labels WHERE %s AND NOT %s IS NULL", (where, geom))
                            if cur.fetchone()[0] == 0:
                                continue

                            self.progress(iThema, "Beschriftungen (%d)" % (j + 1))

                            layer = mapscript.layerObj(mapobj)
                            layer.name = "l%d" % iLayer
                            layer.setExtent(mapobj.extent.minx, mapobj.extent.miny, mapobj.extent.maxx, mapobj.extent.maxy)
                            iLayer += 1
                            self.setLayerMetaData(layer, "norGIS_label", "ALKIS / %s / Beschriftungen" % tname)
                            self.setLayerMetaData(layer, "wms_layer_group", "/%s" % tname)
                            self.setLayerMetaData(layer, "wms_title", "Beschriftungen (%s)" % ("Punkte" if j == 0 else "Linien"))
                            self.setLayerMetaData(layer, "wfs_title", "Beschriftungen (%s)" % ("Punkte" if j == 0 else "Linien"))
                            self.setLayerMetaData(layer, "gml_geom_type", "multipoint")
                            self.setLayerMetaData(layer, "gml_geometries", "geom")
                            self.setLayerMetaData(layer, "gml_featureid", "ogc_fid")
                            self.setLayerMetaData(layer, "gml_include_items", "all")
                            self.setLayerMetaData(layer, "wms_srs", mkmapfile.defcrs)
                            self.setLayerMetaData(layer, "wfs_srs", mkmapfile.defcrs)
                            self.setLayerMetaData(layer, "norGIS_zindex", "999")
                            self.setScale(layer, f['label'])

                            data = (
                                "geom FROM (SELECT"
                                " ogc_fid"
                                ",gml_id"
                                ",text"
                                ",f.umn AS color_umn"
                                ",lower(art) || coalesce('-'||effekt,'') ||"
                                "CASE"
                                " WHEN stil='Kursiv' THEN '-italic'"
                                " WHEN stil='Fett' THEN '-bold'"
                                " WHEN stil='Fett, Kursiv' THEN '-bold-italic'"
                                " ELSE ''"
                                " END || CASE"
                                " WHEN coalesce(fontsperrung,0)=0 THEN ''"
                                " ELSE '-'||(fontsperrung/0.25)::int"
                                " END AS font_umn"
                                ",0.25/0.0254*skalierung*grad_pt AS size_umn"
                            )

                            lwhere = where
                            if geom == "point":
                                data += (
                                    ",CASE coalesce(l.vertikaleausrichtung,s.vertikaleausrichtung) "
                                    " WHEN 'oben' THEN 'L'"
                                    " WHEN 'Basis' THEN 'U'"
                                    " ELSE 'C'"
                                    " END || CASE coalesce(l.horizontaleausrichtung,s.horizontaleausrichtung)"
                                    " WHEN 'linksbündig' THEN 'L'"
                                    " WHEN 'rechtsbündig' THEN 'R'"
                                    " ELSE 'C'"
                                    " END AS position_umn"
                                    ",drehwinkel_grad"
                                    ",point AS geom"
                                )
                                lwhere += " AND point IS NOT NULL"
                            else:
                                data += ",st_offsetcurve(line,0.125*skalierung*grad_pt,'') AS geom"
                                lwhere += " AND line IS NOT NULL"

                            data += (
                                " FROM {0}.po_labels l"
                                " JOIN {0}.alkis_schriften s ON s.signaturnummer=l.signaturnummer{1}"
                                " JOIN {0}.alkis_farben f ON s.farbe=f.id"
                                " WHERE {2}"
                                ") AS foo USING UNIQUE ogc_fid USING SRID={3}"
                            ).format(
                                self.quotedschema(),
                                "" if katalog < 0 else " AND s.katalog=%d" % katalog,
                                lwhere,
                                self.epsg
                            )

                            layer.data = data

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
                            if hasattr(layer, "setProcessing"):
                                layer.setProcessing("CLOSE_CONNECTION=DEFER")
                            else:
                                layer.setProcessingKey("CLOSE_CONNECTION", "DEFER")
                            layer.symbolscaledenom = 1000
                            # layer.labelminscaledenom = 0
                            # layer.labelmaxscaledenom = 2000
                            layer.sizeunits = mapscript.MS_INCHES
                            layer.type = mapscript.MS_LAYER_POINT if mapscript.MS_VERSION_MAJOR > 6 else mapscript.MS_LAYER_ANNOTATION
                            layer.status = mapscript.MS_OFF
                            layer.tileitem = None

                            lgroup.append(layer.name)

                self.reorderLayers(mapobj)

                mapobj.save(dstfile)

                if self.svgpath != BASEDIR:
                    os.rename(dstfile, dstfile + ".bak")
                    i = open(dstfile + ".bak", "r", encoding="utf-8")
                    o = open(dstfile, "w", encoding="utf-8")

                    for lyr in i:
                        if 'FONTSET "' in lyr:
                            o.write('  FONTSET "%s/fonts/fonts.txt"\n' % self.svgpath)
                        else:
                            o.write(lyr)

                    o.close()
                    i.close()

                    os.remove(dstfile + ".bak")

    def addLineStyles(self, conn, cl, kat, sn, c, outline):
        assert cl.numstyles == 0  # nosec: B101

        sql = ("SELECT abschluss,scheitel,coalesce(strichstaerke/100,0),coalesce(laenge/100,0),coalesce(einzug/100,0),abstand{0}"  # nosec: B608
               " FROM alkis_linie l"
               " LEFT OUTER JOIN alkis_stricharten_i ON l.strichart=alkis_stricharten_i.stricharten"
               " LEFT OUTER JOIN alkis_strichart ON alkis_stricharten_i.strichart=alkis_strichart.id"
               "{1}"
               " WHERE l.signaturnummer='{2}'{3}"
               ).format(
                   "" if kat < 0 else ",r,g,b",
                   "" if kat < 0 else " LEFT OUTER JOIN alkis_farben ON l.farbe=alkis_farben.id",
                   sn,
                   "" if kat < 0 else " AND l.katalog=%d" % kat
        )

        with conn.cursor() as cur:
            cur.exec(sql)

            stricharten = []
            maxStrichstaerke = None

            for abschluss, scheitel, strichstaerke, laenge, einzug, abstaende, cr, cg, cb in cur:
                if kat >= 0:
                    c = [cr, cg, cb]

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

            if not stricharten:
                logMessage("Signaturnummer %s: Linienarten konnten nicht abgefragt werden." % sn)
                return False

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
                logMessage("Signaturnummer %s: Keine Linienarten erzeugt." % sn)
                return False

            if not outline:
                style = mapscript.styleObj()
                style.color.setRGB(255, 255, 255)
                style.opacity = 0
                style.width = maxStrichstaerke * 1.01
                cl.insertStyle(style, 0)

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
                raise BaseException("Konnte Layer %d nicht wieder hinzufügen" % i)

            for k in list(idx.keys()):
                if idx[k] >= i and idx[k] < j:
                    idx[k] += 1

    def quotedschema(self):
        return '"{}"'.format(self.schema.replace('"', '""'))


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-s', '--svgpath', default=BASEDIR)
    parser.add_option('-k', '--signaturkatalog', default=1)
    parser.add_option('-m', '--modellarten')
    parser.add_option('-t', '--template')
    parser.add_option('-e', '--epsg', default=25832)
    parser.add_option('-S', '--schema', default='public')
    opts, args = parser.parse_args()
    m = mkmapfile(opts)
    m.mapfile(args)
