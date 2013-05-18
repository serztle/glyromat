#!/usr/bin/python3
from time import sleep
from threading import Thread
from plyr import Cache, Query, Database, PROVIDERS
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject

GObject.threads_init()
Gdk.threads_init()


db = Database('/tmp')

IMG_INFO_TEMPLATE = '''{w}x{h}
{img_format}
{source_url}
'''

TEXT_TEMPLATE = '''{text}

<b>Source:</b> {source_url}
'''


class MetadataChooser:
    def query_data(self, *args):
        self.query.commit()
        self.query_done = True

        Gdk.threads_enter()
        self.toggle_search_sensivity()
        Gdk.threads_leave()

    def query_callback(self, cache, query):
        if cache.is_image:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(cache.data)
            loader.close()
            pixbuf = loader.get_pixbuf()

            info = IMG_INFO_TEMPLATE.format(
                    w=pixbuf.get_width(),
                    h=pixbuf.get_height(),
                    img_format=cache.image_format,
                    source_url=cache.source_url
            )

            self.model_result.append([pixbuf, info])
        elif query.get_type in ['tracklist']:
            duration = '%02d:%02d' % (cache.duration / 60, cache.duration % 60)
            self.model_result.append([str(cache.data, 'utf8'), duration])
        else:
            text = TEXT_TEMPLATE.format(
                    text=str(cache.data, 'utf8'),
                    source_url=cache.source_url
            )
            self.model_result.append([text])

    def query_pulse(self, *args):
        while not self.query_done:
            Gdk.threads_enter()
            self.progress.pulse()
            Gdk.threads_leave()
            sleep(0.1)

    def on_cancel_clicked(self, button):
        self.query.cancel()

    def on_search_clicked(self, button):
        self.toggle_search_sensivity()

        query = Query()
        query.providers = [row[1] for row in self.model if row[0]]
        query.get_type = self.get_chosen_provider()
        query.artist = self.entry_artist.get_text()
        query.album = self.entry_album.get_text()
        query.title = self.entry_title.get_text()
        query.number = self.adj_max.get_value()
        query.callback = self.query_callback
        query.database = db
        query.verbosity = 0

        self.query = query
        self.query_done = False
        self.progress.set_fraction(0.0)

        for col in self.view_results.get_columns():
            self.view_results.remove_column(col)

        def _create_model(data, cells):
            self.model_result = Gtk.ListStore(*data)
            self.view_results.set_model(self.model_result)

            for idx, cell in enumerate(cells):
                cell.set_alignment(idx / 2.0, idx / 2.0)
                if isinstance(cell, Gtk.CellRendererPixbuf):
                    col = Gtk.TreeViewColumn(' ', cell, pixbuf=idx)
                else:
                    col = Gtk.TreeViewColumn(' ', cell, markup=idx)
                self.view_results.append_column(col)

        if query.get_type in ['artistphoto', 'backdrops', 'cover']:
            _create_model(
                    (GdkPixbuf.Pixbuf, str),
                    [Gtk.CellRendererPixbuf(), Gtk.CellRendererText()]
            )
        elif query.get_type in ['tracklist']:
            cell = Gtk.CellRendererText()
            cell.set_property('editable', True)
            _create_model(
                    (str, str),
                    [cell, Gtk.CellRendererText()]
            )
        else:
            cell = Gtk.CellRendererText()
            cell.set_property('wrap_width', 500)
            cell.set_property('wrap_mode', Gtk.WrapMode.WORD)
            _create_model([str], [cell])

        Thread(target=self.query_data).start()
        Thread(target=self.query_pulse).start()

    def on_destroy(self, *args):
        Gtk.main_quit(*args)

    def on_type_changed(self, combobox, *args):
        self.update_provider()

    def on_toggle(self, cell, path, *args):
        if path is not None:
            it = self.model.get_iter(path)
            self.model[it][0] = not self.model[it][0]

    def toggle_search_sensivity(self, *args):
        self.search_panel.set_sensitive(not self.search_panel.get_sensitive())
        self.combobox.set_sensitive(not self.combobox.get_sensitive())
        self.provider.set_sensitive(not self.provider.get_sensitive())
        self.search_progress.set_visible(not self.search_progress.get_visible())
        return False

    def get_chosen_provider(self):
        iterator = self.combobox.get_active_iter()
        if iterator is not None:
            model = self.combobox.get_model()
            key = model[iterator][1]
            return key.lower()
        return None

    def update_provider(self):
        key = self.get_chosen_provider()
        if key is not None:
            providers = PROVIDERS[key]['providers'] + [{
                    'name': 'local',
                    'speed': 100,
                    'quality': 100
                }, {
                    'name': 'musictree',
                    'speed': 99,
                    'quality': 99
                }]
            required = PROVIDERS[key]['required']

            model = Gtk.ListStore(bool, str, str, str, str)
            for p in providers:
                model.append([True, p['name'], str(p['quality']), str(p['speed']), ''])

            self.model = model
            self.provider.set_model(model)
            self.update_entries(required)

    def update_entry(self, required, key):
        obj = getattr(self, key)
        try:
            required.index(key)
            obj.set_sensitive(True)
        except ValueError:
            obj.set_sensitive(False)

    def update_entries(self, required):
        self.update_entry(required, 'artist')
        self.update_entry(required, 'album')
        self.update_entry(required, 'title')

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('metadata-chooser.glade')
        go = self.builder.get_object

        self.window = go('wd_metadata_chooser')
        self.window.connect('destroy', self.on_destroy)

        self.view_results = go('tv_data')

        self.artist = go('e_artist')
        self.artist.set_text('DevilDriver')

        self.album = go('e_album')
        self.album.set_text('Beast')

        self.title = go('e_title')
        self.title.set_text('Dead to Rights')

        self.search_panel = go('g_search_data')
        self.search_progress = go('b_search')

        self.search_button = go('btn_search')
        self.search_button.connect('clicked', self.on_search_clicked)

        self.cancel = go('btn_search_cancel')
        self.cancel.connect('clicked', self.on_cancel_clicked)

        self.adjustment = go('adj_max')

        self.progress = go('pb_search')

        self.entry_artist = go('e_artist')
        self.entry_album = go('e_album')
        self.entry_title = go('e_title')
        self.adj_max = go('adj_max')

        self.combobox = go('cb_metadata_type')
        metadata_types = Gtk.ListStore(str, str)
        for p in sorted(PROVIDERS.keys()):
            required = PROVIDERS[p]['required']

            if 'title' in required:
                icon_name = 'audio-x-generic'
            elif 'album' in required:
                icon_name = 'media-optical'
            else:
                icon_name = 'preferences-desktop-accessibility'

            metadata_types.append([icon_name, p.title()])

        cell = Gtk.CellRendererPixbuf()
        cell.set_alignment(0, 0.5)
        self.combobox.pack_start(cell, False)
        self.combobox.add_attribute(cell, 'icon-name', 0)

        cell = Gtk.CellRendererText()
        cell.set_alignment(0, 0.5)
        cell.set_padding(5, 0)
        self.combobox.pack_start(cell, True)
        self.combobox.add_attribute(cell, 'text', 1)

        self.combobox.set_model(metadata_types)
        self.combobox.connect('changed', self.on_type_changed)

        self.provider = go('tv_provider')

        cell = Gtk.CellRendererToggle()
        cell.connect('toggled', self.on_toggle, None)
        col = Gtk.TreeViewColumn('Active', cell, active=0)
        self.provider.append_column(col)

        for idx, name in enumerate(['Provider', 'Quality', 'Speed', ''], start=1):
            cell = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(name, cell, text=idx)
            col.set_sort_column_id(idx)
            self.provider.append_column(col)

        self.update_provider()
        self.window.show()


if __name__ == '__main__':
    main = MetadataChooser()
    Gtk.main()
