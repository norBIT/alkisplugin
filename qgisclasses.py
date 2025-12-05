# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    qgisclasses.py
    ---------------------
    Date                 : May 2014
    Copyright            : (C) 2014-2025 by Jürgen Fischer
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
from builtins import str
from builtins import range

from qgis.PyQt.QtCore import Qt, QDate, QDir, QByteArray, QSize, QEvent, QSettings, QPoint, QLocale
from qgis.PyQt.QtWidgets import QApplication, QDialog, QDialogButtonBox, QMessageBox, QTableWidgetItem, QAction, QMenu, QFileDialog, QTextBrowser, QVBoxLayout
from qgis.PyQt.QtGui import QCursor, QPixmap, QIntValidator
from qgis.PyQt.QtPrintSupport import QPrintDialog, QPrinter
from qgis.PyQt.QtSql import QSqlQuery
from qgis.PyQt import uic

from qgis.core import QgsMessageLog, QgsProject
from qgis.gui import QgsMapTool, QgsAuthConfigSelect, QgsRubberBand
from qgis.utils import qgsfunction

import qgis.gui

import socket
import os
import re
import operator

try:
    import win32gui
    win32 = True
except ImportError:
    win32 = False

d = os.path.dirname(__file__)
QDir.addSearchPath("alkis", d)
ConfBase = uic.loadUiType(os.path.join(d, 'conf.ui'))[0]
AboutBase = uic.loadUiType(os.path.join(d, 'about.ui'))[0]
ALKISSearchBase = uic.loadUiType(os.path.join(d, 'search.ui'))[0]


def qDebug(s):
    QgsMessageLog.logMessage(s, u'ALKIS')


def quote(x, prefix='E'):
    if type(x) == str:
        x.replace("'", "''")
        x.replace("\\", "\\\\")
        if x.find("\\") < 0:
            return u"'%s'" % x
        else:
            return u"%s'%s'" % (prefix, x)
    elif type(x) == str and x.find(u"\\"):
        x.replace(u"\\", u"\\\\")
        return u"%s'%s'" % (prefix, str(x))
    else:
        return u"'%s'" % str(x)


class ALKISConf(QDialog, ConfBase):
    def __init__(self, plugin):
        QDialog.__init__(self)
        self.setupUi(self)

        self.plugin = plugin
        self.settings = plugin.settings
        self.settings.loadSettings()

        self.leSERVICE.setText(self.settings.service)
        self.leHOST.setText(self.settings.host)
        self.lePORT.setText(self.settings.port)
        self.leDBNAME.setText(self.settings.dbname)
        self.leSCHEMA.setText(self.settings.schema)
        self.leUID.setText(self.settings.uid)
        self.lePWD.setText(self.settings.pwd)
        self.cbxSignaturkatalog.setEnabled(False)

        if hasattr(qgis.gui, 'QgsAuthConfigSelect'):
            self.authCfgSelect = QgsAuthConfigSelect(self, "postgres")
            self.tabWidget.insertTab(1, self.authCfgSelect, "Konfigurationen")

            authcfg = self.settings.authcfg
            if authcfg:
                self.tabWidget.setCurrentIndex(1)
                self.authCfgSelect.setConfigId(authcfg)

        self.leUMNPath.setText(self.settings.umnpath)
        self.pbUMNBrowse.clicked.connect(self.browseUMNPath)
        self.leUMNTemplate.setText(self.settings.umntemplate)
        self.leFussnote.setPlainText(self.settings.footnote)
        self.leTemplate.setText(self.settings.template)
        self.pbTemplateBrowse.clicked.connect(self.browseTemplate)

        self.loadModels(False)

        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        self.bb.addButton("Modelle laden", QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(self.loadModels)
        self.bb.addButton("Layer einbinden", QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(self.loadLayers)

        self.restoreGeometry(QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("confgeom", QByteArray(), type=QByteArray))

    def done(self, r):
        QSettings("norBIT", "norGIS-ALKIS-Erweiterung").setValue("confgeom", self.saveGeometry())
        return QDialog.done(self, r)

    def loadModels(self, error=True):
        self.settings.service = self.leSERVICE.text()
        self.settings.host = self.leHOST.text()
        self.settings.port = self.lePORT.text()
        self.settings.dbname = self.leDBNAME.text()
        self.settings.schema = self.leSCHEMA.text() or 'public'
        self.settings.uid = self.leUID.text()
        self.settings.pwd = self.lePWD.text()
        if hasattr(qgis.gui, 'QgsAuthConfigSelect'):
            self.settings.authcfg = self.authCfgSelect.configId()

        self.twModellarten.clearContents()
        self.cbxSignaturkatalog.clear()

        (db, conninfo) = self.plugin.opendb()
        if not db:
            if error:
                QMessageBox.critical(None, "ALKIS", u"Datenbankverbindung schlug fehl.")

            self.twModellarten.clearContents()
            self.twModellarten.setDisabled(True)
            self.twModellarten.setRowCount(0)

            self.settings.load()

            return

        modelle = self.settings.modellarten
        if modelle is None:
            modelle = ['DLKM', 'DKKM1000']

        qry = QSqlQuery(db)
        if qry.exec("SELECT 1 FROM information_schema.tables WHERE table_schema={} AND table_name='po_modelle'".format(quote(self.plugin.settings.schema))) and qry.next():
            sql = "SELECT modell,n FROM po_modelle WHERE modell IS NOT NULL ORDER BY n DESC"
        else:
            sql = """
SELECT modell,count(*)
FROM (
SELECT unnest(modell) AS modell FROM po_points   UNION ALL
SELECT unnest(modell) AS modell FROM po_lines    UNION ALL
SELECT unnest(modell) AS modell FROM po_polygons UNION ALL
SELECT unnest(modell) AS modell FROM po_labels
) AS foo
WHERE modell IS NOT NULL
GROUP BY modell
ORDER BY count(*) DESC
"""

        if qry.exec(sql):
            res = {}
            while qry.next():
                res[qry.value(0)] = qry.value(1)

            self.twModellarten.setRowCount(len(res))
            i = 0
            for k, n in sorted(iter(list(res.items())), key=operator.itemgetter(1), reverse=True):
                item = QTableWidgetItem(k)
                item.setCheckState(Qt.CheckState.Checked if (item.text() in modelle) else Qt.CheckState.Unchecked)
                self.twModellarten.setItem(i, 0, item)

                item = QTableWidgetItem(str(n))
                self.twModellarten.setItem(i, 1, item)
                i += 1
            self.twModellarten.resizeColumnsToContents()
            self.twModellarten.setEnabled(True)
        else:
            self.twModellarten.clearContents()
            self.twModellarten.setDisabled(True)
            self.twModellarten.setRowCount(0)

        if qry.exec("SELECT id,name FROM alkis_signaturkataloge"):
            while qry.next():
                self.cbxSignaturkatalog.addItem(qry.value(1), int(qry.value(0)))
            self.cbxSignaturkatalog.setEnabled(True)
        else:
            self.cbxSignaturkatalog.addItem(u"Farbe", -1)

        self.cbxSignaturkatalog.setCurrentIndex(max([0, self.cbxSignaturkatalog.findData(self.settings.signaturkatalog)]))

        self.settings.load()

    def saveSettings(self):
        self.settings.service = self.leSERVICE.text()
        self.settings.host = self.leHOST.text()
        self.settings.port = self.lePORT.text()
        self.settings.dbname = self.leDBNAME.text()
        self.settings.schema = self.leSCHEMA.text() or 'public'
        self.settings.uid = self.leUID.text()
        self.settings.pwd = self.lePWD.text()
        if hasattr(qgis.gui, 'QgsAuthConfigSelect'):
            self.settings.authcfg = self.authCfgSelect.configId()

        self.settings.umnpath = self.leUMNPath.text()
        self.settings.umntemplate = self.leUMNTemplate.text()
        self.settings.template = self.leTemplate.text()
        self.settings.footnote = self.leFussnote.toPlainText()

        modelle = []
        if self.twModellarten.isEnabled():
            for i in range(self.twModellarten.rowCount()):
                item = self.twModellarten.item(i, 0)
                if item.checkState() == Qt.CheckState.Checked:
                    modelle.append(item.text())

        self.settings.modellarten = modelle
        self.settings.signaturkatalog = self.cbxSignaturkatalog.itemData(self.cbxSignaturkatalog.currentIndex())

        self.settings.saveSettings()

    def loadLayers(self):
        self.saveSettings()
        self.plugin.run()
        self.settings.load()
        QDialog.accept(self)

    def accept(self):
        self.saveSettings()
        self.settings.load()
        QDialog.accept(self)

    def browseUMNPath(self):
        path = self.leUMNPath.text()
        path = QFileDialog.getExistingDirectory(self, u"UMN-Pfad wählen", path)
        if path != "":
            self.leUMNPath.setText(path)

    def browseTemplate(self):
        path = self.leTemplate.text()
        path = QFileDialog.getOpenFileName(self, u"Jinja2-Template wählen", path, "", "Jinja2-Template (*.jinja2)")
        if isinstance(path, tuple):
            path = path[0]
        if path:
            self.leTemplate.setText(path)


class Info(QDialog):
    info = []

    @classmethod
    def showInfo(cls, plugin, html, gmlid, title, parent):
        info = Info(plugin, html, gmlid, title, parent)
        info.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        info.setModal(False)

        cls.info.append(info)

        info.show()

    def __init__(self, plugin, html, gmlid, title, parent):
        QDialog.__init__(self, parent)
        self.resize(QSize(740, 580))
        self.setWindowTitle(title)

        self.plugin = plugin
        self.gmlid = gmlid

        self.tbEigentuemer = QTextBrowser(self)
        self.tbEigentuemer.setHtml(html)
        self.tbEigentuemer.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tbEigentuemer)
        self.setLayout(layout)

        self.restoreGeometry(QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("infogeom", QByteArray(), type=QByteArray))
        self.move(self.pos() + QPoint(16, 16) * len(self.info))

    def print_(self):
        printer = QPrinter()
        dlg = QPrintDialog(printer)
        if dlg.exec() == QDialog.Accepted:
            self.tbEigentuemer.print_(printer)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        action = QAction("Drucken", self)
        action.triggered.connect(self.print_)
        menu.addAction(action)
        menu.exec(e.globalPos())

    def closeEvent(self, e):
        QSettings("norBIT", "norGIS-ALKIS-Erweiterung").setValue("infogeom", self.saveGeometry())
        self.info.remove(self)
        self.plugin.clearHighlight()
        QDialog.closeEvent(self, e)

    def event(self, e):
        if e.type() == QEvent.Type.WindowActivate:
            self.plugin.highlight(where="gml_id='{}'".format(self.gmlid))
        return QDialog.event(self, e)


class About(QDialog, AboutBase):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)


class ALKISPointInfo(QgsMapTool):
    def __init__(self, plugin):
        QgsMapTool.__init__(self, plugin.iface.mapCanvas())
        self.plugin = plugin
        self.iface = plugin.iface
        self.cursor = QCursor(QPixmap([
            "16 16 3 1",
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
            "       +.+      "
        ]))

        self.areaMarkerLayer = None

    def canvasPressEvent(self, e):
        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.plugin.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")

    def canvasMoveEvent(self, e):
        pass

    def canvasReleaseEvent(self, e):
        if hasattr(e, "mapPoint"):
            point = e.mapPoint()
        else:
            point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())

        point = self.plugin.transform(point)

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            fs = self.plugin.highlight(
                where=u"st_contains(wkb_geometry,st_geomfromtext('POINT(%.3lf %.3lf)'::text,%d))" % (
                    point.x(), point.y(), self.plugin.getepsg()
                )
            )

            if len(fs) == 0:
                QApplication.restoreOverrideCursor()
                QMessageBox.information(None, u"Fehler", u"Kein Flurstück gefunden.")
                return

            try:
                s = QSettings("norBIT", "EDBSgen/PRO")
                if s.value("useTempfile", 0) == 1:
                    f = open(os.path.join(os.getenv("TEMP"), "norgis-msg.log"), "a")
                    f.write("NORGIS_MAIN#EDBS#ALBKEY#{}#\n".format(fs[0]['flsnr']))
                    f.close()
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("localhost", int(s.value("norGISPort", "6102"))))
                    sock.send("NORGIS_MAIN#EDBS#ALBKEY#{}#".format(fs[0]['flsnr']).encode("utf-8"))
                    sock.close()

                if win32:
                    window = win32gui.FindWindow(None, s.value("albWin", "norGIS"))
                    win32gui.SetForegroundWindow(window)
            except socket.error:
                try:
                    QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
                    QMessageBox.information(None, u"Fehler", u"Verbindung zu norGIS schlug fehl.")
                finally:
                    QApplication.restoreOverrideCursor()

        finally:
            QApplication.restoreOverrideCursor()


class ALKISPolygonInfo(QgsMapTool):
    def __init__(self, plugin):
        QgsMapTool.__init__(self, plugin.iface.mapCanvas())
        self.plugin = plugin
        self.iface = plugin.iface
        self.cursor = QCursor(QPixmap([
            "16 16 3 1",
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
            "       +.+      "
        ]))

        self.rubberBand = QgsRubberBand(self.iface.mapCanvas(), self.plugin.PolygonGeometry)
        self.areaMarkerLayer = None

    def canvasPressEvent(self, e):
        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.plugin.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")

    def canvasMoveEvent(self, e):
        if self.rubberBand.numberOfVertices() > 0:
            if hasattr(e, "mapPoint"):
                point = e.mapPoint()
            else:
                point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())

            self.rubberBand.movePoint(point)

    def canvasReleaseEvent(self, e):
        if hasattr(e, "mapPoint"):
            point = e.mapPoint()
        else:
            point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())

        if e.button() == Qt.MouseButton.LeftButton:
            self.rubberBand.addPoint(point)
            return

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            if self.rubberBand.numberOfVertices() >= 3:
                g = self.plugin.transform(
                    self.rubberBand.asGeometry()
                )

                self.rubberBand.reset(self.plugin.PolygonGeometry)

                if hasattr(g, 'asWkt'):
                    wkt = g.asWkt()
                else:
                    wkt = "POLYGON((%s))" % (
                        ",".join(["%.3lf %.3lf" % (p[0], p[1]) for p in g.asPolygon()[0]])
                    )

                fs = self.plugin.highlight(
                    where=u"st_intersects(wkb_geometry,st_geomfromtext('%s'::text,%d))" % (
                        wkt, self.plugin.getepsg()
                    )
                )

                if len(fs) == 0:
                    QMessageBox.information(None, u"Fehler", u"Keine Flurstücke gefunden.")
                    return

                gmlids = []
                for e in fs:
                    gmlids.append(e['gmlid'])

                try:
                    s = QSettings("norBIT", "EDBSgen/PRO")
                    for i in range(0, len(fs)):
                        if s.value("useTempfile", 0) == 1:
                            f = open(os.path.join(os.getenv("TEMP"), "norgis-msg.log"), "a")
                            f.write("NORGIS_MAIN#EDBS#ALBKEY#{}#{}#\n".format(fs[i]['flsnr'], 0 if i + 1 == len(fs) else 1))
                            f.close()
                        else:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.connect(("localhost", int(s.value("norGISPort", "6102"))))
                            sock.send("NORGIS_MAIN#EDBS#ALBKEY#{}#{}#".format(fs[i]['flsnr'], 0 if i + 1 == len(fs) else 1).encode("utf-8"))
                            sock.close()

                    if win32:
                        window = win32gui.FindWindow(None, s.value("albWin", "norGIS"))
                        win32gui.SetForegroundWindow(window)

                except socket.error:
                    try:
                        QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
                        QMessageBox.information(None, u"Fehler", u"Verbindung zu norGIS schlug fehl.")
                    finally:
                        QApplication.restoreOverrideCursor()
            else:
                self.rubberBand.reset(self.plugin.PolygonGeometry)
        finally:
            QApplication.restoreOverrideCursor()


class ALKISSearch(QDialog, ALKISSearchBase):
    def __init__(self, plugin):
        QDialog.__init__(self)
        self.setupUi(self)
        self.plugin = plugin

        s = QSettings("norBIT", "norGIS-ALKIS-Erweiterung")

        v = QIntValidator()
        v.setBottom(1)
        self.leHighlightThreshold.setValidator(v)
        self.leHighlightThreshold.setText(str(s.value("highlightThreshold", 1000)))

        (db, conninfo) = self.plugin.opendb()
        self.db = db

        qry = QSqlQuery(db)
        if not qry.exec("SELECT has_table_privilege('eigner', 'SELECT')") or not qry.next() or not qry.value(0):
            self.tabWidget.removeTab(self.tabWidget.indexOf(self.tabEigentuemer))

        self.replaceButton = self.buttonBox.addButton(u"Ersetzen", QDialogButtonBox.ButtonRole.ActionRole)
        self.addButton = self.buttonBox.addButton(u"Hinzufügen", QDialogButtonBox.ButtonRole.ActionRole)
        self.removeButton = self.buttonBox.addButton(u"Entfernen", QDialogButtonBox.ButtonRole.ActionRole)
        self.clearButton = self.buttonBox.addButton(u"Leeren", QDialogButtonBox.ButtonRole.ActionRole)

        self.replaceButton.clicked.connect(self.replaceClicked)
        self.addButton.clicked.connect(self.addClicked)
        self.removeButton.clicked.connect(self.removeClicked)
        self.clearButton.clicked.connect(self.clearClicked)

        self.cbxStrassen.setEnabled(False)
        self.cbxHNR.setEnabled(False)

        self.pbLabelSearch.clicked.connect(self.evaluate)
        self.pbOwnerSearch.clicked.connect(self.evaluate)
        self.pbSearchFSK.clicked.connect(self.evaluate)

        self.highlighted = set(self.plugin.highlighted())

        self.lblResult.setText(u"{} Objekte bereits gewählt.".format(len(self.highlighted)) if len(self.highlighted) > 0 else "")

        self.restoreGeometry(QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("searchgeom", QByteArray(), type=QByteArray))

        self.tabWidget.setCurrentIndex(s.value("suchmodus", 0, type=int))

        self.cbxGemarkung.currentIndexChanged.connect(self.gfzn)
        self.cbxFlur.currentIndexChanged.connect(self.gfzn)
        self.cbxFSZ.currentIndexChanged.connect(self.gfzn)
        self.cbxFSN.currentIndexChanged.connect(self.gfzn)
        self.gfzn()

    def done(self, r):
        s = QSettings("norBIT", "norGIS-ALKIS-Erweiterung")
        s.setValue("searchgeom", self.saveGeometry())
        s.setValue("suchmodus", self.tabWidget.currentIndex())
        s.setValue("highlightThreshold", int(self.leHighlightThreshold.text()))
        return QDialog.done(self, r)

    #
    # Gemarkung/Flur/Flurstück
    #

    def gfzn(self):
        g = self.cbxGemarkung.itemData(self.cbxGemarkung.currentIndex()) if self.cbxGemarkung.currentIndex() >= 0 else None
        f = self.cbxFlur.itemData(self.cbxFlur.currentIndex()) if self.cbxFlur.currentIndex() >= 0 else None
        z = self.cbxFSZ.itemData(self.cbxFSZ.currentIndex()) if self.cbxFSZ.currentIndex() >= 0 else None
        n = self.cbxFSN.itemData(self.cbxFSN.currentIndex()) if self.cbxFSN.currentIndex() >= 0 else None

        where = []
        if g is not None and g != "":
            where.append("gemashl='%s'" % g)

        if f is not None and f != "":
            where.append("flr='%s'" % f)

        if z is not None and n is not None and z != "" and n != "":
            where.append("flsnrk='%s/%s'" % (z, n))
        elif z is not None and z != "":
            where.append("flsnrk LIKE '%s/%%'" % z)
        elif n is not None and n != "":
            where.append("flsnrk LIKE '%%/%s'" % n)

        where = u" WHERE {}".format(u" AND ".join(where)) if where else ""

        qry = QSqlQuery(self.db)

        # qDebug(u"WHERE:{}".format(where))

        for cbx, sql, val in [
            [
                self.cbxGemarkung,
                "SELECT {0} FROM gema_shl a LEFT OUTER JOIN gem_shl b USING (gemshl){1} GROUP BY {0} ORDER BY {0}".format(
                    "a.gemashl,a.gemarkung||' ('||a.gemashl||coalesce(', '||b.gemname,'')||')'",
                    u" JOIN flurst c USING (gemashl){0}".format(where) if where != "" else " WHERE EXISTS (SELECT 1 FROM flurst f WHERE f.gemashl=a.gemashl)"
                ),
                g,
            ],
            [
                self.cbxFlur,
                "SELECT {0} FROM flurst{1} GROUP BY {0} ORDER BY {0}".format("flr", where),
                f,
            ],
            [
                self.cbxFSZ,
                "SELECT {0} FROM flurst{1} GROUP BY {0} ORDER BY {0}".format("split_part(flsnrk,'/',1)", where),
                z,
            ],
            [
                self.cbxFSN,
                "SELECT {0} FROM flurst{1} GROUP BY {0} ORDER BY {0}".format("split_part(flsnrk,'/',2)", where),
                n,
            ],
        ]:
            cbx.blockSignals(True)
            cbx.clear()
            cbx.addItem("Alle", "")

            if qry.exec(sql):
                d = 0 if qry.record().count() == 1 else 1

                while qry.next():
                    cbx.addItem(qry.value(d), qry.value(0))
            else:
                qDebug(u"SQL:{} [{}]".format(qry.lastQuery(), qry.lastError().text()))

            cbx.setCurrentIndex(cbx.findData(val))
            cbx.blockSignals(False)

        if where == "":
            return

        hits = 0
        if qry.exec(u"SELECT count(*) FROM flurst{}".format(where)) and qry.next():
            hits = qry.value(0)

        if hits > 0 and hits < int(self.leHighlightThreshold.text()):
            self.evaluate()
        else:
            self.lblResult.setText(u"{} Flurstücke gefunden".format(hits) if hits > 0 else u"Keine Flurstücke gefunden")

    #
    # Straße/Hausnummer
    #

    def on_pbSearchStr_clicked(self):
        # qDebug("on_pbSearchStr_clicked: text={}".format(self.leStr.text()))
        qry = QSqlQuery(self.db)

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            self.cbxStrassen.blockSignals(True)
            self.cbxStrassen.clear()
            if qry.exec(
                u"SELECT bezeichnung, schluesselgesamt FROM ("
                u"SELECT k.bezeichnung || coalesce(', ' || g.bezeichnung,'') || coalesce(' (' || k.kennung || ')', '') AS bezeichnung, array_to_string(array_agg(DISTINCT k.schluesselgesamt), '#') AS schluesselgesamt"
                u" FROM ax_lagebezeichnungkatalogeintrag k"
                u" LEFT JOIN ax_lagebezeichnungmithausnummer m USING (land,regierungsbezirk,kreis,gemeinde,lage)"
                u" LEFT JOIN ax_lagebezeichnungohnehausnummer o USING (land,regierungsbezirk,kreis,gemeinde,lage)"
                u" LEFT OUTER JOIN ax_gemeinde g ON k.land=g.land AND k.regierungsbezirk=g.regierungsbezirk AND k.kreis=g.kreis AND k.gemeinde::int=g.gemeinde::int AND g.endet IS NULL"
                u" WHERE k.endet IS NULL AND ((m.gml_id IS NOT NULL AND m.endet IS NULL) OR (o.gml_id IS NOT NULL AND o.endet IS NULL))"
                u" GROUP BY k.bezeichnung, k.kennung, g.bezeichnung"
                u" UNION "
                u"SELECT DISTINCT unverschluesselt, ''"
                u" FROM ax_lagebezeichnungmithausnummer"
                u" WHERE endet IS NULL"
                u" UNION "
                u"SELECT DISTINCT unverschluesselt, ''"
                u" FROM ax_lagebezeichnungohnehausnummer"
                u" WHERE endet IS NULL"
                u") AS foo"
                u" WHERE bezeichnung ILIKE {0}"
                u" ORDER BY bezeichnung".format(quote(self.leStr.text().lower() + '%'))
            ):
                while qry.next():
                    name = qry.value(0)
                    keys = qry.value(1).split("#")
                    if len(keys) > 1:
                        for k in keys:
                            self.cbxStrassen.addItem(u"{} ({})".format(name, k), k)
                    else:
                        self.cbxStrassen.addItem(name, keys[0])
            else:
                qDebug(qry.lastError().text())

            self.cbxStrassen.blockSignals(False)
        finally:
            QApplication.restoreOverrideCursor()

        self.lblResult.setText(u"Keine Straßen gefunden" if self.cbxStrassen.count() == 0 else u"{} Straßen gefunden".format(self.cbxStrassen.count()))

        self.cbxStrassen.setEnabled(self.cbxStrassen.count() > 0)
        self.cbxStrassen.setCurrentIndex(0 if self.cbxStrassen.count() == 1 else -1)
        self.on_cbxStrassen_currentIndexChanged(self.cbxStrassen.currentIndex())

    def on_cbxStrassen_currentIndexChanged(self, index):
        # qDebug(u"on_cbxStrassen_currentIndexChanged: index={} text={}".format(self.cbxStrassen.currentIndex(), self.cbxStrassen.currentText()))
        if self.cbxStrassen.currentIndex() < 0:
            return

        qry = QSqlQuery(self.db)

        schluesselgesamt = self.cbxStrassen.itemData(self.cbxStrassen.currentIndex())
        if schluesselgesamt == '':
            schluesselgesamt = None

        self.cbxHNR.blockSignals(True)
        self.cbxHNR.clear()
        if (schluesselgesamt is None and qry.exec(u"SELECT h.hausnummer FROM ax_lagebezeichnungmithausnummer h WHERE unverschluesselt={0} AND h.endet IS NULL ORDER BY NULLIF(regexp_replace(h.hausnummer, E'\\\\D', '', 'g'), '')::int".format(quote(self.cbxStrassen.currentText())))) or \
           (schluesselgesamt is not None and qry.exec(u"SELECT h.hausnummer FROM ax_lagebezeichnungmithausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE h.endet IS NULL AND k.endet IS NULL AND k.schluesselgesamt={0} ORDER BY NULLIF(regexp_replace(h.hausnummer, E'\\\\D', '', 'g'), '')::int".format(quote(schluesselgesamt)))):
            while qry.next():
                self.cbxHNR.addItem(qry.value(0))
        else:
            qDebug(qry.lastError().text())

        if (schluesselgesamt is None and qry.exec(u"SELECT 1 FROM ax_lagebezeichnungohnehausnummer h WHERE h.endet IS NULL AND h.unverschluesselt={0}".format(quote(self.cbxStrassen.currentText())))) or \
           (schluesselgesamt is not None and qry.exec(u"SELECT 1 FROM ax_lagebezeichnungohnehausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE h.endet IS NULL AND k.endet IS NULL AND k.schluesselgesamt={0}".format(quote(schluesselgesamt)))):
            if qry.next():
                self.cbxHNR.addItem('Ohne')
        else:
            qDebug(qry.lastError().text())

        if self.cbxHNR.count() > 1:
            self.cbxHNR.addItem("Alle")

        self.cbxHNR.blockSignals(False)

        self.cbxHNR.setEnabled(self.cbxHNR.count() > 0)
        self.cbxHNR.setCurrentIndex(-1)
        if self.cbxHNR.count() == 1:
            self.cbxHNR.setCurrentIndex(0)

    def on_cbxHNR_currentIndexChanged(self, index):
        # qDebug(u"on_cbxHNR_currentIndexChanged: index={}".format(self.cbxHNR.currentIndex()))
        if self.cbxHNR.currentIndex() >= 0:
            self.evaluate()
        else:
            self.lblResult.setText(u"")

    def on_tabWidget_currentChanged(self, idx):
        self.updateButtons()

    #
    # Allgemein
    #

    def updateButtons(self, selection=[]):
        if self.tabWidget.currentWidget() == self.tabLabels:
            if not self.plugin.initLayers():
                return

            self.addButton.setEnabled(False)
            self.removeButton.setEnabled(False)
            self.replaceButton.setEnabled(False)
            self.clearButton.setEnabled(self.plugin.pointMarkerLayer.subsetString() != "false")
            return

        hits = len(selection) > 0
        highlighted = len(self.highlighted) > 0
        self.addButton.setEnabled(hits)
        self.removeButton.setEnabled(hits and highlighted)
        self.replaceButton.setEnabled(hits and highlighted)
        self.clearButton.setEnabled(highlighted)

    def evaluate(self):
        if not self.plugin.initLayers():
            return False

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            if self.tabWidget.currentWidget() == self.tabLabels:
                text = self.leSuchbegriff.text()
                if text != "":
                    if self.cbTeiltreffer.isChecked():
                        # Teiltreffer
                        text = u"lower(text) LIKE %s" % quote("%%%s%%" % text.lower())
                    else:
                        # Exakter Treffer
                        text = u"text=%s" % quote(text)

                    qry = QSqlQuery(self.db)

                    sql = u"SELECT count(*),st_extent(coalesce(point,line)) FROM po_labels WHERE {0}".format(text)
                    if qry.exec(sql) and qry.next() and qry.value(0) > 0:
                        self.lblResult.setText("{} Objekte gefunden".format(qry.value(0)))
                        self.plugin.zoomToExtent(qry.value(1), self.plugin.pointMarkerLayer.crs())
                    else:
                        self.lblResult.setText("Keine Objekte gefunden")
                        return False
                else:
                    text = "false"

                self.plugin.pointMarkerLayer.setSubsetString(text)
                self.plugin.lineMarkerLayer.setSubsetString(text)

                self.updateButtons()

            elif self.tabWidget.currentWidget() == self.tabGFF:
                g = self.cbxGemarkung.itemData(self.cbxGemarkung.currentIndex())
                f = self.cbxFlur.itemData(self.cbxFlur.currentIndex())
                z = self.cbxFSZ.itemData(self.cbxFSZ.currentIndex())
                n = self.cbxFSN.itemData(self.cbxFSN.currentIndex())

                flsnr = ""
                flsnr += ("%" if g is None or g == "" else g) + "-"
                flsnr += ("%" if f is None or f == "" else f) + "-"
                flsnr += ("%" if z is None or z == "" else z) + "/"
                flsnr += ("%" if n is None or n == "" else n)

                # qDebug(u"flsnr:{}".format(flsnr))
                fs = self.plugin.highlight(where=u"EXISTS (SELECT * FROM fs WHERE gml_id=fs_obj AND alb_key LIKE %s)" % quote(flsnr), zoomTo=True)

                self.lblResult.setText(u"{} Flurstücke gefunden".format(len(fs)) if len(fs) > 0 else u"Keine Flurstücke gefunden")
                self.updateButtons(fs)

            elif self.tabWidget.currentWidget() == self.tabFLSNR:
                m = re.search("(\\d+)(-\\d+)?-(\\d+)(/\\d+)?", self.leFLSNR.text())
                if m:
                    g, f, z, n = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
                    f = int(f[1:]) if f else 0
                    n = int(n[1:]) if n else 0

                    flsnr = "%06d" % g
                    flsnr += "%03d" % f if f > 0 else "___"
                    flsnr += "%05d" % z
                    flsnr += "%04d" % n if n > 0 else "____"
                    flsnr += "%"

                    fs = self.plugin.highlight(where=u"flurstueckskennzeichen LIKE %s" % quote(flsnr), zoomTo=True)
                else:
                    fs = []

                hits = len(fs)

                self.lblResult.setText(u"{} Flurstücke gefunden".format(hits) if hits > 0 else u"Keine Flurstücke gefunden")

                self.updateButtons(fs)

            elif self.tabWidget.currentWidget() == self.tabSTRHNR:
                text = self.leStr.text()
                if text != "":
                    m = re.search("^(.*)\\s+(\\d+[a-zA-Z]?)$", text)
                    if m:
                        strasse, ha = m.group(1), m.group(2)
                        fs = self.plugin.highlight(where=u"EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h LEFT OUTER JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND (lower(k.bezeichnung) LIKE {0} OR lower(h.unverschluesselt) LIKE {0}) AND h.hausnummer={1})".format(quote(strasse.lower() + '%'), quote(ha.upper())), zoomTo=True)
                        if len(fs) > 0:
                            self.lblResult.setText(u"{} Flurstücke gefunden".format(len(fs)))
                        else:
                            self.lblResult.setText(u"Keine Flurstücke gefunden")

                        self.updateButtons(fs)

                if self.cbxHNR.isEnabled():
                    hnr = self.cbxHNR.currentText()

                    if self.cbxStrassen.itemData(self.cbxStrassen.currentIndex()) != "":
                        # geschlüsselt
                        if hnr in ["Ohne", "Alle"]:
                            sql = u"EXISTS (SELECT * FROM ax_lagebezeichnungohnehausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE ARRAY[h.gml_id] <@ ax_flurstueck.zeigtauf AND k.schluesselgesamt={0})"

                            if hnr == "Alle":
                                sql += u" OR EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND k.schluesselgesamt={0})"
                        else:
                            sql = u"EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND k.schluesselgesamt={0}{2})"
                    else:
                        # unverschlüsselt
                        if hnr in ["Ohne", "Alle"]:
                            sql = u"EXISTS (SELECT * FROM ax_lagebezeichnungohnehausnummer h WHERE ARRAY[h.gml_id] <@ ax_flurstueck.zeigtauf AND unverschluesselt={1})"

                            if hnr == "Alle":
                                sql += u" OR EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND unverschluesselt={1})"
                        else:
                            sql = u"EXISTS (SELECT * FROM ax_lagebezeichnungmithausnummer h WHERE ARRAY[h.gml_id] <@ ax_flurstueck.weistauf AND unverschluesselt={1}{2})"

                    fs = self.plugin.highlight(
                        where=sql.format(
                            quote(self.cbxStrassen.itemData(self.cbxStrassen.currentIndex())),
                            quote(self.cbxStrassen.currentText()),
                            ' AND h.hausnummer={0}'.format(quote(hnr)) if hnr not in ["Alle", "Ohne"] else ""
                        ),
                        zoomTo=True
                    )
                    self.lblResult.setText(u"{} Flurstücke gefunden".format(len(fs)) if len(fs) > 0 else u"Keine Flurstücke gefunden")
                    self.updateButtons(fs)

            elif self.tabWidget.currentWidget() == self.tabEigentuemer:
                where = []
                for e in self.leEigentuemer.text().split():
                    where.append("lower(name1) LIKE " + quote('%' + e.lower() + '%'))

                if where:
                    fs = self.plugin.retrieve(u"gml_id IN (SELECT fs_obj FROM fs JOIN eignerart a ON fs.alb_key=a.flsnr JOIN eigner e ON a.bestdnr=e.bestdnr AND %s)" % " AND ".join(where))
                    if len(fs) == 0:
                        qDebug(u"Kein Flurstück gefunden")
                        self.updateButtons()
                        return False

                    if not self.plugin.logQuery("eigentuemerSuche", self.leEigentuemer.text(), [i['flsnr'] for i in fs]):
                        self.lblResult.setText(u"Flurstücke werden ohne Protokollierung nicht angezeigt.")
                        self.updateButtons()
                        return False

                    fs = self.plugin.highlight(fs=fs, zoomTo=True)
                    self.lblResult.setText(u"{} Flurstücke gefunden".format(len(fs)) if len(fs) > 0 else u"Keine Flurstücke gefunden")
                    self.updateButtons(fs)

        finally:
            QApplication.restoreOverrideCursor()

        return True

    def addClicked(self):
        self.evaluate()
        self.highlighted |= set(self.plugin.highlighted())
        self.plugin.highlight(where="gml_id IN ('" + "','".join(self.highlighted) + "')", zoomTo=True)
        self.lblResult.setText(u"{} Objekte gewählt.".format(len(self.highlighted)) if len(self.highlighted) > 0 else "")
        self.updateButtons()

    def removeClicked(self):
        self.evaluate()
        self.highlighted -= set(self.plugin.highlighted())
        self.plugin.highlight(where="gml_id IN ('" + "','".join(self.highlighted) + "')", zoomTo=True)
        self.lblResult.setText(u"Nun {} Objekte gewählt.".format(len(self.highlighted)) if len(self.highlighted) > 0 else "")
        self.updateButtons()

    def clearClicked(self):
        if self.tabWidget.currentWidget() == self.tabLabels:
            self.plugin.pointMarkerLayer.setSubsetString("false")
        else:
            self.plugin.areaMarkerLayer.setSubsetString("false")
            self.highlighted = set()

        self.lblResult.setText(u"Auswahl gelöscht.")
        self.updateButtons()

    def replaceClicked(self):
        self.evaluate()
        self.highlighted = set(self.highlighted)
        self.lblResult.setText(u"{} Objekte gewählt.".format(len(self.highlighted)) if len(self.highlighted) > 0 else "")
        self.updateButtons()

    def reject(self):
        if len(self.highlighted) > 0:
            self.plugin.highlight(where="gml_id IN ('" + "','".join(self.highlighted) + "')", zoomTo=True)

        QDialog.reject(self)


class ALKISOwnerInfo(QgsMapTool):
    def __init__(self, plugin):
        QgsMapTool.__init__(self, plugin.iface.mapCanvas())
        self.plugin = plugin
        self.iface = plugin.iface
        self.cursor = QCursor(QPixmap([
            "16 16 3 1",
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
            "       +.+      "
        ]))

        self.areaMarkerLayer = None

    def canvasPressEvent(self, e):
        if self.areaMarkerLayer is None:
            (layerId, ok) = QgsProject.instance().readEntry("alkis", "/areaMarkerLayer")
            if ok:
                self.areaMarkerLayer = self.plugin.mapLayer(layerId)

        if self.areaMarkerLayer is None:
            QMessageBox.warning(None, "ALKIS", u"Fehler: Flächenmarkierungslayer nicht gefunden!")

    def canvasMoveEvent(self, e):
        pass

    def fetchall(self, db, sql):
        rows = []

        qry = QSqlQuery(db)

        if qry.exec(sql):
            rec = qry.record()

            while qry.next():
                row = {}

                for i in range(0, rec.count()):
                    v = "%s" % qry.value(i)
                    if v in ["NULL", "None", None]:
                        v = ''
                    row[rec.fieldName(i)] = v.strip()

                rows.append(row)
        else:
            qDebug("Exec failed: " + qry.lastError().text())

        return rows

    def canvasReleaseEvent(self, e):
        if hasattr(e, "mapPoint"):
            point = e.mapPoint()
        else:
            point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())

        point = self.plugin.transform(point)

        p = "POINT(%.3lf %.3lf)" % (point.x(), point.y())

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            fs = self.plugin.retrieve(u"st_contains(wkb_geometry,st_geomfromtext('{}'::text,{}))".format(
                p, self.plugin.getepsg()
            ))

            if not self.plugin.logQuery("eigentuemerInfo", p, [i['flsnr'] for i in fs]):
                QMessageBox.information(None, u"Hinweis", u"Flurstücke werden ohne Protokollierung nicht angezeigt.")
                return

            if len(fs) == 0:
                QMessageBox.information(None, u"Hinweis", u"Kein Flurstück gefunden.")
                return

            fs = self.plugin.highlight(fs=fs, zoomTo=False)

        finally:
            QApplication.restoreOverrideCursor()

        page = self.showPage(fs)
        if page is not None:
            Info.showInfo(self.plugin, page, fs[0]['gmlid'], f"Flurstücksnachweis {fs[0]['flsnr']}", self.iface.mainWindow())

    def showPage(self, fs):
        html = self.getPage(fs, template=self.plugin.settings.template)
        if html is None:
            QMessageBox.information(None, "Fehler", u"Flurstück %s nicht gefunden.\n[%s]" % (flsnr, repr(fs)))
            return None

        return f"""\
<HTML xmlns="http://www.w3.org/1999/xhtml">
  <HEAD>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  </HEAD>
  <BODY>
{html}
</BODY>
</HTML>"""

    def getPage(self, fs, template=None):
        (db, conninfo) = self.plugin.opendb()
        if db is None:
            qDebug("No database")
            return None

        qry = QSqlQuery(db)
        if qry.exec("SELECT 1 FROM information_schema.columns WHERE table_schema={} AND table_name='eignerart' AND column_name='anteil'".format(quote(self.plugin.settings.schema))) and qry.next():
            exists_ea_anteil = qry.value(0) == 1
        else:
            exists_ea_anteil = False

        if qry.exec("SELECT 1 FROM information_schema.columns WHERE table_schema={} AND table_name='ax_buchungsblattbezirk' AND column_name='gehoertzu_land'".format(quote(self.plugin.settings.schema))) and qry.next():
            ghz = qry.value(0) == 1
        else:
            ghz = False

        for i in range(0, len(fs)):
            flsnr = fs[i]['flsnr']

            best = self.fetchall(db, (
                "SELECT"
                " ea.bvnr"
                ",'' as pz"
                ",(SELECT eignerart FROM eign_shl WHERE ea.b=b) as eignerart"
                ",%s as anteil"
                ",ea.ff_stand AS zhist"
                ",b.bestdnr"
                ",b.gbbz"
                ",b.gbblnr"
                ",%s AS bezeichnung"
                ",b.bestfl"
                ",ea.auftlnr"
                ",b.ff_stand AS bhist"
                " FROM eignerart ea"
                " JOIN bestand b ON ea.bestdnr = b.bestdnr"
                " WHERE ea.flsnr = '%s'"
                " ORDER BY zhist,bhist,b") % (
                    "ea.anteil" if exists_ea_anteil else "''",
                    "(SELECT d.bezeichnung FROM ax_buchungsblattbezirk bbb JOIN ax_dienststelle d ON bbb.gehoertzu_land||bbb.gehoertzu_stelle=d.schluesselgesamt AND d.stellenart='1000' WHERE b.gbbz=bbb.bezirk AND substr(b.bestdnr,1,2)=bbb.land LIMIT 1)" if ghz else "''",
                    flsnr)
            )

            res = self.fetchall(db, "SELECT f.*,g.gemarkung FROM flurst f LEFT OUTER JOIN gema_shl g ON (f.gemashl=g.gemashl) WHERE f.flsnr='%s' AND f.ff_stand=0" % flsnr)
            if len(res) == 1:
                res = res[0]
            else:
                qDebug("Flurstück {} nicht gefunden.".format(flsnr))
                return None

            if qry.exec(u"SELECT max(to_timestamp(datadate, 'YYYY-MM-DDTHH:MI:SSZ')) FROM alkis_importe") and qry.next() and qry.value(0) not in ["NULL", "None", None]:
                res['datum'] = 'Stand: ' + QLocale.system().toString(qry.value(0), "d. MMMM yyyy")
            else:
                res['datum'] = QLocale.system().toString(QDate.currentDate(), "d. MMMM yyyy")

            res['hist'] = 0

            if qry.exec(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['strassen', 'str_shl']])) and qry.next() and qry.value(0):
                res['str'] = self.fetchall(db, "SELECT sstr.strname,str.hausnr FROM str_shl sstr JOIN strassen str ON str.strshl=sstr.strshl WHERE str.flsnr='%s' AND str.ff_stand=0 ORDER BY sstr.strname,coalesce(substring(str.hausnr FROM '^(\\d+)$')::integer, 0),str.hausnr" % flsnr)

            if qry.exec(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['nutz_21', 'nutz_shl']])) and qry.next() and qry.value(0):
                res['nutz'] = self.fetchall(db, "SELECT n21.*, nu.nutzshl, nu.nutzung FROM nutz_21 n21, nutz_shl nu WHERE n21.flsnr='%s' AND n21.nutzsl=nu.nutzshl AND n21.ff_stand=0" % flsnr)

            if qry.exec(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['klas_3x', 'kls_shl']])) and qry.next() and qry.value(0):
                res['klas'] = self.fetchall(db, "SELECT sum(fl::int) AS fl, kls.klf_text || coalesce(', EMZ ' || sum(wertz2::int*fl::int/100), '') AS klf_text FROM klas_3x kl, kls_shl kls WHERE kl.flsnr='%s' AND kl.klf=kls.klf AND kl.ff_stand=0 GROUP BY kls.klf, kls.klf_text" % flsnr)
                res['emz'] = self.fetchall(db, "SELECT sum(wertz2::int*fl::int/100) AS emz FROM klas_3x WHERE flsnr='%s' AND ff_stand=0 AND wertz2 IS NOT NULL" % flsnr)
                if len(res['emz']) == 1:
                    res['emz'] = res['emz'][0]['emz']
                    if res['emz'] == '':
                        del res['emz']
                else:
                    del res['emz']

            if qry.exec(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['ausfst', 'afst_shl']])) and qry.next() and qry.value(0):
                res['afst'] = self.fetchall(db, "SELECT au.*, af.afst_txt FROM ausfst au,afst_shl af WHERE au.flsnr='%s' AND au.ausf_st=af.ausf_st AND au.ff_stand=0" % flsnr)

            if qry.exec(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['bestand', 'eignerart', 'eign_shl']])) and qry.next() and qry.value(0):
                res['best'] = best

                if qry.exec("SELECT has_table_privilege('eigner', 'SELECT')") and qry.next() and qry.value(0):
                    for b in res['best']:
                        b['bse'] = self.fetchall(db, "SELECT * FROM eigner WHERE bestdnr='%s' AND ff_stand=0 ORDER BY coalesce(namensnr,'0')" % b['bestdnr'])

#                        for k,v in res.iteritems():
#                                qDebug( u"%s:%s\n" % ( k, unicode(v) ) )

            if self.plugin.settings.footnote:
                res['footnote'] = self.plugin.settings.footnote

            if template:
                with open(template, "r") as f:
                    template = f.read()
            else:
                template = """\
<style>
.fls_tab{width:100%;empty-cells:show;border:0}
.fls_headline{font-weight:bold;font-size:16pt;}
.fls_headline_col{background-color:#EEEEEE;width:100%;height:3em;text-align:left;}
.fls_time{background-color:#EEEEEE;font-weight:bold;font-size:1.5em;text-align:right;width:100%;}
.fls_col_names{font-weight:bold;}
.fls_col_values{vertical-align:top;}
.fls_bst{width:100%;empty-cells:show}
.fls_hr{border:dotted 1px;color:#080808;}
.fls_footnote{text-align:center;}
th { text-align:left;}
</style>

<table class="fls_tab" border="0" width="100%">
  <tr class="fls_headline">
    <td class="fls_headline_col" colspan="3">Flurst&uuml;cksnachweis {{ gemashl }}-{{ flr }}-{{ flsnrk }}</td>
    <td class="fls_time" colspan="4" align="right">{{ datum }}</td>
  </tr>
  <tr><td colspan="7">&nbsp;</td></tr>
  <tr class="fls_col_names">
    <th align=left nowrap>Gemarkung</th>
    <th align=left nowrap>Flur</th>
    <th align=left nowrap>Flurst&uuml;ck</th>
    <th align=left nowrap>Flurkarte</th>
    <th align=left nowrap>Entstehung</th>
    <th align=left nowrap>Fortf&uuml;hrung</th>
    <th align=left nowrap>Fl&auml;che</th>
  </tr>
  <tr class="fls_col_values">
    <td>{{ gemashl }}<br/>{{ gemarkung }}</td>
    <td>{{ flr }}</td>
    <td>{{ flsnrk }}</td>
    <td>{{ flurknr }}</td>
    <td>{{ entst }}</td>
    <td>{{ fortf }}</td>
    <td>{{ flsfl }}&nbsp;m&sup2;</td>
  </tr>

{% if blbnr|length %}
  <tr class="fls_col_names">
    <th align=left colspan=5>&nbsp;</th>
    <th align=left colspan=2>Baulastenblattnr.</th>
  </tr>
  <tr class="fls_col_values">
    <td colspan=5>&nbsp;</td>
    <td colspan=2>{{ blbnr }}</td>
  </tr>
{% endif %}

{% if lagebez|length or anl_verm|length %}
  <tr class="fls_col_names">
    <th align=left>&nbsp;</th>
    <th align=left colspan=3>Lage</th>
    <th align=left colspan=3>Anliegervermerk</th>
  </tr>
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=3>{{ lagebez }}</td>
    <td colspan=3>{{ anl_verm }}</td>
  </tr>
{% endif %}

{% if str|length %}
  <tr class="fls_col_names">
    <th align=left>&nbsp;</th>
    <th align=left colspan=4>Strasse</th>
    <th align=left colspan=2>Hausnummer</th>
  </tr>

  {% for item in str %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=4>{{ item.strname }}</td>
    <td colspan=2>{{ item.hausnr }}</td>
  </tr>
  {% endfor %}
{% endif %}

{% if nutz is defined %}
  <tr><td colspan=7>&nbsp;</td>
  <tr class="fls_col_names">
    <th align=left>&nbsp;</th>
    <th align=left colspan=5>Nutzung</th>
    <th align=left>Fl&auml;che</th>
  </tr>
  {% for item in nutz %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=5>{{ item.nutzung }} ({{ item.nutzshl }})</td>
    <td>{{ item.fl }}&nbsp;m&sup2;</td>
  </tr>
  {% else %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=6>Keine</td>
  </tr>
  {% endfor %}
{% endif %}

{% if klas|length %}
  <tr><td colspan=7>&nbsp;</td>
  <tr class="fls_col_names">
    <td>&nbsp;</td>
    <th align=left colspan=5>Klassifizierung(en)</th>
    <th align=left>Fl&auml;che</th>
  </tr>
  {% for item in klas %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=5>{{ item.klf_text }}</td>
    <td>{{ item.fl }}&nbsp;m&sup2;</td>
  </tr>
  {% endfor %}
{% endif %}

{% if emz|length %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <th colspan=5>Gesamtertragsmesszahl</td>
    <td>{{ emz }}</td>
  </tr>
{% endif %}

{% if afst|length %}
  <tr><td colspan=7>&nbsp;</td>
  <tr class="fls_col_names">
    <th align=left>&nbsp;</th>
    <th align=left colspan=6>Ausf&uuml;hrende Stelle(n)</th>
  </tr>
  {% for item in afst %}
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td colspan=6>{{ item.afst_txt }}</td>
  </tr>
  {% endfor %}
{% endif %}

</table>

<br>

<table class="fls_bst" border="0" width="100%">

{% if best|length %}
  <tr>
    <td colspan="6">
      Best&auml;nde<hr style="width:100%"/>
    </td>
  </tr>

  {% for item in best %}
  <tr><td colspan=6>&nbsp;</td>
  <tr class="fls_col_names">
    <th align=left>Bestandsnummer</th>
    <th align=left>Grundbuchbezirk</th>
    <th align=left>Grundbuchblattnr.</th>
    <th align=left colspan=2>Amtsgericht</th>
    <th align=left>Anteil</th>
  </tr>
  <tr class="fls_col_values">
    <td>{{ item.bestdnr }}</td>
    <td>{{ item.gbbz }}</td>
    <td>{{ item.gbblnr }}</td>
    <td colspan=2>{{ item.bezeichnung }}</td>
    <td>{{ item.anteil }}</td>
  </tr>
  <tr class="fls_col_names">
    <th align=left>&nbsp;</th>
    <th align=left>Buchungskennz.</th>
    <th align=left>Lfd. Nr.</th>
    <th align=left>PZ</th>
    {% if item.hist is defined %}
    <th align=left>Hist. Bestand</th>
    <th align=left>Hist. Zuordnung</th>
    {% else %}
    <td colspan=2>&nbsp;</td>
    {% endif %}
  </tr>
  <tr class="fls_col_values">
    <td>&nbsp;</td>
    <td>{{ item.eignerart }}</td>
    <td>{{ item.auftlnr }}</td>
    <td>{{ item.pz }}</td>
    <td>{% if item.hist is defined and item.bhist is defined %}ja{% endif %}</td>
    <td>{% if item.hist is defined and item.zhist is defined %}ja{% endif %}</td>
  </tr>
  {% if item.bse is defined %}
  <tr><td colspan=6>&nbsp;</td></tr>
  <tr class="fls_col_names">
    <th align=left>Anteil</th>
    <th align=left>Namensnr</th>
    <th align=left colspan="4">Namensinformation</th>
  </tr>
  {% for bse in item.bse %}
  <tr class="fls_col_values">
    <td>{{ bse.antverh }}</td>
    <td>{{ bse.namensnr }}</td>
    <td colspan="4">{{ bse.name1 }} {{ bse.name2 }}<br>{{ bse.name3 }}<br>{{ bse.name4 }}</td>
  </tr>
  {% else %}
  <p>Kein Eigentümer gefunden.</p>
  {% endfor %}
  {% endif %}
  {% endfor %}
</table>
{% endif %}

{% if footnote is defined %}
<hr class="fls_hr">
{{ footnote }}
{% endif %}
"""

        from jinja2 import Template
        return Template(template).render(res)

    def flsnr(self, gml_id):
        if not isinstance(gml_id, str) or len(gml_id) != 16:
            qDebug("gml_id erwartet [{}:{}]".format(len(gml_id), gml_id))
            return None

        (db, conninfo) = self.plugin.opendb()
        if db is None:
            qDebug("keine Datenbankverbindung")
            return None

        res = self.fetchall(db, "SELECT alb_key FROM fs WHERE fs_obj='{}'".format(gml_id))
        if len(res) != 1:
            qDebug("Kein eindeutiges Flurstück gefunden")
            return None

        return res[0]['alb_key']


@qgsfunction(group='ALKIS')
def flsnr(value):
    return qgis.utils.plugins['alkisplugin'].queryOwnerInfoTool.flsnr(value)


@qgsfunction(group='ALKIS')
def flurstuecksnachweis(arg, template=None):
    plugin = qgis.utils.plugins['alkisplugin']
    oi = plugin.queryOwnerInfoTool

    if len(arg) == 16:
        arg = oi.flsnr(arg)

    if arg is None:
        qDebug("arg is None")
        return None

    qDebug("arg:{}".format(arg))
    return oi.getPage([{'flsnr': arg}], template=template or plugin.settings.template)
