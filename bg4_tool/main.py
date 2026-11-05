import os
import sys
from functools import partial
from pathlib import Path

from PySide6 import QtWidgets, QtGui, QtCore

from bg4_tool.classes import BG4Archive, BG4ArchiveError
from bg4_tool.constants import *


def main():
    app = QtWidgets.QApplication(sys.argv)

    if os.name == 'nt':
        app.setStyle('Fusion')

    window = MainWindow(app)
    window.adjustSize()

    screen_center = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
    window_geometry = window.frameGeometry()
    window_geometry.moveCenter(screen_center)
    window.move(window_geometry.topLeft())

    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()


# TODO: be able to drag and drop files to reorganize and move between folders
# TODO: be able to drop BG4 archives onto the window to import them
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(MainWindow, self).__init__()

        self.current_bg4_data = None

        menu_bar = self.menuBar()
        self.menu_bar_file = menu_bar.addMenu("file")

        self.menu_bar_file_new = QtGui.QAction("new", self)
        self.menu_bar_file_new.setShortcut(QtGui.QKeySequence.StandardKey.New)
        self.menu_bar_file_new.triggered.connect(self.new_file)
        self.menu_bar_file.addAction(self.menu_bar_file_new)

        self.menu_bar_file_open = QtGui.QAction("open", self) # TODO
        self.menu_bar_file_open.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        # self.menu_bar_file_open.triggered.connect(self.new_file)
        self.menu_bar_file.addAction(self.menu_bar_file_open)

        self.menu_bar_file_save = QtGui.QAction("save", self) # TODO
        self.menu_bar_file_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        # self.menu_bar_file_save.triggered.connect(self.new_file)
        self.menu_bar_file.addAction(self.menu_bar_file_save)

        self.menu_bar_file_save_as = QtGui.QAction("save as", self) # TODO
        self.menu_bar_file_save_as.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        # self.menu_bar_file_save_as.triggered.connect(self.new_file)
        self.menu_bar_file.addAction(self.menu_bar_file_save_as)

        self.menu_bar_file.addSeparator() # -----------------------------------------

        self.menu_bar_file_import = QtGui.QAction("import", self)
        # self.menu_bar_file_import.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.menu_bar_file_import.triggered.connect(self.import_archive_file)
        self.menu_bar_file.addAction(self.menu_bar_file_import)

        self.menu_bar_file_export = QtGui.QAction("export", self)
        # self.menu_bar_file_export.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.menu_bar_file_export.triggered.connect(self.export_archive_file)
        self.menu_bar_file.addAction(self.menu_bar_file_export)

        self.menu_bar_file.addSeparator() # -----------------------------------------

        self.menu_bar_file_quit = QtGui.QAction("quit", self) # TODO: make it check whether you've saved
        self.menu_bar_file_quit.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
        self.menu_bar_file_quit.triggered.connect(QtWidgets.QApplication.quit)
        self.menu_bar_file.addAction(self.menu_bar_file_quit)

        main = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout(main)
        self.setCentralWidget(main)

        self.version_selector_text = QtWidgets.QLabel()
        self.version_selector = QtWidgets.QComboBox()
        self.version_selector.addItems([str(i) for i in BG4Archive.supported_versions])
        self.version_selector.currentIndexChanged.connect(self.set_version)
        main_layout.addWidget(self.version_selector_text, 0, 0)
        main_layout.addWidget(self.version_selector, 1, 0)

        checkboxes = QtWidgets.QWidget()
        checkboxes_layout = QtWidgets.QVBoxLayout(checkboxes)
        checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(checkboxes, 2, 0)

        toggles = [
            BG4Archive.single_file_keyword,
            BG4Archive.preserve_order_keyword,
        ]

        self.toggle_checkboxes = {}
        for toggle in toggles:
            checkbox = QtWidgets.QCheckBox()
            checkboxes_layout.addWidget(checkbox)

            checkbox.clicked.connect(partial(self.toggle_property, toggle))

            self.toggle_checkboxes[toggle] = checkbox

        self.file_tree = QtWidgets.QTreeWidget()
        self.file_tree.setColumnCount(2)
        self.file_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.tree_context_menu)
        main_layout.addWidget(self.file_tree, 3, 0)

        self._set_program_icons()
        self._set_program_text()
        self.initialize_tree_view()
        self.new_file()

    def _set_program_text(self):
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file.setTitle(self.tr("&File"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_new.setText(self.tr("&New"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_open.setText(self.tr("&Open"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_save.setText(self.tr("&Save"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_save_as.setText(self.tr("Save &as"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_import.setText(self.tr("&Import"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_export.setText(self.tr("&Export"))
        #: The "&" symbol will underline a letter and cause the option to be selectable by pressing the letter on your keyboard while holding Alt. Please ensure all letters that are given this property within each submenu and in the toolbar itself are unique, so all options can be selected this way.
        self.menu_bar_file_quit.setText(self.tr("&Quit"))

        self.version_selector_text.setText(self.tr("Archive Version:"))

        versions = {
            3: [
                self.tr("Lossy Binary Search"),
                self.tr("Uses binary searching to sort through every file's name hash. Does not store file names, and fails to export if two file names share a hash."),
            ],
            4: [
                self.tr("Quick Name Lookup"),
                self.tr("Uses search buckets to narrow down the file being searched for extremely quickly."),
            ],
            5: [
                self.tr("Quick Binary Search"),
                self.tr("Uses binary searching to quickly sort through every file's name hash."),
            ],
        }

        for i, version in enumerate(BG4Archive.supported_versions):
            name_string, desc_string = versions[version]
            self.version_selector.setItemText(i, self.tr("Version {0}: {1}").format(version, name_string))
            self.version_selector.setItemData(i, desc_string, QtCore.Qt.ItemDataRole.ToolTipRole)

        toggles = {
            BG4Archive.single_file_keyword: [
                self.tr("Export Single File"),
                self.tr("Disabling this will split the archive into a '_Header' file and a '_Data' file. Lowers RAM overhead for extremely large archives."),
            ],
            BG4Archive.preserve_order_keyword: [
                self.tr("Preserve File Order"),
                self.tr("Creates an additional table that tracks the index of each file in the archive. Necessary for archives that can use an index to find a file."),
            ],
        }

        for key, checkbox in self.toggle_checkboxes.items():
            name_string, desc_string = toggles.get(key, ["", ""])
            checkbox.setText(name_string)
            checkbox.setToolTip(desc_string)

    def _set_program_icons(self):
        icon_path = "img_icons_dx"
        self.icons = {
            "main":   self._grab_icon(icon_path, 1, (16, 16)),
            "folder": self._grab_icon(icon_path, 2, (16, 16)),
            "file":   self._grab_icon(icon_path, 3, (16, 16)),
            "blz":    self._grab_icon(icon_path, 4, (16, 16)),
        }

    def _throw_error(self, error_code, error_message, file_indeces):
        verbose_message = { # super easy errors are given a translatable "extra info" blurb.
            #100: "Import Error: Unknown",
             101: self.tr("This file's header is not valid. It may be compressed, corrupted, or not an archive at all."),
            #102: "Import Error: Data File Not Provided",
             103: self.tr("This file's header is not valid. It may be compressed, corrupted, or not an archive at all."),

            #200: "Export Error: Unknown",
            #201: "Export Error: Buckets Too Small",
             202: self.tr("Multiple files' names yielded the same hash, which cannot be handled with the current export settings."),
             203: self.tr("Archive is too large to export."),
             204: self.tr("File within archive is too large to export."),
             205: self.tr("At least one file lacks a name, which cannot be handled with the current export settings."),
             206: self.tr("At least one file lacks a name, which cannot be handled with the current export settings."),

            #300: "Access Error: Unknown",
            #301: "Access Error: Bad Property",
            #302: "Access Error: Bad File Name",
            #303: "Access Error: File Does Not Exist",
        }.get(error_code)

        #: Formatted as "Error 101 - Import Error: Bad Header" for example
        error_string_0 = self.tr("An error has occured!\nError {0} - {1}").format(error_code, error_message)
        #: Appended directly to the first error string if a special blurb is provided for the current error
        error_string_1 = self.tr("\n\nAdditional info about this error:\n{0}").format(verbose_message) if verbose_message is not None else ""
        #: Appended directly to the first and second error string if file indeces were provided for the error
        error_string_2 = self.tr("\n\nThe following file ID(s) raised this error:\n{0}").format(QtCore.QLocale().createSeparatedList([str(number) for number in file_indeces])) if len(file_indeces) > 0 else ""

        QtWidgets.QMessageBox.warning(
            self,
            #: Window Title.
            self.tr("An Error Has Occurred"),
            error_string_0 + error_string_1 + error_string_2,
        )



    def new_file(self):
        self.current_bg4_data = BG4Archive()
        #: Name for a newly created archive.
        self.update_name(self.tr("Untitled"))
        self.rebuild_tree_view()



    def update_name(self, name):
        self.current_bg4_name = name
        self.setWindowTitle(name)

    def set_version(self, version_index):
        set_property = BG4Archive.version_keyword
        version = BG4Archive.supported_versions[version_index]
        self.current_bg4_data.set_property(set_property, version)

    def toggle_property(self, set_property):
        checked = self.toggle_checkboxes[set_property].isChecked()
        self.current_bg4_data.set_property(set_property, checked)

    def import_archive_file(self):
        QtWidgets.QMessageBox.about(
            self,
            #: Window Title.
            self.tr("Select a BG4 Archive"),
            self.tr("Please select a BG4 Archive to import."),
        )

        primary_file, path = self._general_import_file()
        if primary_file is None:
            return

        self.current_bg4_data = BG4Archive()

        try:
            if self.current_bg4_data.archive_uses_single_file(primary_file):
                self.current_bg4_data.import_archive(primary_file)
                self.update_name(path.stem)
            else:
                header_name = path.stem
                data_name = header_name.removesuffix("_Header") + "_Data"
                secondary_path = path.with_stem(data_name)

                # i think this might be the funniest code to read that i've ever written
                not_exist = not os.path.exists(secondary_path)
                if not not_exist and not os.path.isfile(secondary_path):
                    not_exist = True

                if not_exist:
                    QtWidgets.QMessageBox.about(
                        self,
                        #: Window Title.
                        self.tr("Data File Needed"),
                        self.tr("Please select the BG4 Archive's Data section file."),
                    )

                    secondary_file, _ = self._general_import_file()
                    if secondary_file is None:
                        return
                else:
                    with open(secondary_path, "rb") as file:
                        secondary_file = file.read()

                self.current_bg4_data.import_archive(primary_file, secondary_file)
                self.update_name(header_name.removesuffix("_Header"))
        except BG4ArchiveError as e:
            self._throw_error(e.error_code, str(e), e.file_indeces)
        else:
            self.initialize_tree_view()
            self.rebuild_tree_view()

    def export_archive_file(self):
        path = Path("").resolve()

        key = BG4Archive.version_keyword
        version = self.current_bg4_data.get_property(key)
        warning = None
        match version:
            case 3:
                warning = self.tr("You are using Version 3 to export this archive. This is supported, but not recommended.\n\nSince file names are lost when exporting this way, other people will not be able to see file names when importing the archive.\n\nUsing Version 3 also means other programs may not be able to open this archive properly.")

        if warning is not None:
            QtWidgets.QMessageBox.warning(
                self,
                #: Window Title.
                self.tr("Export Settings Not Recommended"),
                warning,
            )

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            #: Window title.
            self.tr("Export File"),
            f"{path}/{self.current_bg4_name}.dat",
        )

        if path == '':
            return

        try:
            main_file, sub_file = self.current_bg4_data.export_archive()
        except BG4ArchiveError as e:
            self._throw_error(e.error_code, str(e), e.file_indeces)
        else:
            if sub_file is None:
                with open(path, "wb") as file:
                    file.write(main_file)
            else:
                path = Path(path)
                name = path.stem
                with open(path.with_stem(name + "_Header"), "wb") as file:
                    file.write(main_file)
                with open(path.with_stem(name + "_Data"), "wb") as file:
                    file.write(sub_file)

            QtWidgets.QMessageBox.about(
                self,
                #: Window Title.
                self.tr("Export Successful"),
                self.tr("{0} has been successfully exported!").format(self.current_bg4_name),
            )



    def tree_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)

        file = self.file_tree.itemAt(pos)
        if not file:
            item_name = ""
            item_type = "top"
        else:
            item_name = file.full_item_name
            item_type = file.item_type

        if item_type == "file": self.file_context_menu(item_name, menu)

        menu.exec(QtGui.QCursor.pos())

    def file_context_menu(self, item_name, menu):
        def replace_file():
            data, _ = self._general_import_file()
            if data is None:
                return
            self.current_bg4_data.set_file_data(item_name, data)

        def extract_file(item_name):
            data = self.current_bg4_data.get_uncompressed_file_contents(item_name)
            self._general_export_file(item_name, data)

        action_replace_file = QtGui.QAction(self.tr("Replace File Contents"), self)
        action_replace_file.triggered.connect(replace_file)
        menu.addAction(action_replace_file)

        if self.current_bg4_data.get_file_is_compressed(item_name):
            string = self.tr("Decompress and Extract")
        else:
            string = self.tr("Extract File Contents")

        action_extract_file = QtGui.QAction(string, self)
        action_extract_file.triggered.connect(partial(extract_file, item_name))
        menu.addAction(action_extract_file)



    def initialize_tree_view(self):
        self.file_tree.clear()

        top_parent = NumericTreeItem(self.file_tree)
        top_parent.full_item_name = ""
        top_parent.item_type = "top"

    def rebuild_tree_view(self):
        key = BG4Archive.version_keyword
        version = self.current_bg4_data.get_property(key)
        version_index = BG4Archive.supported_versions.index(version)

        self.version_selector.blockSignals(True)
        self.version_selector.setCurrentIndex(version_index)
        self.version_selector.blockSignals(False)

        for key, checkbox in self.toggle_checkboxes.items():
            toggle_state = self.current_bg4_data.get_property(key)
            checkbox.setChecked(toggle_state)

        top_parent = self.file_tree.topLevelItem(0)
        files = self.current_bg4_data.files.copy()
        for i, file_data in enumerate(files):
            file = file_data["name_hash"] if file_data["file_name"] is None else file_data["file_name"]
            directory = file.split('/') if isinstance(file, str) else [str(file)]

            current_parent = top_parent
            target_file_id = len(directory) - 1
            full_directory_name = ""
            for j, folder in enumerate(directory):
                has_folder_already = False

                if full_directory_name != "":
                    full_directory_name += "/"
                full_directory_name += folder

                for k in range(current_parent.childCount()):
                    child = current_parent.child(k)
                    if child.full_item_name == full_directory_name:
                        has_folder_already = True
                        current_parent = child
                        break

                if not has_folder_already:
                    current_parent = NumericTreeItem(current_parent)
                    current_parent.full_item_name = full_directory_name if isinstance(file, str) else file
                    current_parent.item_type = "file" if j == target_file_id else "folder"
                    current_parent.needs_to_be_deleted = False

        self.update_tree_view()

    def update_tree_view(self):
        iterator = QtWidgets.QTreeWidgetItemIterator(self.file_tree)
        selected_item = None
        while iterator.value():
            item = iterator.value()

            name = item.full_item_name
            content = [name.split('/')[-1]] if isinstance(name, str) else [str(name)]
            if name == "":
                content[0] = self.current_bg4_name

            if item.item_type == "file":
                index = self.current_bg4_data.get_file_id_by_name_or_hash(name)
                content.append(str(index))

            self.file_tree.blockSignals(True)
            [item.setText(i, text) for i, text in enumerate(content)]

            match item.item_type:
                case "folder":
                    item.setIcon(0, self.icons["folder"])
                case "file":
                    if self.current_bg4_data.get_file_is_compressed(name):
                        item.setIcon(0, self.icons["blz"])
                    else:
                        item.setIcon(0, self.icons["file"])
                case _:
                    item.setIcon(0, self.icons["main"])
            self.file_tree.blockSignals(False)

            iterator += 1

        self.file_tree.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
        if selected_item is not None:
            self.file_tree.setCurrentItem(selected_item)



    def _general_import_file(self, path = None):
        if path is None:
            path = Path("").resolve()

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            #: Window Title
            self.tr("Import File"),
            str(path.resolve()),
        )

        if path == '':
            return None, None

        with open(path, "rb") as file:
            data = file.read()

        return data, Path(path)

    def _general_export_file(self, file_name, data, path = None):
        if path is None:
            path = Path("").resolve()

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            #: Window title.
            self.tr("Export File"),
            f"{path}/{file_name}",
        )

        if path == '':
            return

        with open(path, "wb") as file:
            file.write(data)

    def _grab_icon(self, file_path, index, icon_size):
        if index == 0:
            if icon_size is None:
                icon = QtGui.QPixmap(str(FILES_DIR / f'{file_path}.png'))
            else:
                icon = QtGui.QPixmap(*icon_size)
            icon.fill(QtCore.Qt.transparent)
            return icon

        icon_sheet = QtGui.QPixmap(str(FILES_DIR / f'{file_path}.png'))

        if icon_size is None:
            icon = icon_sheet
        else:
            num_columns = icon_sheet.width() // icon_size[0]

            index -= 1
            x = (index % num_columns) * icon_size[0]
            y = (index // num_columns) * icon_size[1]

            img_rect = QtCore.QRect(x, y, *icon_size)
            icon = icon_sheet.copy(img_rect)

        return icon



class NumericTreeItem(QtWidgets.QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        text_self = self.text(column)
        text_other = other.text(column)
        
        try:
            return int(text_self) < int(text_other)
        except ValueError:
            return text_self < text_other