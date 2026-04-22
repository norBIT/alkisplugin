VERSION = $(shell sed -ne "s/^version=//p" metadata.txt)

all:

plugin.xml: metadata.txt
	perl mkxml.pl

zip: alkisplugin-$(VERSION).zip

alkisplugin-$(VERSION).zip: plugin.xml
	git archive --format=zip --prefix=alkisplugin/ HEAD >alkisplugin-$(VERSION).zip

upload: plugin.xml alkisplugin-$(VERSION).zip
	python3 plugin_upload.py alkisplugin-$(VERSION).zip

check:
	flake8 $(wildcard *.py)
	bandit -q -r .

release: check
	@perl mkxml.pl -r
	vim +/changelog= -c "set list" metadata.txt

.PHONY: check upload release
