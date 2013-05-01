#!/usr/bin/python3
import sys
from time import sleep
from threading import Thread
from plyr import Query, PROVIDERS
from gi.repository import Gtk, Gdk, GLib, GObject

GObject.threads_init()
Gdk.threads_init()


class MetadataChooser:
    def query_data(self, *args):
        self.data = self.query.commit()
        print(self.query.error)
        self.query_done = True

        Gdk.threads_enter()
        self.toggle_search()
        Gdk.threads_leave()
        sys.stdout.flush()

    def progress_pulse(self, *args):
        while not self.query_done:
            Gdk.threads_enter()
            self.progress.pulse()
            Gdk.threads_leave()
            sleep(0.1)

    def on_cancel_clicked(self, button):
        self.query.cancel()

    def __call__(self, cache, query):
        print(str(cache.data, 'utf8'))
        sys.stdout.flush()

    def on_search_clicked(self, button):
        self.toggle_search()
        providers = []
        for row in self.model:
            if row[0]:
                providers.append(row[1])

        query = Query()
        query.providers = providers
        query.get_type = self.get_chosen_provider()
        query.artist = self.builder.get_object("e_artist").get_text()
        query.album = self.builder.get_object("e_album").get_text()
        query.title = self.builder.get_object("e_title").get_text()
        query.number = self.builder.get_object("adj_max").get_value()
        query.callback = self
        query.verbosity = 2
        self.query = query
        self.query_done = False
        self.progress.set_fraction(0.0)

        Thread(target=self.query_data).start()
        Thread(target=self.progress_pulse).start()

    def on_destroy(self, *args):
        Gtk.main_quit(*args)

    def on_type_changed(self, combobox, *args):
        self.update_provider()

    def on_toggle(self, cell, path, *args):
        if path is not None:
            it = self.model.get_iter(path)
            self.model[it][0] = not self.model[it][0]

    def toggle_search(self, *args):
        self.search_panel.set_sensitive(not self.search_panel.get_sensitive())
        self.combobox.set_sensitive(not self.combobox.get_sensitive())
        self.provider.set_sensitive(not self.provider.get_sensitive())
        self.search_progress.set_visible(not self.search_progress.get_visible())
        return False

    def get_chosen_provider(self):
        iter = self.combobox.get_active_iter()
        if iter is not None:
            model = self.combobox.get_model()
            key = model[iter][0]
            return key
        return None

    def update_provider(self):
        key = self.get_chosen_provider()
        if key is not None:
            providers = PROVIDERS[key]['providers']
            required = PROVIDERS[key]['required']

            model = Gtk.ListStore(bool, str, str, str, str)
            for p in providers:
                model.append([True, p['name'], str(p['quality']), str(p['speed']), ""])

            self.model = model
            self.provider.set_model(model)
            self.update_entrys(required)

    def update_entry(self, required, key):
        obj = getattr(self, key)
        try:
            required.index(key)
            obj.set_sensitive(True)
        except ValueError:
            obj.set_sensitive(False)

    def update_entrys(self, required):
        self.update_entry(required, "artist")
        self.update_entry(required, "album")
        self.update_entry(required, "title")

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("metadata-chooser.glade")
        self.go = self.builder.get_object

        self.window = self.go("wd_metadata_chooser")
        self.window.connect("destroy", self.on_destroy)

        self.view_results = self.go("tv_data")
        self.artist = self.go("e_artist")
        self.artist.set_text("DevilDriver")

        self.album = self.go("e_album")
        self.album.set_text("Beast")

        self.title = self.go("e_title")
        self.title.set_text("Beast")

        self.search_panel = self.go("g_search_data")
        self.search_progress = self.go("b_search")

        self.search_button = self.go("btn_search")
        self.search_button.connect("clicked", self.on_search_clicked)

        self.cancel = self.go("btn_search_cancel")
        self.cancel.connect("clicked", self.on_cancel_clicked)

        self.adjustment = self.go("adj_max")
        self.adjustment.set_value(1)

        self.progress = self.go("pb_search")
        self.progress.set_pulse_step(0.05)

        self.combobox = self.go("cb_metadata_type")
        metadata_types = Gtk.ListStore(str)
        for p in sorted(PROVIDERS):
            metadata_types.append([p])
        cell = Gtk.CellRendererText()
        self.combobox.pack_start(cell, True)
        self.combobox.add_attribute(cell, 'text', 0)
        self.combobox.set_model(metadata_types)
        self.combobox.set_entry_text_column(1)
        self.combobox.set_active(0)
        self.combobox.connect("changed", self.on_type_changed)

        self.provider = self.go("tv_provider")
        cell = Gtk.CellRendererToggle()
        cell.connect("toggled", self.on_toggle, None)
        col = Gtk.TreeViewColumn("active", cell, active=0)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("provider name", cell, text=1)
        col.set_sort_column_id(1)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        cell.set_fixed_size(50, -1)
        cell.set_alignment(1.0, 0.5)
        col = Gtk.TreeViewColumn("quality", cell, text=2)
        col.set_sort_column_id(2)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        cell.set_fixed_size(50, -1)
        cell.set_alignment(1.0, 0.5)
        col = Gtk.TreeViewColumn("speed", cell, text=3)
        col.set_sort_column_id(3)
        self.provider.append_column(col)

        col = Gtk.TreeViewColumn("", cell, text=4)
        self.provider.append_column(col)

        self.update_provider()
        self.window.show()


if __name__ == "__main__":
    main = MetadataChooser()
    Gtk.main()
