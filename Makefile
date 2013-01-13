all: conf.py resources.py

resources.qrc: logo.png
	touch -r logo.png resources.qrc

%.py: %.ui
	pyuic4 -o $@ $^

%.py: %.qrc
	pyrcc4 -o $@ $^

update: all
	rsync \
		--dry-run \
		-avpP \
		--exclude ".git" \
		--exclude "*.pyc" \
		-v \
		./ \
		jef@zeus.intern.norbit.de:/shares/runtime/norBIT/QGIS/alkis/
