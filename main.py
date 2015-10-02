#!/usr/bin/env python
# -*- coding: utf-8 -*-

#flavie lancereau
#graph plotter

try : 
    import gtk
except ImportError,e :
    print 'could not import gtk %s : %s. Trying with introspection' %(ImportError, e)
    try : 
        from gi.repository import Gtk
    except ImportError,e :
        raise ImportError('could not import Gtk. Please make sure that you have pyGtk : %s' %e)
try : 
    import numpy as np
except ImportError :
    raise ImportError('Could not import Numpy. Please make sure that you have Numpy : %s' %e)
try :
    from matplotlib.backends.backend_gtkagg import FigureCanvasGTK as Canvas
except ImportError :
    try : 
        from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as Canvas
    except ImportError :
        raise ImportError('Could not import Matplotlib gtk modules. Please make sure that you have Matplotlib : %s' %e)
try :
    from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg as NavigationToolbar
except ImportError :
    try : 
        from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar
    except ImportError :
        raise ImportError('Could not import Matplotlib gtk modules. Please make sure that you have Matplotlib : %s' %e)
try :
    from pylab import figure
except ImportError :
    raise ImportError('Could not import Matplotlib gtk modules. Please make sure that you have Matplotlib : %s' %e)
import gobject
import os
from dictlist import DictList
from threaded import thread_it
import logging

logger = logging.getLogger('GPy')
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

#PARSE FILE
    def parse_new_file(self, filepath):
        self.progress_dialog = ProgressDialog()
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
                        content.extend(({'name':value, 'datas':list(), 'pos':j, 'plot_x':None, 'color':color, 'dot_type':'-', 'visible':False, 'graph_position':0 ,'filename':filename},))
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

#TREEVIEW ACTIONS
    def get_element_from_treestore_path(self, path):
        filename = self.treestore[path[0]][0]
        dataname = self.treestore[path][0]
        filedatas = self.datas.get_by_filename(filename)['content']
        element = filedatas.get_by_name(dataname)
        return element

    def treeview_append_data(self, datas):
        try :
            parent_line = self.treestore.append( None, (datas['filename'], None, None ))
            datas['treeline'] = parent_line
            for content in datas['content'] :
                logger.debug('treview append : %s' %content['name'])
                line = self.treestore.append( parent_line, (content['name'],None, gtk.STOCK_PREFERENCES ))
                content['treeline'] = line
        except Exception,e :
            logger.error('%s : %s' %(Exception, e))

    def on_name_edited(self, column, path, name):
        if name != self.treestore[path][0] :
            element = self.get_element_from_treestore_path(path)
            if element is not None :
                self.set_data_name(path, element, name)

    def on_treestore_toggle_pressed(self, column, path):
        visible = not self.treestore[path][1]
        element = self.get_element_from_treestore_path(path)
        if element is not None :
            self.set_data_visibility(path, element, visible)

    def on_treestore_settings_pressed(self, column, path):
        element = self.get_element_from_treestore_path(path)
        def callback(return_element):
            self.set_data_name(path, element, return_element['name'], redraw=False)
            self.set_data_position(path, element, return_element['graph_position'], redraw=False)
            self.set_data_visibility(path, element, return_element['visible'], redraw=False)
            self.set_data_type(path, element, 'color', return_element['color'], redraw=False)
            self.set_data_type(path, element, 'dot_type', return_element['dot_type'], redraw=False)
            self.set_data_type(path, element, 'plot_x', return_element['plot_x'], redraw=False)
            self.draw_element(element, redraw=True)
        filename = self.treestore[path[0]][0]
        dialog = DataSettingsDialog(self.datas.get_by_filename(filename), element, callback)

#DATAS ACTIONS
    def set_data_position(self, treestore_path, element, val, redraw=True):
        if int(val)<=self.nb_graph :
            if element.has_key('ploted') and element['ploted'] is not None :
                element['ploted'].set_visible(False)
            element['ploted'] = None
            element['graph_position'] = int(val)
            if redraw :
                for i in range(self.nb_graph-1) :
                    self.update_legend(i)
                self.draw_element(element)
                self.canvas.draw()

    def set_data_name(self, treestore_path, element, name, redraw=True):
        self.treestore[treestore_path][0] = name
        element['name'] = name
        self.update_legend(element['graph_position'])
        if redraw :
            self.canvas.draw()

    def set_data_visibility(self, treestore_path, element, visible, redraw=True):
        self.treestore[treestore_path][1] = visible
        element['visible'] = visible
        #element['graph_position'] = self.treestore[treestore_path][2]
        if redraw:
            if element.has_key('ploted') and element['ploted'] is not None :
                element['ploted'].set_visible(visible)
                self.update_legend(element['graph_position'])
            else :
                self.draw_element(element)
            self.canvas.draw()

    def set_data_type(self, treestore_path, element, data_type, value, redraw=True):
        element[data_type] = value
        if redraw :
            self.draw_element(element)
            self.canvas.draw()

#MATPLOTLIB FUNCTIONS
    def draw_element(self, element, redraw=False):
        color = element['color']
        filename_datas_content = self.datas.get_by_filename(element['filename'])['content']
        if element['plot_x'] is not None and filename_datas_content.get_by_name(element['plot_x']) is not None :
            x_datas = filename_datas_content.get_by_name(element['plot_x'])
            plot_x = x_datas['datas'].T
        else :
            plot_x = np.array(range(element['datas'].shape[0])).T
        plot_y = element['datas'].T
        print plot_x 
        print plot_y
        try :
            logger.debug('draw line as %s%s' %(color,element['dot_type']))
            l = self.ax_list[element['graph_position']].plot( plot_x, plot_y, '%s%s' %(color,element['dot_type']), label=element['name'])
        except Exception,e :
            logger.error('error when drawing datas %s : %s' %(Exception,e))
            return False 
        element['line'] = l
        element['ploted'] = l[0]
        l[0].set_visible(element['visible'])
        self.update_legend(element['graph_position'])
        if redraw :
            for i in range(self.nb_graph-1) :
                self.update_legend(i)
            self.canvas.draw()
        self.update_limits(element['graph_position'])

    def update_legend(self, graph_position):
        graph_lines = list()
        graph_names = list()
        for filedata in self.datas :
            for content in filedata['content'] :
                if content.has_key('graph_position') and content.has_key('visible') and content['graph_position'] == graph_position and content['visible'] and content.has_key('line') :
                    graph_lines.append(content['ploted'])
                    graph_names.append(content['name'])
        if len(graph_lines) > 0 and len(graph_names) > 0 :
            self.ax_list[graph_position].legend(graph_lines, graph_names, loc=1)

    def update_limits(self, graph_position):
        displayed_datas = list()
        for filedata in self.datas :
            for content in filedata['content'] :
                if content.has_key('graph_position') and content.has_key('visible') and content['graph_position'] == graph_position and content['visible'] :
                    displayed_datas.append(content['datas'])
        min_y = None
        max_y = None
        for data in displayed_datas :
            min_current_data = np.min(data)
            max_current_data = np.max(data)
            if min_y is None : min_y = min_current_data
            else : min_y = min(min_y, min_current_data)
            if max_y is None : max_y = max_current_data
            else : max_y = max(max_y, max_current_data)
        print '>>>>>>>>>>'
        print min_y
        print max_y
        print '>>>>>>>>>>'
        self.ax_list[graph_position].set_ylim([min_y, max_y])

    def update_ax_list(self):
        for ax in self.ax_list :
            self.fig.delaxes(ax)
        '''for toolbar_child in self.toolbar.children() :
            self.toolbar.remove(toolbar_child)
            del toolbar_child'''
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
                if element.has_key('visible') and element['visible'] : 
                    self.draw_element(element)
        self.canvas.draw()

#TOOLBAR ACTIONS
    def open_path(self, file_path):
        self.parse_new_file(file_path)

    def on_adjuster_changed(self, src):
        self.nb_graph = int(src.get_value())
        self.update_graphs()

#BUILD BUTTONS
    def build(self):
        # building gtk window
        self.connect("destroy", gtk.main_quit)
        self.set_default_size(1280, 1024)
        self.set_title("GPy")
        top_container = gtk.VBox(False, 0)
        self.add(top_container)
        #build panel
        self.panel = gtk.HBox(False, 0)
        top_container.pack_end(self.panel, expand=True)
        #build left menu
        self.left_menu = gtk.VBox(False,0)
        self.panel.pack_start(self.left_menu, expand=False)
        treeview = self.build_treeview()
        self.left_menu.add(treeview)
        #build right menu
        self.right_menu = gtk.VBox(False,0)
        self.panel.pack_end(self.right_menu, expand=False)
        adjuster = self.build_adjuster()
        self.right_menu.pack_start(adjuster, expand=False)
        #build grap panel
        self.fig = figure(figsize=(15,8),facecolor='#f0ebe2')
        self.fig.subplots_adjust(left=0.03, bottom=0.03, right=0.97, top=0.97, hspace=0.06, wspace=0.06)
        self.canvas = Canvas(self.fig)
        self.panel.pack_end(self.canvas,expand=True)
        #build toolbars
        menu = gtk.HBox(False, 0)
        top_container.pack_start(menu, expand=False)
        toolbar = self.build_toolbar_button()
        menu.pack_start(toolbar, expand=False)
        matplotlib_toolbar = NavigationToolbar(self.canvas, self)
        menu.pack_end(matplotlib_toolbar, expand=True)
        self.show_all()

    def build_adjuster(self):
        adjuster_box = gtk.HBox(False, 0)
        self.adjust = adjust = gtk.Adjustment(1, 1, 6, 1)
        spin = gtk.SpinButton(adjustment=adjust, climb_rate=0.0, digits=0)
        label = gtk.Label('Nombre de graphs :')
        adjuster_box.add(label)
        adjuster_box.pack_end(spin, expand=False)
        return adjuster_box

    def build_toolbar_button(self):
        toolbar = gtk.Toolbar()

        open_image = gtk.Image()
        open_image.set_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
        def on_file_selected(content):
            pass
            self.open_path(content)
        def on_open_file_pressed(event):
            FileChooser(on_file_selected)
        open_button = toolbar.append_item("Open", "Open file", "open", open_image, on_open_file_pressed)

        def on_clear_pressed(event):
            self.treestore.clear()
            self.datas = DictList()
            for ax in self.ax_list :
                ax.clear()
        clear_image = gtk.Image()
        clear_image.set_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_BUTTON)
        fit_button = toolbar.append_item("Clear", "Remove all datas","remove", clear_image, on_clear_pressed)
        return toolbar

    def build_treeview(self):
        self.treestore = treestore = gtk.TreeStore( gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, str)
        treeview = gtk.TreeView( treestore )
        #data name
        column0 = gtk.CellRendererText()
        column0.set_property( 'editable', True )
        column0.connect( 'edited', self.on_name_edited )
        treeview_column0 = gtk.TreeViewColumn("Nom", column0, text=0)
        #display grap
        column1 = gtk.CellRendererToggle()
        column1.set_property('activatable', True)
        column1.connect( 'toggled', self.on_treestore_toggle_pressed )
        treeview_column1 = gtk.TreeViewColumn("Affiché", column1 )
        treeview_column1.add_attribute( column1, "active", 1)
        #options
        column2 = CellRendererClickablePixbuf()
        column2.connect( 'clicked', self.on_treestore_settings_pressed )
        treeview_column2 = gtk.TreeViewColumn("Settings", column2, stock_id=2)
        treeview_column2.add_attribute( column2, "active", 2)

        treeview.append_column( treeview_column0 )
        treeview.append_column( treeview_column1 )
        treeview.append_column( treeview_column2 )
        return treeview

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

class DataSettingsDialog(gtk.Window):
    def __init__(self, current_file_datas, element, callback):
        super(DataSettingsDialog, self).__init__()
        dialog = gtk.Dialog('%s settings' %element['name'],self, gtk.DIALOG_NO_SEPARATOR | gtk.DIALOG_DESTROY_WITH_PARENT,
                 (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_APPLY, gtk.RESPONSE_OK))
        
        name_entry = gtk.Entry()
        name_entry.set_text(element['name'])
        visible_entry = gtk.CheckButton(label=None)
        visible_entry.set_active(element['visible'])
        graph_entry = gtk.Entry()
        graph_entry.set_text('%s' %(element['graph_position']))
        color_entry = gtk.combo_box_new_text()
        colors = ['g','r','b','c','m','k','y']
        for color in colors :
            color_entry.append_text(color)
        color_entry.set_active(colors.index(element['color']))
        dot_entry =  gtk.combo_box_new_text()
        dots = ['-','--','.',',','o','8','s','*','+','x','d','|','_']
        for dot in dots :
            dot_entry.append_text(dot)
        dot_entry.set_active(dots.index(element['dot_type']))

        plot_x_entry = gtk.combo_box_new_text()
        plot_x = list()
        for data in current_file_datas['content'] :
            plot_x.append(data['name'])
            plot_x_entry.append_text(data['name'])

        buttons = [['Name :', name_entry], ['Visible :', visible_entry], ['Position :', graph_entry], ['Color :', color_entry], ['Dots : (really slow)', dot_entry], ['Axe x', plot_x_entry]]

        for button in buttons :
            box = gtk.HBox()
            dialog.vbox.pack_start(box)
            title = gtk.Label(button[0])
            box.pack_start(title, expand=True)
            box.pack_end(button[1], expand=True)
            box.show()
            title.show()
            button[1].show()

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            element['name'] = name_entry.get_text()
            element['visible'] = visible_entry.get_active()
            element['graph_position'] = int(graph_entry.get_text())
            element['color'] = colors[color_entry.get_active()]
            element['dot_type'] = dots[dot_entry.get_active()]
            element['plot_x'] = plot_x[plot_x_entry.get_active()]
            dialog.destroy()
            callback(element)
        else : dialog.destroy()


class CellRendererClickablePixbuf(gtk.CellRendererPixbuf):
    __gsignals__ = {'clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,))
                   }
    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        self.emit('clicked', path)
    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)

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

    logger.info('deprecated warning from matplotlib can appear whith too old version of numpy')
    files_path = sys.argv[1:]
    plotter = GraphPlotter(files_path)
    gtk.main()
