import resources

def name():
  return "ALKIS-Einbindung"

def description():
  return "Dies Plugin dient zur Einbindung von ALKIS-Layern."

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.8"

def authorName():
  return "Juergen E. Fischer <jef@norbit.de>"

def icon():
    return ":/plugins/alkis/logo.png"

def classFactory(iface):
  from alkisplugin import alkisplugin
  return alkisplugin(iface)
