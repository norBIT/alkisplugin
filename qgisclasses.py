# -*- coding: utf8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 foldmethod=indent autoindent :

"""
***************************************************************************
    qgisclasses.py
    ---------------------
    Date                 : May 2014
    Copyright            : (C) 2014-2020 by Jürgen Fischer
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

from qgis.PyQt.QtCore import Qt, QDate, QDir, QByteArray, QSize, QEvent, QSettings, QPoint
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
        self.teFussnote.setPlainText(self.settings.footnote)

        self.loadModels(False)

        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        self.bb.addButton("Modelle laden", QDialogButtonBox.ActionRole).clicked.connect(self.loadModels)
        self.bb.addButton("Layer einbinden", QDialogButtonBox.ActionRole).clicked.connect(self.loadLayers)

        self.restoreGeometry(QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("confgeom", QByteArray(), type=QByteArray))

    def done(self, r):
        QSettings("norBIT", "norGIS-ALKIS-Erweiterung").setValue("confgeom", self.saveGeometry())
        return QDialog.done(self, r)

    def loadModels(self, error=True):
        self.settings.servicE = self.leSERVICE.text()
        self.settings.host = self.leHOST.text()
        self.settings.port = self.lePORT.text()
        self.settings.dbname = self.leDBNAME.text()
        self.settings.schema = self.leSCHEMA.text()
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
        if qry.exec_("SELECT 1 FROM information_schema.tables WHERE table_schema={} AND table_name='po_modelle'".format(quote(self.plugin.settings.schema))) and qry.next():
            sql = "SELECT modell,n FROM po_modelle WHERE modell IS NOT NULL ORDER BY n DESC"
        else:
            sql = """
SELECT modell,count(*)
FROM (
SELECT unnest(modell) AS modell FROM po_points   UNION ALL
SELECT unnest(modell) AS modell FROM po_lines    UNION ALL
SELECT unnest(modell) AS modell FROM po_polygons UNION ALL
SELECT unnest(modell) AS modell from po_labels
) AS foo
WHERE modell IS NOT NULL
GROUP BY modell
ORDER BY count(*) DESC
"""

        if qry.exec_(sql):
            res = {}
            while qry.next():
                res[qry.value(0)] = qry.value(1)

            self.twModellarten.setRowCount(len(res))
            i = 0
            for k, n in sorted(iter(list(res.items())), key=operator.itemgetter(1), reverse=True):
                item = QTableWidgetItem(k)
                item.setCheckState(Qt.Checked if (item.text() in modelle) else Qt.Unchecked)
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

        if qry.exec_("SELECT id,name FROM alkis_signaturkataloge"):
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
        self.settings.schema = self.leSCHEMA.text()
        self.settings.uid = self.leUID.text()
        self.settings.pwd = self.lePWD.text()
        if hasattr(qgis.gui, 'QgsAuthConfigSelect'):
            self.settings.authcfg = self.authCfgSelect.configId()

        self.settings.umnpath = self.leUMNPath.text()
        self.settings.umntemplate = self.leUMNTemplate.text()
        self.settings.footnote = self.teFussnote.toPlainText()

        modelle = []
        if self.twModellarten.isEnabled():
            for i in range(self.twModellarten.rowCount()):
                item = self.twModellarten.item(i, 0)
                if item.checkState() == Qt.Checked:
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


class Info(QDialog):
    info = []

    @classmethod
    def showInfo(cls, plugin, html, gmlid, parent):
        info = Info(plugin, html, gmlid, parent)
        info.setAttribute(Qt.WA_DeleteOnClose)
        info.setModal(False)

        cls.info.append(info)

        info.show()

    def __init__(self, plugin, html, gmlid, parent):
        QDialog.__init__(self, parent)
        self.resize(QSize(740, 580))
        self.setWindowTitle(u"Flurstücksnachweis")

        self.plugin = plugin
        self.gmlid = gmlid

        self.tbEigentuemer = QTextBrowser(self)
        self.tbEigentuemer.setHtml(html)
        self.tbEigentuemer.setContextMenuPolicy(Qt.NoContextMenu)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tbEigentuemer)
        self.setLayout(layout)

        self.restoreGeometry(QSettings("norBIT", "norGIS-ALKIS-Erweiterung").value("infogeom", QByteArray(), type=QByteArray))
        self.move(self.pos() + QPoint(16, 16) * len(self.info))

    def print_(self):
        printer = QPrinter()
        dlg = QPrintDialog(printer)
        if dlg.exec_() == QDialog.Accepted:
            self.tbEigentuemer.print_(printer)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        action = QAction("Drucken", self)
        action.triggered.connect(self.print_)
        menu.addAction(action)
        menu.exec_(e.globalPos())

    def closeEvent(self, e):
        QSettings("norBIT", "norGIS-ALKIS-Erweiterung").setValue("infogeom", self.saveGeometry())
        self.info.remove(self)
        self.plugin.clearHighlight()
        QDialog.closeEvent(self, e)

    def event(self, e):
        if e.type() == QEvent.WindowActivate:
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
        point = self.plugin.transform(
            self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())
        )

        QApplication.setOverrideCursor(Qt.WaitCursor)

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
            QMessageBox.information(None, u"Fehler", u"Verbindung zu norGIS schlug fehl.")

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
            point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())
            self.rubberBand.movePoint(point)

    def canvasReleaseEvent(self, e):
        point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())
        if e.button() == Qt.LeftButton:
            self.rubberBand.addPoint(point)
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        if self.rubberBand.numberOfVertices() >= 3:
            g = self.plugin.transform(
                self.rubberBand.asGeometry()
            )

            self.rubberBand.reset(self.plugin.PolygonGeometry)

            fs = self.plugin.highlight(
                where=u"st_intersects(wkb_geometry,st_geomfromtext('POLYGON((%s))'::text,%d))" % (
                    ",".join(["%.3lf %.3lf" % (p[0], p[1]) for p in g.asPolygon()[0]]),
                    self.plugin.getepsg()
                )
            )

            if len(fs) == 0:
                QApplication.restoreOverrideCursor()
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
                QMessageBox.information(None, u"Fehler", u"Verbindung zu norGIS schlug fehl.")
        else:
            self.rubberBand.reset(self.plugin.PolygonGeometry)

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
        if not qry.exec_("SELECT has_table_privilege('eigner', 'SELECT')") or not qry.next() or not qry.value(0):
            self.tabWidget.removeTab(self.tabWidget.indexOf(self.tabEigentuemer))

        self.replaceButton = self.buttonBox.addButton(u"Ersetzen", QDialogButtonBox.ActionRole)
        self.addButton = self.buttonBox.addButton(u"Hinzufügen", QDialogButtonBox.ActionRole)
        self.removeButton = self.buttonBox.addButton(u"Entfernen", QDialogButtonBox.ActionRole)
        self.clearButton = self.buttonBox.addButton(u"Leeren", QDialogButtonBox.ActionRole)

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
                    u" JOIN flurst c USING (gemashl){0}".format(where) if where != "" else ""
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

            # qDebug(u"SQL:{} [{}]".format(sql, val))

            if qry.exec_(sql):
                d = 0 if qry.record().count() == 1 else 1

                while qry.next():
                    cbx.addItem(qry.value(d), qry.value(0))

            cbx.setCurrentIndex(cbx.findData(val))
            cbx.blockSignals(False)

        if where == "":
            return

        hits = 0
        if qry.exec_(u"SELECT count(*) FROM flurst{}".format(where)) and qry.next():
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

        self.cbxStrassen.blockSignals(True)
        self.cbxStrassen.clear()
        if qry.exec_(u"SELECT schluesselgesamt, bezeichnung FROM (SELECT DISTINCT k.schluesselgesamt, k.bezeichnung || coalesce(', ' || g.bezeichnung,'') AS bezeichnung FROM ax_lagebezeichnungkatalogeintrag k LEFT OUTER JOIN ax_gemeinde g ON k.land=g.land AND k.regierungsbezirk=g.regierungsbezirk AND k.kreis=g.kreis AND k.gemeinde::int=g.gemeinde::int AND g.endet IS NULL WHERE lower(k.bezeichnung) LIKE {0} AND k.endet IS NULL UNION SELECT DISTINCT '' AS schluesselgesamt,unverschluesselt FROM ax_lagebezeichnungmithausnummer WHERE lower(unverschluesselt) LIKE {0} AND endet IS NULL) AS foo ORDER BY bezeichnung".format(quote(self.leStr.text().lower() + '%'))):
            while qry.next():
                self.cbxStrassen.addItem(qry.value(1), qry.value(0))
        self.cbxStrassen.blockSignals(False)

        self.lblResult.setText(u"Keine Straßen gefunden" if self.cbxStrassen.count() == 0 else u"{} Straßen gefunden".format(self.cbxStrassen.count()))

        self.cbxStrassen.setEnabled(self.cbxStrassen.count() > 0)
        self.cbxStrassen.setCurrentIndex(0 if self.cbxStrassen.count() == 1 else -1)
        self.on_cbxStrassen_currentIndexChanged(self.cbxStrassen.currentIndex())

    def on_cbxStrassen_currentIndexChanged(self, index):
        # qDebug(u"on_cbxStrassen_currentIndexChanged: index={} text={}".format(self.cbxStrassen.currentIndex(), self.cbxStrassen.currentText()))
        qry = QSqlQuery(self.db)

        schluesselgesamt = self.cbxStrassen.itemData(self.cbxStrassen.currentIndex())
        if schluesselgesamt == '':
            schluesselgesamt = None

        self.cbxHNR.blockSignals(True)
        self.cbxHNR.clear()
        if (schluesselgesamt is None and qry.exec_(u"SELECT h.hausnummer FROM ax_lagebezeichnungmithausnummer h WHERE unverschluesselt={0} ORDER BY NULLIF(regexp_replace(h.hausnummer, E'\\\\D', '', 'g'), '')::int".format(quote(self.cbxStrassen.currentText())))) or \
           (schluesselgesamt is not None and qry.exec_(u"SELECT h.hausnummer FROM ax_lagebezeichnungmithausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE k.schluesselgesamt={0} ORDER BY NULLIF(regexp_replace(h.hausnummer, E'\\\\D', '', 'g'), '')::int".format(quote(schluesselgesamt)))):
            while qry.next():
                self.cbxHNR.addItem(qry.value(0))
        else:
            qDebug(qry.lastError().text())

        if (schluesselgesamt is None and qry.exec_(u"SELECT 1 FROM ax_lagebezeichnungohnehausnummer h WHERE unverschluesselt={0}".format(quote(self.cbxStrassen.currentText())))) or \
           (schluesselgesamt is not None and qry.exec_(u"SELECT 1 FROM ax_lagebezeichnungohnehausnummer h JOIN ax_lagebezeichnungkatalogeintrag k USING (land,regierungsbezirk,kreis,gemeinde,lage) WHERE k.schluesselgesamt={0}".format(quote(schluesselgesamt)))):
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
                if qry.exec_(sql) and qry.next() and qry.value(0) > 0:
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
            hits = 0

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

        if qry.exec_(sql):
            rec = qry.record()

            while qry.next():
                row = {}

                for i in range(0, rec.count()):
                    v = "%s" % qry.value(i)
                    if v == "NULL":
                        v = ''
                    row[rec.fieldName(i)] = v.strip()

                rows.append(row)
        else:
            qDebug("Exec failed: " + qry.lastError().text())

        return rows

    def canvasReleaseEvent(self, e):
        point = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(e.x(), e.y())
        point = self.plugin.transform(point)

        p = "POINT(%.3lf %.3lf)" % (point.x(), point.y())

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

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
            Info.showInfo(self.plugin, page, fs[0]['gmlid'], self.iface.mainWindow())

    def showPage(self, fs):
        html = self.getPage(fs)
        if html is None:
            QMessageBox.information(None, "Fehler", u"Flurstück %s nicht gefunden.\n[%s]" % (flsnr, repr(fs)))
            return None

        return """\
<HTML xmlns="http://www.w3.org/1999/xhtml">
  <HEAD>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  </HEAD>
  <BODY>
<style>
.fls_tab{width:100%%;empty-cells:show}
.fls_headline{font-weight:bold;font-size:4em;}
.fls_headline_col{background-color:#EEEEEE;width:100%%;height:30px;text-align:left;}
.fls_time        {background-color:#EEEEEE;font-weight:bold;font-size:4em;text-align:right;width:100%%}
.fls_col_names{font-weight:bold;}
.fls_col_values{vertical-align:top;}
.fls_bst{width:100%%;empty-cells:show}
.fls_hr{border:dotted 1px;color:#080808;}
.fls_footnote{text-align:center;}
</style>""" + html + """\
</BODY>
</HTML>
"""

    def getPage(self, fs):
        (db, conninfo) = self.plugin.opendb()
        if db is None:
            qDebug("No database")
            return None

        qry = QSqlQuery(db)
        if qry.exec_("SELECT 1 FROM information_schema.columns WHERE table_schema={} AND table_name='eignerart' AND column_name='anteil'".format(quote(self.plugin.settings.schema))) and qry.next():
            exists_ea_anteil = qry.value(0) == 1
        else:
            exists_ea_anteil = False

        html = ""
        for i in range(0, len(fs)):
            flsnr = fs[i]['flsnr']

            best = self.fetchall(db, (
                "SELECT " +
                "ea.bvnr" +
                ",'' as pz" +
                ",(SELECT eignerart FROM eign_shl WHERE ea.b=b) as eignerart" +
                ",%s as anteil" +
                ",ea.ff_stand AS zhist" +
                ",b.bestdnr" +
                ",b.gbbz" +
                ",b.gbblnr" +
                ",b.bestfl" +
                ",b.ff_stand AS bhist" +
                " FROM eignerart ea" +
                " JOIN bestand b ON ea.bestdnr = b.bestdnr" +
                " WHERE ea.flsnr = '%s'" +
                " ORDER BY zhist,bhist,b") % ("ea.anteil" if exists_ea_anteil else "''", flsnr)
            )

            res = self.fetchall(db, "SELECT f.*,g.gemarkung FROM flurst f LEFT OUTER JOIN gema_shl g ON (f.gemashl=g.gemashl) WHERE f.flsnr='%s' AND f.ff_stand=0" % flsnr)
            if len(res) == 1:
                res = res[0]
            else:
                qDebug("Flurstück {} nicht gefunden.".format(flsnr))
                return None

            res['datum'] = QDate.currentDate().toString("d. MMMM yyyy")
            res['hist'] = 0

            if qry.exec_(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['strassen', 'str_shl']])) and qry.next() and qry.value(0):
                res['str'] = self.fetchall(db, "SELECT sstr.strname,str.hausnr FROM str_shl sstr JOIN strassen str ON str.strshl=sstr.strshl WHERE str.flsnr='%s' AND str.ff_stand=0" % flsnr)

            if qry.exec_(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['nutz_21', 'nutz_shl']])) and qry.next() and qry.value(0):
                res['nutz'] = self.fetchall(db, "SELECT n21.*, nu.nutzshl, nu.nutzung FROM nutz_21 n21, nutz_shl nu WHERE n21.flsnr='%s' AND n21.nutzsl=nu.nutzshl AND n21.ff_stand=0" % flsnr)

            if qry.exec_(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['klas_3x', 'kls_shl']])) and qry.next() and qry.value(0):
                res['klas'] = self.fetchall(db, "SELECT sum(fl::int) AS fl, min(kls.klf_text) AS klf_text FROM klas_3x kl, kls_shl kls WHERE kl.flsnr='%s' AND kl.klf=kls.klf AND kl.ff_stand=0 GROUP BY kls.klf" % flsnr)

            if qry.exec_(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['ausfst', 'afst_shl']])) and qry.next() and qry.value(0):
                res['afst'] = self.fetchall(db, "SELECT au.*, af.afst_txt FROM ausfst au,afst_shl af WHERE au.flsnr='%s' AND au.ausf_st=af.ausf_st AND au.ff_stand=0" % flsnr)

            if qry.exec_(u"SELECT " + u" AND ".join(["has_table_privilege('{}', 'SELECT')".format(x) for x in ['bestand', 'eignerart', 'eign_shl']])) and qry.next() and qry.value(0):
                res['best'] = self.fetchall(db, "SELECT ea.bvnr,'' as pz,(SELECT eignerart FROM eign_shl WHERE ea.b = b) as eignerart,%s as anteil,ea.ff_stand AS zhist,b.bestdnr,b.gbbz,b.gbblnr,b.bestfl,b.ff_stand AS bhist FROM eignerart ea JOIN bestand b ON ea.bestdnr = b.bestdnr WHERE ea.flsnr='%s' ORDER BY zhist,bhist,b" % (
                    "ea.anteil" if exists_ea_anteil else "''",
                    flsnr
                ))

                if qry.exec_("SELECT has_table_privilege('eigner', 'SELECT')") and qry.next() and qry.value(0):
                    for b in res['best']:
                        b['bse'] = self.fetchall(db, "SELECT * FROM eigner WHERE bestdnr='%s' AND ff_stand=0 ORDER BY coalesce(namensnr,'0')" % b['bestdnr'])

#                        for k,v in res.iteritems():
#                                qDebug( u"%s:%s\n" % ( k, unicode(v) ) )

            html = u"""\
<TABLE class="fls_tab" border="0" width="100%%" cellspacing="0">
    <TR class="fls_headline">
        <TD colspan="3" class="fls_headline_col">Flurst&uuml;cksnachweis</TD><TD class="fls_time" colspan="4" align="right">%(datum)s</TD></TR>
    </TR>
    <TR><TD colspan="7">&nbsp;</TD></TR>
    <TR>
        <TD colspan="7"><h3>Flurst&uuml;ck %(gemashl)s-%(flr)s-%(flsnrk)s<hr style="width:100%%"></h3></TD>
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
        <TD>%(flsfl)s&nbsp;m&sup2;</TD>
    </TR>
</TABLE>
""" % res

            if res['blbnr']:
                html += u"""
<TABLE class="fls_tab" border="0" width="100%%">
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
                html += u"""
<TABLE class="fls_tab" border="0" width="100%%">
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

            if 'str' in res:
                if res['str']:
                    html += u"""
<TABLE border="0" class="fls_tab" width="100%">
    <TR class="fls_col_names">
        <TD width="21%"></TD>
        <TD width="52%">Strasse</TD>
        <TD width="27%">Hausnummer</TD>
    </TR>
"""

                    for strres in res['str']:
                        html += u"""
    <TR class="fls_col_values">
        <TD></TD><TD>%(strname)s</TD><TD>%(hausnr)s</TD></TR>
    </TR>
""" % strres

                    html += u"""
</TABLE>
"""

            if 'nutz' in res:
                html += u"""
<TABLE border="0" class="fls_tab" width="100%">
        <TR class="fls_col_names"><TD width="21%"></TD><TD width="69%">Nutzung</TD><TD width="10%">Fl&auml;che</TD></TR>
"""
                if res['nutz']:
                    for nutz in res['nutz']:
                        html += u"""
        <TR class="fls_col_values"><TD></TD><TD>21%(nutzshl)s - %(nutzung)s</TD><TD>%(fl)s&nbsp;m&sup2;</TD></TR>
""" % nutz
                else:
                    html += u"""
        <TR class="fls_col_values"><TD></TD><TD colspan=2>Keine</TD></TR>
"""

            html += u"""
</TABLE>
"""

            if 'klas' in res:
                html += u"""
<TABLE border="0" class="fls_tab" width="100%">
        <TR class="fls_col_names"><TD width="21%"></TD><TD width="69%">Klassifizierung(en)</TD><TD width="10%">Fl&auml;che</TD></TR>
"""

                if res['klas']:
                    for klas in res['klas']:
                        html += u"""
        <TR class="fls_col_values"><TD></TD><TD>%(klf_text)s</TD><TD>%(fl)s&nbsp;m&sup2;</TD></TR>
""" % klas
                else:
                    html += u"""
        <TR class="fls_col_values"><TD></TD><TD colspan=2>Keine</TD></TR>
"""

            html += u"""
</TABLE>
"""

            if 'afst' in res:
                html += u"""
<TABLE border="0" class="fls_tab" width="100%">
        <TR class="fls_col_names"><TD width="21%"></TD><TD width="79%">Ausf&uuml;hrende Stelle(n)</TD></TR>
"""

                if res['afst']:
                    for afst in res['afst']:
                        html += u"""
        <TR class="fls_col_values"><TD></TD><TD>%(afst_txt)s</TD></TR>
""" % afst

                else:
                    html += u"""
        <TR class="fls_col_values"><TD></TD><TD colspan=2>Keine</TD></TR>
"""

                html += u"""
</TABLE>
"""

            if 'best' in res:
                if res['best']:
                    html += u"""
<br>
<TABLE border="0" class="fls_bst" width="100%">
        <TR><TD colspan="6"><h3>Best&auml;nde<hr style="width:100%"></h3></TD></TR>
"""

                    for best in res['best']:
                        html += u"""
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
                            html += u"""
                <TD>Hist. Bestand</TD><TD>Hist. Zuordnung</TD>
"""
                        else:
                            html += u"""
                <TD></TD><TD></TD>
"""

                        html += u"""
        </TR>
        <TR class="fls_col_values">
                <TD></TD>
                <TD>%(eignerart)s</TD>
                <TD>%(bvnr)s</TD>
                <TD>%(pz)s</TD>
""" % best

                        html += "<TD>%s</TD>" % ("ja" if res['hist'] and best['bhist'] else "")
                        html += "<TD>%s</TD>" % ("ja" if res['hist'] and best['zhist'] else "")

                        html += u"""
        </TR>
"""

                        if 'bse' in best:
                            if best['bse']:
                                html += u"""
        <TR class="fls_col_names"><TD>Anteil</TD><TD>Namensnr</TD><TD colspan="5">Namensinformation</TD></TR>
"""

                                for bse in best['bse']:
                                    html += u"""
        <TR class="fls_col_values">
                <TD>%(antverh)s</TD>
                <TD>%(namensnr)s</TD>
                <TD colspan="4">%(name1)s %(name2)s<br>%(name3)s<br>%(name4)s</TD>
        </TR>
""" % bse
                            else:
                                html += u"""
        <p>Kein Eigentümer gefunden.</p>
"""

                            html += u"""
        <TR><TD colspan="6"><hr class="fls_hr"></TD></TR>
"""

        html += u"""
"""

        footnote = self.plugin.settings.footnote
        if footnote:
            html += u"""
        <TR><TD colspan="7" class="fls_footnote">%s</TD></TR>
""" % footnote

        html += u"""
        </TABLE>
"""

        return html

    def flsnr(self, gml_id):
        if not isinstance(gml_id, str) or len(gml_id)!=16:
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


@qgsfunction(args=1, group='ALKIS')
def flsnr(values, feature, parent):
    return qgis.utils.plugins['alkisplugin'].queryOwnerInfoTool.flsnr(values[0])

@qgsfunction(args=1, group='ALKIS')
def flurstuecksnachweis(values, feature, parent):
    oi = qgis.utils.plugins['alkisplugin'].queryOwnerInfoTool

    arg = values[0]
    if len(arg)==16:
        arg = oi.flsnr(arg)

    if arg is None:
        qDebug("arg is None")
        return None

    qDebug("arg:{}".format(arg))
    return """\
<style>
.fls_tab{width:100%%;empty-cells:show;}
.fls_headline{font-weight:bold;font-size:1.5em;}
.fls_headline_col{background-color:#EEEEEE;width:100%%;height:2em;text-align:left;}
.fls_time{background-color:#EEEEEE;font-weight:bold;font-size:1.5em;text-align:right;width:100%%}
.fls_col_names{font-weight:bold;}
.fls_col_values{vertical-align:top;}
.fls_bst{width:100%%;empty-cells:show}
.fls_hr{border:dotted 1px;color:#080808;}
.fls_footnote{text-align:center;}
</style>
""" + oi.getPage([{'flsnr': arg}])
