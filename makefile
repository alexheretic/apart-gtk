
PREFIX = /usr

all:
	./build-dist

install: target
	mkdir -p $(DESTDIR)$(PREFIX)
	cp -R ./target/* $(DESTDIR)$(PREFIX)/
	$(info consider running: sudo gtk-update-icon-cache $(DESTDIR)$(PREFIX)/share/icons/hicolor)

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/apart-gtk
	rm -rf $(DESTDIR)$(PREFIX)/lib/apart-gtk
	rm -f $(DESTDIR)$(PREFIX)/share/applications/apart-gtk.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/apart.svg
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/apart.png
	rm -f $(DESTDIR)$(PREFIX)/share/polkit-1/actions/com.github.alexheretic.pkexec.apart-gtk.policy
