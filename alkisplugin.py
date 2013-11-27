#!/usr/bin/python
# -*- coding: utf8 -*-

from PyQt4.QtCore import QObject, QSettings, Qt, QPointF
from PyQt4.QtGui import QApplication, QDialog, QIcon, QMessageBox, QAction, QColor, QInputDialog, QCursor, QPixmap
from PyQt4.QtSql import QSqlDatabase, QSqlQuery, QSqlError, QSql
from PyQt4 import QtCore

from qgis.core import *
from qgis.gui import *

try:
	import win32gui
	win32 = True
except:
	win32 = False

import time, info, conf, os, socket, resources

def qDebug(s):
	QtCore.qDebug( s.encode('ascii', 'ignore') )

class Conf(QDialog, conf.Ui_Dialog):
	def __init__(self, plugin):
		QDialog.__init__(self)
		self.setupUi(self)

		self.plugin = plugin

		s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )

		self.leSERVICE.setText( s.value( "service", "" ) )
		self.leHOST.setText( s.value( "host", "" ) )
		self.lePORT.setText( s.value( "port", "5432" ) )
		self.leDBNAME.setText( s.value( "dbname", "" ) )
		self.leUID.setText( s.value( "uid", "" ) )
		self.lePWD.setText( s.value( "pwd", "" ) )

		self.leAPPHOST.setText( s.value( "apphost", "localhost" ) )
		self.leAPPPORT.setText( s.value( "appport", "6102" ) )

		self.bb.accepted.connect(self.accept)
		self.bb.rejected.connect(self.reject)
		self.pbEinbinden.clicked.connect(self.run)

	def accept(self):
		s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
		s.setValue( "service", self.leSERVICE.text() )
		s.setValue( "host", self.leHOST.text() )
		s.setValue( "port", self.lePORT.text() )
		s.setValue( "dbname", self.leDBNAME.text() )
		s.setValue( "uid", self.leUID.text() )
		s.setValue( "pwd", self.lePWD.text() )
		s.setValue( "apphost", self.leAPPHOST.text() )
		s.setValue( "appport", self.leAPPPORT.text() )

		QDialog.accept(self)

	def run(self):
		self.plugin.run()

class Info(QDialog, info.Ui_Dialog):
	def __init__(self, html):
		QDialog.__init__(self)
		self.setupUi(self)

		self.wvEigner.setHtml( html )

class alkisplugin:
	themen = (
                {
                        'name'   : u"Flurstücke",
                        'area'   : { 'min':0, 'max':5000 },
                        'outline': { 'min':0, 'max':5000 },
                        'line'   : { 'min':0, 'max':5000 },
                        'point'  : { 'min':0, 'max':5000 },
                        'label'  : { 'min':0, 'max':5000 },
			'classes': {
				'2001': u'Bruchstriche',
				'2004': u'Zuordnungspfeil',
				'2005': u'Zuordnungspfeil, abweichender Rechtszustand',
				'2008': u'Flurstücksgrenze nicht feststellbar',
				'2028': u'Flurstücksgrenze',
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
				'1301': 'Wohngebäude',
				'1309': 'Gebäude für öffentliche Zwecke',
				'1501': 'Aussichtsturm',
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
                        'area'   : { 'min':None, 'max':None },
                        'outline': { 'min':None, 'max':None },
                        'line'   : { 'min':None, 'max':None },
                        'point'  : { 'min':None, 'max':None },
                        'label'  : { 'min':None, 'max':None },
                        'classes': {
				'1701': u'BAB/Bundesstraße',
				'1702': u'Landes-/Staatsstraße',
				'rn1701': u'BAB/Bundesstraße',
				'rn1702': u'Landes-/Staatsstraße',
				'rn1703': u'Schutzgebiet',
				'rn1704': u'Bau-, Raum-, Bodenordnungsrecht',
			},
                },
                {
                        'name'   : u"Verkehr",
                        'area'   : { 'min':None, 'max':None },
                        'outline': { 'min':None, 'max':None },
                        'line'   : { 'min':None, 'max':None },
                        'point'  : { 'min':None, 'max':None },
                        'label'  : { 'min':None, 'max':None },
                        'classes': {
				'2533': u'Widerlager',
				'2515': u'Bahnverkehr',
				'1530': u'Brücke, Hochbahn/-straße',
				'rn1530': u'Brücke, Hochbahn/-straße',
				},
                },
                {
                        'name'   : u"Friedhöfe",
                        'area'   : { 'min':None, 'max':None },
                        'outline': { 'min':None, 'max':None },
                        'line'   : { 'min':None, 'max':None },
                        'point'  : { 'min':None, 'max':None },
                        'label'  : { 'min':None, 'max':None },
                        'classes': { },
                },
                {
                        'name'   : u"Vegetation",
                        'area'   : { 'min':None, 'max':None },
                        'outline': { 'min':None, 'max':None },
                        'line'   : { 'min':None, 'max':None },
                        'point'  : { 'min':None, 'max':None },
                        'label'  : { 'min':None, 'max':None },
                        'classes': { },
                },
                {
                        'name'   : u"Landwirtschaftliche Nutzung",
                        'area'   : { 'min':None, 'max':None },
                        'outline': { 'min':None, 'max':None },
                        'line'   : { 'min':None, 'max':None },
                        'point'  : { 'min':None, 'max':None },
                        'label'  : { 'min':None, 'max':None },
                        'classes': { },
                },
                {
                        'name'   : u"Gewässer",
                        'area'   : { 'min':None, 'max':None, },
                        'outline': { 'min':None, 'max':None, },
                        'line'   : { 'min':None, 'max':None, },
                        'point'  : { 'min':None, 'max':None, },
                        'label'  : { 'min':None, 'max':None, },
                        'classes': { },
                },
                {
                        'name'   : u"Politische Grenzen",
                        'area'   : { 'min':None, 'max':None, },
                        'outline': { 'min':None, 'max':None, },
                        'line'   : { 'min':None, 'max':None, },
                        'point'  : { 'min':None, 'max':None, },
                        'label'  : { 'min':None, 'max':None, },
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
                        'area'   : { 'min':None, 'max':None, },
                        'outline': { 'min':None, 'max':None, },
                        'line'   : { 'min':None, 'max':None, },
                        'point'  : { 'min':None, 'max':None, },
                        'label'  : { 'min':None, 'max':None, },
                        'classes': { },
                },
                {
                        'name'   : u"Sport und Freizeit",
                        'area'   : { 'min':None, 'max':None, },
                        'outline': { 'min':None, 'max':None, },
                        'line'   : { 'min':None, 'max':None, },
                        'point'  : { 'min':None, 'max':None, },
                        'label'  : { 'min':None, 'max':None, },
                        'classes': { },
                },
                {
                        'name'   : u"Wohnbauflächen",
                        'area'   : { 'min':None, 'max':None, },
                        'outline': { 'min':None, 'max':None, },
                        'line'   : { 'min':None, 'max':None, },
                        'point'  : { 'min':None, 'max':None, },
                        'label'  : { 'min':None, 'max':None, },
                        'classes': { },
		}
		)

	exts = {
		'3010': { 'minx':-0.6024,	'miny':-1.0152,	'maxx':0.6171,	'maxy':1.2357 },
		'3011': { 'minx':-0.6216,	'miny':-1.0061,	'maxx':0.6299,	'maxy':1.2222 },
		'3020': { 'minx':-0.8459,	'miny':-0.8475,	'maxx':0.8559,	'maxy':0.8569 },
		'3021': { 'minx':-0.8459,	'miny':-0.8475,	'maxx':0.8559,	'maxy':0.8569 },
		'3022': { 'minx':-0.8722,	'miny':-0.8628,	'maxx':0.8617,	'maxy':0.8415 },
		'3023': { 'minx':-0.8722,	'miny':-0.8628,	'maxx':0.8617,	'maxy':0.8415 },
		'3024': { 'minx':-0.7821,	'miny':-0.7727,	'maxx':0.7588,	'maxy':0.7721 },
		'3025': { 'minx':-0.7821,	'miny':-0.7727,	'maxx':0.7588,	'maxy':0.7721 },
		'3300': { 'minx':-2.6223,	'miny':-2.6129,	'maxx':2.601,	'maxy':2.5987 },
		'3302': { 'minx':-2.5251,	'miny':-2.5107,	'maxx':2.5036,	'maxy':2.5163 },
		'3303': { 'minx':-3.4963,	'miny':-3.0229,	'maxx':3.4825,	'maxy':3.0199 },
		'3305': { 'minx':-2.5129,	'miny':-2.5091,	'maxx':2.5156,	'maxy':2.5179 },
		'3306': { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		'3308': { 'minx':-2.4464,	'miny':-2.4446,	'maxx':2.5817,	'maxy':2.5817 },
		'3309': { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		'3311': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3312': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3314': { 'minx':-2.7808,	'miny':-3.0312,	'maxx':2.8638,	'maxy':3.0117 },
		'3315': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3316': { 'minx':-2.7685,	'miny':-5.0168,	'maxx':2.7791,	'maxy':5.0062 },
		'3317': { 'minx':-1.5189,	'miny':-1.7538,	'maxx':1.5364,	'maxy':1.7565 },
		'3318': { 'minx':-0.8139,	'miny':-1.5046,	'maxx':0.8234,	'maxy':1.5017 },
		'3319': { 'minx':-2.1918,	'miny':-2.5922,	'maxx':2.1569,	'maxy':2.5962 },
		'3320': { 'minx':-2.7685,	'miny':-2.5016,	'maxx':2.7791,	'maxy':2.5028 },
		'3321': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3323': { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		'3324': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3326': { 'minx':-2.5251,	'miny':-2.5107,	'maxx':2.5036,	'maxy':2.5163 },
		'3328': { 'minx':-2.7822,	'miny':-2.7729,	'maxx':2.7656,	'maxy':2.7617 },
		'3330': { 'minx':-2.7822,	'miny':-2.7729,	'maxx':2.7656,	'maxy':2.7617 },
		'3332': { 'minx':-2.7825,	'miny':-2.7731,	'maxx':2.7653,	'maxy':2.7614 },
		'3334': { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		'3336': { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.2195 },
		'3338': { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		'3340': { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		'3342': { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		'3343': { 'minx':-2.0122,	'miny':-2.0122,	'maxx':2.0126,	'maxy':2.0027 },
		'3401': { 'minx':-1.9675,	'miny':-2.6149,	'maxx':1.96,	'maxy':2.6196 },
		'3402': { 'minx':-3.7939,	'miny':-3.5892,	'maxx':3.8046,	'maxy':3.5886 },
		'3403': { 'minx':-3.6978,	'miny':-3.6799,	'maxx':3.7045,	'maxy':3.6842 },
		'3404': { 'minx':-3.6978,	'miny':-3.6799,	'maxx':3.7045,	'maxy':3.6842 },
		'3405': { 'minx':-4.1785,	'miny':-3.8158,	'maxx':4.3008,	'maxy':3.9871 },
		'3406': { 'minx':-4.2746,	'miny':-3.9971,	'maxx':4.3678,	'maxy':3.8105 },
		'3407': { 'minx':-6.2567,	'miny':-2.2569,	'maxx':6.2643,	'maxy':2.2639 },
		'3409': { 'minx':-3.7075,	'miny':-3.6981,	'maxx':3.695,	'maxy':3.6888 },
		'3410': { 'minx':-3.6816,	'miny':-3.6797,	'maxx':3.6887,	'maxy':3.6844 },
		'3411': { 'minx':-3.7075,	'miny':-3.6981,	'maxx':3.695,	'maxy':3.6888 },
		'3412': { 'minx':-3.8813,	'miny':-3.8719,	'maxx':3.3302,	'maxy':3.8636 },
		'3413': { 'minx':-1.2257,	'miny':-0.2181,	'maxx':1.2166,	'maxy':0.2127 },
		'3415': { 'minx':-5.0815,	'miny':-2.5197,	'maxx':4.9078,	'maxy':3.1702 },
		'3417': { 'minx':-3.6945,	'miny':-3.6889,	'maxx':3.6754,	'maxy':3.6978 },
		'3419': { 'minx':-2.6093,	'miny':-3.2037,	'maxx':2.6138,	'maxy':3.2091 },
		'3421': { 'minx':-1.0193,	'miny':-0.9064,	'maxx':1.0043,	'maxy':0.9118 },
		'3423': { 'minx':-3.6945,	'miny':-3.6889,	'maxx':3.6754,	'maxy':3.6978 },
		'3424': { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		'3426': { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		'3428': { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		'3430': { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		'3432': { 'minx':-2.5193,	'miny':-2.9017,	'maxx':2.5093,	'maxy':2.5895 },
		'3434': { 'minx':-2.5193,	'miny':-2.8235,	'maxx':2.5093,	'maxy':2.6663 },
		'3436': { 'minx':-6.0195,	'miny':-6.1918,	'maxx':6.0061,	'maxy':6.0214 },
		'3438': { 'minx':-6.2697,	'miny':-6.2641,	'maxx':6.2508,	'maxy':6.2528 },
		'3439': { 'minx':-6.2697,	'miny':-6.2641,	'maxx':6.2508,	'maxy':6.2528 },
		'3440': { 'minx':-1.1856,	'miny':-2.0168,	'maxx':1.1925,	'maxy':2.1807 },
		'3441': { 'minx':-2.6945,	'miny':-2.0062,	'maxx':2.5297,	'maxy':2.1914 },
		'3442': { 'minx':-1.2818,	'miny':-1.3142,	'maxx':1.2894,	'maxy':1.326 },
		'3444': { 'minx':-0.5701,	'miny':-1.5137,	'maxx':0.5529,	'maxy':1.5608 },
		'3446': { 'minx':-1.9144,	'miny':-2.0137,	'maxx':1.6907,	'maxy':2.1838 },
		'3448': { 'minx':-0.175,	'miny':-1.5,	'maxx':0.175,	'maxy':1.5 },
		'3450': { 'minx':-2.2109,	'miny':-2.0168,	'maxx':2.202,	'maxy':2.1807 },
		'3452': { 'minx':-1.1856,	'miny':-2.0168,	'maxx':1.1925,	'maxy':2.1807 },
		'3454': { 'minx':-0.9292,	'miny':-0.929,	'maxx':0.9335,	'maxy':0.935 },
		'3456': { 'minx':-4.1028,	'miny':-2.7517,	'maxx':3.4036,	'maxy':2.7596 },
		'3458': { 'minx':-2.0507,	'miny':-1.6767,	'maxx':1.8776,	'maxy':1.6959 },
		'3460': { 'minx':-1.8905,	'miny':-2.1752,	'maxx':1.6503,	'maxy':2.664 },
		'3462': { 'minx':-3.4608,	'miny':-2.6966,	'maxx':3.2266,	'maxy':2.6765 },
		'3470': { 'minx':-2.7435,	'miny':-2.1025,	'maxx':2.7393,	'maxy':2.7579 },
		'3472': { 'minx':-0.8011,	'miny':-0.7704,	'maxx':0.8041,	'maxy':0.7516 },
		'3474': { 'minx':-1.4221,	'miny':-0.9636,	'maxx':1.4072,	'maxy':0.9686 },
		'3476': { 'minx':-1.562,	'miny':-0.8073,	'maxx':1.5577,	'maxy':0.8058 },
		'3478': { 'minx':-4.0053,	'miny':-0.5438,	'maxx':4.0176,	'maxy':0.5458 },
		'3480': { 'minx':-1.8193,	'miny':-2.0137,	'maxx':1.9459,	'maxy':2.0013 },
		'3481': { 'minx':-1.8905,	'miny':-1.8808,	'maxx':1.94,	'maxy':1.9043 },
		'3482': { 'minx':-2.115,	'miny':-1.6314,	'maxx':2.1682,	'maxy':1.6038 },
		'3483': { 'minx':-1.9026,	'miny':-1.3693,	'maxx':1.8312,	'maxy':1.2484 },
		'3484': { 'minx':-2.1193,	'miny':-1.5137,	'maxx':2.1316,	'maxy':1.5153 },
		'3486': { 'minx':-1.506,	'miny':-1.5182,	'maxx':1.517,	'maxy':1.5108 },
		'3488': { 'minx':-3.044,	'miny':-0.7478,	'maxx':3.0241,	'maxy':0.7514 },
		'3490': { 'minx':-2.5057,	'miny':-0.6882,	'maxx':2.5873,	'maxy':0.6518 },
		'3501': { 'minx':-2.852,	'miny':-3.5574,	'maxx':2.8258,	'maxy':3.3221 },
		'3502': { 'minx':-1.6984,	'miny':-2.1752,	'maxx':1.6797,	'maxy':2.1846 },
		'3503': { 'minx':-3.044,	'miny':-2.787,	'maxx':3.0564,	'maxy':3.0227 },
		'3504': { 'minx':-1.1216,	'miny':-1.1104,	'maxx':1.0953,	'maxy':1.0957 },
		'3506': { 'minx':-1.4583,	'miny':-2.6887,	'maxx':1.4677,	'maxy':2.5699 },
		'3507': { 'minx':-2.262,	'miny':-3.2279,	'maxx':2.0229,	'maxy':3.2312 },
		'3508': { 'minx':-1.6984,	'miny':-1.6767,	'maxx':1.6797,	'maxy':1.6959 },
		'3509': { 'minx':-1.7693,	'miny':-1.6387,	'maxx':1.7702,	'maxy':1.6422 },
		'3510': { 'minx':-1.9093,	'miny':-1.3037,	'maxx':1.9211,	'maxy':1.2908 },
		'3511': { 'minx':-1.7945,	'miny':-2.5606,	'maxx':1.6809,	'maxy':2.6044 },
		'3512': { 'minx':-1.6342,	'miny':-2.6059,	'maxx':1.5504,	'maxy':2.6056 },
		'3513': { 'minx':-3.012,	'miny':-2.6059,	'maxx':3.0234,	'maxy':2.6056 },
		'3514': { 'minx':-5.031,	'miny':-2.6284,	'maxx':5.0211,	'maxy':2.6067 },
		'3515': { 'minx':-1.4443,	'miny':-2.1887,	'maxx':1.4495,	'maxy':2.1938 },
		'3516': { 'minx':-1.1536,	'miny':-1.2009,	'maxx':1.1919,	'maxy':1.2106 },
		'3517': { 'minx':-1.442,	'miny':-2.1074,	'maxx':1.4517,	'maxy':2.0914 },
		'3518': { 'minx':-2.0956,	'miny':-0.8475,	'maxx':2.091,	'maxy':0.8569 },
		'3519': { 'minx':-0.8652,	'miny':-0.8611,	'maxx':0.8687,	'maxy':0.8432 },
		'3520': { 'minx':-1.6021,	'miny':-1.6089,	'maxx':1.6146,	'maxy':1.6033 },
		'3521': { 'minx':-1.8585,	'miny':-1.8581,	'maxx':1.8427,	'maxy':1.8583 },
		'3522': { 'minx':-1.6129,	'miny':-1.6037,	'maxx':1.6037,	'maxy':1.6084 },
		'3523': { 'minx':-1.6982,	'miny':-2.3567,	'maxx':1.7123,	'maxy':2.3709 },
		'3524': { 'minx':-3.2045,	'miny':-3.1951,	'maxx':3.1883,	'maxy':3.1947 },
		'3525': { 'minx':-4.4542,	'miny':-3.0362,	'maxx':4.4509,	'maxy':3.0297 },
		'3526': { 'minx':-2.5315,	'miny':-1.5408,	'maxx':2.5294,	'maxy':1.557 },
		'3527': { 'minx':-1.8906,	'miny':-1.9033,	'maxx':1.8752,	'maxy':1.9052 },
		'3528': { 'minx':-2.5315,	'miny':-1.5408,	'maxx':2.5294,	'maxy':1.557 },
		'3529': { 'minx':-1.3458,	'miny':-1.3596,	'maxx':1.3546,	'maxy':1.3491 },
		'3531': { 'minx':-1.7623,	'miny':-1.6767,	'maxx':1.7774,	'maxy':1.6959 },
		'3532': { 'minx':-1.4739,	'miny':-2.4473,	'maxx':1.4845,	'maxy':2.4416 },
		'3533': { 'minx':-1.2176,	'miny':-2.1752,	'maxx':1.2247,	'maxy':2.002 },
		'3534': { 'minx':-0.8973,	'miny':-2.0168,	'maxx':0.901,	'maxy':2.2035 },
		'3535': { 'minx':-1.2176,	'miny':-2.0168,	'maxx':1.2247,	'maxy':2.021 },
		'3536': { 'minx':-0.9421,	'miny':-1.4366,	'maxx':0.9527,	'maxy':1.4322 },
		'3537': { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		'3539': { 'minx':-1.8585,	'miny':-2.0846,	'maxx':1.8752,	'maxy':1.9541 },
		'3540': { 'minx':-1.6663,	'miny':-3.0589,	'maxx':1.7436,	'maxy':3.1911 },
		'3541': { 'minx':-2.6083,	'miny':-1.5952,	'maxx':2.6148,	'maxy':1.5943 },
		'3542': { 'minx':-2.5954,	'miny':-1.6089,	'maxx':2.5957,	'maxy':1.6033 },
		'3543': { 'minx':-1.6342,	'miny':-0.4532,	'maxx':1.6471,	'maxy':0.4546 },
		'3544': { 'minx':-1.1216,	'miny':-0.6118,	'maxx':1.0953,	'maxy':0.5916 },
		'3545': { 'minx':-2.6081,	'miny':-1.6037,	'maxx':2.6151,	'maxy':1.6084 },
		'3546': { 'minx':-2.6093,	'miny':-1.6037,	'maxx':2.6138,	'maxy':1.6084 },
		'3547': { 'minx':-2.6093,	'miny':-1.6037,	'maxx':2.6138,	'maxy':1.6084 },
		'3548': { 'minx':-1.09,		'miny':-1.1536,	'maxx':1.0947,	'maxy':1.0528 },
		'3549': { 'minx':-1.5061,	'miny':-3.8749,	'maxx':1.5488,	'maxy':3.9066 },
		'3550': { 'minx':-0.8652,	'miny':-3.2855,	'maxx':0.8687,	'maxy':3.29 },
		'3551': { 'minx':-1.6021,	'miny':-2.6059,	'maxx':1.6146,	'maxy':2.6056 },
		'3552': { 'minx':-0.8652,	'miny':-2.8552,	'maxx':1.2218,	'maxy':2.7724 },
		'3553': { 'minx':-1.0894,	'miny':-3.3082,	'maxx':1.1595,	'maxy':3.4053 },
		'3554': { 'minx':-2.7696,	'miny':-2.764,	'maxx':2.778,	'maxy':2.7704 },
		'3556': { 'minx':-1.5061,	'miny':-1.5636,	'maxx':1.5488,	'maxy':1.557 },
		'3557': { 'minx':-1.0254,	'miny':-3.3535,	'maxx':1.0303,	'maxy':3.3605 },
		'3558': { 'minx':-1.0894,	'miny':-3.3764,	'maxx':1.1595,	'maxy':3.361 },
		'3559': { 'minx':-1.3137,	'miny':-3.648,	'maxx':1.322,	'maxy':3.5547 },
		'3560': { 'minx':-2.852,	'miny':-3.1495,	'maxx':2.9226,	'maxy':3.1477 },
		'3561': { 'minx':-2.9481,	'miny':-3.4217,	'maxx':2.9568,	'maxy':3.3167 },
		'3562': { 'minx':-2.0956,	'miny':-0.5978,	'maxx':2.091,	'maxy':0.6056 },
		'3563': { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		'3564': { 'minx':-1.6021,	'miny':-1.6089,	'maxx':1.6465,	'maxy':1.6033 },
		'3565': { 'minx':-1.3778,	'miny':-3.1045,	'maxx':1.3871,	'maxy':3.0086 },
		'3566': { 'minx':-1.1216,	'miny':-0.6118,	'maxx':1.0953,	'maxy':0.5916 },
		'3567': { 'minx':-2.0964,	'miny':-1.0945,	'maxx':2.0902,	'maxy':1.1116 },
		'3568': { 'minx':-2.115,	'miny':-1.1104,	'maxx':2.1037,	'maxy':1.0957 },
		'3569': { 'minx':-1.3458,	'miny':-1.3596,	'maxx':1.3546,	'maxy':1.3491 },
		'3570': { 'minx':-3.1081,	'miny':-1.1104,	'maxx':3.025,	'maxy':1.0957 },
		'3571': { 'minx':-1.3137,	'miny':-1.3143,	'maxx':1.322,	'maxy':1.303 },
		'3572': { 'minx':-1.5701,	'miny':-1.6089,	'maxx':1.5821,	'maxy':1.6033 },
		'3573': { 'minx':-29.7675,	'miny':-6.0952,	'maxx':29.7664,	'maxy':6.0919 },
		'3574': { 'minx':-2.7693,	'miny':-2.7637,	'maxx':2.7783,	'maxy':2.7707 },
		'3576': { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		'3578': { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		'3579': { 'minx':-0.8011,	'miny':-0.8158,	'maxx':0.8042,	'maxy':0.8201 },
		'3580': { 'minx':-0.09,		'miny':-0.3,	'maxx':0.09,	'maxy':0.3 },
		'3583': { 'minx':-1.2177,	'miny':-2.8099,	'maxx':1.1925,	'maxy':2.794 },
		'3584': { 'minx':-1.3884,	'miny':-2.6038,	'maxx':1.4728,	'maxy':2.5162 },
		'3585': { 'minx':-0.5127,	'miny':-0.5212,	'maxx':0.514,	'maxy':0.5002 },
		'3586': { 'minx':-1.0254,	'miny':-0.5212,	'maxx':1.0303,	'maxy':0.5002 },
		'3587': { 'minx':-3.3968,	'miny':-3.3761,	'maxx':3.3866,	'maxy':3.3847 },
		'3588': { 'minx':-3.5973,	'miny':-3.1348,	'maxx':3.674,	'maxy':3.2307 },
		'3589': { 'minx':-0.596,	'miny':-2.5968,	'maxx':0.5914,	'maxy':2.5006 },
		'3590': { 'minx':-2.879,	'miny':-3.0183,	'maxx':2.8637,	'maxy':2.4292 },
		'3592': { 'minx':-1.6214,	'miny':-0.6027,	'maxx':1.5952,	'maxy':0.6006 },
		'3593': { 'minx':-10.1131,	'miny':-2.0983,	'maxx':10.1004,	'maxy':2.1007 },
		'3594': { 'minx':-1.8137,	'miny':-2.0983,	'maxx':1.8228,	'maxy':2.1007 },
		'3595': { 'minx':-2.07,		'miny':-0.6027,	'maxx':2.116,	'maxy':0.6006 },
		'3596': { 'minx':-0.5965,	'miny':-1.8446,	'maxx':0.5909,	'maxy':1.8491 },
		'3597': { 'minx':-1.4611,	'miny':-2.2794,	'maxx':1.4651,	'maxy':2.5843 },
		'3599': { 'minx':-1.2398,	'miny':-2.2796,	'maxx':1.2349,	'maxy':2.1731 },
		'3601': { 'minx':-0.731,	'miny':-0.6744,	'maxx':0.7457,	'maxy':0.7336 },
		'3603': { 'minx':-1.5253,	'miny':-1.6223,	'maxx':1.5298,	'maxy':2.0915 },
		'3605': { 'minx':-0.6314,	'miny':-1.2045,	'maxx':0.6523,	'maxy':1.2072 },
		'3607': { 'minx':-1.4611,	'miny':-1.3958,	'maxx':1.4651,	'maxy':1.4498 },
		'3609': { 'minx':-1.3971,	'miny':-2.0303,	'maxx':1.4963,	'maxy':2.0077 },
		'3613': { 'minx':-0.5064,	'miny':-0.5045,	'maxx':0.5203,	'maxy':0.5169 },
		'3615': { 'minx':-2.9032,	'miny':-0.852,	'maxx':2.9048,	'maxy':0.8523 },
		'3617': { 'minx':-9.4081,	'miny':-2.5062,	'maxx':9.4305,	'maxy':2.498 },
		'3619': { 'minx':-3.6365,	'miny':-0.6045,	'maxx':3.6361,	'maxy':0.6216 },
		'3621': { 'minx':-3.7565,	'miny':-0.6045,	'maxx':3.7768,	'maxy':0.6216 },
		'3623': { 'minx':-1.5253,	'miny':-1.4865,	'maxx':1.5298,	'maxy':1.4739 },
		'3625': { 'minx':-2.0064,	'miny':-1.9762,	'maxx':2.0183,	'maxy':1.9929 },
		'3627': { 'minx':-2.807,	'miny':-2.5968,	'maxx':2.8379,	'maxy':2.7521 },
		'3629': { 'minx':-0.5064,	'miny':-0.5045,	'maxx':0.5203,	'maxy':0.5169 },
		'3631': { 'minx':-0.15,		'miny':-0.15,	'maxx':0.15,	'maxy':0.15 },
		'3632': { 'minx':-0.09,		'miny':-1,	'maxx':0.09,	'maxy':1 },
		'3634': { 'minx':-1.7176,	'miny':-1.5998,	'maxx':1.7572,	'maxy':1.749 },
		'3636': { 'minx':-3.3518,	'miny':-0.852,	'maxx':3.3662,	'maxy':0.8523 },
		'3637': { 'minx':-1.9739,	'miny':-1.9623,	'maxx':0.3762,	'maxy':1.9607 },
		'3638': { 'minx':-2.1982,	'miny':-0.852,	'maxx':2.2146,	'maxy':0.8523 },
		'3640': { 'minx':-2.1021,	'miny':-2.0983,	'maxx':2.1168,	'maxy':2.1007 },
		'3641': { 'minx':-2.3584,	'miny':-2.3475,	'maxx':2.346,	'maxy':2.3574 },
		'3642': { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6006 },
		'3643': { 'minx':-0.09,		'miny':-0.5,	'maxx':0.09,	'maxy':0.5 },
		'3644': { 'minx':-1.5253,	'miny':-0.6027,	'maxx':1.5298,	'maxy':0.6007 },
		'3645': { 'minx':-0.596,	'miny':-0.852,	'maxx':0.5914,	'maxy':0.8523 },
		'3646': { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6007 },
		'3647': { 'minx':-0.3076,	'miny':-0.6027,	'maxx':0.3017,	'maxy':0.6007 },
		'3648': { 'minx':-0.8524,	'miny':-0.6027,	'maxx':0.8495,	'maxy':0.6006 },
		'3649': { 'minx':-2.0058,	'miny':-0.6027,	'maxx':2.019,	'maxy':0.6007 },
		'3650': { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6006 },
		'3651': { 'minx':-1.4932,	'miny':-0.784,	'maxx':1.4651,	'maxy':0.829 },
		'3653': { 'minx':-3.0314,	'miny':-0.6027,	'maxx':3.0038,	'maxy':0.6006 },
		'3701': { 'minx':-1.4931,	'miny':-2.2569,	'maxx':1.4333,	'maxy':2.8576 },
		'3703': { 'minx':-1.2048,	'miny':-1.1919,	'maxx':1.2052,	'maxy':1.197 },
		'3705': { 'minx':-1.6855,	'miny':-1.6904,	'maxx':1.6927,	'maxy':1.6822 },
		'3707': { 'minx':-3.0314,	'miny':-3.0047,	'maxx':3.0038,	'maxy':3.0153 },
		'3709': { 'minx':-1.6855,	'miny':-1.6904,	'maxx':1.6927,	'maxy':1.6822 },
	}

	def __init__(self, iface):
		self.iface = iface
		self.pointMarkerLayer = None
		self.areaMarkerLayer = None
		self.alkisGroup = None

	def initGui(self):
		self.confAction = QAction(QIcon(":/plugins/alkis/logo.png"), "Konfiguration", self.iface.mainWindow())
		self.confAction.setWhatsThis("Konfiguration der ALKIS-Erweiterung")
		self.confAction.setStatusTip("Konfiguration der ALKIS-Erweiterung")
		self.confAction.triggered.connect(self.conf)

		self.searchAction = QAction(QIcon(":/plugins/alkis/find.png"), "Beschriftung suchen", self.iface.mainWindow())
		self.searchAction.setWhatsThis("ALKIS-Beschriftung suchen")
		self.searchAction.setStatusTip("ALKIS-Beschriftung suchen")
		self.searchAction.triggered.connect(self.search)
		self.iface.addToolBarIcon( self.searchAction )

		if hasattr(self.iface, "addPluginToDatabaseMenu"):
			self.iface.addPluginToDatabaseMenu("&ALKIS", self.searchAction)
			self.iface.addPluginToDatabaseMenu("&ALKIS", self.confAction)
		else:
			self.iface.addPluginToMenu("&ALKIS", self.searchAction)
			self.iface.addPluginToMenu("&ALKIS", self.confAction)

		self.pointInfoAction = QAction(QIcon(":/plugins/alkis/info.png"), u"Flurstücksabfrage (Punkt)", self.iface.mainWindow())
		self.pointInfoAction.activated.connect( self.setPointInfoTool )
		self.iface.addToolBarIcon( self.pointInfoAction )
		self.pointInfoTool = ALKISPointInfo( self )

		self.polygonInfoAction = QAction(QIcon(":/plugins/alkis/pinfo.png"), u"Flurstücksabfrage (Polygon)", self.iface.mainWindow())
		self.polygonInfoAction.activated.connect( self.setPolygonInfoTool )
		self.iface.addToolBarIcon( self.polygonInfoAction )
		self.polygonInfoTool = ALKISPolygonInfo( self )

		self.queryOwnerAction = QAction(QIcon(":/plugins/alkis/eigner.png"), "Eigner abfragen", self.iface.mainWindow())
		self.queryOwnerAction.triggered.connect( self.setQueryOwnerTool )
		self.iface.addToolBarIcon( self.queryOwnerAction )
		self.queryOwnerInfoTool = ALKISOwnerInfo( self )

		self.clearAction = QAction(QIcon(":/plugins/alkis/clear.png"), "Hervorhebungen entfernen", self.iface.mainWindow())
		self.clearAction.setWhatsThis("Hervorhebungen entfernen")
		self.clearAction.setStatusTip("Hervorhebungen entfernen")
		self.clearAction.triggered.connect(self.clearHighlight)
		self.iface.addToolBarIcon( self.clearAction )

		if not self.register():
			self.iface.mainWindow().initializationCompleted.connect( self.register )

	def unload(self):
		#try:
			self.iface.removeToolBarIcon( self.pointInfoAction )
			self.iface.removeToolBarIcon( self.polygonInfoAction )
			self.iface.removeToolBarIcon( self.queryOwnerAction )

			if self.confAction:
				self.confAction.deleteLater()
				self.confAction = None
			if self.searchAction:
				self.searchAction.deleteLater()
				self.searchAction = None

			if self.clearAction:
				self.clearAction.deleteLater()
				self.clearAction = None

			if self.pointInfoTool:
				self.pointInfoTool.deleteLater()
				self.pointInfoTool = None

			if self.polygonInfoTool:
				self.polygonInfoTool.deleteLater()
				self.polygonInfoTool = None

			if self.queryOwnerInfoTool:
				self.queryOwnerInfoTool.deleteLater()
				self.queryOwnerInfoTool = None
		#except:
		#	pass

	def conf(self):
		dlg = Conf(self)
		dlg.exec_()

	def search(self):
		if self.pointMarkerLayer is None:
			(layerId,ok) = QgsProject.instance().readEntry( "alkis", "/pointMarkerLayer" )
			if ok:
				self.pointMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

		if self.pointMarkerLayer is None:
			QMessageBox.warning( None, "ALKIS", u"Fehler: Punktmarkierungslayer nicht gefunden!\n" )
			return

		(text,ok) = QInputDialog.getText( self.iface.mainWindow(), u"Beschriftung suchen", u"Suchbegriff" )
		if not ok:
			return

		if text == "":
			text = "false"
		else:
			text = u"text LIKE '%%%s%%'" % text.replace("'", "''")

		self.pointMarkerLayer.setSubsetString( text )

		currentLayer = self.iface.activeLayer()

		self.iface.setActiveLayer( self.pointMarkerLayer )
		self.iface.zoomToActiveLayer()
		self.iface.setActiveLayer( currentLayer )

	def setScale(self, layer, d):
		if d['min'] is None and d['max'] is None:
			return

		if not d['min'] is None: layer.setMinimumScale(d['min'])
		if not d['max'] is None: layer.setMaximumScale(d['max'])

		layer.toggleScaleBasedVisibility(True)

	def categoryLabel(self, d, sn):
		qDebug( "categories: %s" % d['classes'] )
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

	def alkisimport(self):
		(db,conninfo) = self.opendb()
		if db is None:
			return

		self.iface.mapCanvas().setRenderFlag( False )

		qry = QSqlQuery(db)

		qs = QSettings( "QGIS", "QGIS2" )
		svgpaths = qs.value( "svg/searchPathsForSVG", "", type=str ).split("|")
		svgpath = os.path.dirname(__file__) + "/svg"
		if not svgpath.upper() in map(unicode.upper, svgpaths):
			svgpaths.append( svgpath )
			qs.setValue( "svg/searchPathsForSVG", "|".join( svgpaths ) )

		self.alkisGroup = self.iface.legendInterface().addGroup( "ALKIS", False )

		markerGroup = self.iface.legendInterface().addGroup( "Markierungen", False, self.alkisGroup )

		nGroups = 0
		for d in alkisplugin.themen:
			t = d['name']
			thisGroup = self.iface.legendInterface().addGroup( t, False, self.alkisGroup )
			nLayers = 0

			qDebug( "Thema: %s" % t )

			sql = (u"SELECT signaturnummer,r,g,b FROM alkis_flaechen"
			       u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
			       u" WHERE EXISTS (SELECT * FROM po_polygons WHERE thema='%s'"
			       u" AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer)"
                               u" ORDER BY darstellungsprioritaet") % t
			qDebug( "SQL: %s" % sql )
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
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=25832 table=po_polygons (polygon) sql=thema='%s'" % (conninfo, t),
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

			sql = (u"SELECT"
			       u" signaturnummer,r,g,b,(SELECT avg(strichstaerke)/100 FROM alkis_linie WHERE alkis_linie.signaturnummer=alkis_linien.signaturnummer) AS ss"
			       u" FROM alkis_linien"
			       u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
			       u" WHERE EXISTS (SELECT * FROM po_polygons WHERE thema='%s'"
			       u" AND po_polygons.sn_randlinie=alkis_linien.signaturnummer)"
			       u" ORDER BY darstellungsprioritaet" ) % t
			qDebug( "SQL: %s" % sql )
			if qry.exec_(sql):
				r = QgsCategorizedSymbolRendererV2( "sn_randlinie" )
				r.deleteAllCategories()

				n = 0
				while qry.next():
					sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )

					sn = qry.value(0)
					c = QColor( int(qry.value(1)), int(qry.value(2)), int(qry.value(3)) )
					sym.changeSymbolLayer( 0, QgsSimpleFillSymbolLayerV2( c, Qt.NoBrush, c, Qt.SolidLine, float(qry.value(4)) ) )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )

					r.addCategory( QgsRendererCategoryV2( sn, sym, self.categoryLabel(d, sn) ) )
					n += 1

				if n>0:
					layer = self.iface.addVectorLayer(
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=25832 table=po_polygons (polygon) sql=thema='%s'" % (conninfo, t),
						u"Grenzen (%s)" % t,
						"postgres" )
					layer.setReadOnly()
					layer.setRendererV2( r )
					self.setScale( layer, d['outline'] )
					self.iface.legendInterface().refreshLayerSymbology( layer )
					self.iface.legendInterface().moveLayer( layer, thisGroup )
					nLayers += 1
				else:
					del r
			else:
				QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )

			sql = (u"SELECT"
			       u" signaturnummer,r,g,b,(SELECT avg(strichstaerke)/100 FROM alkis_linie WHERE alkis_linie.signaturnummer=alkis_linien.signaturnummer) AS ss"
			       u" FROM alkis_linien"
                               u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
			       u" WHERE EXISTS (SELECT * FROM po_lines WHERE thema='%s'"
			       u" AND po_lines.signaturnummer=alkis_linien.signaturnummer)"
			       u" ORDER BY darstellungsprioritaet" ) % t
			qDebug( "SQL: %s" % sql )
			if qry.exec_( sql ):
				r = QgsCategorizedSymbolRendererV2( "signaturnummer" )
				r.deleteAllCategories()

				n = 0
				while qry.next():
					sym = QgsSymbolV2.defaultSymbol( QGis.Line )

					sn = qry.value(0)
					sym.setColor( QColor( int(qry.value(1)), int(qry.value(2)), int(qry.value(3)) ) )
					sym.setWidth( float(qry.value(4)) )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )

					r.addCategory( QgsRendererCategoryV2( sn, sym, self.categoryLabel(d, sn) ) )
					n += 1

				if n>0:
					layer = self.iface.addVectorLayer(
							u"%s estimatedmetadata=true key='ogc_fid' type=MULTILINESTRING srid=25832 table=po_lines (line) sql=thema='%s'" % (conninfo, t),
							u"Linien (%s)" % t,
							"postgres" )
					layer.setReadOnly()
					layer.setRendererV2( r )
					self.setScale( layer, d['line'] )
					self.iface.legendInterface().refreshLayerSymbology( layer )
					self.iface.legendInterface().moveLayer( layer, thisGroup )
					nLayers += 1
				else:
					del r
			else:
				QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )

			sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE thema='%s'" % t
			qDebug( "SQL: %s" % sql )
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
					qDebug( "symlayer.setSize %s:%f" % (sn, w) )
					symlayer.setSize( w )
					symlayer.setOffset( QPointF( -x, -y ) )

					sym = QgsMarkerSymbolV2( [symlayer] )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )
					qDebug( "sym.setSize %s:%f" % (sn, w) )
					sym.setSize( w )

					r.addCategory( QgsRendererCategoryV2( "%s" % sn, sym, self.categoryLabel(d, sn) ) )
					n += 1

				qDebug( "classes: %d" % n )
				if n>0:
					layer = self.iface.addVectorLayer(
							u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=25832 table=\"(SELECT ogc_fid,gml_id,thema,layer,signaturnummer,-drehwinkel_grad AS drehwinkel_grad,point FROM po_points WHERE thema='%s')\" (point) sql=" % (conninfo, t),
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

			n = 0
			labelGroup = -1
			for i in range(2):
				geom = "point" if i==0 else "line"
				geomtype = "MULTIPOINT" if i==0 else "MULTILINESTRING"

				if not qry.exec_( "SELECT count(*) FROM po_labels WHERE thema='%s' AND NOT %s IS NULL" % (t,geom) ):
					QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
					continue

				if not qry.next() or int(qry.value(0))==0:
					continue

				if n==1:
					labelGroup = self.iface.legendInterface().addGroup( "Beschriftungen", False, thisGroup )
					self.iface.legendInterface().moveLayer( layer, labelGroup )

				uri = ( conninfo +
                                    u" estimatedmetadata=true key='ogc_fid' type=%s srid=25832 table="
				    u"\"("
				    u"SELECT"
				    u" ogc_fid"
				    u",%s"
				    u",st_x(point) AS tx"
				    u",st_y(point) AS ty"
				    u",drehwinkel_grad AS tangle"
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
				    u",CASE WHEN font_umn LIKE '%%italic%%' THEN 1 ELSE 0 END AS italic"
				    u",CASE WHEN font_umn LIKE '%%bold%%' THEN 1 ELSE 0 END AS bold"
				    u" FROM po_labels"
				    u" WHERE thema='%s'"
				    u")\" (%s) sql=" ) % (geomtype,geom,t,geom)

				qDebug( "URI: %s" % uri )

				layer = self.iface.addVectorLayer(
					uri,
					u"Beschriftungen (%s)" % t,
					"postgres" )
				layer.setReadOnly()

				self.setScale( layer, d['label'] )

                                sym = QgsMarkerSymbolV2()
                                sym.setSize( 0.0 );
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
				try:
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Size, True, False, "", "tsize" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Family, True, False, "", "family" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Italic, True, False, "", "italic" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Bold, True, False, "", "bold" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionX, True, False, "", "tx" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionY, True, False, "", "ty" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Hali, True, False, "", "halign" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Vali, True, False, "", "valign" )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Rotation, True, False, "", "tangle" )
				except:
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Size, layer.dataProvider().fieldNameIndex("tsize") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Family, layer.dataProvider().fieldNameIndex("family") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Italic, layer.dataProvider().fieldNameIndex("italic") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Bold, layer.dataProvider().fieldNameIndex("bold") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionX, layer.dataProvider().fieldNameIndex("tx") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.PositionY, layer.dataProvider().fieldNameIndex("ty") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Hali, layer.dataProvider().fieldNameIndex("halign") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Vali, layer.dataProvider().fieldNameIndex("valign") )
					lyr.setDataDefinedProperty( QgsPalLayerSettings.Rotation, layer.dataProvider().fieldNameIndex("tangle") )
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
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=25832 table=po_labels (point) sql=false" % conninfo,
						u"Punktmarkierung",
						"postgres" )

			sym = QgsMarkerSymbolV2()
			sym.setColor( Qt.yellow )
			sym.setSize( 20.0 )
			sym.setOutputUnit( QgsSymbolV2.MM )
			sym.setAlpha( 0.5 )
			self.pointMarkerLayer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
			self.iface.legendInterface().moveLayer( self.pointMarkerLayer, markerGroup )

			self.areaMarkerLayer = self.iface.addVectorLayer(
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=25832 table=po_polygons (polygon) sql=false" % conninfo,
						u"Flächenmarkierung",
						"postgres" )

			sym = QgsMarkerSymbolV2()
			sym.setColor( Qt.yellow )
			sym.setSize( 20.0 )
			sym.setOutputUnit( QgsSymbolV2.MM )
			sym.setAlpha( 0.5 )
			self.areaMarkerLayer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
			self.iface.legendInterface().moveLayer( self.areaMarkerLayer, markerGroup )

			QgsProject.instance().writeEntry( "alkis", "/pointMarkerLayer", self.pointMarkerLayer.id() )
			QgsProject.instance().writeEntry( "alkis", "/areaMarkerLayer", self.areaMarkerLayer.id() )
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
				qDebug( "connected" )
			else:
				qDebug( "not connected" )
		else:
			return False

	def opendb(self):
		s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )

		service = s.value( "service", "" )
		host = s.value( "host", "" )
		port = s.value( "port", "5432" )
		dbname = s.value( "dbname", "" )
		uid = s.value( "uid", "" )
		pwd = s.value( "pwd", "" )

		uri = QgsDataSourceURI()

		if service == "":
			uri.setConnection( host, port, dbname, uid, pwd )
		else:
			uri.setConnection( service, dbname, uid, pwd )

		conninfo = uri.connectionInfo()

		db = QSqlDatabase.addDatabase( "QPSQL" )
		db.setConnectOptions( conninfo )

		if not db.open():
			while not db.open():
				if not QgsCredentials.instance().get( conninfo, uid, pwd, u"Datenbankverbindung schlug fehl [%s]" % db.lastError().text() ):
					return (None,None)

				uri.setUsername(uid)
				uri.setPassword(pwd)

				db.setConnectOptions( uri.connectionInfo() )

			QgsCredentials.instance().put( conninfo, uid, pwd )

		return (db,conninfo)


	def message(self, msg):
		if msg.startswith("ALKISDRAW"):
			(prefix,hatch,window,qry) = msg.split(' ', 3)
#			qDebug( u"prefix:%s hatch:%s window:%s qry:%s" % (prefix,hatch,window,qry) )
			if qry.startswith("ids:"):
				self.highlight( "gml_id in (%s)" % qry[4:], True )
			elif qry.startswith("where:"):
				self.highlight( qry[6:], True )
			elif qry.startswith("select "):
				self.highlight( "gml_id in (%s)" % qry, True )
#			else:
#				qDebug( u"ALKIS: Ignorierte Nachricht:%s" % msg )
#		else:
#			qDebug( u"ALKIS: Ignorierte Nachricht:%s" % msg )

	def clearHighlight(self):
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
		if self.areaMarkerLayer is None:
			(layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
			if ok:
				self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

		if self.areaMarkerLayer is None:
			QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )
			return

		(db,conninfo) = self.opendb()
		if db is None:
			return

		qry = QSqlQuery(db)

		fs = []

		if not qry.exec_(
			u"SELECT "
			u"gml_id"
			u",to_char(land,'fm00') || to_char(gemarkungsnummer,'fm0000') || "
			u"'-' || to_char(flurnummer,'fm000') ||"
			u"'-' || to_char(zaehler,'fm00000') || '/' || to_char(coalesce(nenner,0),'fm000')"
			u" FROM ax_flurstueck"
			u" WHERE endet IS NULL"
			u" AND (%s)" % where
			):
			QMessageBox.critical( None, u"Fehler", u"Konnte Abfrage nicht ausführen.\nSQL:%s\nFehler:%s" % ( qry.lastQuery(), qry.lastError().text() ) )
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

		if zoomTo and qry.exec_( u"SELECT st_extent(wkb_geometry) FROM ax_flurstueck WHERE gml_id IN ('" + "','".join( gmlids ) + "')" ) and qry.next():
			bb = qry.value(0)[4:-1]
			(p0,p1) = bb.split(",")
			(x0,y0) = p0.split(" ")
			(x1,y1) = p1.split(" ")
			qDebug( "x0:%s y0:%s x1:%s y1:%s" % (x0, y0, x1, y1) )
			rect = QgsRectangle( float(x0), float(y0), float(x1), float(y1) )

			r = self.iface.mapCanvas().mapRenderer()
			if r.hasCrsTransformEnabled():
				t = QgsCoordinateTransform( QgsCoordinateReferenceSystem(25832), r.destinationCrs() )
				rect = t.transform( rect )

			qDebug( "rect:%s" % rect.toString() )

			self.iface.mapCanvas().setExtent( rect )
			self.iface.mapCanvas().refresh()

		return fs


class ALKISPointInfo(QgsMapTool):
	def __init__(self, plugin):
		QgsMapTool.__init__(self, plugin.iface.mapCanvas())
		self.plugin = plugin
		self.iface = plugin.iface
		self.cursor = QCursor( QPixmap( ["16 16 3 1",
					"      c None",
					".     c #FF0000",
					"+     c #FFFFFF",
					"                ",
					"       +.+      ",
					"      ++.++     ",
					"     +.....+    ",
					"    +.     .+   ",
					"   +.   .   .+  ",
					"  +.    .    .+ ",
					" ++.    .    .++",
					" ... ...+... ...",
					" ++.    .    .++",
					"  +.    .    .+ ",
					"   +.   .   .+  ",
					"   ++.     .+   ",
					"    ++.....+    ",
					"      ++.++     ",
					"       +.+      "] ) )

		self.crs = QgsCoordinateReferenceSystem(25832)

		self.areaMarkerLayer = None

	def canvasPressEvent(self,event):
		pass

	def canvasMoveEvent(self,event):
		pass

	def canvasReleaseEvent(self,e):
		point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( e.x(), e.y() )

		r = self.iface.mapCanvas().mapRenderer()
		if r.hasCrsTransformEnabled():
			t = QgsCoordinateTransform( r.destinationCrs(), self.crs )
			point = t.transform( point )

		if self.areaMarkerLayer is None:
			(layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
			if ok:
				self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

		if self.areaMarkerLayer is None:
			QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )
			return

		QApplication.setOverrideCursor( Qt.WaitCursor )

		fs = self.plugin.highlight( u"st_contains(wkb_geometry,st_geomfromewkt('SRID=25832;POINT(%.3lf %.3lf)'::text))" % ( point.x(), point.y() ) )

		if len(fs) == 0:
			QApplication.restoreOverrideCursor()
			QMessageBox.information( None, u"Fehler", u"Kein Flurstück gefunden." )
			return

		try:
			s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
			sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
			sock.connect( ( s.value( "apphost", "localhost" ), int( s.value( "appport", "6102" ) ) ) )
			sock.send( "NORGIS_MAIN#EDBS#ALBKEY#%s#" % fs[0]['flsnr'] )
			sock.close()

			if win32:
				s = QSettings( "norBIT", "EDBSgen/PRO" )
				window = win32gui.FindWindow( None, s.value( "albWin", "norGIS" ) )
				win32gui.SetForegroundWindow( window )
		except:
			QMessageBox.information( None, u"Fehler", u"Verbindung schlug fehl." )

		QApplication.restoreOverrideCursor()



class ALKISPolygonInfo(QgsMapTool):
	def __init__(self, plugin):
		QgsMapTool.__init__(self, plugin.iface.mapCanvas())
		self.plugin = plugin
		self.iface = plugin.iface
		self.cursor = QCursor( QPixmap( ["16 16 3 1",
					"      c None",
					".     c #FF0000",
					"+     c #FFFFFF",
					"                ",
					"       +.+      ",
					"      ++.++     ",
					"     +.....+    ",
					"    +.     .+   ",
					"   +.   .   .+  ",
					"  +.    .    .+ ",
					" ++.    .    .++",
					" ... ...+... ...",
					" ++.    .    .++",
					"  +.    .    .+ ",
					"   +.   .   .+  ",
					"   ++.     .+   ",
					"    ++.....+    ",
					"      ++.++     ",
					"       +.+      "] ) )

		self.crs = QgsCoordinateReferenceSystem(25832)
		self.rubberBand = QgsRubberBand( self.iface.mapCanvas(), QGis.Polygon )
		self.areaMarkerLayer = None

	def canvasPressEvent(self,e):
		pass

	def canvasMoveEvent(self,e):
		if self.rubberBand.numberOfVertices()>0:
		  point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( e.x(), e.y() )
		  self.rubberBand.movePoint( point )

	def canvasReleaseEvent(self,e):
		point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( e.x(), e.y() )
		if e.button() == Qt.LeftButton:
			self.rubberBand.addPoint( point )
			return

		QApplication.setOverrideCursor( Qt.WaitCursor )

		if self.rubberBand.numberOfVertices()>=3:
			g = self.rubberBand.asGeometry()

			r = self.iface.mapCanvas().mapRenderer()
			if r.hasCrsTransformEnabled():
				t = QgsCoordinateTransform( r.destinationCrs(), self.crs )
				g.transform( t )

			self.rubberBand.reset( QGis.Polygon )

			fs = self.plugin.highlight( "st_intersects(wkb_geometry,st_geomfromewkt('SRID=25832;POLYGON((%s))'::text))" % ",".join( map ( lambda p : "%.3lf %.3lf" % ( p[0], p[1] ), g.asPolygon()[0] ) ) )

			if len(fs) == 0:
				QApplication.restoreOverrideCursor()
				QMessageBox.information( None, u"Fehler", u"Keine Flurstücke gefunden." )
				return

			gmlids = []
			for e in fs:
				gmlids.append( e['gmlid'] )

			try:
				s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
				for i in range(0, len(fs)):
					sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
					sock.connect( ( s.value( "apphost", "localhost" ), int( s.value( "appport", "6102" ) ) ) )
					sock.send( "NORGIS_MAIN#EDBS#ALBKEY#%s#%d#" % (fs[i]['flsnr'], 0 if i+1 == len(fs) else 1 ) )
					sock.close()

				if win32:
					s = QSettings( "norBIT", "EDBSgen/PRO" )
					window = win32gui.FindWindow( None, s.value( "albWin", "norGIS" ) )
					win32gui.SetForegroundWindow( window )

			except:
				QMessageBox.information( None, u"Fehler", u"Verbindung schlug fehl." )
		else:
			self.rubberBand.reset( QGis.Polygon )

		QApplication.restoreOverrideCursor()

class ALKISOwnerInfo(QgsMapTool):
	def __init__(self, plugin):
		QgsMapTool.__init__(self, plugin.iface.mapCanvas())
		self.plugin = plugin
		self.iface = plugin.iface
		self.cursor = QCursor( QPixmap( ["16 16 3 1",
					"      c None",
					".     c #FF0000",
					"+     c #FFFFFF",
					"                ",
					"       +.+      ",
					"      ++.++     ",
					"     +.....+    ",
					"    +.     .+   ",
					"   +.   .   .+  ",
					"  +.    .    .+ ",
					" ++.    .    .++",
					" ... ...+... ...",
					" ++.    .    .++",
					"  +.    .    .+ ",
					"   +.   .   .+  ",
					"   ++.     .+   ",
					"    ++.....+    ",
					"      ++.++     ",
					"       +.+      "] ) )

		self.crs = QgsCoordinateReferenceSystem(25832)
		self.areaMarkerLayer = None

	def canvasPressEvent(self,e):
		pass

	def canvasMoveEvent(self,e):
		pass

	def fetchall(self, db, sql):
		rows = []

		qry = QSqlQuery(db)

		if qry.exec_(sql):
			rec = qry.record()

			while qry.next():
				row = {}

				for i in range(0, rec.count()):
					v = "%s" % qry.value(i)
					if v=="NULL":
						v=''
					row[ rec.fieldName(i) ] = v.strip()

				rows.append( row )
		else:
			qDebug( "Exec failed: " + qry.lastError().text() )

		return rows


	def canvasReleaseEvent(self,e):
                point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( e.x(), e.y() )

                r = self.iface.mapCanvas().mapRenderer()
                if r.hasCrsTransformEnabled():
                        t = QgsCoordinateTransform( r.destinationCrs(), self.crs )
                        point = t.transform( point )

                if self.areaMarkerLayer is None:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if self.areaMarkerLayer is None:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )
                        return

		try:
			QApplication.setOverrideCursor( Qt.WaitCursor )

			fs = self.plugin.highlight( u"st_contains(wkb_geometry,st_geomfromewkt('SRID=25832;POINT(%.3lf %.3lf)'::text))" % ( point.x(), point.y() ) )

			if len(fs) == 0:
				QApplication.restoreOverrideCursor()
				QMessageBox.information( None, u"Fehler", u"Kein Flurstück gefunden." )
				return
		finally:
			QApplication.restoreOverrideCursor()

		info = Info( self.getPage(fs) )
		info.setWindowTitle( "Flurstücksnachweis" )
		info.exec_()


	def getPage(self,fs):
		(db,conninfo) = self.plugin.opendb()
		if db is None:
			return

		qry = QSqlQuery(db)
		if qry.exec_("SELECT 1 FROM pg_attribute WHERE attrelid=(SELECT oid FROM pg_class WHERE relname='eignerart') AND attname='anteil'") and qry.next():
			exists_ea_anteil = qry.value(0) == 1
		else:
			exists_ea_anteil = False

		html=""
		for i in range(0, len(fs)):
			flsnr = fs[i]['flsnr']

			best = self.fetchall( db, ("SELECT "
				+ "ea.bvnr"
				+ ",'' as pz"
				+ ",(SELECT eignerart FROM eign_shl WHERE ea.b=b) as eignerart"
				+ ",%s as anteil"
				+ ",ea.ff_stand AS zhist"
				+ ",b.bestdnr"
				+ ",b.gbbz"
				+ ",b.gbblnr"
				+ ",b.bestfl"
				+ ",b.ff_stand AS bhist"
				+ " FROM eignerart ea"
				+ " JOIN bestand b ON ea.bestdnr = b.bestdnr"
				+ " WHERE ea.flsnr = '%s'"
				+ " ORDER BY zhist,bhist,b") % ("ea.anteil" if exists_ea_anteil else "''", flsnr)
				)

			res = self.fetchall( db, "SELECT f.*,g.gemarkung FROM flurst f LEFT OUTER JOIN gema_shl g ON (f.gemashl=g.gemashl) WHERE f.flsnr='%s' AND f.ff_stand=0" % flsnr )
			res = res[0]

			res['datum'] = time.strftime( "%d. %B %Y" )
			res['hist'] = 0

			res['str']  = self.fetchall( db, "SELECT sstr.strname,str.hausnr FROM str_shl sstr JOIN strassen str ON str.strshl=sstr.strshl WHERE str.flsnr='%s' AND str.ff_stand=0" % flsnr )
			res['nutz'] = self.fetchall( db, "SELECT n21.*, nu.nutzshl, nu.nutzung FROM nutz_21 n21, nutz_shl nu WHERE n21.flsnr='%s' AND n21.nutzsl=nu.nutzshl AND n21.ff_stand=0" % flsnr )
			res['klas'] = self.fetchall( db, "SELECT kl.*, kls.klf_text FROM klas_3x kl, kls_shl kls WHERE kl.flsnr='%s' AND kl.klf=kls.klf AND kl.ff_stand=0" % flsnr )
			res['afst'] = self.fetchall( db, "SELECT au.*, af.afst_txt FROM ausfst au,afst_shl af WHERE au.flsnr='%s' AND au.ausf_st=af.ausf_st AND au.ff_stand=0" % flsnr )
			res['best'] = self.fetchall( db, "SELECT ea.bvnr,'' as pz,(SELECT eignerart FROM eign_shl WHERE ea.b = b) as eignerart,%s as anteil,ea.ff_stand AS zhist,b.bestdnr,b.gbbz,b.gbblnr,b.bestfl,b.ff_stand AS bhist FROM eignerart ea JOIN bestand b ON ea.bestdnr = b.bestdnr WHERE ea.flsnr='%s' ORDER BY zhist,bhist,b" %
								("ea.anteil" if exists_ea_anteil else "''", flsnr) )

			for b in res['best']:
				b['bse'] = self.fetchall( db, "SELECT * FROM eigner WHERE bestdnr='%s' AND ff_stand=0" % b['bestdnr'] )

			for k,v in res.iteritems():
				qDebug( "%s:%s\n" % ( k, unicode(v) ) )

			html = u"""
<HTML xmlns="http://www.w3.org/1999/xhtml">
  <HEAD>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  </HEAD>
  <BODY>
<style>
.fls_tab{width:100%%;empty-cells:show}
.fls_time{text-align:right;width:100%%}
.fls_headline_col{background-color:#EEEEEE;width:100%%;height:30px;text-align:center;}
.fls_headline{font-weight:bold;font-size:24px;}
.fls_col_names{font-weight:bold;}
.fls_col_values{vertical-align:top;}
.fls_bst{width:100%%;empty-cells:show}
.fls_hr{border:dotted 1px;color:#080808;}
</style>

<TABLE class="fls_tab" border="0">
    <TR><TD>Flurst&uuml;cksnachweis</TD><TD class="fls_time" colspan="6"><span>%(datum)s</TD></TR>
    <TR><TD colspan="7"><hr style="width:100%%"></TD></TR>
    <TR class="fls_headline_col">
        <TD colspan="7"><span class="fls_headline">Flurst&uuml;cksnachweis<span></TD>
    </TR>
    <TR><TD colspan="7">&nbsp;</TD></TR>
    <TR>
        <TD colspan="7"><h3>Flurst&uuml;ck<hr style="width:100%%"></h3></TD>
    </TR>
    <TR class="fls_col_names">
        <TD width="15%%">Gemarkung</TD>
        <TD width="6%%">Flur</TD>
        <TD width="15%%">Flurst&uuml;ck</TD>
        <TD width="20%%">Flurkarte</TD>
        <TD width="17%%">Entstehung</TD>
        <TD width="17%%">Fortf&uuml;hrung</TD>
        <TD width="5%%">Fl&auml;che</TD>
    </TR>
    <TR class="fls_col_values">
        <TD>%(gemashl)s<br>%(gemarkung)s</TD>
        <TD>%(flr)s</TD>
        <TD>%(flsnrk)s</TD>
        <TD>%(flurknr)s</TD>
        <TD>%(entst)s</TD>
        <TD>%(fortf)s</TD>
        <TD>%(flsfl)s m&sup2;</TD>
    </TR>
</TABLE>
""" % res

			if res['blbnr']:
				html += """
<TABLE border="0" class="fls_tab">
    <TR class="fls_col_names">
        <TD width="21%%"></TD>
        <TD width="79%%">Baulastenblattnr.</TD>
    </TR>
    <TR class="fls_col_values">
        <TD></TD>
        <TD>%(blbnr)s</TD>
    </TR>
</TABLE>
""" % res

			if res['lagebez'] or res['anl_verm']:
				html += """
<TABLE border="0" class="fls_tab">
    <TR class="fls_col_names">
        <TD width="21%%"></TD>
        <TD width="52%%">Lage</TD>
        <TD width="27%%">Anliegervermerk</TD>
    </TR>
    <TR class="fls_col_values">
        <TD></TD>
        <TD>%(lagebez)s</TD>
        <TD>%(anl_verm)s</TD>
    </TR>
</TABLE>
""" % res

			if res['str']:
				html += """
<TABLE border="0" class="fls_tab">
    <TR class="fls_col_names">
	<TD></TD><TD>Strasse</TD><TD>Hausnummer</TD>
    </TR>
"""

				for strres in res['str']:
					html += """
    <TR class="fls_col_values">
        <TD></TD><TD>%(strname)s</TD><TD>%(hausnr)s</TD></TR>
    </TR>
""" % strres

				html += """
</TABLE>
"""

			if res['nutz']:
				html += """
<TABLE border="0" class="fls_tab">
	<TR class="fls_col_names"><TD width="21%%"></TD><TD width="69%%">Nutzung</TD><TD width="10%%">Fl&auml;che</TD></TR>
"""

				for nutz in res['nutz']:
					html += """
	<TR class="fls_col_values"><TD></TD><TD>21%(nutzshl)s - %(nutzung)s</TD><TD>%(fl)s m&sup2;</TD></TR>
""" % nutz

				html += """
</TABLE>
"""
			else:
				html += """
        <p>Keine Nutzungen.</p>
"""

			if res['klas']:
				html += """
<TABLE border="0" class="fls_tab">
	<TR class="fls_col_names"><TD></TD><TD>Klassifizierung</TD><TD>Fl&auml;che</TD></TR>
"""

				for klas in res['klas']:
					html += """
	<TR class="fls_col_values"><TD></TD><TD>%(klf_text)s</TD><TD>%(fl)s m&sup2;</TD></TR>
""" % klas

				html += """
</TABLE>
"""
			else:
				html += """
	<p>Keine Klassifizierungen.</p>
"""

			if res['afst']:
				html += """
<TABLE border="0" class="fls_tab">
	<TR class="fls_col_names"><TD width="21%%"></TD><TD width="79%%">Ausf&uuml;hrende Stelle</TD></TR>
"""

				for afst in res['afst']:
					html += """
	<TR class="fls_col_values"><TD></TD><TD>%(afst_txt)s</TD></TR>
""" % afst

				html += """
</TABLE>
"""
			else:
				html += """
        <p>Keine ausf&uuml;hrenden Stellen.</p>
"""

			if res['best']:
				html += """
<TABLE border="0" class="fls_bst">
	<TR><TD colspan="6">&nbsp;<br>&nbsp;</TD></TR>
	<TR><TD colspan="6"><h3>Best&auml;nde<hr style="width:100%%"></h3></TD></TR>
"""

				for best in res['best']:
					html += """
	<TR class="fls_col_names">
		<TD>Bestandsnummer</TD>
		<TD>Grundbuchbezirk</TD>
		<TD colspan="2">Grundbuchblattnr.</TD>
		<TD>Anteil</TD>
	</TR>
	<TR class="fls_col_values">
		<TD>%(bestdnr)s</TD>
		<TD>%(gbbz)s</TD>
		<TD colspan="2">%(gbblnr)s</TD>
		<TD>%(anteil)s</TD>
	</TR>
        <TR class="fls_col_names">
		<TD></TD>
		<TD>Buchungskennz.</TD>
		<TD>BVNR</TD>
		<TD>PZ</TD>
""" % best

					if res['hist']:
						html += """
		<TD>Hist. Bestand</TD><TD>Hist. Zuordnung</TD>
"""
					else:
						html += """
		<TD></TD><TD></TD>
"""

					html += """
	</TR>
	<TR class="fls_col_values">
		<TD></TD>
		<TD>%(eignerart)s</TD>
		<TD>%(bvnr)s</TD>
		<TD>%(pz)s</TD>
""" % best

					html += "<TD>%s</TD>" % ("ja" if res['hist'] and best['bhist'] else "")
					html += "<TD>%s</TD>" % ("ja" if res['hist'] and best['zhist'] else "")

					html += """
	</TR>
"""

				if best['bse']:
					html += """
	<TR class="fls_col_names"><TD>Anteil</TD><TD colspan="5">Namensinformation</TD></TR>
"""

					for bse in best['bse']:
						html += """
	<TR class="fls_col_values">
		<TD>%(antverh)s</TD>
		<TD colspan="5">%(name1)s %(name2)s<br>%(name3)s<br>%(name4)s</TD>
	</TR>
""" % bse
				else:
					html += """
	<p>Keine Eigner gefunden.</p>
"""

					html += """
        <TR><TD colspan="6"><hr class="fls_hr"></TD></TR>
"""

			html += """
        </TABLE>
</BODY>
</HTML>
"""

#		f = open("c:/cygwin/tmp/fs.html", "w")
#		f.write(html.encode('utf8'))
#		f.close()

		return html
