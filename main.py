#!/usr/bin/python3
from time import sleep
from threading import Thread
from subprocess import Popen
from tempfile import mkstemp
from plyr import Cache, Query, Database, PROVIDERS
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject

GObject.threads_init()
Gdk.threads_init()


IMAGE_DESCRIPTION = '''
<tt>Image-Size:    </tt>   {size}
<tt>Image-Format:  </tt>   {image_format}
<tt>Image-Provider:</tt>   {provider}


<b>Source-URL:</b>
'''


class MetadataChooser:
    def query_data(self, *args):
        self.results = self.query.commit()
        self.query_done = True

        Gdk.threads_enter()
        self.toggle_search_sensivity()
        Gdk.threads_leave()

    def query_callback(self, cache, query):
        Gdk.threads_enter()
        try:
            if cache.is_image:
                template = self.create_template_image(cache)
            elif query.get_type in ['tracklist']:
                template = self.create_template_list(cache)
            else:
                template = self.create_template_text(cache)

            self.content_box.pack_start(template, False, False, 1)
        finally:
            Gdk.threads_leave()

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
        query.database = self.db
        query.verbosity = 0
        query.db_autowrite = False

        query.force_utf8 = self.settings['force-utf8']
        query.language = self.settings['language']
        query.language_aware_only = self.settings['only-lang']
        query.img_size = (self.settings['min-size'], self.settings['max-size'])

        query.qsratio = self.settings['qsratio']
        query.max_per_plugins = self.settings['plugmax']

        self.results = []
        self.query = query
        self.query_done = False
        self.progress.set_fraction(0.0)

        for widget in self.content_box.get_children():
            self.content_box.remove(widget)

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

    def on_draw_image(self, widget, ctx, pixbuf):
        alloc = widget.get_allocation()
        width, height = pixbuf.get_width(), pixbuf.get_height()
        fac = float(alloc.width) / max(width, height)
        asp_width, asp_height = fac * width, fac * height

        border = 5

        center_rect = int((alloc.height - asp_height) / 2)

        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(
                0,
                center_rect,
                asp_width,
                asp_height
        )
        ctx.fill()

        asp_width -= 2 * border
        asp_height -= 2 * border

        thumbnail = pixbuf.scale_simple(
                asp_width, asp_height,
                GdkPixbuf.InterpType.HYPER
        )

        Gdk.cairo_set_source_pixbuf(ctx, thumbnail, border, center_rect + border)
        ctx.rectangle(
                border,
                center_rect + border,
                asp_width,
                asp_height
        )
        ctx.fill()

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

    def result_set(self, widget, cache):
        self.db.insert(self.query, cache)
        widget.set_sensitive(False)

    def create_template_image(self, cache):
        builder = Gtk.Builder()
        builder.add_from_file('template_image.glade')
        go = builder.get_object
        da = go('da')

        lb_descr = go('lb_descr')
        lb_source = go('lb_source')

        loader = GdkPixbuf.PixbufLoader()
        loader.write(cache.data)
        loader.close()
        pixbuf = loader.get_pixbuf()

        def show_in_image_viewer(widget, event, pixbuf):
            file_id, path = mkstemp(suffix='png')
            pixbuf.savev(path, 'png', [], [])

            try:
                Popen(self.settings['image-viewer'] % path,  shell=True)
            except TypeError:
                pass

        event_box = go('image_eventbox')
        event_box.connect('button-press-event', show_in_image_viewer, pixbuf)

        da.connect('draw', self.on_draw_image, pixbuf)

        lb_descr.set_markup(IMAGE_DESCRIPTION.format(
            size='{0}x{1}'.format(pixbuf.get_width(), pixbuf.get_height()),
            image_format=cache.image_format,
            provider=cache.provider
        ))

        lb_source.set_label(cache.source_url)
        lb_source.set_uri(cache.source_url)

        btn_set = go('btn_set')
        btn_set.set_sensitive(not cache.is_cached)
        btn_set.connect('clicked', self.result_set, cache)

        return go('template_image')

    def create_template_text(self, cache):
        builder = Gtk.Builder()
        builder.add_from_file('template_text.glade')
        go = builder.get_object

        lb_provider = go('lb_provider')
        lb_source = go('lb_source')
        text_field = go('tev_text')

        lb_provider.set_text(cache.provider)
        lb_source.set_label(cache.source_url)
        lb_source.set_uri(cache.source_url)

        text_buf = Gtk.TextBuffer()
        text_buf.set_text(str(cache.data, 'utf-8'))
        text_field.set_buffer(text_buf)

        btn_set = go('btn_set')
        btn_set.set_sensitive(not cache.is_cached)
        btn_set.connect('clicked', self.result_set, cache)

        return go('template_text')

    def create_template_list(self, cache):
        builder = Gtk.Builder()
        builder.add_from_file('template_track.glade')
        go = builder.get_object

        lb_track = go('lb_track')
        lb_duration = go('lb_duration')

        lb_track.set_text(str(cache.data, 'utf-8'))
        lb_duration.set_text('{0:02}:{1:02}'.format(
            int(cache.duration / 60),
            cache.duration % 60)
        )

        return go('template_track')

    ########i###################################################################
    #                           Setttings Callbacks                           #
    ###########################################################################

    def set_default_settings(self):
        self.settings = {
            'force-utf8': False,
            'language': 'en',
            'only-lang': False,
            'min-size': -1,
            'max-size': -1,
            'qsratio': 0.9,
            'plugmax': -1,
            'image-viewer': 'sxiv %s'
        }

    def set_setting(self, key, value):
        self.settings[key] = value

    def __init__(self):
        self.db = Database('/tmp')

        self.set_default_settings()

        self.builder = Gtk.Builder()
        self.builder.add_from_file('metadata-chooser.glade')
        go = self.builder.get_object

        self.window = go('wd_metadata_chooser')
        self.window.connect('destroy', self.on_destroy)

        self.content_box = go('b_result')

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

        ##############
        #  Settings  #
        ##############

        go('forceutf8_switch').connect('button-press-event',
                lambda sw, ev: self.set_setting('force-utf8', not sw.get_active())
        )
        go('only_lang_switch').connect('button-press-event',
                lambda sw, ev: self.set_setting('only-lang', not sw.get_active())
        )
        go('lang_combobox').connect('changed',
                lambda co: self.set_setting('language', co.get_model()[co.get_active()][0])
        )
        go('minsize_spin').connect('changed',
                lambda spin: self.set_setting('min-size', int(spin.get_value()))
        )
        go('maxsize_spin').connect('changed',
                lambda spin: self.set_setting('max-size', int(spin.get_value()))
        )
        go('image_viewer_entry').connect('activate',
                lambda ent: self.set_setting('image-viewer', ent.get_text())
        )
        go('qsratio_scale').connect('value-changed',
                lambda sc: self.set_setting('qsratio', sc.get_value())
        )
        go('plugmax_scale').connect('value-changed',
                lambda sc: self.set_setting('plugmax', int(sc.get_value()))
        )

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

        self.results = []

        cell = Gtk.CellRendererToggle()
        cell.connect('toggled', self.on_toggle, None)
        col = Gtk.TreeViewColumn('Active', cell, active=0)
        self.provider.append_column(col)

        for idx, name in enumerate(['Provider', 'Quality', 'Speed'], start=1):
            cell = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(name, cell, text=idx)
            col.set_sort_column_id(idx)
            self.provider.append_column(col)

        self.update_provider()
        self.window.show()


if __name__ == '__main__':
    main = MetadataChooser()
    Gtk.main()
