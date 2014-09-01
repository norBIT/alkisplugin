# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    qgisclasses.py
    ---------------------
    Date                 : May 2014
    Copyright            : (C) 2014 by Jürgen Fischer
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


from PyQt4.QtCore import QSettings, Qt, QDate, QDir, QByteArray
from PyQt4.QtGui import QApplication, QDialog, QDialogButtonBox, QMessageBox, QCursor, QPixmap, QTableWidgetItem, QPrintDialog, QAction, QPrinter, QMenu
from PyQt4.QtSql import QSqlQuery
from PyQt4 import QtCore, uic

from qgis.core import *
from qgis.gui import *

import socket, os, re, sys, operator

try:
        import win32gui
        win32 = True
except:
        win32 = False

d = os.path.dirname(__file__)
QDir.addSearchPath( "alkis", d )
ConfBase = uic.loadUiType( os.path.join( d, 'conf.ui' ) )[0]
InfoBase = uic.loadUiType( os.path.join( d, 'info.ui' ) )[0]
AboutBase = uic.loadUiType( os.path.join( d, 'about.ui' ) )[0]
ALKISSearchBase = uic.loadUiType( os.path.join( d, 'search.ui' ) )[0]

def qDebug(s):
    QgsMessageLog.logMessage( s, u'ALKIS' )

def quote(x,prefix='E'):
    if type(x)==str:
        x.replace("'", "''")
        x.replace("\\", "\\\\")
        if x.find( "\\" )<0:
            return u"'%s'" % x
        else:
            return u"%s'%s'" % (prefix, x)
    elif type(x)==unicode and x.find( u"\\" ):
        x.replace(u"\\", u"\\\\")
        return u"%s'%s'" % (prefix, unicode(x))
    else:
        return u"'%s'" % unicode(x)

class ALKISConf(QDialog, ConfBase):
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

                self.load(False)

                self.bb.accepted.connect(self.accept)
                self.bb.rejected.connect(self.reject)
                self.bb.addButton( "Modelle laden", QDialogButtonBox.ActionRole ).clicked.connect( self.load )

        def load(self, error=True):
                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                s.setValue( "service", self.leSERVICE.text() )
                s.setValue( "host", self.leHOST.text() )
                s.setValue( "port", self.lePORT.text() )
                s.setValue( "dbname", self.leDBNAME.text() )
                s.setValue( "uid", self.leUID.text() )
                s.setValue( "pwd", self.lePWD.text() )

                modelle = s.value( "modellarten", ['DLKM','DKKM1000'] )
                (db,conninfo) = self.plugin.opendb()
                if db:
                        qry = QSqlQuery(db)
                        if qry.exec_( """
SELECT modell,count(*)
FROM (
        SELECT unnest(modell) AS modell FROM po_points   UNION ALL
        SELECT unnest(modell) AS modell FROM po_lines    UNION ALL
        SELECT unnest(modell) AS modell FROM po_polygons UNION ALL
        SELECT unnest(modell) AS modell from po_lines    UNION ALL
        SELECT unnest(modell) AS modell from po_labels
) AS foo
GROUP BY modell
ORDER BY count(*) DESC
""" ):
                                self.twModellarten.clearContents()
                                res = {}
                                while qry.next():
                                        res[ qry.value(0) ] = qry.value(1)

                                self.twModellarten.setRowCount( len(res) )
                                i = 0
                                for k,n in sorted(res.iteritems(), key=operator.itemgetter(1), reverse=True):
                                        item = QTableWidgetItem( k )
                                        item.setCheckState( Qt.Checked if (item.text() in modelle) else Qt.Unchecked )
                                        self.twModellarten.setItem( i, 0, item )

                                        item = QTableWidgetItem( str(n) )
                                        self.twModellarten.setItem( i, 1, item )
                                        i += 1
                                self.twModellarten.resizeColumnsToContents()
                        elif error:
                                modelle = []
                                self.twModellarten.clearContents()
                                self.twModellarten.setDisabled( True )
                        else:
                                modelle = []
                elif error:
                        QMessageBox.critical( None, "ALKIS", u"Datenbankverbindung schlug fehl." )

        def accept(self):
                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                s.setValue( "service", self.leSERVICE.text() )
                s.setValue( "host", self.leHOST.text() )
                s.setValue( "port", self.lePORT.text() )
                s.setValue( "dbname", self.leDBNAME.text() )
                s.setValue( "uid", self.leUID.text() )
                s.setValue( "pwd", self.lePWD.text() )

                modelle = []
                for i in range( self.twModellarten.rowCount() ):
                        item = self.twModellarten.item(i,0)
                        if item.checkState() == Qt.Checked:
                                modelle.append( item.text() )

                s.setValue( "modellarten", modelle )

                QDialog.accept(self)

class Info( QDialog, InfoBase ):
        def __init__(self, html):
                QDialog.__init__(self)
                self.setupUi(self)

                self.wvEigner.setHtml( html )

                self.restoreGeometry( QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" ).value("infogeom", QByteArray(), type=QByteArray) )

	def print_(self):
		printer = QPrinter()
		dlg = QPrintDialog( printer )
		if dlg.exec_() == QDialog.Accepted:
			self.wvEigner.print_( printer )

	def contextMenuEvent(self,e):
		menu = QMenu( self )
		action = QAction( "Drucken", self );
		action.triggered.connect( self.print_ )
		menu.addAction( action )
		menu.exec_( e.globalPos() )

        def closeEvent(self, e):
                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                s.setValue( "infogeom", self.saveGeometry() )
                QDialog.closeEvent(self, e)


class About( QDialog, AboutBase ):
        def __init__(self):
                QDialog.__init__(self)
                self.setupUi(self)

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

                self.areaMarkerLayer = None

        def canvasPressEvent(self,event):
                if not self.areaMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.areaMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )

        def canvasMoveEvent(self,event):
                pass

        def canvasReleaseEvent(self,e):
                point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( e.x(), e.y() )

                c = self.iface.mapCanvas()
                if c.hasCrsTransformEnabled():
                        try:
                                t = QgsCoordinateTransform( c.mapSettings().destinationCrs(), self.areaMarkerLayer.crs() )
                        except:
                                t = QgsCoordinateTransform( c.mapRenderer().destinationCrs(), self.areaMarkerLayer.crs() )
                        point = t.transform( point )

                QApplication.setOverrideCursor( Qt.WaitCursor )

                fs = self.plugin.highlight( u"st_contains(wkb_geometry,st_geomfromtext('POINT(%.3lf %.3lf)'::text,find_srid('','ax_flurstueck','wkb_geometry')))" % (
                                                        point.x(), point.y()
                                        ) )

                if len(fs) == 0:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.information( None, u"Fehler", u"Kein Flurstück gefunden." )
                        return

                try:
			s = QSettings( "norBIT", "EDBSgen/PRO" )
                        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                        sock.connect( ( "localhost", int( s.value( "norGISPort", "6102" ) ) ) )
                        sock.send( "NORGIS_MAIN#EDBS#ALBKEY#%s#" % fs[0]['flsnr'] )
                        sock.close()

                        if win32:
                                window = win32gui.FindWindow( None, s.value( "albWin", "norGIS" ) )
                                win32gui.SetForegroundWindow( window )
                except:
                        QMessageBox.information( None, u"Fehler", u"Verbindung zu norGIS schlug fehl." )

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

                self.rubberBand = QgsRubberBand( self.iface.mapCanvas(), QGis.Polygon )
                self.areaMarkerLayer = None

        def canvasPressEvent(self,e):
                if not self.areaMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.areaMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )

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

                        c = self.iface.mapCanvas()
                        if c.hasCrsTransformEnabled():
                                try:
                                        t = QgsCoordinateTransform( c.mapSettings().destinationCrs(), self.areaMarkerLayer.crs() )
                                except:
                                        t = QgsCoordinateTransform( c.mapRenderer().destinationCrs(), self.areaMarkerLayer.crs() )
                                g.transform( t )

                        self.rubberBand.reset( QGis.Polygon )

                        fs = self.plugin.highlight( u"st_intersects(wkb_geometry,st_geomfromtext('POLYGON((%s))'::text,find_srid('','ax_flurstueck','wkb_geometry')))" % (
                                                        ",".join( map ( lambda p : "%.3lf %.3lf" % ( p[0], p[1] ), g.asPolygon()[0] ) )
                                                ) )

                        if len(fs) == 0:
                                QApplication.restoreOverrideCursor()
                                QMessageBox.information( None, u"Fehler", u"Keine Flurstücke gefunden." )
                                return

                        gmlids = []
                        for e in fs:
                                gmlids.append( e['gmlid'] )

                        try:
                                s = QSettings( "norBIT", "EDBSgen/PRO" )
                                for i in range(0, len(fs)):
                                        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                                        sock.connect( ( "localhost", int( s.value( "norGISPort", "6102" ) ) ) )
                                        sock.send( "NORGIS_MAIN#EDBS#ALBKEY#%s#%d#" % (fs[i]['flsnr'], 0 if i+1 == len(fs) else 1 ) )
                                        sock.close()

                                if win32:
                                        window = win32gui.FindWindow( None, s.value( "albWin", "norGIS" ) )
                                        win32gui.SetForegroundWindow( window )

                        except:
                                QMessageBox.information( None, u"Fehler", u"Verbindung zu norGIS schlug fehl." )
                else:
                        self.rubberBand.reset( QGis.Polygon )

                QApplication.restoreOverrideCursor()

class ALKISSearch(QDialog, ALKISSearchBase ):
        def __init__(self, plugin):
                QDialog.__init__(self)
                self.setupUi(self)
                self.plugin = plugin

                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                self.cbxSuchmodus.setCurrentIndex( s.value( "suchmodus", 0, type=int ) )

        def accept(self):
                if not self.plugin.initLayers():
                        return

                text = self.leSuchbegriff.text()

                if self.cbxSuchmodus.currentIndex() < 2:
                        if text <> "":
                            text = text.replace("'", "''")
                            if self.cbxSuchmodus.currentIndex() == 0:
                                # Teiltreffer
                                text = u"text LIKE '%%%s%%'" % text
                            else:
                                # Exakter Treffer
                                text = u"text='%s'" % text

                            (db,conninfo) = self.plugin.opendb()
                            if db is None:
                                return

                            qry = QSqlQuery(db)

                            if qry.exec_( u"SELECT find_srid('','po_labels', 'point')" ) and qry.next():
                                crs = qry.value(0)

                                sql = u"SELECT count(*),st_extent( coalesce(point,line) ) FROM po_labels WHERE {0}".format( text )
                                if qry.exec_( sql ) and qry.next() and qry.value(0)>0:
                                    self.plugin.zoomToExtent( qry.value(1), crs )
                                else:
                                    QMessageBox.information( None, "ALKIS", u"Keine Treffer gefunden." )
                                    return
                        else:
                            text = "false"

                        self.plugin.pointMarkerLayer.setSubsetString( text )
                        self.plugin.lineMarkerLayer.setSubsetString( text )

                elif self.cbxSuchmodus.currentIndex() == 2:  # Flurstücksnummer
                        m = re.search( "(\\d+)(-\\d+)?-(\\d+)(/\\d+)?", text )
                        if m:
                                g, f, z, n = int( m.group(1) ), m.group(2), int( m.group(3) ), m.group(4)
                                f = int( f[1:] ) if f else 0
                                n = int( n[1:] ) if n else 0

                                flsnr  = "%06d" % g
                                flsnr += "%03d" % f if f>0 else "___"
                                flsnr += "%05d" % z
                                flsnr += "%04d" % n if n>0 else "____"
                                flsnr += "%"

                                fs = self.plugin.highlight( u"flurstueckskennzeichen LIKE %s" % quote(flsnr), True )
                                if len(fs)==0:
                                        QMessageBox.information( None, u"Fehler", u"Kein Flurstück %s gefunden." % flsnr )
                                        return

                elif self.cbxSuchmodus.currentIndex() == 3:  # Straße und Hausnummer
                        m = re.search( "^(.*)\s+(\d+[a-zA-Z]?)$", text )
                        if m:
                                strasse, ha = m.group(1), m.group(2)
                                fs = self.plugin.highlight( u"EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h JOIN ax_lagebezeichnungkatalogeintrag k ON h.land=k.land AND h.regierungsbezirk=k.regierungsbezirk AND h.kreis=k.kreis AND h.gemeinde=k.gemeinde AND h.lage=k.lage WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND k.bezeichnung LIKE {0} AND h.hausnummer={1})".format( quote(strasse+'%'), quote(ha.upper()) ), True )
                                if len(fs)==0:
                                    QMessageBox.information( None, u"Fehler", u"Kein Flurstück %s %s gefunden." % (strasse, ha) )
                                    return

                elif self.cbxSuchmodus.currentIndex() == 4:  # Eigentümer
                        where = "bs.gml_id=ax_flurstueck.istgebucht AND bs.endet IS NULL"
                        for e in text.split():
                                where += ( " AND " +
                                  (
                                  u"coalesce((SELECT v||' ' FROM alkis_wertearten WHERE element='ax_person' AND bezeichnung='anrede' AND k=p.anrede::text),'')||"
                                  u"coalesce(p.akademischergrad||' ', '')||"
                                  u"coalesce(p.vorname||' ', '')||"
                                  u"coalesce(p.namensbestandteil||' ', '')||"
                                  u"p.nachnameoderfirma||"
                                  u"coalesce(', geb. '||p.geburtsname,'')"
                                  ) + " LIKE " + quote('%'+e+'%')
                                )

                        fs = self.plugin.highlight( (
                                u"EXISTS ("
                                u" SELECT *"
                                u" FROM ax_buchungsstelle bs"
                                u" JOIN ax_buchungsblatt bb ON bb.gml_id=bs.istbestandteilvon OR EXISTS (SELECT * FROM ax_buchungsstelle bs0 WHERE bs0.endet IS NULL AND ARRAY[bs0.gml_id] <@ bs.an AND bb.gml_id=bs0.istbestandteilvon)"
                                u" JOIN ax_namensnummer nn ON bb.gml_id=nn.istbestandteilvon AND bb.endet IS NULL"
                                u" JOIN ax_person p ON p.gml_id=nn.benennt AND p.endet IS NULL"
                                u" WHERE " ) + where + ")", True )
                        if len(fs)==0:
                            QMessageBox.information( None, u"Fehler", u"Kein Flurstück mit Eigentümer '%s' gefunden." % text )
                            return

                s = QSettings( "norBIT", "norGIS-ALKIS-Erweiterung" )
                s.setValue( "suchmodus", self.cbxSuchmodus.currentIndex() )

                QDialog.accept(self)

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

                self.areaMarkerLayer = None

        def canvasPressEvent(self,e):
                if not self.areaMarkerLayer:
                        (layerId,ok) = QgsProject.instance().readEntry( "alkis", "/areaMarkerLayer" )
                        if ok:
                                self.areaMarkerLayer = QgsMapLayerRegistry.instance().mapLayer( layerId )

                if not self.areaMarkerLayer:
                        QMessageBox.warning( None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!\n" )

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

                c = self.iface.mapCanvas()
                if c.hasCrsTransformEnabled():
                        try:
                                t = QgsCoordinateTransform( c.mapSettings().destinationCrs(), self.areaMarkerLayer.crs() )
                        except:
                                t = QgsCoordinateTransform( c.mapRenderer().destinationCrs(), self.areaMarkerLayer.crs() )
                        point = t.transform( point )

                try:
                        QApplication.setOverrideCursor( Qt.WaitCursor )

                        fs = self.plugin.highlight( u"st_contains(wkb_geometry,st_geomfromtext('POINT(%.3lf %.3lf)'::text,find_srid('','ax_flurstueck','wkb_geometry')))" % (
                                                        point.x(), point.y()
                                                ) )

                        if len(fs) == 0:
                                QApplication.restoreOverrideCursor()
                                QMessageBox.information( None, u"Fehler", u"Kein Flurstück gefunden." )
                                return
                finally:
                        QApplication.restoreOverrideCursor()

                info = Info( self.getPage(fs) )
                info.setWindowTitle( u"Flurstücksnachweis" )
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
                        if len(res) == 1:
                                res = res[0]
                        else:
                                QMessageBox.information( None, "Fehler", u"Flurstück %s nicht gefunden.\n[%s]" % (flsnr,repr(fs)) )
                                return

                        res['datum'] = QDate.currentDate().toString( "d. MMMM yyyy" )
                        res['hist'] = 0

                        res['str']  = self.fetchall( db, "SELECT sstr.strname,str.hausnr FROM str_shl sstr JOIN strassen str ON str.strshl=sstr.strshl WHERE str.flsnr='%s' AND str.ff_stand=0" % flsnr )
                        res['nutz'] = self.fetchall( db, "SELECT n21.*, nu.nutzshl, nu.nutzung FROM nutz_21 n21, nutz_shl nu WHERE n21.flsnr='%s' AND n21.nutzsl=nu.nutzshl AND n21.ff_stand=0" % flsnr )
                        res['klas'] = self.fetchall( db, "SELECT kl.*, kls.klf_text FROM klas_3x kl, kls_shl kls WHERE kl.flsnr='%s' AND kl.klf=kls.klf AND kl.ff_stand=0" % flsnr )
                        res['afst'] = self.fetchall( db, "SELECT au.*, af.afst_txt FROM ausfst au,afst_shl af WHERE au.flsnr='%s' AND au.ausf_st=af.ausf_st AND au.ff_stand=0" % flsnr )
                        res['best'] = self.fetchall( db, "SELECT ea.bvnr,'' as pz,(SELECT eignerart FROM eign_shl WHERE ea.b = b) as eignerart,%s as anteil,ea.ff_stand AS zhist,b.bestdnr,b.gbbz,b.gbblnr,b.bestfl,b.ff_stand AS bhist FROM eignerart ea JOIN bestand b ON ea.bestdnr = b.bestdnr WHERE ea.flsnr='%s' ORDER BY zhist,bhist,b" %
                                                                ("ea.anteil" if exists_ea_anteil else "''", flsnr) )

                        for b in res['best']:
                                b['bse'] = self.fetchall( db, "SELECT * FROM eigner WHERE bestdnr='%s' AND ff_stand=0" % b['bestdnr'] )

#                        for k,v in res.iteritems():
#                                qDebug( u"%s:%s\n" % ( k, unicode(v) ) )

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

#               f = open("c:/cygwin/tmp/fs.html", "w")
#               f.write(html.encode('utf8'))
#               f.close()

                return html
