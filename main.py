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

import logging
logger = logging.getLogger('graph plotter')

class GraphPlotter(gtk.Window):
    def __init__(self, files_path=list()):
        super(GraphPlotter, self).__init__()
        # building gtk window
        self.connect("destroy", gtk.main_quit)
        self.set_default_size(1280, 1024)
        self.set_title("Graph Plotter")
        self.container = gtk.HBox(False, 0)
        self.add(self.container)
        self.left_container = gtk.VBox(False,0)
        self.container.pack_start(self.left_container, expand=False)
        open_file_button = self.build_open_file_button()
        self.left_container.pack_start(open_file_button, expand=False)
        adjuster = self.build_adjuster()
        self.left_container.pack_start(adjuster, expand=False)
        treeview = self.build_treeview()
        self.left_container.add(treeview)
        self.fig = figure(figsize=(15,8),facecolor='#f0ebe2')
        self.fig.subplots_adjust(left=0.03, bottom=0.03, right=0.97, top=0.97, hspace=0.06, wspace=0.06)
        self.canvas = Canvas(self.fig)
        self.container.pack_end(self.canvas,expand=True)
        self.toolbar = gtk.VBox(False,0) #NavigationToolbar(self.canvas, self)
        self.left_container.pack_end(self.toolbar, False, False)
        self.show_all()
        #datas
        self.nb_graph = 1
        self.ax_list = list()
        self.update_ax_list()
        self.adjust.connect("value_changed", self.on_adjuster_changed)
        self.datas = DictList()
        self.color_nb = 0
        #parse files
        if len(files_path) > 0:
            for file_path in files_path :
                content = self.parse_new_file(file_path)

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
        self.treestore = treestore = gtk.TreeStore( gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, int , gobject.TYPE_BOOLEAN)#, gobject.TYPE_STRING )
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

        #column4 = gtk.CellRendererText()
        #column4.set_property('editable', True)
        #column4.connect( 'edited', self.on_color_pressed )

        treeview_column0 = gtk.TreeViewColumn("Nom", column0, text=0)
        treeview_column1 = gtk.TreeViewColumn("Affiché", column1 )
        treeview_column1.add_attribute( column1, "active", 1)
        treeview_column2 = gtk.TreeViewColumn("Position", column2, text=2 )
        treeview_column3 = gtk.TreeViewColumn("axe x", column3)
        treeview_column3.add_attribute( column3, "active", 3)
        #treeview_column4 = gtk.TreeViewColumn("color", column4, text=4, markup=0)

        treeview.append_column( treeview_column0 )
        treeview.append_column( treeview_column1 )
        treeview.append_column( treeview_column2 )
        treeview.append_column( treeview_column3 )
        #treeview.append_column( treeview_column4 )
        return treeview

    def on_color_pressed(self, src, path, text):
        print 'color pressed', src, path
        print dir(src)
        for child in self.treestore[path].iterchildren() :
            print child
            print dir(child)
        self.treestore[path][4] = '<span background="green"></span>'#   toto  </span>'
            
        #src.set_property('cell-background', 'green')

    def treeview_append_data(self, datas):
        parent_line = self.treestore.append( None, (datas['filename'], None, 1, None) )#, ''
        datas['treeline'] = parent_line
        for content in datas['content'] :
            line = self.treestore.append( parent_line, (content['name'],None, 1, None) )#, ''
            content['treeline'] = line
            content['displayed'] = False
            content['graph_position'] = 0
            content['color'] = ''

    def build_adjuster(self):
        adjuster_box = gtk.HBox(False, 0)
        self.adjust = adjust = gtk.Adjustment(1, 1, 6, 1)
        spin = gtk.SpinButton(adjustment=adjust, climb_rate=0.0, digits=0)
        label = gtk.Label('Nombre de graphs :')
        adjuster_box.add(label)
        adjuster_box.pack_end(spin, expand=False)
        return adjuster_box

    def on_adjuster_changed(self, src):
        self.nb_graph = int(src.get_value())
        self.update_graphs()

    def get_element_from_treestore_path(self, path):
        filename = self.treestore[path[0]][0]
        dataname = self.treestore[path][0]
        filedatas = self.datas.get_by_filename(filename)['content']
        element = filedatas.get_by_name(dataname)
        return element

    def on_treestore_toggle_pressed(self, column, path):
        self.treestore[path][1] = not self.treestore[path][1]
        element = self.get_element_from_treestore_path(path)
        if element is not None :
            element['displayed'] = self.treestore[path][1]
            element['graph_position'] = self.treestore[path][2]-1
            if element.has_key('ploted') and element['ploted'] is not None :
                element['ploted'].set_visible(element['displayed'])
                self.update_limits(element['graph_position'])
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

    def draw_element(self, element):
        if element.has_key('color') :
            color = element['color']
        else : 
            colors = ['g-','r-','b-','c-','m-','k-','y-']
            color = colors[self.color_nb]
            element['color'] = color
            self.color_nb +=1 
            if self.color_nb == 7 : self.color_nb = 0
        if element['plot_x'] is not None :
            plot_x = element['plot_x']
        else :
            plot_x = np.array(range(element['datas'].shape[0])).T
        plot_y = element['datas'].T
        l = self.ax_list[element['graph_position']].plot( plot_x, plot_y, color, label=element['name'])
        element['line'] = l
        element['ploted'] = l[0]
        l[0].set_visible(element['displayed'])
        self.update_legend(element['graph_position'])
        self.update_limits(element['graph_position'])

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
            graph_toolbar = self.build_graph_toolbar(i)
            self.toolbar.pack_start(graph_toolbar)
        self.canvas.draw()
        self.show_all()

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

    def update_graphs(self):
        self.update_ax_list()
        for filedatas in self.datas :
            for element in filedatas['content'] :
                element['ploted'] = None
                if element.has_key('displayed') and element['displayed'] : 
                    self.draw_element(element)
        self.canvas.draw()

    def open_path(self, file_path):
        self.parse_new_file(file_path)

    def parse_new_file(self, filepath):
        lines = self.get_data_from_file(filepath)
        content = DictList()
        if lines is not None :
            for i,line in enumerate(lines):
                datas = line.rstrip('\n').split('\t')
                for j,value in enumerate(datas):
                    if value == '': value = 0
                    if i == 0:
                        content.extend(({'name':value, 'datas':list(), 'pos':j, 'plot_x':None},))
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
        for element in content :
            if len(element['datas'])>1 and element['name'] != 0:
                element['datas'] = np.array(element['datas'])
            else :
                to_remove.append(element)
        for empty_element in to_remove :
            if empty_element in content :
                content.remove(empty_element)
        self.datas.extend(({'filepath':filepath, 'filename':os.path.basename(filepath), 'content':content, },))
        self.treeview_append_data({'filepath':filepath, 'filename':os.path.basename(filepath), 'content':content, })

    def get_data_from_file(self, fname):
        if os.path.isfile(fname) :
            dfile = open( fname, 'r')
            lines = dfile.readlines()
            dfile.close()
            return lines
        else :
            logger.error('File %s not found' %fname)
            return None

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

class DictList(list):
    '''List that can only contain dictionaries.
    
    Provide lookup functionality'''
    
    def __init__(self, iterable=None):
        list.__init__(self)
        self._dict_properties = set()
        if iterable is not None:
            if isinstance(iterable, dict):
                self.append(iterable)
            else:
                self.extend(iterable)
    
    def _add_key(self, key):
        if key not in self._dict_properties:
            self._dict_properties.add(key)
            def get_by_key(self, value):
                return self.get_key(key, value)
            def get_all_by_key(self, value):
                return self.get_all_key(key, value)
            setattr(self, 'get_by_%s' % key, MethodType(get_by_key, self, self.__class__))
            setattr(self, 'get_all_by_%s' % key, MethodType(get_all_by_key, self, self.__class__))
    
    def _after_add_dict(self, dct):
        for key in dct:
            self._add_key(key)
        self._synchronize_properties()
    
    def _after_extend_list(self, dict_list):
        for dct in dict_list:
            for key in dct:
                self._add_key(key)
        self._synchronize_properties()
    
    def _check_item(self, item):
        if not isinstance(item, dict):
            raise TypeError('DictList item type must be %s (%s found)' % (dict, type(item)))
        for key in item:
            self._check_key(key)
    
    def _check_key(self, key):
        match = re.search(r'[^a-z0-9_]', key)
        if match is not None:
            raise ValueError('Key can only contain small letters, digits and underscores, "%s" is invalid' % key)
    
    def _check_list(self, l):
        for item in l:
            self._check_item(item)
    
    def _synchronize_properties(self):
        for dct in self:
            for prop in self._dict_properties:
                if prop not in dct:
                    dct[prop] = None
    
    def get_all_key(self, key, value):
        result = list()
        try:
            for item in self:
                if item[key] == value:
                    result.append(item)
        except KeyError:
            raise KeyError('Items of this list have no key "%s"' % key)
        return result
    
    def get_key(self, key, value):
        try:
            for item in self:
                if item[key] == value:
                    return item
        except KeyError:
            raise KeyError('Items of this list have no key "%s"' % key)
        return None
    
    def __add__(self, dict_list):
        self.extend(dict_list)
    
    def __setitem__(self, index, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.__setitem__(self, index, copied_dict)
        self._after_add_dict(copied_dict)
    
    def __getslice__(self, i, j):
        return DictList(list.__getslice__(self, i, j))
    
    def __setslice__(self, i, j, dict_list):
        copied_dict_list = list()
        for dct in dict_list:
            copied_dict_list.append(dict(dct))
        self._check_list(copied_dict_list)
        list.__setslice__(self, i, j, copied_dict_list)
        self._after_extend_list(copied_dict_list)
    
    def append(self, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.append(self, copied_dict)
        self._after_add_dict(copied_dict)
    
    def copy(self):
        new_dict_list = list()
        for dct in self:
            new_dict_list.append(dict(dct))
        return new_dict_list
    
    def extend(self, dict_list):
        copied_dict_list = list()
        for dct in dict_list:
            copied_dict_list.append(dict(dct))
        self._check_list(copied_dict_list)
        list.extend(self, copied_dict_list)
        self._after_extend_list(copied_dict_list)
    
    def insert(self, index, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.insert(self, index, copied_dict)
        self._after_add_dict(copied_dict)
    
    def sort_by(self, key):
        self.sort(key=lambda d: d[key])

try:
    from collections import OrderedDict
except ImportError:
    # Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
    # Passes Python2.7's test suite and incorporates all the latest updates.

    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass


if __name__ == '__main__':
    import sys
    files_path = sys.argv[1:]
    plotter = GraphPlotter(files_path)
    gtk.main()
