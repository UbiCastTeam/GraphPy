#!/usr/bin/env python
# -*- coding: utf-8 -*-

#flavie lancereau
#graph plotter
import gobject
import gtk.glade
import numpy as np
import os
#import random
from matplotlib.backends.backend_gtkagg import FigureCanvasGTK as Canvas
from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg as NavigationToolbar
from pylab import figure
from dictlist import DictList
from threaded import thread_it

import logging
logger = logging.getLogger('GankPy')

gobject.threads_init()

class GraphPlotter(gtk.Window):
    def __init__(self, files_path=list()):
        super(GraphPlotter, self).__init__()
        self.build()
        #datas
        self.nb_graph = 1
        self.ax_list = list()
        self.update_ax_list()
        self.adjust.connect("value_changed", self.on_adjuster_changed)
        self.datas = DictList()
        self.color_nb = 0
        self.check_thread_id = None
        self.process_percent = 0
        self.progress_dialog = None
        #parse files
        if len(files_path) > 0:
            for file_path in files_path :
                content = self.parse_new_file(file_path)

    def get_element_from_treestore_path(self, path):
        filename = self.treestore[path[0]][0]
        dataname = self.treestore[path][0]
        filedatas = self.datas.get_by_filename(filename)['content']
        element = filedatas.get_by_name(dataname)
        return element

    def parse_new_file(self, filepath):
        self.progress_dialog = ProgressDialog()
        #self._parse_new_file(filepath) #for debug
        thread = thread_it(self._parse_new_file, filepath)
        self.check_thread_id = gobject.timeout_add(100, self._check_parse_file_thread, thread)

    def _check_parse_file_thread(self, thread):
        if self.check_thread_id is not None:
            gobject.source_remove(self.check_thread_id)
            self.check_thread_id = None
        if thread is None or not thread.is_alive():
            logger.debug('thread is done')
            if self.progress_dialog is not None :
                self.progress_dialog.destroy()
        else:
            #logger.debug('still alive')
            self.check_thread_id = gobject.timeout_add(100, self._check_parse_file_thread, thread)

    def _parse_new_file(self, filepath):
        filename = os.path.basename(filepath)
        self.set_progress_text('parsing new file %s ...' %filename)
        lines = self.get_data_from_file(filepath)
        content = DictList()
        if lines is not None :
            self.set_progress_text('nb lines found %s\n parsing lines ...' %len(lines))
            for i,line in enumerate(lines):
                self.update_process_percent(i, len(lines), 0, 0.8)
                datas = line.rstrip('\n').split('\t')
                for j,value in enumerate(datas):
                    if value == '': value = 0
                    if i == 0:
                        colors = ['g','r','b','c','m','k','y']
                        color = colors[self.color_nb]
                        self.color_nb +=1 
                        if self.color_nb == 7 : self.color_nb = 0

                        content.extend(({'name':value, 'datas':list(), 'pos':j, 'plot_x':None, 'color':color, 'dot_type':'-', 'visible':False},))
                    else :
                        element = content.get_by_pos(j)
                        try:
                            element['datas'].append(int(value))
                        except Exception:
                            try:
                                element['datas'].append(float(value))
                            except Exception:
                                pass
        to_remove = list()
        self.set_progress_text('nb columns found %s\n check for unvalid datas ...' %len(content))
        for i,element in enumerate(content) :
            self.update_process_percent(i, len(content), 80, 0.15)
            if len(element['datas'])>1 and element['name'] != 0:
                element['datas'] = np.array(element['datas'])
            else :
                to_remove.append(element)
        self.set_progress_text('nb unvalid datas found %s\n remove unvalid datas ...' %len(to_remove))
        for i,empty_element in enumerate(to_remove) :
            self.update_process_percent(i, len(to_remove), 95, 0.05)
            if empty_element in content :
                    content.remove(empty_element)
        self.set_progress_text('parsing file %s done\n adding data to treeview' %filename)
        self.datas.extend(({'filepath':filepath, 'filename':filename, 'content':content, },))
        self.treeview_append_data({'filepath':filepath, 'filename':filename, 'content':content, })

    def get_data_from_file(self, fname):
        if os.path.isfile(fname) :
            dfile = open( fname, 'r')
            lines = dfile.readlines()
            dfile.close()
            return lines
        else :
            logger.error('File %s not found' %fname)
            return None

#PROGRESS DIALOG FUNCTIONS
    def set_progress_text(self, text):
        logger.info(text)
        if self.progress_dialog is not None :
            self.progress_dialog.set_label(text)

    def update_process_percent(self, nb_current, nb_max, base, global_process_factor):
        new_percent = base + global_process_factor*(nb_current/float(nb_max))*100
        if int(new_percent) != self.process_percent :
            self.process_percent = int(new_percent)
            if self.progress_dialog is not None :
                self.progress_dialog.set_progress(self.process_percent/100.)

#MATPLOTLIB FUNCTIONS
    def draw_element(self, element):
        color = element['color']
        if element['plot_x'] is not None :
            plot_x = element['plot_x']
        else :
            plot_x = np.array(range(element['datas'].shape[0])).T
        plot_y = element['datas'].T
        l = self.ax_list[element['graph_position']].plot( plot_x, plot_y, '%s%s' %(color,element['dot_type']), label=element['name'])
        element['line'] = l
        element['ploted'] = l[0]
        l[0].set_visible(element['displayed'])
        self.update_legend(element['graph_position'])
        #self.update_limits(element['graph_position'])

    def update_legend(self, graph_position):
        graph_lines = list()
        graph_names = list()
        for filedata in self.datas :
            for content in filedata['content'] :
                if content.has_key('graph_position') and content.has_key('displayed') and content['graph_position'] == graph_position and content['displayed'] and content.has_key('line') :
                    graph_lines.append(content['ploted'])
                    graph_names.append(content['name'])
        if len(graph_lines) > 0 and len(graph_names) > 0 :
            self.ax_list[graph_position].legend(graph_lines, graph_names, loc=1)

    def update_limits(self, graph_position):
        displayed_datas = list()
        for filedata in self.datas :
            for content in filedata['content'] :
                if content.has_key('graph_position') and content.has_key('displayed') and content['graph_position'] == graph_position and content['displayed'] :
                    displayed_datas.append(content['datas'])
        min_y = 100000000
        max_y = 0
        for data in displayed_datas :
            min_current_data = np.min(data)
            max_current_data = np.max(data)
            min_y = min(min_y, min_current_data)
            max_y = max(max_y, max_current_data)
        self.ax_list[graph_position].set_ylim([min_y, max_y])

    def update_ax_list(self):
        for ax in self.ax_list :
            self.fig.delaxes(ax)
        for toolbar_child in self.toolbar.children() :
            self.toolbar.remove(toolbar_child)
            del toolbar_child
        self.ax_list = list()
        index = 0
        for i in range(self.nb_graph) :
            l = round(self.nb_graph/2.)
            if self.nb_graph== 2: l = 2
            c = 2
            if self.nb_graph%2 == 1 and i == 0 or self.nb_graph== 2:
                c = 1
            if self.nb_graph%2 == 1 and i == 1 :
                index += 1
            index += 1
            ax = self.fig.add_subplot(l, c, index)
            self.ax_list.append(ax)
            #graph_toolbar = self.build_graph_toolbar(i)
            #self.toolbar.pack_start(graph_toolbar)
        self.canvas.draw()
        self.show_all()

    def update_graphs(self):
        self.update_ax_list()
        for filedatas in self.datas :
            for element in filedatas['content'] :
                element['ploted'] = None
                if element.has_key('displayed') and element['displayed'] : 
                    self.draw_element(element)
        self.canvas.draw()

#BUTTONS ACTIONS
    def open_path(self, file_path):
        self.parse_new_file(file_path)

    def on_adjuster_changed(self, src):
        self.nb_graph = int(src.get_value())
        self.update_graphs()

    def on_toolbar_pressed(self, src, control_press, graph_nb):
        fig = self.ax_list[graph_nb]
        x_start, x_stop = fig.get_xlim()
        step = (x_stop - x_start)/20.
        if control_press == 'zoom_in' :
            x_start = x_start + step
            x_stop = x_stop - step
            fig.set_xlim(x_start, x_stop)
        elif control_press == 'zoom_out' :
            x_start = x_start - step
            x_stop = x_stop + step
            fig.set_xlim(x_start, x_stop)
        elif control_press == 'zoom_right' :
            x_start = x_start + step
            x_stop = x_stop + step
            fig.set_xlim(x_start, x_stop)
        elif control_press == 'zoom_left' :
            x_start = x_start - step
            x_stop = x_stop - step
            fig.set_xlim(x_start, x_stop)
        elif control_press == 'zoom_fit' :
            fig.autoscale_view()
        self.canvas.draw()

#TREEVIEW ACTIONS
    def on_position_edited(self, column, path, val):
        if int(val) != self.treestore[path][2] and int(val)<=self.nb_graph :
            self.treestore[path][2] = int(val)
            element = self.get_element_from_treestore_path(path)
            if element is not None :
                if element.has_key('ploted') and element['ploted'] is not None :
                    element['ploted'].set_visible(False)
                element['ploted'] = None
                element['graph_position'] = int(val) -1
                self.draw_element(element)
            for i in range(self.nb_graph-1) :
                self.update_legend(i)
            self.canvas.draw()

    def on_name_edited(self, column, path, name):
        if name != self.treestore[path][0] :
            element = self.get_element_from_treestore_path(path)
            self.treestore[path][0] = name
            if element is not None :
                element['name'] = name
                self.update_legend(element['graph_position'])
            self.canvas.draw()

    def treeview_append_data(self, datas):
        parent_line = self.treestore.append( None, (datas['filename'], None, 1, None, gtk.STOCK_PREFERENCES ))
        datas['treeline'] = parent_line
        for content in datas['content'] :
            line = self.treestore.append( parent_line, (content['name'],None, 1, None, gtk.STOCK_PREFERENCES ))
            content['treeline'] = line
            content['displayed'] = False
            content['graph_position'] = 0
            content['color'] = ''

    def on_treestore_toggle_pressed(self, column, path):
        self.treestore[path][1] = not self.treestore[path][1]
        element = self.get_element_from_treestore_path(path)
        if element is not None :
            element['displayed'] = self.treestore[path][1]
            element['graph_position'] = self.treestore[path][2]-1
            if element.has_key('ploted') and element['ploted'] is not None :
                element['ploted'].set_visible(element['displayed'])
                #self.update_limits(element['graph_position'])
                self.update_legend(element['graph_position'])
            else :
                self.draw_element(element)
            self.canvas.draw()

    def on_axe_x_toggle_pressed(self, column, path):
        #only iter for one file
        parent = self.treestore[path].parent
        element = self.get_element_from_treestore_path(path)
        if parent is not None :
            iterchild = parent.iterchildren()
            for child in iterchild :
                child[3] = False
                child_path = child.path
                child_element = self.get_element_from_treestore_path(child.path)
                child_element['plot_x'] = element['datas'].T
                if child_element.has_key('ploted') and child_element['ploted'] is not None and child_element['ploted'] :
                    child_element['ploted'].set_visible(False)
                    self.draw_element(child_element)
            self.treestore[path][3] = True
            self.canvas.draw()
        #ToDo updates graphs for file 

    def on_treestore_settings_pressed(self, column, path):
        print 'on settings pressed'

#BUILD BUTTONS
    def build(self):
        # building gtk window
        self.connect("destroy", gtk.main_quit)
        self.set_default_size(1280, 1024)
        self.set_title("GankPy")
        top_container = gtk.VBox(False, 0)
        self.add(top_container)

        self.container = gtk.HBox(False, 0)
        top_container.pack_end(self.container, expand=True)
        self.left_container = gtk.VBox(False,0)
        self.container.pack_start(self.left_container, expand=False)
        treeview = self.build_treeview()
        self.left_container.add(treeview)
        self.fig = figure(figsize=(15,8),facecolor='#f0ebe2')
        self.fig.subplots_adjust(left=0.03, bottom=0.03, right=0.97, top=0.97, hspace=0.06, wspace=0.06)
        self.canvas = Canvas(self.fig)
        self.container.pack_end(self.canvas,expand=True)
        self.toolbar = gtk.VBox(False,0)
        self.left_container.pack_end(self.toolbar, False, False)

        menu = gtk.HBox(False, 0)
        top_container.pack_start(menu, expand=False)
        open_file_button = self.build_open_file_button()
        menu.pack_start(open_file_button, expand=True)
        adjuster = self.build_adjuster()
        menu.pack_end(adjuster, expand=False)
        matplotlib_toolbar = NavigationToolbar(self.canvas, self)
        menu.pack_end(matplotlib_toolbar, expand=True)

        self.show_all()

    def build_open_file_button(self):
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
        button = gtk.Button()
        button.set_image(image)
        def on_file_selected(content):
            self.open_path(content)
        def on_open_file_pressed(event):
            FileChooser(on_file_selected)
        button.connect("clicked", on_open_file_pressed)
        return button

    def build_treeview(self):
        self.treestore = treestore = gtk.TreeStore( gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, int , gobject.TYPE_BOOLEAN, str)
        treeview = gtk.TreeView( treestore )
        #data name
        column0 = gtk.CellRendererText()
        column0.set_property( 'editable', True )
        column0.connect( 'edited', self.on_name_edited )
        #display grap
        column1 = gtk.CellRendererToggle()
        column1.set_property('activatable', True)
        column1.connect( 'toggled', self.on_treestore_toggle_pressed )
        #select grap
        column2 = gtk.CellRendererText()
        column2.set_property( 'editable', True )
        column2.connect( 'edited', self.on_position_edited )
        column3 = gtk.CellRendererToggle()
        column3.set_property('activatable', True)
        column3.connect( 'toggled', self.on_axe_x_toggle_pressed )
        column3.set_radio(True)
        column4 = CellRendererClickablePixbuf()
        column4.connect( 'clicked', self.on_treestore_settings_pressed )
        treeview_column0 = gtk.TreeViewColumn("Nom", column0, text=0)
        treeview_column1 = gtk.TreeViewColumn("Affiché", column1 )
        treeview_column1.add_attribute( column1, "active", 1)
        treeview_column2 = gtk.TreeViewColumn("Position", column2, text=2 )
        treeview_column3 = gtk.TreeViewColumn("axe x", column3)
        treeview_column3.add_attribute( column3, "active", 3)
        treeview_column4 = gtk.TreeViewColumn("Settings", column4, stock_id=4)
        treeview_column4.add_attribute( column4, "active", 4)
        treeview.append_column( treeview_column0 )
        treeview.append_column( treeview_column1 )
        treeview.append_column( treeview_column2 )
        treeview.append_column( treeview_column3 )
        treeview.append_column( treeview_column4 )
        return treeview

    def build_adjuster(self):
        adjuster_box = gtk.HBox(False, 0)
        self.adjust = adjust = gtk.Adjustment(1, 1, 6, 1)
        spin = gtk.SpinButton(adjustment=adjust, climb_rate=0.0, digits=0)
        label = gtk.Label('Nombre de graphs :')
        adjuster_box.add(label)
        adjuster_box.pack_end(spin, expand=False)
        return adjuster_box

    def build_graph_toolbar(self, graph_nb):
        toolbar = gtk.HBox(False, 0)
        button = gtk.Label('%s' %graph_nb)
        toolbar.pack_start(button)
        button_list = [ ['zoom_in', gtk.STOCK_ZOOM_IN],
                        ['zoom_out', gtk.STOCK_ZOOM_OUT],
                        ['zoom_fit', gtk.STOCK_ZOOM_FIT],
                        ['zoom_right', gtk.STOCK_GO_FORWARD],
                        ['zoom_left', gtk.STOCK_GO_BACK],
                      ]

        for button_content in button_list :
            image = gtk.Image()
            image.set_from_stock(button_content[1], gtk.ICON_SIZE_LARGE_TOOLBAR)
            button = gtk.Button()
            button.set_image(image)
            button.connect("clicked", self.on_toolbar_pressed, button_content[0], graph_nb)
            toolbar.pack_end(button)
        return toolbar

class ProgressDialog(gtk.Window):
    def __init__(self):
        super(ProgressDialog, self).__init__()
        self.dialog = gtk.Dialog('Progress',self, gtk.DIALOG_NO_SEPARATOR | gtk.DIALOG_DESTROY_WITH_PARENT)

        self.progress_label = gtk.Label('0%')
        self.progress_bar = gtk.ProgressBar()
        self.label = gtk.Label('Progress')
        self.dialog.vbox.pack_start(self.progress_label, expand=True)
        self.progress_label.show()
        self.dialog.vbox.pack_start(self.progress_bar, expand=True)
        self.progress_bar.show()
        self.dialog.vbox.pack_start(self.label, expand=True)
        self.label.show()
        self.dialog.show()

    def set_label(self, label):
        self.label.set_text(label)

    def set_progress(self, value):
        self.progress_label.set_text('%s percent' %int(value*100))
        self.progress_bar.set_fraction(value)

class CellRendererClickablePixbuf(gtk.CellRendererPixbuf):
    __gsignals__ = {'clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,))
                   }
    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        self.emit('clicked', path)
    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)

class FileChooser(gtk.Window):
    def __init__(self, callback):
        super(FileChooser, self).__init__()
        dialog = gtk.FileChooserDialog('Open',self, gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            content = dialog.get_filename()
            dialog.destroy()
            callback(content)
        else : dialog.destroy()

if __name__ == '__main__':
    import logging, sys
    logging.basicConfig(
        level=getattr(logging, "DEBUG"),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    files_path = sys.argv[1:]
    plotter = GraphPlotter(files_path)
    gtk.main()
