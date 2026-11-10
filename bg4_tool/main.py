import os
import sys
from functools import partial
from pathlib import Path

from PySide6 import QtWidgets, QtGui, QtCore

from bg4_tool.classes import BinGluArchive, BinGluError
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


# TODO: display file ID number next to file
# TODO: be able to drag and drop files to reorganize and move between folders
# TODO: be able to drop archives onto the window to import them
# TODO: check all files during import for whether there are nested archive files
#       DO NOT ALLOW THE USER TO SWAP A FOLDER FOR AN ARCHIVE IN THE PROGRAM, only deal with that semantic difference when saving and/or loading an archive from a folder on the user's pc
#       don't bother checking for a data component for a two-file header, just display it as a nested folder
#       if data component isn't found, disallow any data-related changing for nested files, inform the user that they need to save the parent archive first (at which point it'll ask the user to identify the data chunk during saving)
#       if data is changed in any nested files, extract and import the archive file as a new object, change the file data in it, and export it back into the parent archive's data
#       file ID number should be identical to its parent in the same column, and make a new column for sub-numbers within the archive
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(MainWindow, self).__init__()

        self.current_binglu_data = None
        self.current_save_path = None

        self.current_binglu_name = ""
        self.current_binglu_saved = True

        self._update_window_title()

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

        self.menu_bar_file_save = QtGui.QAction("save", self)
        self.menu_bar_file_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.menu_bar_file_save.triggered.connect(self.save_file)
        self.menu_bar_file.addAction(self.menu_bar_file_save)

        self.menu_bar_file_save_as = QtGui.QAction("save as", self)
        self.menu_bar_file_save_as.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        self.menu_bar_file_save_as.triggered.connect(partial(self.save_file, True))
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
        self.version_selector.addItems([str(i) for i in BinGluArchive.supported_versions])
        self.version_selector.currentIndexChanged.connect(self.set_version)
        main_layout.addWidget(self.version_selector_text, 0, 0)
        main_layout.addWidget(self.version_selector, 1, 0)

        checkboxes = QtWidgets.QWidget()
        checkboxes_layout = QtWidgets.QVBoxLayout(checkboxes)
        checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(checkboxes, 2, 0)

        toggles = [
            BinGluArchive.single_file_keyword,
            BinGluArchive.preserve_order_keyword,
        ]

        self.toggle_checkboxes = {}
        for toggle in toggles:
            checkbox = QtWidgets.QCheckBox()
            checkboxes_layout.addWidget(checkbox)

            checkbox.clicked.connect(partial(self.toggle_property, toggle))

            self.toggle_checkboxes[toggle] = checkbox

        self.file_tree = QtWidgets.QTreeWidget()
        self.file_tree.setColumnCount(1)
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
                self.tr("Compact Binary Search"),
                self.tr("Uses binary searching to quickly sort through every file's name hash. Does not store file names, and fails to export if two file names share a hash."),
            ],
            4: [
                self.tr("Quick Name Lookup"),
                self.tr("Uses search buckets to narrow down the file being searched for extremely quickly. Stores file names in case two names share a hash."),
            ],
            5: [
                self.tr("Safe Binary Search"),
                self.tr("Uses binary searching to sort through every file's name hash. Stores file names in case two names share a hash."),
            ],
        }

        for i, version in enumerate(BinGluArchive.supported_versions):
            name_string, desc_string = versions[version]
            self.version_selector.setItemText(i, self.tr("Version {0}: {1}").format(version, name_string))
            self.version_selector.setItemData(i, desc_string, QtCore.Qt.ItemDataRole.ToolTipRole)

        toggles = {
            BinGluArchive.single_file_keyword: [
                self.tr("Export Single File"),
                self.tr("Disabling this will split the archive into a '_Header' file and a '_Data' file. Lowers RAM overhead for extremely large archives."),
            ],
            BinGluArchive.preserve_order_keyword: [
                self.tr("Preserve File Order"),
                self.tr("Creates an additional table that tracks the index of each file in the archive. Necessary for archives that can use an index to find a file."),
            ],
        }

        for key, checkbox in self.toggle_checkboxes.items():
            name_string, desc_string = toggles.get(key, ["", ""])
            checkbox.setText(name_string)
            checkbox.setToolTip(desc_string)
        
        self.file_tree.setHeaderLabels([self.tr("File Tree")])

    def _set_program_icons(self):
        icon_path = "img_icons_dx"
        self.icons = {
            "main":   self._grab_icon(icon_path, 1, (16, 16)),
            "folder": self._grab_icon(icon_path, 2, (16, 16)),
            "file":   self._grab_icon(icon_path, 3, (16, 16)),
            "blz":    self._grab_icon(icon_path, 4, (16, 16)),
        }

    def _throw_error(self, error_code, error_message, file_indices):
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
        #: Appended directly to the first and second error string if file indices were provided for the error
        error_string_2 = self.tr("\n\nThe following file ID(s) raised this error:\n{0}").format(QtCore.QLocale().createSeparatedList([str(number) for number in file_indices])) if len(file_indices) > 0 else ""

        QtWidgets.QMessageBox.warning(
            self,
            #: Window Title.
            self.tr("An Error Has Occurred"),
            error_string_0 + error_string_1 + error_string_2,
        )



    def new_file(self):
        self.current_binglu_data = BinGluArchive()
        #: Name for a newly created archive.
        self._update_name(self.tr("Untitled"))
        self._update_saved(True)
        self.rebuild_tree_view()

    def save_file(self, force_try = False):
        # TODO: do header yamls
        if (self.current_save_path is None) or force_try:
            folder = self._general_select_folder(Path(self.current_binglu_name))
            if folder is None:
                return
        else:
            folder = self.current_save_path

        folder_path = Path(folder)

        # gather all saved file names
        archive_file_names = self._gather_archive_file_names(self.current_binglu_data)

        # ensure the directory is empty (not including ignored files), as long as it is not already either identical to the current archive, or already being worked on
        for file in folder_path.rglob("*"):
            relative_string = str(file.relative_to(folder_path))
            file_is_ignored = relative_string[0] == "."
            if self.current_save_path != folder_path and file.is_file() and not file_is_ignored and not relative_string in archive_file_names:
                QtWidgets.QMessageBox.warning(
                    self,
                    #: Window Title.
                    self.tr("Directory Not Empty"),
                    self.tr("Please choose an empty directory to save project to."),
                )
                return

        # write individual files
        for i, file in enumerate(archive_file_names):
            file_data = self.current_binglu_data.get_uncompressed_file_contents(i, is_by_index = True)
            with open(folder_path / file, "wb") as file_path:
                file_path.write(file_data)

        self.current_save_path = folder_path
        self._update_name(folder_path.stem)
        self._update_saved(True)
        self.rebuild_tree_view()

    def _gather_archive_file_names(self, archive):
        archive_file_names = []
        for i, file in enumerate(archive.files):
            if file["file_name"] is not None:
                archive_file_names.append(file["file_name"])
            elif file["name_hash"] is not None:
                archive_file_names.append(f"(hash;{file["name_hash"]:08X})")
            else:
                archive_file_names.append(f"(index;{i:04X})")
        return archive_file_names



    def _update_name(self, name):
        self.current_binglu_name = name
        self._update_window_title()

    # TODO: keep track of what was actually changed so the whole thing doesn't need to be saved every time (that includes file order changes for (index) files, and name updates for (hash) files)
    def _update_saved(self, saved):
        self.current_binglu_saved = saved
        self._update_window_title()

    def _update_window_title(self):
        name = self.current_binglu_name
        if not self.current_binglu_saved:
            name += "*"
        self.setWindowTitle(name)

    def set_version(self, version_index):
        set_property = BinGluArchive.version_keyword
        version = BinGluArchive.supported_versions[version_index]
        self.current_binglu_data.set_property(set_property, version)
        self._update_saved(False)

    def toggle_property(self, set_property):
        checked = self.toggle_checkboxes[set_property].isChecked()
        self.current_binglu_data.set_property(set_property, checked)
        self._update_saved(False)

    def import_archive_file(self):
        QtWidgets.QMessageBox.about(
            self,
            #: Window Title.
            self.tr("Select an Archive"),
            self.tr("Please select an archive to import."),
        )

        primary_file, path = self._general_import_file()
        if primary_file is None:
            return

        self.current_binglu_data, name = self._import_archive_file(primary_file, path)
        self._update_name(name)

        self.current_save_path = None
        self._update_saved(False)
        self.initialize_tree_view()
        self.rebuild_tree_view()

    def _import_archive_file(self, primary_file, path):
        archive_data = BinGluArchive()
        try:
            if archive_data.archive_uses_single_file(primary_file):
                archive_data.import_archive(primary_file)
                archive_name = path.stem
            else:
                QtWidgets.QMessageBox.about(
                    self,
                    #: Window Title.
                    self.tr("Data File Needed"),
                    self.tr("Please select the Data section file for archive '{0}'.").format(path.stem),
                )

                secondary_file, _ = self._general_import_file(path.parent)
                if secondary_file is None:
                    return

                archive_data.import_archive(primary_file, secondary_file)
                archive_name = str(path.stem).removesuffix("_Header")
        except BinGluError as e:
            self._throw_error(e.error_code, str(e), e.file_indices)
        else:
            return archive_data, archive_name

    def export_archive_file(self):
        path = Path("").resolve()

        key = BinGluArchive.version_keyword
        version = self.current_binglu_data.get_property(key)
        warning = None
        match version:
            case 3:
                warning = self.tr("You are using Version 3 to export this archive. This is supported, but not recommended.\n\nSince file names are lost when exporting this way, you or other people will not be able to see file names when importing the archive.\n\nUsing Version 3 also means other programs may not be able to open this archive properly.")

        if warning is not None:
            QtWidgets.QMessageBox.warning(
                self,
                #: Window Title.
                self.tr("Export Settings Not Recommended"),
                warning,
            )

        key = BinGluArchive.single_file_keyword
        if self.current_binglu_data.get_property(key):
            path_0, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                #: Window title.
                self.tr("Export File"),
                f"{path}/{self.current_binglu_name}.dat",
            )

            if path_0 == '':
                return

            path_1 = None
        else:
            path_0, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                #: Window title.
                self.tr("Export File Header Section"),
                f"{path}/{self.current_binglu_name}_Header.dat",
            )

            if path_0 == '':
                return

            path_1, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                #: Window title.
                self.tr("Export File Data Section"),
                f"{path}/{self.current_binglu_name}_Data.dat",
            )

            if path_1 == '':
                return

        try:
            main_file, sub_file = self.current_binglu_data.export_archive()
        except BinGluError as e:
            self._throw_error(e.error_code, str(e), e.file_indices)

        with open(path_0, "wb") as file:
            file.write(main_file)
        if path_1 is not None:
            with open(path_1, "wb") as file:
                file.write(sub_file)

        QtWidgets.QMessageBox.about(
            self,
            #: Window Title.
            self.tr("Export Successful"),
            self.tr("{0} has been successfully exported!").format(self.current_binglu_name),
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
            self.current_binglu_data.set_file_data(item_name, data)
            self._update_saved(True)

        def extract_file(item_name):
            data = self.current_binglu_data.get_uncompressed_file_contents(item_name)
            self._general_export_file(item_name, data)

        action_replace_file = QtGui.QAction(self.tr("Replace File Contents"), self)
        action_replace_file.triggered.connect(replace_file)
        menu.addAction(action_replace_file)

        if self.current_binglu_data.get_file_is_compressed(item_name):
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
        key = BinGluArchive.version_keyword
        version = self.current_binglu_data.get_property(key)
        version_index = BinGluArchive.supported_versions.index(version)

        self.version_selector.blockSignals(True)
        self.version_selector.setCurrentIndex(version_index)
        self.version_selector.blockSignals(False)

        for key, checkbox in self.toggle_checkboxes.items():
            toggle_state = self.current_binglu_data.get_property(key)
            checkbox.setChecked(toggle_state)

        top_parent = self.file_tree.topLevelItem(0)
        files = self.current_binglu_data.files.copy()
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
                content[0] = self.current_binglu_name

            if item.item_type == "file":
                index = self.current_binglu_data.get_file_id_by_name_or_hash(name)
                content.append(str(index))

            self.file_tree.blockSignals(True)
            [item.setText(i, text) for i, text in enumerate(content)]

            match item.item_type:
                case "folder":
                    item.setIcon(0, self.icons["folder"])
                case "file":
                    if self.current_binglu_data.get_file_is_compressed(name):
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

    def _general_select_folder(self, path = None):
        if path is None:
            path = Path("").resolve()

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Folder"),
            str(path.resolve()),
            options = QtWidgets.QFileDialog.Option.ShowDirsOnly
        )

        if path == '':
            return
        
        return path

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