VERSION = $(shell sed -ne "s/^version=//p" metadata.txt)

all:

%.py: %.qrc
	pyrcc4 -o $@ $^

plugin.xml: metadata.txt
	perl mkxml.pl

zip: alkisplugin-$(VERSION).zip

alkisplugin-$(VERSION).zip: plugin.xml
	git archive --format=zip --prefix=alkisplugin/ HEAD >alkisplugin-$(VERSION).zip

upload: plugin.xml alkisplugin-$(VERSION).zip
	rsync -apvP alkisplugin-$(VERSION).zip plugin.xml logo.svg jef@buten.intern.norbit.de:~jef/public_html/qgis/

release:
	@perl mkxml.pl -r
