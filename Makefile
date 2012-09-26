all: conf.py resources.py

resources.qrc: logo.png
	touch -r logo.png resources.qrc


%.py: %.ui
	pyuic4 -o $@ $^

%.py: %.qrc
	pyrcc4 -o $@ $^
