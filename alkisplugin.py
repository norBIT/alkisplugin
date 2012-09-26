#!/usr/bin/python
# -*- coding: utf8 -*-

from PyQt4.QtCore import QObject, QSettings, QString, QVariant, Qt, QPointF, qDebug
from PyQt4.QtGui import QApplication, QDialog, QIcon, QMessageBox, QAction, QColor
from PyQt4.QtSql import QSqlDatabase, QSqlQuery, QSqlError, QSql

from qgis.core import *

import conf, os, resources

class Conf(QDialog, conf.Ui_Dialog):
	def __init__(self):
		QDialog.__init__(self)
		self.setupUi(self)

		s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )

		self.leSERVICE.setText( s.value( "service", "" ).toString() )
		self.leHOST.setText( s.value( "host", "" ).toString() )
		self.lePORT.setText( s.value( "port", "5432" ).toString() )
		self.leDBNAME.setText( s.value( "dbname", "" ).toString() )
		self.leUID.setText( s.value( "uid", "" ).toString() )
		self.lePWD.setText( s.value( "pwd", "" ).toString() )

		self.bb.accepted.connect(self.accept)
		self.bb.rejected.connect(self.reject)

	def accept(self):
              	s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
		s.setValue( "service", self.leSERVICE.text() )
		s.setValue( "host", self.leHOST.text() )
		s.setValue( "port", self.lePORT.text() )
               	s.setValue( "dbname", self.leDBNAME.text() )
               	s.setValue( "uid", self.leUID.text() )
               	s.setValue( "pwd", self.lePWD.text() )

		QDialog.accept(self)


class alkisplugin:
	exts = {
		3010: { 'minx':-0.6024,	'miny':-1.0152,	'maxx':0.6171,	'maxy':1.2357 },
		3011: { 'minx':-0.6216,	'miny':-1.0061,	'maxx':0.6299,	'maxy':1.2222 },
		3020: { 'minx':-0.8459,	'miny':-0.8475,	'maxx':0.8559,	'maxy':0.8569 },
		3021: { 'minx':-0.8459,	'miny':-0.8475,	'maxx':0.8559,	'maxy':0.8569 },
		3022: { 'minx':-0.8722,	'miny':-0.8628,	'maxx':0.8617,	'maxy':0.8415 },
		3023: { 'minx':-0.8722,	'miny':-0.8628,	'maxx':0.8617,	'maxy':0.8415 },
		3024: { 'minx':-0.7821,	'miny':-0.7727,	'maxx':0.7588,	'maxy':0.7721 },
		3025: { 'minx':-0.7821,	'miny':-0.7727,	'maxx':0.7588,	'maxy':0.7721 },
		3300: { 'minx':-2.6223,	'miny':-2.6129,	'maxx':2.601,	'maxy':2.5987 },
		3302: { 'minx':-2.5251,	'miny':-2.5107,	'maxx':2.5036,	'maxy':2.5163 },
		3303: { 'minx':-3.4963,	'miny':-3.0229,	'maxx':3.4825,	'maxy':3.0199 },
		3305: { 'minx':-2.5129,	'miny':-2.5091,	'maxx':2.5156,	'maxy':2.5179 },
		3306: { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		3308: { 'minx':-2.4464,	'miny':-2.4446,	'maxx':2.5817,	'maxy':2.5817 },
		3309: { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		3311: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3312: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3314: { 'minx':-2.7808,	'miny':-3.0312,	'maxx':2.8638,	'maxy':3.0117 },
		3315: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3316: { 'minx':-2.7685,	'miny':-5.0168,	'maxx':2.7791,	'maxy':5.0062 },
		3317: { 'minx':-1.5189,	'miny':-1.7538,	'maxx':1.5364,	'maxy':1.7565 },
		3318: { 'minx':-0.8139,	'miny':-1.5046,	'maxx':0.8234,	'maxy':1.5017 },
		3319: { 'minx':-2.1918,	'miny':-2.5922,	'maxx':2.1569,	'maxy':2.5962 },
		3320: { 'minx':-2.7685,	'miny':-2.5016,	'maxx':2.7791,	'maxy':2.5028 },
		3321: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3323: { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		3324: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3326: { 'minx':-2.5251,	'miny':-2.5107,	'maxx':2.5036,	'maxy':2.5163 },
		3328: { 'minx':-2.7822,	'miny':-2.7729,	'maxx':2.7656,	'maxy':2.7617 },
		3330: { 'minx':-2.7822,	'miny':-2.7729,	'maxx':2.7656,	'maxy':2.7617 },
		3332: { 'minx':-2.7825,	'miny':-2.7731,	'maxx':2.7653,	'maxy':2.7614 },
		3334: { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.1051 },
		3336: { 'minx':-2.5322,	'miny':-3.1229,	'maxx':2.5288,	'maxy':3.2195 },
		3338: { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		3340: { 'minx':-2.5322,	'miny':-2.5228,	'maxx':2.5288,	'maxy':2.5044 },
		3342: { 'minx':-2.5064,	'miny':-2.5046,	'maxx':2.5224,	'maxy':2.5227 },
		3343: { 'minx':-2.0122,	'miny':-2.0122,	'maxx':2.0126,	'maxy':2.0027 },
		3401: { 'minx':-1.9675,	'miny':-2.6149,	'maxx':1.96,	'maxy':2.6196 },
		3402: { 'minx':-3.7939,	'miny':-3.5892,	'maxx':3.8046,	'maxy':3.5886 },
		3403: { 'minx':-3.6978,	'miny':-3.6799,	'maxx':3.7045,	'maxy':3.6842 },
		3404: { 'minx':-3.6978,	'miny':-3.6799,	'maxx':3.7045,	'maxy':3.6842 },
		3405: { 'minx':-4.1785,	'miny':-3.8158,	'maxx':4.3008,	'maxy':3.9871 },
		3406: { 'minx':-4.2746,	'miny':-3.9971,	'maxx':4.3678,	'maxy':3.8105 },
		3407: { 'minx':-6.2567,	'miny':-2.2569,	'maxx':6.2643,	'maxy':2.2639 },
		3409: { 'minx':-3.7075,	'miny':-3.6981,	'maxx':3.695,	'maxy':3.6888 },
		3410: { 'minx':-3.6816,	'miny':-3.6797,	'maxx':3.6887,	'maxy':3.6844 },
		3411: { 'minx':-3.7075,	'miny':-3.6981,	'maxx':3.695,	'maxy':3.6888 },
		3412: { 'minx':-3.8813,	'miny':-3.8719,	'maxx':3.3302,	'maxy':3.8636 },
		3413: { 'minx':-1.2257,	'miny':-0.2181,	'maxx':1.2166,	'maxy':0.2127 },
		3415: { 'minx':-5.0815,	'miny':-2.5197,	'maxx':4.9078,	'maxy':3.1702 },
		3417: { 'minx':-3.6945,	'miny':-3.6889,	'maxx':3.6754,	'maxy':3.6978 },
		3419: { 'minx':-2.6093,	'miny':-3.2037,	'maxx':2.6138,	'maxy':3.2091 },
		3421: { 'minx':-1.0193,	'miny':-0.9064,	'maxx':1.0043,	'maxy':0.9118 },
		3423: { 'minx':-3.6945,	'miny':-3.6889,	'maxx':3.6754,	'maxy':3.6978 },
		3424: { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		3426: { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		3428: { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		3430: { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		3432: { 'minx':-2.5193,	'miny':-2.9017,	'maxx':2.5093,	'maxy':2.5895 },
		3434: { 'minx':-2.5193,	'miny':-2.8235,	'maxx':2.5093,	'maxy':2.6663 },
		3436: { 'minx':-6.0195,	'miny':-6.1918,	'maxx':6.0061,	'maxy':6.0214 },
		3438: { 'minx':-6.2697,	'miny':-6.2641,	'maxx':6.2508,	'maxy':6.2528 },
		3439: { 'minx':-6.2697,	'miny':-6.2641,	'maxx':6.2508,	'maxy':6.2528 },
		3440: { 'minx':-1.1856,	'miny':-2.0168,	'maxx':1.1925,	'maxy':2.1807 },
		3441: { 'minx':-2.6945,	'miny':-2.0062,	'maxx':2.5297,	'maxy':2.1914 },
		3442: { 'minx':-1.2818,	'miny':-1.3142,	'maxx':1.2894,	'maxy':1.326 },
		3444: { 'minx':-0.5701,	'miny':-1.5137,	'maxx':0.5529,	'maxy':1.5608 },
		3446: { 'minx':-1.9144,	'miny':-2.0137,	'maxx':1.6907,	'maxy':2.1838 },
		3448: { 'minx':-0.175,	'miny':-1.5,	'maxx':0.175,	'maxy':1.5 },
		3450: { 'minx':-2.2109,	'miny':-2.0168,	'maxx':2.202,	'maxy':2.1807 },
		3452: { 'minx':-1.1856,	'miny':-2.0168,	'maxx':1.1925,	'maxy':2.1807 },
		3454: { 'minx':-0.9292,	'miny':-0.929,	'maxx':0.9335,	'maxy':0.935 },
		3456: { 'minx':-4.1028,	'miny':-2.7517,	'maxx':3.4036,	'maxy':2.7596 },
		3458: { 'minx':-2.0507,	'miny':-1.6767,	'maxx':1.8776,	'maxy':1.6959 },
		3460: { 'minx':-1.8905,	'miny':-2.1752,	'maxx':1.6503,	'maxy':2.664 },
		3462: { 'minx':-3.4608,	'miny':-2.6966,	'maxx':3.2266,	'maxy':2.6765 },
		3470: { 'minx':-2.7435,	'miny':-2.1025,	'maxx':2.7393,	'maxy':2.7579 },
		3472: { 'minx':-0.8011,	'miny':-0.7704,	'maxx':0.8041,	'maxy':0.7516 },
		3474: { 'minx':-1.4221,	'miny':-0.9636,	'maxx':1.4072,	'maxy':0.9686 },
		3476: { 'minx':-1.562,	'miny':-0.8073,	'maxx':1.5577,	'maxy':0.8058 },
		3478: { 'minx':-4.0053,	'miny':-0.5438,	'maxx':4.0176,	'maxy':0.5458 },
		3480: { 'minx':-1.8193,	'miny':-2.0137,	'maxx':1.9459,	'maxy':2.0013 },
		3481: { 'minx':-1.8905,	'miny':-1.8808,	'maxx':1.94,	'maxy':1.9043 },
		3482: { 'minx':-2.115,	'miny':-1.6314,	'maxx':2.1682,	'maxy':1.6038 },
		3483: { 'minx':-1.9026,	'miny':-1.3693,	'maxx':1.8312,	'maxy':1.2484 },
		3484: { 'minx':-2.1193,	'miny':-1.5137,	'maxx':2.1316,	'maxy':1.5153 },
		3486: { 'minx':-1.506,	'miny':-1.5182,	'maxx':1.517,	'maxy':1.5108 },
		3488: { 'minx':-3.044,	'miny':-0.7478,	'maxx':3.0241,	'maxy':0.7514 },
		3490: { 'minx':-2.5057,	'miny':-0.6882,	'maxx':2.5873,	'maxy':0.6518 },
		3501: { 'minx':-2.852,	'miny':-3.5574,	'maxx':2.8258,	'maxy':3.3221 },
		3502: { 'minx':-1.6984,	'miny':-2.1752,	'maxx':1.6797,	'maxy':2.1846 },
		3503: { 'minx':-3.044,	'miny':-2.787,	'maxx':3.0564,	'maxy':3.0227 },
		3504: { 'minx':-1.1216,	'miny':-1.1104,	'maxx':1.0953,	'maxy':1.0957 },
		3506: { 'minx':-1.4583,	'miny':-2.6887,	'maxx':1.4677,	'maxy':2.5699 },
		3507: { 'minx':-2.262,	'miny':-3.2279,	'maxx':2.0229,	'maxy':3.2312 },
		3508: { 'minx':-1.6984,	'miny':-1.6767,	'maxx':1.6797,	'maxy':1.6959 },
		3509: { 'minx':-1.7693,	'miny':-1.6387,	'maxx':1.7702,	'maxy':1.6422 },
		3510: { 'minx':-1.9093,	'miny':-1.3037,	'maxx':1.9211,	'maxy':1.2908 },
		3511: { 'minx':-1.7945,	'miny':-2.5606,	'maxx':1.6809,	'maxy':2.6044 },
		3512: { 'minx':-1.6342,	'miny':-2.6059,	'maxx':1.5504,	'maxy':2.6056 },
		3513: { 'minx':-3.012,	'miny':-2.6059,	'maxx':3.0234,	'maxy':2.6056 },
		3514: { 'minx':-5.031,	'miny':-2.6284,	'maxx':5.0211,	'maxy':2.6067 },
		3515: { 'minx':-1.4443,	'miny':-2.1887,	'maxx':1.4495,	'maxy':2.1938 },
		3516: { 'minx':-1.1536,	'miny':-1.2009,	'maxx':1.1919,	'maxy':1.2106 },
		3517: { 'minx':-1.442,	'miny':-2.1074,	'maxx':1.4517,	'maxy':2.0914 },
		3518: { 'minx':-2.0956,	'miny':-0.8475,	'maxx':2.091,	'maxy':0.8569 },
		3519: { 'minx':-0.8652,	'miny':-0.8611,	'maxx':0.8687,	'maxy':0.8432 },
		3520: { 'minx':-1.6021,	'miny':-1.6089,	'maxx':1.6146,	'maxy':1.6033 },
		3521: { 'minx':-1.8585,	'miny':-1.8581,	'maxx':1.8427,	'maxy':1.8583 },
		3522: { 'minx':-1.6129,	'miny':-1.6037,	'maxx':1.6037,	'maxy':1.6084 },
		3523: { 'minx':-1.6982,	'miny':-2.3567,	'maxx':1.7123,	'maxy':2.3709 },
		3524: { 'minx':-3.2045,	'miny':-3.1951,	'maxx':3.1883,	'maxy':3.1947 },
		3525: { 'minx':-4.4542,	'miny':-3.0362,	'maxx':4.4509,	'maxy':3.0297 },
		3526: { 'minx':-2.5315,	'miny':-1.5408,	'maxx':2.5294,	'maxy':1.557 },
		3527: { 'minx':-1.8906,	'miny':-1.9033,	'maxx':1.8752,	'maxy':1.9052 },
		3528: { 'minx':-2.5315,	'miny':-1.5408,	'maxx':2.5294,	'maxy':1.557 },
		3529: { 'minx':-1.3458,	'miny':-1.3596,	'maxx':1.3546,	'maxy':1.3491 },
		3531: { 'minx':-1.7623,	'miny':-1.6767,	'maxx':1.7774,	'maxy':1.6959 },
		3532: { 'minx':-1.4739,	'miny':-2.4473,	'maxx':1.4845,	'maxy':2.4416 },
		3533: { 'minx':-1.2176,	'miny':-2.1752,	'maxx':1.2247,	'maxy':2.002 },
		3534: { 'minx':-0.8973,	'miny':-2.0168,	'maxx':0.901,	'maxy':2.2035 },
		3535: { 'minx':-1.2176,	'miny':-2.0168,	'maxx':1.2247,	'maxy':2.021 },
		3536: { 'minx':-0.9421,	'miny':-1.4366,	'maxx':0.9527,	'maxy':1.4322 },
		3537: { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		3539: { 'minx':-1.8585,	'miny':-2.0846,	'maxx':1.8752,	'maxy':1.9541 },
		3540: { 'minx':-1.6663,	'miny':-3.0589,	'maxx':1.7436,	'maxy':3.1911 },
		3541: { 'minx':-2.6083,	'miny':-1.5952,	'maxx':2.6148,	'maxy':1.5943 },
		3542: { 'minx':-2.5954,	'miny':-1.6089,	'maxx':2.5957,	'maxy':1.6033 },
		3543: { 'minx':-1.6342,	'miny':-0.4532,	'maxx':1.6471,	'maxy':0.4546 },
		3544: { 'minx':-1.1216,	'miny':-0.6118,	'maxx':1.0953,	'maxy':0.5916 },
		3545: { 'minx':-2.6081,	'miny':-1.6037,	'maxx':2.6151,	'maxy':1.6084 },
		3546: { 'minx':-2.6093,	'miny':-1.6037,	'maxx':2.6138,	'maxy':1.6084 },
		3547: { 'minx':-2.6093,	'miny':-1.6037,	'maxx':2.6138,	'maxy':1.6084 },
		3548: { 'minx':-1.09,	'miny':-1.1536,	'maxx':1.0947,	'maxy':1.0528 },
		3549: { 'minx':-1.5061,	'miny':-3.8749,	'maxx':1.5488,	'maxy':3.9066 },
		3550: { 'minx':-0.8652,	'miny':-3.2855,	'maxx':0.8687,	'maxy':3.29 },
		3551: { 'minx':-1.6021,	'miny':-2.6059,	'maxx':1.6146,	'maxy':2.6056 },
		3552: { 'minx':-0.8652,	'miny':-2.8552,	'maxx':1.2218,	'maxy':2.7724 },
		3553: { 'minx':-1.0894,	'miny':-3.3082,	'maxx':1.1595,	'maxy':3.4053 },
		3554: { 'minx':-2.7696,	'miny':-2.764,	'maxx':2.778,	'maxy':2.7704 },
		3556: { 'minx':-1.5061,	'miny':-1.5636,	'maxx':1.5488,	'maxy':1.557 },
		3557: { 'minx':-1.0254,	'miny':-3.3535,	'maxx':1.0303,	'maxy':3.3605 },
		3558: { 'minx':-1.0894,	'miny':-3.3764,	'maxx':1.1595,	'maxy':3.361 },
		3559: { 'minx':-1.3137,	'miny':-3.648,	'maxx':1.322,	'maxy':3.5547 },
		3560: { 'minx':-2.852,	'miny':-3.1495,	'maxx':2.9226,	'maxy':3.1477 },
		3561: { 'minx':-2.9481,	'miny':-3.4217,	'maxx':2.9568,	'maxy':3.3167 },
		3562: { 'minx':-2.0956,	'miny':-0.5978,	'maxx':2.091,	'maxy':0.6056 },
		3563: { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		3564: { 'minx':-1.6021,	'miny':-1.6089,	'maxx':1.6465,	'maxy':1.6033 },
		3565: { 'minx':-1.3778,	'miny':-3.1045,	'maxx':1.3871,	'maxy':3.0086 },
		3566: { 'minx':-1.1216,	'miny':-0.6118,	'maxx':1.0953,	'maxy':0.5916 },
		3567: { 'minx':-2.0964,	'miny':-1.0945,	'maxx':2.0902,	'maxy':1.1116 },
		3568: { 'minx':-2.115,	'miny':-1.1104,	'maxx':2.1037,	'maxy':1.0957 },
		3569: { 'minx':-1.3458,	'miny':-1.3596,	'maxx':1.3546,	'maxy':1.3491 },
		3570: { 'minx':-3.1081,	'miny':-1.1104,	'maxx':3.025,	'maxy':1.0957 },
		3571: { 'minx':-1.3137,	'miny':-1.3143,	'maxx':1.322,	'maxy':1.303 },
		3572: { 'minx':-1.5701,	'miny':-1.6089,	'maxx':1.5821,	'maxy':1.6033 },
		3573: { 'minx':-29.7675,'miny':-6.0952,	'maxx':29.7664,	'maxy':6.0919 },
		3574: { 'minx':-2.7693,	'miny':-2.7637,	'maxx':2.7783,	'maxy':2.7707 },
		3576: { 'minx':-2.5193,	'miny':-2.5137,	'maxx':2.5093,	'maxy':2.5134 },
		3578: { 'minx':-1.6094,	'miny':-1.6037,	'maxx':1.6072,	'maxy':1.6084 },
		3579: { 'minx':-0.8011,	'miny':-0.8158,	'maxx':0.8042,	'maxy':0.8201 },
		3580: { 'minx':-0.09,	'miny':-0.3,	'maxx':0.09,	'maxy':0.3 },
		3583: { 'minx':-1.2177,	'miny':-2.8099,	'maxx':1.1925,	'maxy':2.794 },
		3584: { 'minx':-1.3884,	'miny':-2.6038,	'maxx':1.4728,	'maxy':2.5162 },
		3585: { 'minx':-0.5127,	'miny':-0.5212,	'maxx':0.514,	'maxy':0.5002 },
		3586: { 'minx':-1.0254,	'miny':-0.5212,	'maxx':1.0303,	'maxy':0.5002 },
		3587: { 'minx':-3.3968,	'miny':-3.3761,	'maxx':3.3866,	'maxy':3.3847 },
		3588: { 'minx':-3.5973,	'miny':-3.1348,	'maxx':3.674,	'maxy':3.2307 },
		3589: { 'minx':-0.596,	'miny':-2.5968,	'maxx':0.5914,	'maxy':2.5006 },
		3590: { 'minx':-2.879,	'miny':-3.0183,	'maxx':2.8637,	'maxy':2.4292 },
		3592: { 'minx':-1.6214,	'miny':-0.6027,	'maxx':1.5952,	'maxy':0.6006 },
		3593: { 'minx':-10.1131,'miny':-2.0983,	'maxx':10.1004,	'maxy':2.1007 },
		3594: { 'minx':-1.8137,	'miny':-2.0983,	'maxx':1.8228,	'maxy':2.1007 },
		3595: { 'minx':-2.07,	'miny':-0.6027,	'maxx':2.116,	'maxy':0.6006 },
		3596: { 'minx':-0.5965,	'miny':-1.8446,	'maxx':0.5909,	'maxy':1.8491 },
		3597: { 'minx':-1.4611,	'miny':-2.2794,	'maxx':1.4651,	'maxy':2.5843 },
		3599: { 'minx':-1.2398,	'miny':-2.2796,	'maxx':1.2349,	'maxy':2.1731 },
		3601: { 'minx':-0.731,	'miny':-0.6744,	'maxx':0.7457,	'maxy':0.7336 },
		3603: { 'minx':-1.5253,	'miny':-1.6223,	'maxx':1.5298,	'maxy':2.0915 },
		3605: { 'minx':-0.6314,	'miny':-1.2045,	'maxx':0.6523,	'maxy':1.2072 },
		3607: { 'minx':-1.4611,	'miny':-1.3958,	'maxx':1.4651,	'maxy':1.4498 },
		3609: { 'minx':-1.3971,	'miny':-2.0303,	'maxx':1.4963,	'maxy':2.0077 },
		3613: { 'minx':-0.5064,	'miny':-0.5045,	'maxx':0.5203,	'maxy':0.5169 },
		3615: { 'minx':-2.9032,	'miny':-0.852,	'maxx':2.9048,	'maxy':0.8523 },
		3617: { 'minx':-9.4081,	'miny':-2.5062,	'maxx':9.4305,	'maxy':2.498 },
		3619: { 'minx':-3.6365,	'miny':-0.6045,	'maxx':3.6361,	'maxy':0.6216 },
		3621: { 'minx':-3.7565,	'miny':-0.6045,	'maxx':3.7768,	'maxy':0.6216 },
		3623: { 'minx':-1.5253,	'miny':-1.4865,	'maxx':1.5298,	'maxy':1.4739 },
		3625: { 'minx':-2.0064,	'miny':-1.9762,	'maxx':2.0183,	'maxy':1.9929 },
		3627: { 'minx':-2.807,	'miny':-2.5968,	'maxx':2.8379,	'maxy':2.7521 },
		3629: { 'minx':-0.5064,	'miny':-0.5045,	'maxx':0.5203,	'maxy':0.5169 },
		3631: { 'minx':-0.15,	'miny':-0.15,	'maxx':0.15,	'maxy':0.15 },
		3632: { 'minx':-0.09,	'miny':-1,	'maxx':0.09,	'maxy':1 },
		3634: { 'minx':-1.7176,	'miny':-1.5998,	'maxx':1.7572,	'maxy':1.749 },
		3636: { 'minx':-3.3518,	'miny':-0.852,	'maxx':3.3662,	'maxy':0.8523 },
		3637: { 'minx':-1.9739,	'miny':-1.9623,	'maxx':0.3762,	'maxy':1.9607 },
		3638: { 'minx':-2.1982,	'miny':-0.852,	'maxx':2.2146,	'maxy':0.8523 },
		3640: { 'minx':-2.1021,	'miny':-2.0983,	'maxx':2.1168,	'maxy':2.1007 },
		3641: { 'minx':-2.3584,	'miny':-2.3475,	'maxx':2.346,	'maxy':2.3574 },
		3642: { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6006 },
		3643: { 'minx':-0.09,	'miny':-0.5,	'maxx':0.09,	'maxy':0.5 },
		3644: { 'minx':-1.5253,	'miny':-0.6027,	'maxx':1.5298,	'maxy':0.6007 },
		3645: { 'minx':-0.596,	'miny':-0.852,	'maxx':0.5914,	'maxy':0.8523 },
		3646: { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6007 },
		3647: { 'minx':-0.3076,	'miny':-0.6027,	'maxx':0.3017,	'maxy':0.6007 },
		3648: { 'minx':-0.8524,	'miny':-0.6027,	'maxx':0.8495,	'maxy':0.6006 },
		3649: { 'minx':-2.0058,	'miny':-0.6027,	'maxx':2.019,	'maxy':0.6007 },
		3650: { 'minx':-0.596,	'miny':-0.6027,	'maxx':0.5914,	'maxy':0.6006 },
		3651: { 'minx':-1.4932,	'miny':-0.784,	'maxx':1.4651,	'maxy':0.829 },
		3653: { 'minx':-3.0314,	'miny':-0.6027,	'maxx':3.0038,	'maxy':0.6006 },
		3701: { 'minx':-1.4931,	'miny':-2.2569,	'maxx':1.4333,	'maxy':2.8576 },
		3703: { 'minx':-1.2048,	'miny':-1.1919,	'maxx':1.2052,	'maxy':1.197 },
		3705: { 'minx':-1.6855,	'miny':-1.6904,	'maxx':1.6927,	'maxy':1.6822 },
		3707: { 'minx':-3.0314,	'miny':-3.0047,	'maxx':3.0038,	'maxy':3.0153 },
		3709: { 'minx':-1.6855,	'miny':-1.6904,	'maxx':1.6927,	'maxy':1.6822 },
	}

	def __init__(self, iface):
		self.iface = iface

	def initGui(self):
		self.confAction = QAction(QIcon(":/plugins/alkis/logo.png"), "Konfiguration", self.iface.mainWindow())
		self.confAction.setWhatsThis("Konfiguration der ALKIS-Erweiterung")
		self.confAction.setStatusTip("Konfiguration der ALKIS-Erweiterung")
		self.confAction.triggered.connect(self.conf)

		self.insertAction = QAction(QIcon(":/plugins/alkis/logo.png"), "Einbinden", self.iface.mainWindow())
		self.insertAction.setWhatsThis("ALKIS-Layer einbinden")
		self.insertAction.setStatusTip("ALKIS-Layer einbinden")
		self.insertAction.triggered.connect(self.run)

		if hasattr(self.iface, "addPluginToDatabaseMenu"):
			self.iface.addPluginToDatabaseMenu("&ALKIS", self.insertAction)
			self.iface.addPluginToDatabaseMenu("&ALKIS", self.confAction)
		else:
			self.iface.addPluginToMenu("&ALKIS", self.insertAction)
			self.iface.addPluginToMenu("&ALKIS", self.confAction)

	def unload(self):
		self.confAction.deleteLater()
		self.confAction = None
		self.insertAction.deleteLater()
		self.insertAction = None

	def conf(self):
		dlg = Conf()
		dlg.exec_()


	def run(self):
		s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )

		service = s.value( "service", "" ).toString()
		host = s.value( "host", "" ).toString()
		port = s.value( "port", "5432" ).toString()
		dbname = s.value( "dbname", "" ).toString()
		uid = s.value( "uid", "" ).toString()
		pwd = s.value( "pwd", "" ).toString()
		
		uri = QgsDataSourceURI()

		if service.isEmpty():
			uri.setConnection( host, port, dbname, uid, pwd )
		else:
			uri.setConnection( service, dbname, uid, pwd )

		conninfo = uri.connectionInfo()

		db = QSqlDatabase.addDatabase( "QPSQL" )
		db.setConnectOptions( conninfo )

		self.iface.mapCanvas().setRenderFlag( False )

		if not db.open():
			while not db.open():
				if not QgsCredentials.instance().get( conninfo, uid, pwd, u"Datenbankverbindung schlug fehl [%s]" % db.lastError().text() ):
					return

				uri.setUsername(uid)
				uri.setPassword(pwd)

				db.setConnectOptions( uri.connectionInfo() )

			QgsCredentials.instance().put( conninfo, uid, pwd )

		QApplication.setOverrideCursor( Qt.WaitCursor )

		qry = QSqlQuery(db)

		s = QSettings()
		oldAdd = s.value( "/qgis/addNewLayersToCurrentGroup", False ).toBool()
		s.setValue( "/qgis/addNewLayersToCurrentGroup", True )

		svgpaths = s.value( "svg/searchPathsForSVG" ).toString().split("|")
		svgpath = os.path.dirname(__file__) + "/svg"
		if not svgpaths.contains( svgpath, Qt.CaseInsensitive ):
			svgpaths.append( svgpath )
			s.setValue( "svg/searchPathsForSVG", svgpaths.join("|") )

		self.iface.legendInterface().addGroup( "ALKIS", False )
		alkisGroup = self.iface.legendInterface().groups().count() - 1
		
		for t in (
			u"Flurstücke",
			u"Gebäude",
			u"Rechtliche Festlegungen",
			u"Verkehr",
			u"Friedhöfe",
			u"Vegetation",
			u"Gewässer",
			u"Politische Grenzen",
			u"Industrie und Gewerbe",
			u"Sport und Freizeit",
			u"Wohnbauflächen"
			):

			self.iface.legendInterface().addGroup( t, False, alkisGroup )
			thisGroup = self.iface.legendInterface().groups().count() - 1

			qDebug( QString( "Thema: %1" ).arg( t ) )

			sql = (u"SELECT signaturnummer,r,g,b FROM alkis_flaechen" 
			    + u" JOIN alkis_farben ON alkis_flaechen.farbe=alkis_farben.id"
			    + u" WHERE EXISTS (SELECT * FROM po_polygons WHERE thema='%s'" % t
			    + u" AND po_polygons.sn_flaeche=alkis_flaechen.signaturnummer)"
                            + u" ORDER BY darstellungsprioritaet")
			qDebug( QString( "SQL: %1" ).arg( sql ) )
			if qry.exec_( sql ):
				r = QgsCategorizedSymbolRendererV2( "sn_flaeche" )
				r.deleteAllCategories()

				n = 0
				while qry.next():
					sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )
	
					sn = qry.value(0).toString()
					sym.setColor( QColor( qry.value(1).toInt()[0], qry.value(2).toInt()[0], qry.value(3).toInt()[0] ) )
	
					r.addCategory( QgsRendererCategoryV2( sn, sym, "" ) )
					n += 1

				if n>0:
					layer = self.iface.addVectorLayer(
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=25832 table=po_polygons (polygon) sql=thema='%s'" % (conninfo, t),
						u"Flächen (%s)" % t,
						"postgres" )
					layer.setRendererV2( r )
					self.iface.refreshLegend( layer )
				else:
					del r
			else:
				QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )

			sql = (u"SELECT"
			    + u" signaturnummer,r,g,b,(SELECT avg(strichstaerke)/100 FROM alkis_linie WHERE alkis_linie.signaturnummer=alkis_linien.signaturnummer) AS ss"
			    + u" FROM alkis_linien"
			    + u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
			    + u" WHERE EXISTS (SELECT * FROM po_polygons WHERE thema='%s'" % t
			    + u" AND po_polygons.sn_randlinie=alkis_linien.signaturnummer)"
			    + u" ORDER BY darstellungsprioritaet" )
			qDebug( QString( "SQL: %1" ).arg( sql ) )
			if qry.exec_(sql):
				r = QgsCategorizedSymbolRendererV2( "sn_randlinie" )
				r.deleteAllCategories()

				n = 0
				while qry.next():
					sym = QgsSymbolV2.defaultSymbol( QGis.Polygon )

					sn = qry.value(0).toString()
					c = QColor( qry.value(1).toInt()[0], qry.value(2).toInt()[0], qry.value(3).toInt()[0] )
					sym.changeSymbolLayer( 0, QgsSimpleFillSymbolLayerV2( c, Qt.NoBrush, c, Qt.SolidLine, qry.value(4).toDouble()[0] ) )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )

					r.addCategory( QgsRendererCategoryV2( sn, sym, "" ) )
					n += 1

				if n>0:
					layer = self.iface.addVectorLayer(
						u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOLYGON srid=25832 table=po_polygons (polygon) sql=thema='%s'" % (conninfo, t),
						u"Grenzen (%s)" % t,
						"postgres" )
					layer.setRendererV2( r )
					self.iface.refreshLegend( layer )
				else:
					del r
			else:
				QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )

			sql = (u"SELECT"
			    + u" signaturnummer,r,g,b,(SELECT avg(strichstaerke)/100 FROM alkis_linie WHERE alkis_linie.signaturnummer=alkis_linien.signaturnummer) AS ss"
 			    + u" FROM alkis_linien"
                            + u" JOIN alkis_farben ON alkis_linien.farbe=alkis_farben.id"
			    + u" WHERE EXISTS (SELECT * FROM po_lines WHERE thema='%s'" % t
			    + u" AND po_lines.signaturnummer=alkis_linien.signaturnummer)"
			    + u" ORDER BY darstellungsprioritaet" )
			qDebug( QString( "SQL: %1" ).arg( sql ) )
			if qry.exec_( sql ):
				r = QgsCategorizedSymbolRendererV2( "signaturnummer" )
				r.deleteAllCategories()

				n = 0
				while qry.next():
					sym = QgsSymbolV2.defaultSymbol( QGis.Line )

					sn = qry.value(0).toString()
					sym.setColor( QColor( qry.value(1).toInt()[0], qry.value(2).toInt()[0], qry.value(3).toInt()[0] ) )
					sym.setWidth( qry.value(4).toDouble()[0] )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )

					r.addCategory( QgsRendererCategoryV2( sn, sym, "" ) )
					n += 1

				if n>0:
					layer = self.iface.addVectorLayer(
							u"%s estimatedmetadata=true key='ogc_fid' type=MULTILINESTRING srid=25832 table=po_lines (line) sql=thema='%s'" % (conninfo, t),
							u"Linien (%s)" % t,
							"postgres" )
	
					layer.setRendererV2( r )
					self.iface.refreshLegend( layer )
				else:
					del r
			else:
				QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )

			sql = u"SELECT DISTINCT signaturnummer FROM po_points WHERE thema='%s'" % t
			qDebug( QString( "SQL: %1" ).arg( sql ) )
			if qry.exec_( sql ):
				r = QgsCategorizedSymbolRendererV2( "signaturnummer" )
				r.deleteAllCategories()
				r.setRotationField( "drehwinkel_grad" )

				n = 0
				while qry.next():
					sn = qry.value(0).toInt()[0]
					svg = "alkis%d.svg" % sn
					x = ( alkisplugin.exts[sn]['minx'] + alkisplugin.exts[sn]['maxx'] ) / 2
					y = ( alkisplugin.exts[sn]['miny'] + alkisplugin.exts[sn]['maxy'] ) / 2
					w = alkisplugin.exts[sn]['maxx'] - alkisplugin.exts[sn]['minx']
					h = alkisplugin.exts[sn]['maxy'] - alkisplugin.exts[sn]['miny']

					symlayer = QgsSvgMarkerSymbolLayerV2( svg )
					symlayer.setSize( w )
					symlayer.setOffset( QPointF( -x, -y ) )
					
					sym = QgsMarkerSymbolV2( [symlayer] )
					sym.setSize( w )
					sym.setOutputUnit( QgsSymbolV2.MapUnit )

					r.addCategory( QgsRendererCategoryV2( "%d" % sn, sym, "" ) )
					n += 1

				qDebug( QString( "classes: %1" ).arg( n ) )
				if n>0:
					layer = self.iface.addVectorLayer(
							u"%s estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=25832 table=po_points (point) sql=thema='%s'" % (conninfo, t),
							u"Punkte (%s)" % t,
							"postgres" )
					layer.setRendererV2( r )
					self.iface.refreshLegend( layer )
				else:
					del r

			n = 0
			for i in range(2):
				geom = "point" if i==0 else "line"

				if not qry.exec_( "SELECT count(*) FROM po_labels WHERE thema='%s' AND NOT %s IS NULL" % (t,geom) ):
					QMessageBox.critical( None, "ALKIS", u"Fehler: %s\nSQL: %s\n" % (qry.lastError().text(), qry.executedQuery() ) )
					continue

				if not qry.next() or qry.value(0).toInt()[0]==0:
					continue

				if n==1:
					self.iface.legendInterface().addGroup( "Beschriftungen", False, thisGroup )
					self.iface.legendInterface().moveLayer( layer, self.iface.legendInterface().groups().count() - 1 )

				uri = ( conninfo
                                        + u" estimatedmetadata=true key='ogc_fid' type=MULTIPOINT srid=25832 table="
					+ u"\"("
					+ u"SELECT"
					+ u" ogc_fid"
					+ u"," + geom
					+ u",st_x(point) AS tx"
					+ u",st_y(point) AS ty"
					+ u",drehwinkel_grad AS tangle"
					+ u",(size_umn*0.0254)::float8 AS tsize"
					+ u",text"
 				        + u",CASE"
 				        + u" WHEN horizontaleausrichtung='linksbündig' THEN 'Left'"
 				        + u" WHEN horizontaleausrichtung='zentrisch' THEN 'Center'"
 				        + u" WHEN horizontaleausrichtung='rechtsbündig' THEN 'Right'"
 				        + u" END AS halign"
 				        + u",CASE"
 				        + u" WHEN vertikaleausrichtung='oben' THEN 'Top'"
 				        + u" WHEN vertikaleausrichtung='Mitte' THEN 'Half'"
 				        + u" WHEN vertikaleausrichtung='Basis' THEN 'Bottom'"
 				        + u" END AS valign"
 					+ u",'Arial'::text AS family"
 				        + u",CASE WHEN font_umn LIKE '%italic%' THEN 1 ELSE 0 END AS italic"
 				        + u",CASE WHEN font_umn LIKE '%bold%' THEN 1 ELSE 0 END AS bold"
					+ u" FROM po_labels"
					+ u" WHERE thema='" + t + "'"
					+ u")\" (" + geom + ") sql=" )

				qDebug( QString( "URI: %1" ).arg( uri ) )

				layer = self.iface.addVectorLayer(
					uri,
					u"Beschriftungen (%s)" % t,
					"postgres" )

                                sym = QgsMarkerSymbolV2()
                                sym.setSize( 0.0 );
                                layer.setRendererV2( QgsSingleSymbolRendererV2( sym ) )
				self.iface.refreshLegend( layer )

				lyr = QgsPalLayerSettings()
                		lyr.fieldName = "text"
				lyr.isExpression = False
				lyr.enabled = True
                		lyr.fontSizeInMapUnits = True
				lyr.textFont.setPointSizeF( 2.5 )
				lyr.textFont.setFamily( "Sans Serif" )
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

				self.iface.refreshLegend( layer )

				n += 1

			self.iface.legendInterface().setGroupExpanded( thisGroup, False )

		self.iface.legendInterface().setGroupExpanded( alkisGroup, False )
		self.iface.legendInterface().setGroupVisible( alkisGroup, False )
		self.iface.mapCanvas().setRenderFlag( True )
		s.setValue( "/qgis/addNewLayersToCurrentGroup", oldAdd )
		QApplication.restoreOverrideCursor()
