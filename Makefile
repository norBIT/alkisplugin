all: conf.py info.py resources.py plugin.xml

resources.qrc: logo.png
	touch -r logo.png resources.qrc

%.py: %.ui
	pyuic4 -o $@ $^

%.py: %.qrc
	pyrcc4 -o $@ $^

update: all
	rsync \
		-avpP \
		--exclude ".git" \
		--exclude "*.pyc" \
		--exclude ".gitignore" \
		--exclude "mkxml.pl" \
		--exclude "plugin.xml" \
		--exclude "alkisplugin.zip" \
		-v \
		./ \
		jef@zeus.intern.norbit.de:/shares/runtime/norBIT/QGIS/alkis/unstable

plugin.xml: metadata.txt
	perl mkxml.pl

alkisplugin.zip: plugin.xml
	cd ..; zip -pr alkisplugin/alkisplugin.zip alkisplugin \
			-x "alkisplugin/.git/*" \
			-x "alkisplugin/*.pyc" \
			-x "alkisplugin/.gitignore" \
			-x "alkisplugin/Makefile" \
			-x "alkisplugin/mkxml.pl" \
			-x "alkisplugin/plugin.xml"

upload: plugin.xml alkisplugin.zip
	rsync -apvP alkisplugin.zip plugin.xml logo.png jef@buten.intern.norbit.de:~jef/public_html/qgis/
