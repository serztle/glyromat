#!/usr/bin/python3
from plyr import Query, PROVIDERS
from gi.repository import Gtk


class MetadataChooser:
    def on_search_clicked(self, button):
        self.search.set_visible(True)
        self.progress.pulse()

    def on_destroy(self, *args):
        Gtk.main_quit(*args)

    def on_type_changed(self, combobox, *args):
        self.update_provider()

    def on_toggle(self, cell, path, *args):
        print(path)
        if path is not None:
            it = self.model.get_iter(path)
            self.model[it][0] = not self.model[it][0]

    def sort_column_quality(self, model, iter1, iter2, data):
        if model[iter1][2] == model[iter2][2]:
            return 0
        elif model[iter1][2] > model[iter2][2]:
            return 1
        else:
            return -1

    def update_provider(self):
        iter = self.combobox.get_active_iter()
        if iter is not None:
            model = self.combobox.get_model()
            key = model[iter][0]
            details = PROVIDERS[key]
            self.model = Gtk.ListStore(bool, str, str, str)
            self.model.set_sort_func(0, self.sort_column_quality)
            self.model.set_sort_column_id(0, 1)

            for p in details['providers']:
                self.model.append([True, p['name'], str(p['quality']), str(p['speed'])])
            self.provider.set_model(self.model)
            self.update_entrys(details['required'])

    def update_entrys(self, required):
            artist = self.builder.get_object("e_artist")
            album = self.builder.get_object("e_album")
            title = self.builder.get_object("e_title")
            try:
                required.index('artist')
                artist.set_sensitive(True)
            except ValueError:
                artist.set_sensitive(False)
            try:
                required.index('album')
                album.set_sensitive(True)
            except ValueError:
                album.set_sensitive(False)
            try:
                required.index('title')
                title.set_sensitive(True)
            except ValueError:
                title.set_sensitive(False)

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("metadata-chooser.glade")

        self.window = self.builder.get_object("wd_metadata_chooser")
        self.window.connect("destroy", self.on_destroy)

        self.search = self.builder.get_object("b_search")

        self.search_button = self.builder.get_object("btn_search")
        self.search_button.connect("clicked", self.on_search_clicked)

        self.adjustment = self.builder.get_object("adj_max")
        self.adjustment.set_value(10)

        self.progress = self.builder.get_object("pb_search")
        self.progress.set_pulse_step(0.05)
        self.combobox = self.builder.get_object("cb_metadata_type")

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

        self.provider = self.builder.get_object("tv_provider")

        cell = Gtk.CellRendererToggle()
        cell.connect("toggled", self.on_toggle, None)
        col = Gtk.TreeViewColumn("active", cell, active=0)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("provider name", cell, text=1)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        cell.set_fixed_size(50, -1)
        cell.set_alignment(1.0, 0.5)
        col = Gtk.TreeViewColumn("quality", cell, text=2)
        self.provider.append_column(col)

        cell = Gtk.CellRendererText()
        cell.set_fixed_size(50, -1)
        cell.set_alignment(1.0, 0.5)
        col = Gtk.TreeViewColumn("speed", cell, text=3)
        self.provider.append_column(col)

        #cell = Gtk.CellRendererText()
        #col = Gtk.TreeViewColumn("", cell, text=4)
        #self.provider.append_column(col)

        self.update_provider()

        self.window = self.builder.get_object("wd_metadata_chooser")
        self.window.show()


if __name__ == "__main__":
    main = MetadataChooser()
    Gtk.main()
