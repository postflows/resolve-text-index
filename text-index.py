#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ================================================
# Text Index
# Part of PostFlows toolkit for DaVinci Resolve
# https://github.com/postflows
# ================================================

"""
RMT Text Index Tool v16
=======================

A comprehensive text management solution for DaVinci Resolve

Key Features:
-------------
- Unified text element management:
  - Text+ clips
  - Subtitles (track-based)
  - MultiText layers
  - Rich text from third-party formats

- Advanced Editing:
  - In-place text editing with multi-line support
  - Dedicated text editor panel
  - Smart text navigation (jump to source position)

- Professional Tools:
  - Dual spelling engines (Yandex/LanguageTool)
  - Regex-powered search with multiple modes
  - Find and Replace functionality
  - CSV Export/Import: export Text+/MultiText/Subtitles to CSV, edit externally,
    import back with one-click apply (tree update + timeline write for all types)
  - Frame-accurate timecode handling
  - Fractional FPS support (23.98, 29.97, 59.94)
  - Timeline offset compensation
  - Subtitle cleanup: remove punctuation and change case (UPPER/lower/Title/Sentence)

Editing Shortcuts:
-----------------
[Enter]       Confirm edit
[Ctrl+Enter]  Insert line break
[Esc]         Cancel editing
[Ctrl+F]      Focus search
[Ctrl+S]      Apply changes in editor
[Double-click] Navigate to clip

Version 16 Changes:
------------------
- CSV Export/Import: full round-trip for Text+, MultiText, Subtitle
  - Export: unique_id, element_type, original/edited text, timings, track/clip/comp/node IDs
  - Import dialog: Browse, preview, type filters (Subtitle/Text+/MultiText), modes Load/Apply
  - Apply mode: updates tree + applies Text+/MultiText to timeline + regenerates subtitle track
- Removed Ctrl+H shortcut (conflicted with system commands). Use button to show Find & Replace.

Required Dependencies:
---------------------
- Python 3.6+ (recommended: Python 3.8+) — Resolve uses its bundled Python
- PySide6 (GUI framework) — pip install PySide6
- requests (HTTP requests for spelling API) — pip install requests
- Standard library (no install): sys, os, datetime, fractions, tempfile, csv,
  re, shutil, webbrowser, xml.etree.ElementTree
- DaVinci Resolve API (provided by Resolve when script runs)
See INSTALL_DEPENDENCIES.md in this folder for installation instructions.

Development Info:
----------------
- Version: 16.0.0
- Last Updated: February 2025
- License: MIT
- Author: Sergey Knyazkov

"""
import sys
import os
from datetime import datetime
import fractions
import requests
import tempfile
import csv
import re
import shutil
import webbrowser
from xml.etree import ElementTree as ET
from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                              QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, 
                              QComboBox, QLineEdit, QTabWidget, QTextEdit, QCheckBox, QDialog, 
                              QDialogButtonBox, QFileDialog, QMessageBox, QGroupBox, 
                              QStyledItemDelegate, QMenu, QProgressBar, QRadioButton, QButtonGroup,
                              QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal, QThread, QEvent
from PySide6.QtGui import QTextDocument, QTextOption, QShortcut, QKeySequence, QColor

# Debugging onoff
original_print = print
def noprint(*args, **kwargs):
    pass

DEBUG = False
if not DEBUG:
    print = noprint

# Initialize Resolve API
try:
    fusion = resolve.Fusion()
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    media_pool = project.GetMediaPool()
    timeline = project.GetCurrentTimeline()
    timeline_fps = float(project.GetSetting("timelineFrameRate") or "25") if project else 25.0
except Exception as e:
    print(f"Error initializing Resolve API: {e}")
    resolve = None
    timeline_fps = 25.0
class SMPTE(object):
    '''Frames to SMPTE timecode converter and reverse.'''

    def __init__(self):
        self.fps = 24
        self.df  = False

    def getframes(self, tc):
        '''Converts SMPTE timecode to frame count.'''

        if int(tc[9:]) > self.fps:
            raise ValueError ('SMPTE timecode to frame rate mismatch.', tc, self.fps)

        hours   = int(tc[:2])
        minutes = int(tc[3:5])
        seconds = int(tc[6:8])
        frames  = int(tc[9:])

        totalMinutes = int(60 * hours + minutes)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:
            dropFrames = int(round(self.fps * 0.066666))
            timeBase   = int(round(self.fps))
            hourFrames   = int(timeBase * 60 * 60)
            minuteFrames = int(timeBase * 60)
            frm = int(((hourFrames * hours) + (minuteFrames * minutes) + (timeBase * seconds) + frames) - (dropFrames * (totalMinutes - (totalMinutes // 10))))
        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            frm = int((totalMinutes * 60 + seconds) * self.fps + frames)

        return frm

    def gettc(self, frames):
        '''Converts frame count to SMPTE timecode.'''

        frames = abs(frames)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:
            spacer = ':'
            spacer2 = ';'
            dropFrames         = int(round(self.fps * .066666))
            framesPerHour      = int(round(self.fps * 3600))
            framesPer24Hours   = framesPerHour * 24
            framesPer10Minutes = int(round(self.fps * 600))
            framesPerMinute    = int(round(self.fps) * 60 - dropFrames)

            frames = frames % framesPer24Hours
            d = frames // framesPer10Minutes
            m = frames % framesPer10Minutes

            if m > dropFrames:
                frames = frames + (dropFrames * 9 * d) + dropFrames * ((m - dropFrames) // framesPerMinute)
            else:
                frames = frames + dropFrames * 9 * d

            frRound = int(round(self.fps))
            hr = int(frames // frRound // 60 // 60)
            mn = int((frames // frRound // 60) % 60)
            sc = int((frames // frRound) % 60)
            fr = int(frames % frRound)
        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            spacer  = ':'
            spacer2 = spacer
            frHour = self.fps * 3600
            frMin  = self.fps * 60

            hr = int(frames // frHour)
            mn = int((frames - hr * frHour) // frMin)
            sc = int((frames - hr * frHour - mn * frMin) // self.fps)
            fr = int(round(frames -  hr * frHour - mn * frMin - sc * self.fps))

        # Return SMPTE timecode string.
        return(
                str(hr).zfill(2) + spacer +
                str(mn).zfill(2) + spacer +
                str(sc).zfill(2) + spacer2 +
                str(fr).zfill(2)
                )
class TextEditDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree_widget = parent
        
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        if index.column() in [2, 3]:
            text = index.model().data(index, Qt.DisplayRole)
            if text:
                doc = QTextDocument()
                doc.setPlainText(text)
                doc.setDefaultFont(option.font)
                width = self.tree_widget.columnWidth(index.column()) - 20
                doc.setTextWidth(width)
                height = doc.size().height() + 10
                size.setHeight(int(max(height, 30)))
        return size

    def createEditor(self, parent, option, index):
        if index.column() not in [2, 3]:
            return None
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        editor.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        editor.setPlainText(value)

    def setModelData(self, editor, model, index):
        new_text = editor.toPlainText()
        if index.column() == 2:
            model.setData(index, new_text, Qt.DisplayRole)
            
            if self.tree_widget and hasattr(self.tree_widget, 'all_clips'):
                clip_type = model.data(model.index(index.row(), 0), Qt.DisplayRole)
                timecode = model.data(model.index(index.row(), 1), Qt.DisplayRole)
                
                for clip in self.tree_widget.all_clips:
                    current_timecode = (
                        self.tree_widget.frames_to_timecode(clip["start_frame"], clip["framerate"])
                        if "start_frame" in clip
                        else clip.get("start_timecode", "")
                    )
                    if current_timecode == timecode and clip["type"] == clip_type:
                        clip["edited_text"] = new_text
                        if clip_type == "Text+":
                            self.tree_widget.update_text_plus_clip(clip)
                        break

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def eventFilter(self, editor, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() == Qt.NoModifier:
                    self.commitData.emit(editor)
                    self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
                    return True
            
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
                    editor.insertPlainText("\n")
                    return True
            
            elif event.key() == Qt.Key_Escape:
                self.closeEditor.emit(editor, QStyledItemDelegate.RevertModelCache)
                return True
            
            elif event.key() == Qt.Key_Tab:
                self.commitData.emit(editor)
                self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
                tree_widget = self.tree_widget
                if tree_widget:
                    current_item = tree_widget.currentItem()
                    if current_item:
                        next_item = tree_widget.itemBelow(current_item)
                        if next_item:
                            tree_widget.editItem(next_item, 2)
                return True
        
        return False

class SpellCheckerThread(QThread):
    """Thread for spell-checking"""
    progress = Signal(int, int)  
    finished = Signal(list)  
    error = Signal(str)  

    def __init__(self, clips, spelling_service, language):
        super().__init__()
        self.clips = clips
        self.spelling_service = spelling_service
        self.language = language

    def run(self):
        try:
            checked_clips = []
            total_clips = len(self.clips)
            
            for i, clip in enumerate(self.clips):
                try:
                    if self.spelling_service == "Yandex Speller":
                        clip["spelling_errors"] = self.check_spelling_yandex(clip["text"], lang="ru")
                    else:
                        clip["spelling_errors"] = self.check_spelling_languagetool(clip["text"], lang=self.language)
                    clip["is_checked"] = True
                    checked_clips.append(clip)
                    self.progress.emit(i + 1, total_clips)
                except Exception as e:
                    print(f"Error checking clip: {str(e)}")
                    continue
                    
            self.finished.emit(checked_clips)
        except Exception as e:
            self.error.emit(str(e))

    def check_spelling_yandex(self, text, lang="ru"):
        url = "http://speller.yandex.net/services/spellservice.json/checkText"
        params = {"text": text, "lang": lang, "options": 6, "format": "plain"}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Yandex Speller error: {str(e)}")
        return []

    def check_spelling_languagetool(self, text, lang="Auto-Detect"):
        url = "https://api.languagetool.org/v2/check"
        data = {"text": text, "textType": "SUBTITLE", "disabledRules": "UPPERCASE_SENTENCE_START", "level": "default"}
        if lang and lang != "Auto-Detect":
            data["language"] = lang
        else:
            data["language"] = "auto"
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                errors = []
                for match in result.get("matches", []):
                    if match.get("ruleId") != "UPPERCASE_SENTENCE_START":
                        error = {
                            "word": match["context"]["text"][match["context"]["offset"]:match["context"]["offset"] + match["context"]["length"]],
                            "s": [replacement["value"] for replacement in match.get("replacements", [])[:1]]
                        }
                        errors.append(error)
                return errors
        except Exception as e:
            print(f"LanguageTool error: {str(e)}")
        return []
class PunctuationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clean Punctuation and Change Case")
        self.setMinimumSize(400, 400)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2A2A2A;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 15px;
                padding: 5px;
            }
            QCheckBox {
                color: #CCCCCC;
                font-size: 13px;
                padding: 5px;
                min-height: 30px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid #666666;
                border-radius: 3px;
                background-color: #2A2A2A;
            }
            QCheckBox::indicator:checked {
                background-color: #FF0000;
                border: 1px solid #E3E3E3;
            }
            QCheckBox::indicator:hover {
                border-color: #c0c0c0;
            }
            QGroupBox {
                color: #CCCCCC;
                font-size: 14px;
                border: 1px solid #666666;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QRadioButton {
                color: #CCCCCC;
                font-size: 13px;
                padding: 5px;
                min-height: 28px;
            }
            QPushButton {
                background-color: #3A3A3A;
                color: #CCCCCC;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #454545;
            }
        """)
        
        layout = QVBoxLayout(self)
        info_label = QLabel("Changes apply to subtitles only")
        layout.addWidget(info_label)
        
        self.checkboxes = {
            "Dots (.)": QCheckBox(" Dots (.)"),
            "Commas (,)": QCheckBox(" Commas (,)"),
            "Exclamation Marks (!)": QCheckBox(" Exclamation Marks (!)"),
            "Question Marks (?)": QCheckBox(" Question Marks (?)"),
            "Colons (:)": QCheckBox(" Colons (:)"),
            "Semicolons (;)": QCheckBox(" Semicolons (;)")
        }
        self.checkboxes["Dots (.)"].setChecked(True)
        self.checkboxes["Commas (,)"].setChecked(True)
        for checkbox in self.checkboxes.values():
            layout.addWidget(checkbox)
        
        case_group = QGroupBox("Change Case Mode")
        case_layout = QVBoxLayout(case_group)
        self.case_button_group = QButtonGroup(case_group)
        self.case_radio_none = QRadioButton("No change (default)")
        self.case_radio_upper = QRadioButton("UPPERCASE")
        self.case_radio_lower = QRadioButton("lowercase")
        self.case_radio_title = QRadioButton("Title Case (Each Word)")
        self.case_radio_sentence = QRadioButton("Sentence case (First letter)")
        self.case_radio_none.setChecked(True)
        self.case_button_group.addButton(self.case_radio_none, 0)
        self.case_button_group.addButton(self.case_radio_upper, 1)
        self.case_button_group.addButton(self.case_radio_lower, 2)
        self.case_button_group.addButton(self.case_radio_title, 3)
        self.case_button_group.addButton(self.case_radio_sentence, 4)
        case_layout.addWidget(self.case_radio_none)
        case_layout.addWidget(self.case_radio_upper)
        case_layout.addWidget(self.case_radio_lower)
        case_layout.addWidget(self.case_radio_title)
        case_layout.addWidget(self.case_radio_sentence)
        layout.addWidget(case_group)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Apply")
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
    
    def get_selected_punctuation(self):
        return [key.split("(")[1][:-1] for key, cb in self.checkboxes.items() if cb.isChecked()]
    
    def get_selected_case_mode(self):
        checked_id = self.case_button_group.checkedId()
        return checked_id


class CSVImportDialog(QDialog):
    """Dialog for importing text changes from CSV file."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_editor = parent
        self.import_data = {}
        self.file_path = ""
        self.setWindowTitle("Import from CSV")
        self.setMinimumWidth(550)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # File selection
        file_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.on_browse)
        self.path_label = QLabel("No file selected")
        self.path_label.setStyleSheet("color: #888;")
        file_layout.addWidget(self.browse_btn)
        file_layout.addWidget(self.path_label, 1)
        layout.addLayout(file_layout)

        # Delimiter selector (for Numbers/Excel compatibility)
        delim_layout = QHBoxLayout()
        delim_layout.addWidget(QLabel("Delimiter:"))
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems(["Comma (,)", "Semicolon (;)", "Tab", "Pipe (|)", "Auto-detect"])
        self.delimiter_combo.setCurrentText("Auto-detect")
        self.delimiter_combo.setMinimumWidth(130)
        self.delimiter_combo.setToolTip("Numbers/Excel often use Semicolon. Auto-detect tries to guess from file.")
        self.delimiter_combo.currentTextChanged.connect(self._on_options_changed)
        delim_layout.addWidget(self.delimiter_combo)
        delim_layout.addStretch()
        layout.addLayout(delim_layout)

        # Text column selector
        col_layout = QHBoxLayout()
        col_layout.addWidget(QLabel("Text column:"))
        self.text_column_combo = QComboBox()
        self.text_column_combo.addItems(["edited_text", "original_text"])
        self.text_column_combo.setMinimumWidth(150)
        self.text_column_combo.currentTextChanged.connect(self._on_options_changed)
        col_layout.addWidget(self.text_column_combo)
        col_layout.addStretch()
        layout.addLayout(col_layout)

        # Type filters (default: Text+ only)
        filter_group = QGroupBox("Apply to")
        filter_layout = QVBoxLayout()
        self.cb_subtitles = QCheckBox("Subtitles")
        self.cb_textplus = QCheckBox("Text+")
        self.cb_textplus.setChecked(True)
        self.cb_multitext = QCheckBox("MultiText")
        filter_layout.addWidget(self.cb_subtitles)
        filter_layout.addWidget(self.cb_textplus)
        filter_layout.addWidget(self.cb_multitext)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Stats
        self.stats_label = QLabel("Load CSV file to see stats")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(180)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("Preview (first 15 rows):"))
        layout.addWidget(self.preview_table)

        # Mode
        mode_group = QGroupBox("Import mode")
        mode_layout = QVBoxLayout()
        self.mode_interface = QRadioButton("Load to interface only (update tree, no timeline write)")
        self.mode_apply = QRadioButton("Apply immediately (update tree + apply Text+/MultiText + Subtitles to timeline)")
        self.mode_interface.setChecked(True)
        self.mode_interface.toggled.connect(self._update_action_button_text)
        self.mode_apply.toggled.connect(self._update_action_button_text)
        mode_layout.addWidget(self.mode_interface)
        mode_layout.addWidget(self.mode_apply)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Buttons (single action button, text depends on mode)
        btn_layout = QHBoxLayout()
        self.action_btn = QPushButton("Import & Load")
        self.action_btn.clicked.connect(self.on_action)
        self.action_btn.setEnabled(False)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.action_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self._update_action_button_text()

    def _get_delimiter(self):
        """Return delimiter character for CSV parsing. None = auto-detect."""
        label = self.delimiter_combo.currentText()
        m = {"Comma (,)": ",", "Semicolon (;)": ";", "Tab": "\t", "Pipe (|)": "|"}
        return m.get(label)

    def _on_options_changed(self):
        """Re-parse CSV when delimiter or text column changes."""
        if not self.file_path:
            return
        text_col = self.text_column_combo.currentText()
        delim = self._get_delimiter()
        import_data, err = self.parent_editor.parse_import_csv(self.file_path, text_col, delimiter=delim)
        if err:
            return
        self.import_data = import_data
        self._update_preview()
        self._update_stats()

    def get_type_filters(self):
        filters = set()
        if self.cb_subtitles.isChecked():
            filters.add("Subtitle")
        if self.cb_textplus.isChecked():
            filters.add("Text+")
        if self.cb_multitext.isChecked():
            filters.add("MultiText")
        return filters

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        self.file_path = path
        self.path_label.setText(path)
        self.path_label.setStyleSheet("")
        text_col = self.text_column_combo.currentText()
        delim = self._get_delimiter()
        import_data, err = self.parent_editor.parse_import_csv(path, text_col, delimiter=delim)
        if err:
            QMessageBox.warning(self, "CSV Error", err)
            self.import_data = {}
            self.preview_table.setRowCount(0)
            self.stats_label.setText("Error loading CSV")
            return
        self.import_data = import_data
        self._update_preview()
        self._update_stats()
        self.action_btn.setEnabled(True)

    def _update_preview(self):
        if not self.import_data:
            self.preview_table.setRowCount(0)
            return
        rows = list(self.import_data.items())[:15]
        self.preview_table.setRowCount(len(rows))
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["unique_id", "element_type", "original_text", "edited_text"])
        for i, (uid, data) in enumerate(rows):
            self.preview_table.setItem(i, 0, QTableWidgetItem(uid[:40] + ("..." if len(uid) > 40 else "")))
            self.preview_table.setItem(i, 1, QTableWidgetItem(data.get("element_type", "")))
            orig = str(data.get("original_text", ""))[:30]
            self.preview_table.setItem(i, 2, QTableWidgetItem(orig + ("..." if len(orig) >= 30 else "")))
            new_t = str(data.get("new_text", ""))[:30]
            self.preview_table.setItem(i, 3, QTableWidgetItem(new_t + ("..." if len(new_t) >= 30 else "")))
        self.preview_table.resizeColumnsToContents()

    def _update_stats(self):
        filters = self.get_type_filters()
        if not filters:
            self.stats_label.setText("Select at least one type to apply")
            return
        matched, not_found = self.parent_editor.match_clips_with_import(self.import_data, filters)
        counts = {"Subtitle": 0, "Text+": 0, "MultiText": 0}
        for clip, _ in matched:
            t = clip.get("type", "")
            if t in counts:
                counts[t] += 1
        parts = [f"Found: {counts['Subtitle']} Subs, {counts['Text+']} Text+, {counts['MultiText']} MultiText"]
        if not_found:
            parts.append(f"Not found: {len(not_found)}")
        self.stats_label.setText(" | ".join(parts))

    def _update_action_button_text(self):
        """Update action button text based on selected mode."""
        if self.mode_apply.isChecked():
            self.action_btn.setText("Import & Apply")
        else:
            self.action_btn.setText("Import & Load")

    def on_action(self):
        """Single action: Load or Apply depending on selected mode."""
        apply_to_timeline = self.mode_apply.isChecked()
        if self._do_import(apply_to_timeline=apply_to_timeline):
            if apply_to_timeline:
                self.accept()
            else:
                self.action_btn.setEnabled(False)

    def _do_import(self, apply_to_timeline):
        if not self.import_data:
            QMessageBox.warning(self, "Import", "Load a CSV file first")
            return False
        filters = self.get_type_filters()
        if not filters:
            QMessageBox.warning(self, "Import", "Select at least one type to apply")
            return False
        matched, not_found = self.parent_editor.match_clips_with_import(self.import_data, filters)
        if not matched:
            QMessageBox.information(self, "Import", "No matching clips found")
            return False
        for clip, new_text in matched:
            clip["edited_text"] = new_text
            if apply_to_timeline and clip.get("type") in ("Text+", "MultiText"):
                self.parent_editor.update_text_plus_clip(clip)
        self.parent_editor.populate_tree(self.parent_editor.all_clips)
        if apply_to_timeline:
            matched_subs = [c for c, _ in matched if c.get("type") == "Subtitle"]
            if matched_subs:
                self.parent_editor.on_apply_changes()  # Creates SRT, imports to new subtitle track
            else:
                self.parent_editor.status_bar.setText(f"Imported {len(matched)} items (applied to timeline)")
        else:
            self.parent_editor.status_bar.setText(f"Imported {len(matched)} items")
        return True


class SubtitleEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.all_clips = []
        self.filtered_clips = []
        self.clip_to_item_map = {}
        self.selected_type_filter = "All"
        self.selected_spelling_service = "LanguageTool"
        self.search_mode = "Contains"
        self.editing_enabled = False
        self.timeline_fps = self.get_timeline_fps() 
        self.spell_checker = None
        self.smpte = SMPTE()
        self.smpte.fps = self.get_timeline_fps()
        
        # New attributes for extended functionality
        self.current_editing_item = None
        self.replace_mode = False
        self.replace_history = []
        
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """Setup main interface"""
        self.setWindowTitle("RMT Text Index v16")
        self.setGeometry(300, 300, 600, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Set global style
        self.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #CCCCCC;
                border: 1px solid #666666;
                border-radius: 15px;
                padding: 5px 15px;
                font-size: 12px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #454545;
                color: #EEEEEE;
                border: 1px solid #E3E3E3;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #666666;
                border: 1px solid #222222;
            }
            QLineEdit {
                background-color: #2A2A2A;
                color: #CCCCCC;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
                min-height: 25px;
                max-width: 220px;
            }
            QLineEdit:focus {
                border: 1px solid #888888;
            }
            QComboBox {
                background-color: #393939;
                color: #CCCCCC;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
                min-height: 20px;
            }
            QGroupBox {
                color: #CCCCCC;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #666666;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ba5e29;
            }
            QProgressBar {
                border: 1px solid #666666;
                border-radius: 4px;
                background-color: #393939;
                color: #CCCCCC;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #ba5e29;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: none;
                background-color: #2A2A2A;
            }
            QTabBar::tab {
                background-color: #2A2A2A;
                color: #666666;
                border: none;
                padding: 8px 24px;
                margin-right: 4px;
                min-width: 120px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                color: #FB5041;
                background-color: #2A2A2A;
                border-bottom: 2px solid #FB5041;
            }
            QTabBar::tab:hover:!selected {
                color: #CCCCCC;
            }
        """)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Вкладка Text Index
        self.text_index_tab = QWidget()
        self.tab_widget.addTab(self.text_index_tab, "Text Index")
        self.setup_text_index_tab()
        
        # Вкладка Settings
        self.settings_tab = QWidget()
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.setup_settings_tab()
        
        # Статус бар
        self.status_bar = QLabel()
        self.status_bar.setAlignment(Qt.AlignCenter)
        self.status_bar.setStyleSheet("color: #c0c0c0; font-size: 12px; font-weight: bold; padding: 5px 0;")
        main_layout.addWidget(self.status_bar)
    def setup_text_index_tab(self):
        """Setup Text Index tab"""
        layout = QVBoxLayout(self.text_index_tab)
        layout.setSpacing(10)
        
        # Панель загрузки
        load_panel = QHBoxLayout()
        self.load_timeline_btn = QPushButton("Load Subtitles and Text+")
        self.load_fcpxml_btn = QPushButton("Load Rich Text clips")
        self.fcpxml_path = QLineEdit()
        self.fcpxml_path.setPlaceholderText("Use Load from FCPXML to get Rich Text clips")
        self.enable_edit_btn = QPushButton("Enable Editing")
        self.enable_edit_btn.setCheckable(True)
        
        load_panel.addWidget(self.load_timeline_btn)
        load_panel.addWidget(self.load_fcpxml_btn)
        load_panel.addWidget(self.enable_edit_btn)
        layout.addLayout(load_panel)
        
        # Таблица
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(4)
        self.tree_widget.setHeaderLabels(["Type", "Timecode", "Text Content", "Spelling"])
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setSortingEnabled(True)
        self.tree_widget.setWordWrap(True)  
        self.tree_widget.setColumnWidth(3, 300)
        
        self.tree_widget.setColumnWidth(0, 100)
        self.tree_widget.setColumnWidth(1, 100)
        self.tree_widget.setColumnWidth(2, 250)
        self.tree_widget.setColumnWidth(3, 150)
        
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #2A2A2A;
                border-radius: 5px;
                background-color: #2A2A2A;
                color: #ebebeb;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: #ebebeb;
                padding: 5px;
                border: 1px solid #2A2A2A;
            }
        """)
        
        delegate = TextEditDelegate(self.tree_widget)
        self.tree_widget.setItemDelegateForColumn(2, delegate)
        self.tree_widget.setItemDelegateForColumn(3, delegate)
        self.tree_widget.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed)
        
        layout.addWidget(self.tree_widget)
# ===== НОВАЯ ПАНЕЛЬ РЕДАКТИРОВАНИЯ =====
        self.edit_panel = QGroupBox("Text Editor")
        edit_layout = QVBoxLayout(self.edit_panel)
        
        # Информация о клипе
        info_layout = QHBoxLayout()
        self.edit_info_label = QLabel("No clip selected")
        self.edit_info_label.setStyleSheet("color: #c0c0c0; font-size: 12px;")
        info_layout.addWidget(self.edit_info_label)
        info_layout.addStretch()
        edit_layout.addLayout(info_layout)
        
        # Текстовое поле для редактирования
        self.edit_text_field = QTextEdit()
        self.edit_text_field.setPlaceholderText("Select a clip to edit its text here...")
        self.edit_text_field.setMaximumHeight(120)
        self.edit_text_field.setStyleSheet("""
            QTextEdit {
                background-color: #2A2A2A;
                color: #CCCCCC;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #888888;
            }
        """)
        edit_layout.addWidget(self.edit_text_field)
        
        # Кнопки управления
        edit_buttons = QHBoxLayout()
        self.apply_edit_btn = QPushButton("Apply Changes")
        self.revert_edit_btn = QPushButton("Revert")
        self.apply_edit_btn.setEnabled(False)
        self.revert_edit_btn.setEnabled(False)
        edit_buttons.addWidget(self.apply_edit_btn)
        edit_buttons.addWidget(self.revert_edit_btn)
        edit_buttons.addStretch()
        edit_layout.addLayout(edit_buttons)
        
        self.edit_panel.setVisible(False)
        layout.addWidget(self.edit_panel)
        # ===== КОНЕЦ ПАНЕЛИ РЕДАКТИРОВАНИЯ =====
# ===== УЛУЧШЕННАЯ ПАНЕЛЬ ПОИСКА =====
        search_panel = QVBoxLayout()
        
        # Первая строка: режим поиска и поле поиска
        search_line1 = QHBoxLayout()
        search_line1.addWidget(QLabel("Search:"))
        
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItems(["Contains", "Exact", "Starts With", "Ends With"])
        self.search_mode_combo.setMinimumWidth(125)
        search_line1.addWidget(self.search_mode_combo)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        self.search_input.setMinimumHeight(35)
        search_line1.addWidget(self.search_input)
        
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["All", "Text+", "Subtitle", "MultiText", "Text"])
        self.type_filter_combo.setMinimumWidth(100)
        search_line1.addWidget(self.type_filter_combo)
        
        self.search_btn = QPushButton("Search")
        self.reset_btn = QPushButton("Reset")
        search_line1.addWidget(self.search_btn)
        search_line1.addWidget(self.reset_btn)
        
        search_panel.addLayout(search_line1)
        
        # Вторая строка: Find and Replace
        self.replace_panel = QWidget()
        replace_layout = QHBoxLayout(self.replace_panel)
        replace_layout.setContentsMargins(0, 5, 0, 0)
        
        replace_layout.addWidget(QLabel("Replace:"))
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.setMinimumHeight(35)
        replace_layout.addWidget(self.replace_input)
        
        # Опции замены
        self.match_case_check = QCheckBox("Match case")
        self.match_case_check.setStyleSheet("color: #CCCCCC;")
        replace_layout.addWidget(self.match_case_check)
        
        # Кнопки замены
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")
        replace_layout.addWidget(self.replace_btn)
        replace_layout.addWidget(self.replace_all_btn)
        
        # Счетчик результатов
        self.replace_count_label = QLabel("")
        self.replace_count_label.setStyleSheet("color: #ba5e29; font-weight: bold;")
        replace_layout.addWidget(self.replace_count_label)
        
        # Кнопка истории (опционально)
        self.history_btn = QPushButton("📋")
        self.history_btn.setToolTip("View replace history")
        self.history_btn.setMaximumWidth(35)
        replace_layout.addWidget(self.history_btn)
        
        self.replace_panel.setVisible(False)
        search_panel.addWidget(self.replace_panel)
        
        # Кнопка переключения режима
        toggle_replace_layout = QHBoxLayout()
        self.toggle_replace_btn = QPushButton("▼ Show Find & Replace")
        self.toggle_replace_btn.setCheckable(True)
        self.toggle_replace_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                text-align: left;
                padding: 2px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #CCCCCC;
            }
            QPushButton:checked {
                color: #ba5e29;
            }
        """)
        toggle_replace_layout.addWidget(self.toggle_replace_btn)
        toggle_replace_layout.addStretch()
        search_panel.addLayout(toggle_replace_layout)
        
        layout.addLayout(search_panel)
        # ===== КОНЕЦ ПАНЕЛИ ПОИСКА =====
# Панель действий
        action_panel = QHBoxLayout()
        action_panel.setSpacing(8)
        action_panel.setContentsMargins(0, 12, 0, 12)
        
        self.add_markers_btn = QPushButton("Add Markers")
        self.check_spelling_btn = QPushButton("Check Spelling")
        self.clean_punctuation_btn = QPushButton("Subs Cleanup")
        self.apply_changes_btn = QPushButton("Apply Subs Changes")
        self.export_csv_btn = QPushButton("Export to CSV")
        self.import_csv_btn = QPushButton("Import from CSV")
        
        # Стиль для субтитровых кнопок
        dark_btn_style = '''
            QPushButton {
                background-color: #232323;
                color: #CCCCCC;
                border: 1px solid #444444;
                border-radius: 15px;
                padding: 5px 15px;
                font-size: 12px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #2A2A2A;
                color: #EEEEEE;
                border: 1px solid #666666;
            }
            QPushButton:pressed {
                background-color: #1A1A1A;
            }
        '''
        self.clean_punctuation_btn.setStyleSheet(dark_btn_style)
        self.apply_changes_btn.setStyleSheet(dark_btn_style)
        
        action_panel.addWidget(self.add_markers_btn)
        action_panel.addWidget(self.check_spelling_btn)
        action_panel.addWidget(self.clean_punctuation_btn)
        action_panel.addWidget(self.apply_changes_btn)
        action_panel.addWidget(self.export_csv_btn)
        action_panel.addWidget(self.import_csv_btn)
        
        self.tree_widget.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)       
        layout.addLayout(action_panel)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    def setup_settings_tab(self):
        """Setup Settings tab with improved layout"""
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addSpacing(20)

        # Настройки проверки орфографии
        spelling_group = QGroupBox("Spelling Settings")
        spelling_layout = QVBoxLayout(spelling_group)
        spelling_layout.setContentsMargins(15, 15, 15, 15)
        
        spelling_panel = QHBoxLayout()
        spelling_panel.addWidget(QLabel("Spelling Service:"))
        self.spelling_service_combo = QComboBox()
        self.spelling_service_combo.addItems(["LanguageTool", "Yandex Speller"])
        spelling_panel.addWidget(self.spelling_service_combo)
        spelling_layout.addLayout(spelling_panel)

        language_panel = QHBoxLayout()
        language_panel.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto-Detect", "en-US", "fr-FR", "de-DE", "es-ES", "it-IT", "ru-RU"])
        language_panel.addWidget(self.language_combo)
        spelling_layout.addLayout(language_panel)

        layout.addWidget(spelling_group)

        # Информационный блок
        info_group = QGroupBox("About this Tool")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
            <style>
                h3 {
                    font-size: 16px;
                    color: #CCCCCC;
                    margin-top: 10px;
                    margin-bottom: 5px;
                }
            </style>
            <h3>RMT Text Index Tool v16</h3>
            <p><b>Text Editing Guide:</b></p>
            <ul>
                <li><b>Start Editing:</b> Double-click text cell or use editor panel</li>
                <li><b>Confirm Edit:</b> Press <span style='color:#ba5e29'>Enter</span></li>
                <li><b>New Line:</b> <span style='color:#ba5e29'>Cmd+Enter</span> (Mac) / <span style='color:#ba5e29'>Ctrl+Enter</span> (Win)</li>
                <li><b>Cancel:</b> <span style='color:#ba5e29'>Esc</span></li>
                <li><b>Navigation:</b> Double-click timecode to jump</li>
            </ul>
            <p><b>Keyboard Shortcuts:</b></p>
            <ul>
                <li><span style='color:#ba5e29'>Ctrl+F</span> - Focus search field</li>
                <li><span style='color:#ba5e29'>Ctrl+S</span> - Apply changes in editor</li>
                <li><span style='color:#ba5e29'>Esc</span> - Revert changes in editor</li>
            </ul>
            <p><b>CSV Export/Import:</b></p>
            <ul>
                <li><b>Export to CSV</b> - Save Text+/MultiText/Subtitles for external editing</li>
                <li><b>Import from CSV</b> - Load edited CSV; Load mode updates tree, Apply mode writes to timeline</li>
                <li>Apply applies Text+/MultiText directly and regenerates subtitle track</li>
            </ul>
            <p><b>Supported Clip Types:</b></p>
            <ul>
                <li>Text+</li>
                <li>MultiText layers</li>
                <li>Subtitles</li>
            </ul>
            <h3>Find & Replace</h3>
            <ul>
                <li><b>Replace</b> - Replace in selected clip</li>
                <li><b>Replace All</b> - Replace in all matching clips</li>
                <li>Match case option for precise replacements</li>
                <li>Works with all search modes (Contains, Exact, etc.)</li>
            </ul>
            <h3>Spelling Check</h3>
            <ul>
                <li>Errors are shown in format: <i>word → suggestion</i></li>
                <li>Use <b>right-click → Copy</b> on error messages</li>
                <li>Multiple suggestions are comma-separated</li>
            </ul>
            <h3>Punctuation Cleaning</h3>
            <ul>
                <li>Use <b>Clean Punctuation</b> to remove punctuation from subtitles</li>
                <li>Select punctuation marks (e.g., Dots, Commas) and click <b>Apply</b></li>
                <li>Changes are applied to all subtitles and saved in memory</li>
                <li><b>Note:</b> Filters are reset after cleaning</li>
            </ul>
        """)
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 5px;
                color: #CCCCCC;
                font-size: 12px;
                padding: 10px;
            }
            QTextEdit a {
                color: #ba5e29;
                text-decoration: none;
            }
        """)
        info_text.setMinimumHeight(280)
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        layout.addStretch()

        # Кнопка сайта
        website_container = QHBoxLayout()
        website_container.addStretch()
        self.website_btn = QPushButton("Учебный онлайн центр ResolveMaster.training")
        self.website_btn.setFixedSize(400, 50)
        self.website_btn.setStyleSheet("""
            QPushButton {
                background-color: #ba5e29;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 5px 15px;
                min-height: 35px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ca6e39;
            }
            QPushButton:pressed {
                background-color: #aa4e19;
            }
        """)
        website_container.addWidget(self.website_btn)
        website_container.addStretch()
        layout.addLayout(website_container)
    def _sanitize_node_name_for_id(self, name):
        """Sanitize node name for use in unique_id (CSV-safe)."""
        if not name:
            return "Unnamed"
        return str(name).replace('.', '_').replace('/', '_').replace('\\', '_').replace(',', '_')

    def generate_unique_id(self, clip):
        """
        Generate unique ID for round-trip CSV export/import.
        Format:
        - Subtitle: SUB_track_startframe
        - Text+: TEXTPLUS_track_startframe_sanitized_node_name
        - MultiText: MULTI_track_startframe_sanitized_node_name_L{layer_num}
        """
        clip_type = clip.get('type', 'Unknown')
        track = clip.get('track_idx') or clip.get('track_index', 0)
        start = clip.get('start_frame', 0)

        if clip_type == 'Subtitle':
            return f"SUB_{track}_{start}"

        elif clip_type == 'Text+':
            node_name = clip.get('node_name', '')
            safe_name = self._sanitize_node_name_for_id(node_name)
            return f"TEXTPLUS_{track}_{start}_{safe_name}"

        elif clip_type == 'MultiText':
            node_name = clip.get('node_name', '')
            layer_num = clip.get('layer_num') or clip.get('layer_index', 0)
            safe_name = self._sanitize_node_name_for_id(node_name)
            return f"MULTI_{track}_{start}_{safe_name}_L{layer_num}"

        elif clip_type in ['Fusion', 'Fusion Macro']:
            node_path = clip.get('node_path', 'root')
            safe_path = self._sanitize_node_name_for_id(node_path)
            return f"FUSION_{track}_{start}_{safe_path}"

        return f"UNKNOWN_{track}_{start}"
    def setup_connections(self):
        """Setup signals and slots"""
        # Основные подключения
        self.load_timeline_btn.clicked.connect(self.on_load_text_plus)
        self.load_fcpxml_btn.clicked.connect(self.export_and_load_timeline)
        self.search_btn.clicked.connect(self.on_search_clicked)
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        self.type_filter_combo.currentTextChanged.connect(self.on_type_filter_changed)
        self.spelling_service_combo.currentTextChanged.connect(self.on_spelling_service_changed)
        self.search_input.returnPressed.connect(self.on_search_clicked)
        self.add_markers_btn.clicked.connect(self.add_markers)
        self.check_spelling_btn.clicked.connect(self.on_check_spelling)
        self.enable_edit_btn.clicked.connect(self.on_enable_editing)
        self.apply_changes_btn.clicked.connect(self.on_apply_changes)
        self.export_csv_btn.clicked.connect(self.on_export_csv)
        self.import_csv_btn.clicked.connect(self.show_import_dialog)
        self.website_btn.clicked.connect(self.on_website_button_clicked)
        self.clean_punctuation_btn.clicked.connect(self.on_clean_punctuation)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree_widget.itemChanged.connect(self.on_item_changed)
        self.search_mode_combo.currentTextChanged.connect(self.on_search_mode_changed)
        
        # Панель редактирования
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.edit_text_field.textChanged.connect(self.on_edit_text_changed)
        self.apply_edit_btn.clicked.connect(self.on_apply_edit)
        self.revert_edit_btn.clicked.connect(self.on_revert_edit)
        
        # Find and Replace
        self.toggle_replace_btn.clicked.connect(self.on_toggle_replace_panel)
        self.replace_btn.clicked.connect(self.on_replace_single)
        self.replace_all_btn.clicked.connect(self.on_replace_all)
        self.replace_input.returnPressed.connect(self.on_replace_single)
        self.history_btn.clicked.connect(self.show_replace_history)
        
        # Валидация Replace
        self.search_input.textChanged.connect(self.validate_replace_input)
        self.match_case_check.stateChanged.connect(self.highlight_search_results)

    def setup_shortcuts(self):
        """Setup hotkeys"""
        # Ctrl+F - фокус на поиск
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(lambda: self.search_input.setFocus())
        
        # Ctrl+S - применить изменения в редакторе
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.edit_text_field)
        save_shortcut.activated.connect(self.on_apply_edit)
        
        # Escape - отменить изменения в редакторе
        escape_shortcut = QShortcut(QKeySequence("Escape"), self.edit_text_field)
        escape_shortcut.activated.connect(self.on_revert_edit)

    def on_selection_changed(self):
        """Обработчик изменения выбора в таблице"""
        selected_items = self.tree_widget.selectedItems()
        
        if not selected_items or len(selected_items) != 1:
            self.edit_panel.setVisible(False)
            self.current_editing_item = None
            return
        
        if not self.editing_enabled:
            self.edit_panel.setVisible(False)
            return
        
        item = selected_items[0]
        self.current_editing_item = item
        clip = item.data(0, Qt.UserRole)
        
        if not clip:
            return
        
        # Показываем панель редактирования
        self.edit_panel.setVisible(True)
        
        # Обновляем информацию о клипе
        clip_type = clip["type"]
        timecode = item.text(1)
        info_text = f"Editing: {clip_type} at {timecode}"
        
        if clip_type == "MultiText":
            info_text += f" (Layer {clip.get('layer_num', 'N/A')})"
        elif clip_type == "Text+":
            info_text += f" (Node: {clip.get('node_name', 'N/A')})"
        
        self.edit_info_label.setText(info_text)
        
        # Загружаем текст в редактор
        current_text = clip.get("edited_text", clip.get("text", ""))
        
        # Блокируем сигнал textChanged чтобы избежать ложного срабатывания
        self.edit_text_field.blockSignals(True)
        self.edit_text_field.setPlainText(current_text)
        self.edit_text_field.blockSignals(False)
        
        # Сбрасываем состояние кнопок
        self.apply_edit_btn.setEnabled(False)
        self.revert_edit_btn.setEnabled(False)

    def on_edit_text_changed(self):
        """Обработчик изменения текста в редакторе"""
        if not self.current_editing_item:
            return
        
        clip = self.current_editing_item.data(0, Qt.UserRole)
        if not clip:
            return
        
        original_text = clip.get("edited_text", clip.get("text", ""))
        new_text = self.edit_text_field.toPlainText()
        
        # Активируем кнопки если текст изменился
        has_changes = new_text != original_text
        self.apply_edit_btn.setEnabled(has_changes)
        self.revert_edit_btn.setEnabled(has_changes)

    def on_apply_edit(self):
        """Применить изменения из редактора"""
        if not self.current_editing_item:
            return
        
        clip = self.current_editing_item.data(0, Qt.UserRole)
        if not clip:
            return
        
        new_text = self.edit_text_field.toPlainText()
        clip["edited_text"] = new_text
        
        # Обновляем таблицу
        self.current_editing_item.setText(2, new_text)
        
        # Применяем изменения в зависимости от типа клипа
        clip_type = clip["type"]
        
        if clip_type in ["Text+", "MultiText"]:
            if self.update_text_plus_clip(clip):
                self.status_bar.setText(f"{clip_type} updated successfully")
            else:
                self.status_bar.setText(f"Error updating {clip_type}")
        elif clip_type == "Subtitle":
            self.status_bar.setText("Subtitle updated (in memory)")
        
        # Сбрасываем состояние кнопок
        self.apply_edit_btn.setEnabled(False)
        self.revert_edit_btn.setEnabled(False)

    def on_revert_edit(self):
        """Отменить изменения в редакторе"""
        if not self.current_editing_item:
            return
        
        clip = self.current_editing_item.data(0, Qt.UserRole)
        if not clip:
            return
        
        original_text = clip.get("edited_text", clip.get("text", ""))
        
        self.edit_text_field.blockSignals(True)
        self.edit_text_field.setPlainText(original_text)
        self.edit_text_field.blockSignals(False)
        
        self.apply_edit_btn.setEnabled(False)
        self.revert_edit_btn.setEnabled(False)
        self.status_bar.setText("Changes reverted")
    def on_toggle_replace_panel(self, checked):
        """Переключение видимости панели Replace"""
        self.replace_panel.setVisible(checked)
        if checked:
            self.toggle_replace_btn.setText("▲ Hide Find & Replace")
            self.replace_mode = True
        else:
            self.toggle_replace_btn.setText("▼ Show Find & Replace")
            self.replace_mode = False
            self.replace_count_label.setText("")

    def validate_replace_input(self):
        """Проверка корректности ввода для замены"""
        search_text = self.search_input.text().strip()
        
        if not search_text:
            self.replace_btn.setEnabled(False)
            self.replace_all_btn.setEnabled(False)
            return False
        
        self.replace_btn.setEnabled(True)
        self.replace_all_btn.setEnabled(True)
        return True

    def highlight_search_results(self):
        """Подсветка найденных элементов в таблице"""
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            # Сбрасываем подсветку
            root = self.tree_widget.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                for col in range(4):
                    item.setBackground(col, QColor("#2A2A2A"))
            return
        
        match_count = 0
        root = self.tree_widget.invisibleRootItem()
        
        for i in range(root.childCount()):
            item = root.child(i)
            text = item.text(2).lower()
            
            matched = False
            if self.search_mode == "Contains":
                matched = search_text in text
            elif self.search_mode == "Exact":
                matched = search_text == text
            elif self.search_mode == "Starts With":
                matched = text.startswith(search_text)
            elif self.search_mode == "Ends With":
                matched = text.endswith(search_text)
            
            if matched:
                # Подсвечиваем найденную строку
                for col in range(4):
                    item.setBackground(col, QColor("#3A2A2A"))
                match_count += 1
            else:
                # Сбрасываем подсветку
                for col in range(4):
                    item.setBackground(col, QColor("#2A2A2A"))
        
        if self.replace_mode:
            self.replace_count_label.setText(f"{match_count} found")
    def on_replace_single(self):
        """Заменить один найденный элемент"""
        search_text = self.search_input.text().strip()
        replace_text = self.replace_input.text()
        
        if not search_text:
            self.status_bar.setText("Enter search text first")
            return
        
        # Получаем текущий выбранный элемент
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            self.status_bar.setText("No clip selected. Select a clip first or use Replace All")
            return
        
        item = selected_items[0]
        clip = item.data(0, Qt.UserRole)
        
        if not clip:
            return
        
        current_text = clip.get("edited_text", clip.get("text", ""))
        
        # Выполняем замену с учетом настроек
        match_case = self.match_case_check.isChecked()
        
        if self.search_mode == "Contains":
            if match_case:
                new_text = current_text.replace(search_text, replace_text)
            else:
                # Case-insensitive замена
                pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                new_text = pattern.sub(replace_text, current_text)
        elif self.search_mode == "Exact":
            if (match_case and current_text == search_text) or \
               (not match_case and current_text.lower() == search_text.lower()):
                new_text = replace_text
            else:
                self.status_bar.setText("Text doesn't match exactly")
                return
        elif self.search_mode == "Starts With":
            if (match_case and current_text.startswith(search_text)) or \
               (not match_case and current_text.lower().startswith(search_text.lower())):
                new_text = replace_text + current_text[len(search_text):]
            else:
                self.status_bar.setText("Text doesn't start with search term")
                return
        elif self.search_mode == "Ends With":
            if (match_case and current_text.endswith(search_text)) or \
               (not match_case and current_text.lower().endswith(search_text.lower())):
                new_text = current_text[:-len(search_text)] + replace_text
            else:
                self.status_bar.setText("Text doesn't end with search term")
                return
        
        # Применяем изменения
        clip["edited_text"] = new_text
        item.setText(2, new_text)
        
        # Обновляем редактор если он открыт
        if self.current_editing_item == item:
            self.edit_text_field.blockSignals(True)
            self.edit_text_field.setPlainText(new_text)
            self.edit_text_field.blockSignals(False)
        
        # Применяем в Resolve
        if clip["type"] in ["Text+", "MultiText"]:
            self.update_text_plus_clip(clip)
        
        self.status_bar.setText(f"✓ Replaced in 1 clip")
        self.replace_count_label.setText("1 replaced")
    def on_replace_all(self):
        """Заменить во всех найденных элементах"""
        search_text = self.search_input.text().strip()
        replace_text = self.replace_input.text()
        
        if not search_text:
            self.status_bar.setText("Enter search text first")
            return
        
        # Подтверждение для массовой замены
        clips_count = len(self.filtered_clips if self.filtered_clips else self.all_clips)
        reply = QMessageBox.question(
            self, 
            'Confirm Replace All',
            f'Replace all occurrences of "{search_text}" with "{replace_text}"?\n\n'
            f'This will affect up to {clips_count} clips.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        match_case = self.match_case_check.isChecked()
        replaced_count = 0
        
        clips_to_process = self.filtered_clips if self.filtered_clips else self.all_clips
        
        for clip in clips_to_process:
            current_text = clip.get("edited_text", clip.get("text", ""))
            new_text = current_text
            replaced = False
            
            if self.selected_type_filter != "All" and clip["type"] != self.selected_type_filter:
                continue
            
            if self.search_mode == "Contains":
                if match_case:
                    if search_text in current_text:
                        new_text = current_text.replace(search_text, replace_text)
                        replaced = True
                else:
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    if pattern.search(current_text):
                        new_text = pattern.sub(replace_text, current_text)
                        replaced = True
                        
            elif self.search_mode == "Exact":
                if (match_case and current_text == search_text) or \
                   (not match_case and current_text.lower() == search_text.lower()):
                    new_text = replace_text
                    replaced = True
                    
            elif self.search_mode == "Starts With":
                if (match_case and current_text.startswith(search_text)) or \
                   (not match_case and current_text.lower().startswith(search_text.lower())):
                    new_text = replace_text + current_text[len(search_text):]
                    replaced = True
                    
            elif self.search_mode == "Ends With":
                if (match_case and current_text.endswith(search_text)) or \
                   (not match_case and current_text.lower().endswith(search_text.lower())):
                    new_text = current_text[:-len(search_text)] + replace_text
                    replaced = True
            
            if replaced:
                clip["edited_text"] = new_text
                replaced_count += 1
                
                if clip["type"] in ["Text+", "MultiText"]:
                    self.update_text_plus_clip(clip)
        
        # Обновляем отображение таблицы
        self.populate_tree(self.all_clips)
        
        # Обновляем статус
        self.status_bar.setText(f"✓ Replaced in {replaced_count} clips")
        self.replace_count_label.setText(f"{replaced_count} replaced")
        
        # Логируем операцию
        self.export_replace_history(replaced_count)
        
        if replaced_count == 0:
            self.status_bar.setText("No matches found for replacement")

    def export_replace_history(self, count):
        """Экспорт истории замен в лог"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        search = self.search_input.text()
        replace = self.replace_input.text()
        
        history_entry = {
            'timestamp': timestamp,
            'search': search,
            'replace': replace,
            'count': f"{count} replaced",
            'mode': self.search_mode,
            'match_case': self.match_case_check.isChecked()
        }
        
        self.replace_history.append(history_entry)
        print(f"Replace operation logged: {history_entry}")

    def show_replace_history(self):
        """Показать историю замен"""
        if not self.replace_history:
            QMessageBox.information(self, "Replace History", "No replace operations recorded yet.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Replace History")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        
        history_html = "<h3>Replace Operations History</h3><hr>"
        for entry in reversed(self.replace_history[-20:]):  # Последние 20 операций
            history_html += f"""
            <p><b>{entry['timestamp']}</b><br>
            Search: <code>{entry['search']}</code><br>
            Replace: <code>{entry['replace']}</code><br>
            Mode: {entry['mode']}<br>
            Match case: {entry['match_case']}<br>
            Result: {entry['count']}</p>
            <hr>
            """
        
        history_text.setHtml(history_html)
        layout.addWidget(history_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    def get_timeline_fps(self):
        """Получаем точное FPS текущего таймлайна"""
        if not timeline:
            return 25.0
        
        try:
            # Способ 1: Из настроек таймлайна
            fps_str = timeline.GetSetting("timelineFrameRate")
            if fps_str:
                return float(fractions.Fraction(fps_str))
            
            # Способ 2: Из продолжительности кадра
            frame_duration = timeline.GetSetting("timelineFrameDuration")
            if frame_duration:
                parts = frame_duration.replace("s", "").split("/")
                if len(parts) == 2:
                    return float(fractions.Fraction(parts[1]) / fractions.Fraction(parts[0]))
            
            # Способ 3: Из проекта (fallback)
            return float(project.GetSetting("timelineFrameRate") or 25.0)
        except Exception as e:
            print(f"Error getting timeline FPS: {e}")
            return 25.0

    def frames_to_timecode(self, frames, framerate=None):
        self.smpte.fps = framerate or self.timeline_fps
        return self.smpte.gettc(frames)

    def frames_to_srt_timecode(self, frames, framerate=None):
        """Конвертация фреймов в SRT-таймкод с учетом дробных FPS"""
        framerate = framerate or self.timeline_fps
        try:
            fps_frac = fractions.Fraction.from_float(float(framerate)).limit_denominator()
            total_seconds = fractions.Fraction(int(frames), 1) / fps_frac
            
            hours = int(total_seconds / 3600)
            minutes = int((total_seconds % 3600) / 60)
            seconds = int(total_seconds % 60)
            milliseconds = int(round(float((total_seconds % 1) * 1000)))
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        except Exception as e:
            print(f"Error converting to SRT timecode: {e}")
            return "00:00:00,000"

    def fraction_to_smpte(self, fraction, fps=None):
        """Конвертация дроби в SMPTE формат с улучшенной обработкой ошибок"""
        try:
            if not fraction:
                print("Ошибка: Пустая строка fraction")
                return "00:00:00:00"
                
            fps = fps or self.timeline_fps
            
            if "s" not in fraction or "/" not in fraction:
                print(f"Ошибка: Неверный формат дроби: {fraction}")
                return "00:00:00:00"
                
            try:
                fraction_clean = fraction.replace("s", "")
                num, denom = map(int, fraction_clean.split("/"))
                
                if denom == 0:
                    print("Ошибка: Деление на ноль")
                    return "00:00:00:00"
                    
                seconds = num / denom
                total_frames = int(seconds * fps)
                
                hours = int(total_frames // (3600 * fps))
                minutes = int((total_frames % (3600 * fps)) // (60 * fps))
                seconds = int((total_frames % (60 * fps)) // fps)
                frames = int(total_frames % fps)
                
                smpte = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                
                return smpte
                
            except ValueError as e:
                print(f"Ошибка при разборе дроби: {str(e)}")
                return "00:00:00:00"
            except Exception as e:
                print(f"Неожиданная ошибка при конвертации: {str(e)}")
                return "00:00:00:00"
                
        except Exception as e:
            print(f"Критическая ошибка в fraction_to_smpte: {str(e)}")
            return "00:00:00:00"

    def smpte_to_frames(self, tc, framerate=None):
        self.smpte.fps = framerate or self.timeline_fps
        return self.smpte.getframes(tc)
    def get_text_plus_clips(self):
        text_clips = []
        framerate = self.get_timeline_fps()

        if not timeline:
            print("Error: No active timeline in get_text_plus_clips")
            return text_clips

        for track_idx in range(1, timeline.GetTrackCount("video") + 1):
            
            if not timeline or not hasattr(timeline, 'GetIsTrackEnabled'):
                print(f"Warning: Timeline or GetIsTrackEnabled unavailable for video track {track_idx}")
                continue
            try:
                is_enabled = timeline.GetIsTrackEnabled("video", track_idx)
                if not is_enabled:
                    print(f"Skipping disabled video track {track_idx}")
                    continue
            except AttributeError:
                print(f"Warning: GetIsTrackEnabled not supported or failed for video track {track_idx}")
                continue
            
            track_items = timeline.GetItemListInTrack("video", track_idx)
            if not track_items:
                continue
                
            for tl_item in track_items:
                if not tl_item.GetClipEnabled():
                    continue
                        
                start_frame = tl_item.GetStart()
                clip_name = tl_item.GetName() if hasattr(tl_item, 'GetName') else 'N/A'
                clip_id = f"{start_frame}_{tl_item.GetDuration()}_{track_idx}"
                
                unique_texts_in_clip = set()
                
                for comp_idx in range(1, tl_item.GetFusionCompCount() + 1):
                    comp = tl_item.GetFusionCompByIndex(comp_idx)
                    if not comp:
                        continue
                            
                    tool_list = comp.GetToolList(False)
                    for node in tool_list.values():
                        try:
                            attrs = node.GetAttrs()
                            node_name = attrs.get("TOOLS_Name", "Unnamed")
                            reg_id = attrs.get('TOOLS_RegID', '')
                            
                            is_multitext = reg_id == 'MultiText'
                            is_text_plus = reg_id == 'TextPlus'
                            
                            if is_multitext or is_text_plus:
                                text_list = []
                                
                                if is_multitext:
                                    for i in range(1, 10):
                                        input_name = f"Text{i}.StyledText"
                                        text = node.GetInput(input_name)
                                        if text and isinstance(text, str) and text.strip():
                                            text_list.append((text.strip(), i))
                                elif is_text_plus:
                                    if hasattr(node, "StyledText"):
                                        text = str(node.StyledText[1]) if hasattr(node.StyledText, "__getitem__") and len(dir(node.StyledText)) > 1 else str(node.StyledText)
                                        if text:
                                            text_list.append((text.strip(), None))
                                
                                for text, layer_num in text_list:
                                    if not text or text.lower() == "none":
                                        continue
                                        
                                    if text in unique_texts_in_clip:
                                        continue
                                        
                                    unique_texts_in_clip.add(text)
                                    
                                    comp_id = comp.GetAttrs().get("Comp_ID", f"Comp{comp_idx}")
                                    unique_node_id = f"{clip_id}_{comp_id}_{node_name}"
                                    
                                    text_clips.append({
                                        "type": "MultiText" if is_multitext else "Text+",
                                        "start_frame": start_frame,
                                        "text": text,
                                        "framerate": framerate,
                                        "spelling_errors": [],
                                        "is_checked": False,
                                        "edited_text": text,
                                        "fusion_node_ref": node,
                                        "node_id": unique_node_id,
                                        "node_name": node_name,
                                        "clip_name": clip_name,
                                        "track_idx": track_idx,
                                        "clip_id": clip_id,
                                        "duration": tl_item.GetDuration(),
                                        "timecode": self.frames_to_timecode(start_frame, framerate),
                                        "comp_id": comp_id,
                                        "is_multitext_layer": is_multitext,
                                        "layer_num": layer_num
                                    })
                            
                        except Exception as e:
                            print(f"Error processing tool: {str(e)}")

        print(f"Total Text+ and MultiText clips found on enabled tracks: {len(text_clips)}")
        return text_clips
    def update_text_plus_clip(self, clip_data):
        """Update Text+/MultiText clip. Works with or without fusion_node_ref (e.g. after CSV import)."""
        if not timeline:
            print("Error: No active timeline")
            return False

        # Require either fusion_node_ref OR (clip_id, comp_id, node_name) for re-find
        has_ref = clip_data.get("fusion_node_ref")
        has_ids = all(clip_data.get(k) for k in ("clip_id", "comp_id", "node_name"))
        if not has_ref and not has_ids:
            print("Error: Need fusion_node_ref or (clip_id, comp_id, node_name)")
            return False

        new_text = clip_data["edited_text"]
        target_node_name = clip_data.get("node_name", "")
        target_comp_id = clip_data.get("comp_id", "")
        target_start_frame = clip_data.get("start_frame", -1)
        target_track_idx = clip_data.get("track_idx", -1)
        target_clip_id = clip_data.get("clip_id", "")
        is_multitext = clip_data.get("is_multitext_layer", False)
        layer_num = clip_data.get("layer_num", None)
        
        print(f"Attempting to update: '{new_text}' (Target Node: {target_node_name}, Clip ID: {target_clip_id}, Comp ID: {target_comp_id}, MultiText: {is_multitext}, Layer: {layer_num})")
        
        try:
            # Ищем родительский клип в таймлинии
            current_tl_item = None
            for track_idx in range(1, timeline.GetTrackCount("video") + 1):
                track_items = timeline.GetItemListInTrack("video", track_idx)
                for item in track_items:
                    current_clip_id = f"{item.GetStart()}_{item.GetDuration()}_{track_idx}"
                    if current_clip_id == target_clip_id:
                        current_tl_item = item
                        break
                if current_tl_item:
                    break

            if not current_tl_item:
                print(f"Error: Can't find timeline item with Clip ID {target_clip_id}")
                return False

            # Проверяем все композиции в клипе
            for comp_idx in range(1, current_tl_item.GetFusionCompCount() + 1):
                comp = current_tl_item.GetFusionCompByIndex(comp_idx)
                if not comp or comp.GetAttrs().get("Comp_ID", f"Comp{comp_idx}") != target_comp_id:
                    continue

                # Ищем ноду по точному имени
                tool_list = comp.GetToolList(False)
                for node in tool_list.values():
                    current_attrs = node.GetAttrs()
                    current_node_name = current_attrs.get("TOOLS_Name", "")
                    current_reg_id = current_attrs.get("TOOLS_RegID", "")
                    
                    if current_node_name == target_node_name and current_reg_id == ("MultiText" if is_multitext else "TextPlus"):
                        # Обновляем текст
                        if is_multitext:
                            if layer_num:
                                input_name = f"Text{layer_num}.StyledText"
                                node.SetInput(input_name, new_text)
                                print(f"Successfully updated MultiText layer {layer_num}: '{new_text}' at {clip_data['timecode']}")
                                return True
                            else:
                                print("Error: No layer number specified for MultiText")
                                return False
                        else:
                            if hasattr(node, "StyledText"):
                                if hasattr(node.StyledText, "__setitem__"):
                                    node.StyledText[1] = new_text
                                else:
                                    node.StyledText = new_text
                                print(f"Successfully updated Text+: '{new_text}' at {clip_data['timecode']}")
                                return True
                        break
                else:
                    print(f"Error: Could not find matching node with name {target_node_name} in composition {target_comp_id}")
                    return False

        except Exception as e:
            print(f"Failed to update clip: {str(e)}")
            return False
    def get_subtitle_clips(self):
        subtitle_clips = []
        framerate = self.get_timeline_fps()

        if not timeline:
            print("Error: No active timeline in get_subtitle_clips")
            return subtitle_clips

        all_subtitles = []
        for track_idx in range(1, timeline.GetTrackCount("subtitle") + 1):
            if not timeline or not hasattr(timeline, 'GetIsTrackEnabled'):
                print(f"Warning: Timeline or GetIsTrackEnabled unavailable for subtitle track {track_idx}")
                continue
            try:
                is_enabled = timeline.GetIsTrackEnabled("subtitle", track_idx)
                if not is_enabled:
                    print(f"Skipping disabled subtitle track {track_idx}")
                    continue
            except AttributeError:
                print(f"Warning: GetIsTrackEnabled not supported or failed for subtitle track {track_idx}")
                continue
            
            track_items = timeline.GetItemListInTrack("subtitle", track_idx)
            if track_items:
                for tl_item in track_items:
                    if tl_item.GetClipEnabled():
                        text = tl_item.GetName().strip()
                        start_frame = tl_item.GetStart()
                        try:
                            duration = tl_item.GetDuration()
                            end_frame = start_frame + duration
                        except AttributeError:
                            end_frame = None
                        all_subtitles.append({
                            "start_frame": start_frame, 
                            "end_frame": end_frame, 
                            "text": text, 
                            "item": tl_item,
                            "track_idx": track_idx
                        })

        all_subtitles.sort(key=lambda x: x["start_frame"])

        for i, sub in enumerate(all_subtitles):
            start_frame = sub["start_frame"]
            text = sub["text"]
            if sub["end_frame"] is not None:
                end_frame = sub["end_frame"]
            else:
                next_start = all_subtitles[i + 1]["start_frame"] if i < len(all_subtitles) - 1 else None
                end_frame = next_start if next_start else start_frame + int(7 * framerate)

            subtitle_clips.append({
                "type": "Subtitle",
                "start_frame": start_frame,
                "end_frame": end_frame,
                "text": text,
                "framerate": framerate,
                "spelling_errors": [],
                "is_checked": False,
                "edited_text": text,
                "track_idx": sub.get("track_idx", 1)
            })

        print(f"Total Subtitle clips found on enabled tracks: {len(subtitle_clips)}")
        return subtitle_clips
    def parse_fcpxml(self, file_path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            titles = []
            
            # Получаем FPS из FCPXML
            fps = self.timeline_fps
            sequence = root.find(".//sequence")
            if sequence is not None:
                format_id = sequence.get("format")
                if format_id:
                    format_elem = root.find(f".//format[@id='{format_id}']")
                    if format_elem is not None:
                        frame_duration = format_elem.get("frameDuration")
                        if frame_duration:
                            try:
                                num, denom = map(int, frame_duration.replace("s", "").split("/"))
                                fps = float(denom) / float(num)
                            except (ValueError, ZeroDivisionError) as e:
                                print(f"Ошибка вычисления FPS: {e}, используется timeline_fps")

            self.smpte.fps = fps

            for title in root.findall(".//title"):
                start = title.get("start")
                if not start:
                    continue

                # Конвертируем время из FCPXML в абсолютные фреймы
                try:
                    parts = start.replace("s", "").split("/")
                    if len(parts) == 2:
                        seconds = float(parts[0]) / float(parts[1])
                        frames = int(seconds * fps)
                    else:
                        frames = int(float(start.replace("s", ""))) * fps

                    timecode = self.frames_to_timecode(frames)

                except Exception as e:
                    print(f"Ошибка конвертации времени {start}: {e}")
                    continue

                text = " ".join([t.text for t in title.findall(".//text-style") if t.text])
                titles.append({
                    "type": "Text",
                    "start_timecode": timecode,
                    "start_frame": frames,
                    "text": text.strip(),
                    "framerate": fps,
                    "spelling_errors": [],
                    "is_checked": False
                })

            return titles

        except Exception as e:
            print(f"Ошибка парсинга FCPXML: {e}")
            return []
    def populate_tree(self, clips):
        self.all_clips = []
        self.clip_to_item_map = {}
        self.tree_widget.clear()

        if not clips:
            self.status_bar.setText("No clips found")
            return

        timeline_start = timeline.GetStartTimecode() if timeline else "00:00:00:00"
        
        for clip in clips:
            try:
                # Create unique key (include track_idx for Subtitle/MultiText to avoid collisions)
                if clip["type"] == "Text+":
                    clip_key = clip.get("node_id", "")
                elif clip["type"] == "MultiText":
                    clip_key = f"multi_{clip.get('track_idx', '')}_{clip.get('start_frame', '')}_{clip.get('node_name', '')}_{clip.get('layer_num', '')}"
                else:
                    clip_key = f"sub_{clip.get('track_idx', '')}_{clip.get('start_frame', '')}_{clip.get('text', '')}"

                if clip_key in self.clip_to_item_map:
                    print(f"Warning: Duplicate clip key found: {clip_key}")
                    continue

                item = QTreeWidgetItem()
                item.setText(0, clip["type"])
                
                # Tooltips
                if clip["type"] == "Text+":
                    tooltip = (f"Clip: {clip.get('clip_name', 'N/A')}\n"
                            f"Node: {clip.get('node_name', 'N/A')}\n"
                            f"Track: V{clip.get('track_idx', '')}\n"
                            f"Clip ID: {clip.get('clip_id', '')}\n"
                            f"Comp ID: {clip.get('comp_id', '')}")
                elif clip["type"] == "MultiText":
                    tooltip = (f"Clip: {clip.get('clip_name', 'N/A')}\n"
                            f"Node: {clip.get('node_name', 'N/A')}\n"
                            f"Layer: {clip.get('layer_num', 'N/A')}\n"
                            f"Track: V{clip.get('track_idx', '')}\n"
                            f"Clip ID: {clip.get('clip_id', '')}\n"
                            f"Comp ID: {clip.get('comp_id', '')}")
                else:
                    tooltip = (f"Track: {clip.get('track_idx', '')}\n"
                            f"Duration: {clip.get('duration_frames', '')} frames")
                item.setToolTip(0, tooltip)
                
                # Обработка времени
                if "start_frame" in clip:
                    if clip["start_frame"] == 0 and timeline_start == "00:00:00:00":
                        item.setText(1, timeline_start)
                    else:
                        item.setText(1, self.frames_to_timecode(clip["start_frame"], clip.get("framerate", self.timeline_fps)))
                else:
                    item.setText(1, str(clip.get("start_timecode", "")))
                
                # Текст и возможность редактирования
                item.setText(2, str(clip.get("edited_text", clip.get("text", ""))))
                item.setToolTip(2, "Double-click to edit" if self.editing_enabled else "Double-click to navigate")
                
                # Проверка орфографии
                if not clip.get("is_checked", False):
                    item.setText(3, "—")
                elif not clip.get("spelling_errors", []):
                    item.setText(3, "✓ OK")
                else:
                    errors_text = []
                    for i, error in enumerate(clip["spelling_errors"], 1):
                        if isinstance(error, dict):
                            word = error.get('word', '')
                            suggestions = ", ".join(error.get('s', []))[:50]
                            errors_text.append(f"{i}. {word} → {suggestions}" if suggestions else f"{i}. {word}")
                    
                    error_display = "\n".join(errors_text) if errors_text else "✗ Errors"
                    item.setText(3, error_display)
                    item.setToolTip(3, "Правый клик для копирования ошибок")
                
                # Сохраняем полный объект клипа
                item.setData(0, Qt.UserRole, clip)
                self.tree_widget.addTopLevelItem(item)
                self.all_clips.append(clip)
                self.clip_to_item_map[clip_key] = item

            except Exception as e:
                print(f"Error adding clip to tree: {str(e)}")

        self.status_bar.setText(f"✓ Loaded {len(self.all_clips)} text clips ({sum(1 for c in clips if c['type']=='Text+')} Text+, {sum(1 for c in clips if c['type']=='MultiText')} MultiText, {sum(1 for c in clips if c['type']=='Subtitle')} Subtitles)")
        self.tree_widget.sortByColumn(1, Qt.AscendingOrder)
        self.tree_widget.resizeColumnToContents(0)
        self.tree_widget.resizeColumnToContents(1)
    def filter_tree(self, search_text):
        """Фильтрация дерева с учётом поиска и типа клипа"""
        search_text = search_text.lower() if search_text else ""
        self.tree_widget.clear()
        self.filtered_clips = []
        
        for clip in self.all_clips:
            # Проверка соответствия типу
            type_match = (self.selected_type_filter == "All" or 
                        clip["type"] == self.selected_type_filter)
            
            # Проверка соответствия поисковому запросу
            text_match = False
            clip_text = clip.get("edited_text", clip.get("text", "")).lower()
            
            if search_text:
                if self.search_mode == "Contains":
                    text_match = search_text in clip_text
                elif self.search_mode == "Exact":
                    text_match = search_text == clip_text
                elif self.search_mode == "Starts With":
                    text_match = clip_text.startswith(search_text)
                elif self.search_mode == "Ends With":
                    text_match = clip_text.endswith(search_text)
            else:
                text_match = True

            # Если клип не соответствует фильтрам - пропускаем его
            if not (type_match and text_match):
                continue
                
            # Create tree item only for matching clips
            item = QTreeWidgetItem()
            item.setText(0, clip["type"])
            
            # Set timecode
            if "start_frame" in clip:
                item.setText(1, self.frames_to_timecode(clip["start_frame"]))
            else:
                item.setText(1, clip.get("start_timecode", ""))
            
            # Set text
            item.setText(2, clip.get("edited_text", clip.get("text", "")))
            
            # Set spell-check status
            if not clip.get("is_checked", False):
                item.setText(3, "—")
            elif not clip.get("spelling_errors", []):
                item.setText(3, "✓ OK")
            else:
                errors_text = []
                for i, error in enumerate(clip["spelling_errors"], 1):
                    if isinstance(error, dict):
                        word = error.get('word', '')
                        suggestions = ", ".join(error.get('s', []))[:50]
                        errors_text.append(f"{i}. {word} → {suggestions}" if suggestions else f"{i}. {word}")
                
                error_display = "\n".join(errors_text) if errors_text else "✗ Ошибки"
                item.setText(3, error_display)
            
            # Сохраняем ссылку на клип
            item.setData(0, Qt.UserRole, clip)
            self.tree_widget.addTopLevelItem(item)
            self.filtered_clips.append(clip)
        
        visible_count = len(self.filtered_clips)
        self.status_bar.setText(f"Showing {visible_count} of {len(self.all_clips)} clips")
    def add_markers(self):
        if not timeline:
            self.status_bar.setText("Error: No timeline available")
            return
        
        start_timecode = timeline.GetStartTimecode()
        if not start_timecode:
            start_timecode = "00:00:00:00"
        
        start_frame_offset = self.smpte_to_frames(start_timecode, self.timeline_fps)
        
        clips_to_use = self.filtered_clips if self.filtered_clips else self.all_clips
        if not clips_to_use:
            self.status_bar.setText("Error: No clips loaded")
            return
        
        marker_count = 0
        for clip in clips_to_use:
            if "start_frame" in clip:
                timecode = self.frames_to_timecode(clip["start_frame"], clip["framerate"])
            elif "start_timecode" in clip:
                timecode = clip["start_timecode"]
            
            clip_frame = self.smpte_to_frames(timecode, self.timeline_fps) - start_frame_offset
            result = timeline.AddMarker(clip_frame, "Sky", clip["text"], f"Generated from {clip['type']}", 1)
            if result:
                marker_count += 1
        
        self.status_bar.setText(f"Added {marker_count} markers")

    def clean_punctuation(self, text, punctuation_marks):
        """Удаляет указанные знаки препинания из текста"""
        escaped_marks = [re.escape(mark) for mark in punctuation_marks]
        pattern = f"[{''.join(escaped_marks)}]"
        cleaned_text = re.sub(pattern, "", text)
        return cleaned_text.strip()

    def on_clean_punctuation(self):
        """Handler for Clean Punctuation button"""
        if not any(clip["type"] == "Subtitle" for clip in self.all_clips):
            self.status_bar.setText("No subtitles found")
            return
        
        dialog = PunctuationDialog(self)
        if dialog.exec() == QDialog.Accepted:
            punctuation_marks = dialog.get_selected_punctuation()
            case_mode = dialog.get_selected_case_mode()
            if not punctuation_marks and case_mode == 0:
                self.status_bar.setText("No punctuation or case mode selected")
                return
            cleaned_count = 0
            for clip in self.all_clips:
                if clip["type"] == "Subtitle":
                    original_text = clip.get("edited_text", clip["text"])
                    cleaned_text = original_text
                    # Remove punctuation if selected
                    if punctuation_marks:
                        cleaned_text = self.clean_punctuation(cleaned_text, punctuation_marks)
                    # Change case if selected
                    if case_mode == 1:
                        cleaned_text = cleaned_text.upper()
                    elif case_mode == 2:
                        cleaned_text = cleaned_text.lower()
                    elif case_mode == 3:
                        cleaned_text = cleaned_text.title()
                    elif case_mode == 4:
                        # Sentence case: first letter uppercase, rest as is
                        def sentence_case(s):
                            s = s.strip()
                            if not s:
                                return s
                            # Capitalize first letter of each sentence
                            return re.sub(r'(?:^|[.!?]\s+)([a-zA-Zа-яА-Я])', lambda m: m.group(0).upper(), s)
                        cleaned_text = sentence_case(cleaned_text)
                    if cleaned_text != original_text:
                        clip["edited_text"] = cleaned_text
                        cleaned_count += 1
            # Reset filters if any
            if self.filtered_clips or self.search_input.text() or self.type_filter_combo.currentText() != "All":
                self.search_input.clear()
                self.type_filter_combo.setCurrentText("All")
                self.filtered_clips = []
                self.status_bar.setText(f"✓ Cleaned punctuation and changed case in {cleaned_count} subtitles. Filters reset.")
            else:
                self.status_bar.setText(f"✓ Cleaned punctuation and changed case in {cleaned_count} subtitles")
            self.populate_tree(self.all_clips)
    def on_check_spelling(self):
        if not self.all_clips:
            self.status_bar.setText("No clips loaded for checking")
            return
        
        # Создаем и запускаем поток проверки орфографии
        self.spell_checker = SpellCheckerThread(
            self.all_clips.copy(),
            self.selected_spelling_service,
            self.language_combo.currentText()
        )
        
        # Подключаем сигналы
        self.spell_checker.progress.connect(self.update_progress)
        self.spell_checker.finished.connect(self.on_spell_check_finished)
        self.spell_checker.error.connect(self.on_spell_check_error)
        
        # Показываем прогресс-бар и блокируем кнопку
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.check_spelling_btn.setEnabled(False)
        self.status_bar.setText("Checking spelling...")
        
        # Запускаем проверку
        self.spell_checker.start()

    def update_progress(self, current, total):
        """Обновление прогресс-бара"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_bar.setText(f"Checking spelling... {current}/{total} clips")

    def on_spell_check_finished(self, checked_clips):
        """Обработка завершения проверки орфографии"""
        self.all_clips = checked_clips
        
        # Сбрасываем фильтрацию, если она была активна
        if self.filtered_clips or self.search_input.text() or self.type_filter_combo.currentText() != "All":
            self.search_input.clear()
            self.type_filter_combo.setCurrentText("All")
            self.filtered_clips = []
            self.status_bar.setText("✓ Spell check completed. Filters reset, please reapply if needed.")
        else:
            self.status_bar.setText("✓ Spell check completed")
        
        # Обновляем таблицу со всеми клипами
        self.populate_tree(self.all_clips)
        
        # Скрываем прогресс-бар и разблокируем кнопку
        self.progress_bar.setVisible(False)
        self.check_spelling_btn.setEnabled(True)
        if self.editing_enabled:
            self.on_enable_editing(False)

    def on_spell_check_error(self, error_message):
        """Обработка ошибки проверки орфографии"""
        self.progress_bar.setVisible(False)
        self.check_spelling_btn.setEnabled(True)
        self.status_bar.setText(f"Error during spell check: {error_message}")
        QMessageBox.warning(self, "Spell Check Error", error_message)
    def on_search_clicked(self):
        search_text = self.search_input.text().strip()
        self.filter_tree(search_text)
        self.highlight_search_results()

    def on_reset_clicked(self):
        self.search_input.clear()
        self.type_filter_combo.setCurrentText("All")
        self.populate_tree(self.all_clips)
        self.filtered_clips = []

    def on_type_filter_changed(self, text):
        self.selected_type_filter = text
        self.filter_tree(self.search_input.text())

    def on_spelling_service_changed(self, text):
        self.selected_spelling_service = text
        self.status_bar.setText(f"Selected service: {text}")

    def on_search_mode_changed(self, text):
        """Обработчик изменения режима поиска"""
        self.search_mode = text
        self.status_bar.setText(f"Search mode changed to: {text}")
        # Применяем текущий поиск с новым режимом
        self.filter_tree(self.search_input.text())

    def on_website_button_clicked(self):
        try:
            webbrowser.open("https://resolvemaster.training")
            self.status_bar.setText("Opened website")
        except Exception as e:
            self.status_bar.setText(f"Error opening website: {str(e)}")
    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика - навигация при клике в любом месте, если редактирование отключено"""
        if not timeline:
            self.status_bar.setText("Error: No active timeline")
            return
        
        # Режим просмотра (редактирование отключено) - навигация при клике в любом месте
        if not self.editing_enabled:
            # Получаем таймкод из столбца 1 (как было раньше)
            timecode = item.text(1)
            if timeline.SetCurrentTimecode(timecode):
                self.status_bar.setText(f"Moved to {timecode}")
            else:
                self.status_bar.setText("Failed to navigate to timecode")
            return
        
        # Старое поведение при включенном редактировании:
        if column in [0, 1]:  # Столбцы Type и Timecode
            if column == 1:  # Навигация по таймкоду
                timecode = item.text(1)
                if timeline.SetCurrentTimecode(timecode):
                    self.status_bar.setText(f"Moved to {timecode}")
                else:
                    self.status_bar.setText("Failed to navigate to timecode")
            return
            
        if column in [2, 3]:  # Текст или орфография
            self.status_bar.setText("Enable editing to modify text or spelling errors")

    def on_item_changed(self, item, column):
        if column == 2 and self.editing_enabled:  # Изменение текста
            new_text = item.text(2)
            clip_type = item.text(0)
            timecode = item.text(1)
            
            # Получаем оригинальный текст и предполагаемое имя ноды из элемента дерева
            original_text = item.data(0, Qt.UserRole)["text"] if item.data(0, Qt.UserRole) else ""
            print(f"Item changed: Type: {clip_type}, Timecode: {timecode}, Original Text: '{original_text}', New Text: '{new_text}'")
            
            # Находим соответствующий клип
            clip_found = None
            for clip in (self.filtered_clips if self.filtered_clips else self.all_clips):
                current_timecode = (
                    self.frames_to_timecode(clip["start_frame"], clip["framerate"])
                    if "start_frame" in clip
                    else clip.get("start_timecode", "")
                )
                if (current_timecode == timecode and 
                    clip["type"] == clip_type and 
                    clip["text"] == original_text):  # Используем оригинальный текст для точного соответствия
                    clip_found = clip
                    break

            if clip_found:
                clip_found["edited_text"] = new_text
                
                # Логирование в зависимости от типа клипа
                if clip_type == "Text+":
                    print(f"Clip found: Node: {clip_found['node_name']}, Clip ID: {clip_found['clip_id']}, Comp ID: {clip_found['comp_id']}")
                    if self.update_text_plus_clip(clip_found):
                        self.status_bar.setText("Text+ clip updated successfully")
                        item.setText(2, new_text)
                    else:
                        self.status_bar.setText("Error updating Text+ clip")
                elif clip_type == "MultiText":
                    print(f"Clip found: Node: {clip_found['node_name']}, Layer: {clip_found['layer_num']}, Clip ID: {clip_found['clip_id']}, Comp ID: {clip_found['comp_id']}")
                    if self.update_text_plus_clip(clip_found):
                        self.status_bar.setText(f"MultiText layer {clip_found['layer_num']} updated successfully")
                        item.setText(2, new_text)
                    else:
                        self.status_bar.setText("Error updating MultiText layer")
                elif clip_type == "Subtitle":
                    print(f"Clip found: Start Frame: {clip_found['start_frame']}, End Frame: {clip_found['end_frame']}, Text: {clip_found['text']}")
                    self.status_bar.setText("Subtitle updated (in memory)")
                    item.setText(2, new_text)
                else:
                    self.status_bar.setText(f"{clip_type} updated")
                    item.setText(2, new_text)
            else:
                self.status_bar.setText("Clip not found")
                print("Error: Clip not found in all_clips or filtered_clips")
    def on_enable_editing(self, enable=None):
        if enable is not None:
            self.editing_enabled = enable
        else:
            self.editing_enabled = not self.editing_enabled
        
        # Синхронизируем состояние кнопки с editing_enabled
        self.enable_edit_btn.setChecked(self.editing_enabled)
        
        if self.editing_enabled:
            # Включаем редактирование и обновляем стиль таблицы
            self.tree_widget.setStyleSheet("""
                QTreeWidget {
                    border: 1px solid #FB5041;
                    border-radius: 5px;
                    background-color: #2A2A2A;
                    color: #ebebeb;
                    font-size: 13px;
                }
                QTreeWidget::item {
                    padding: 5px;
                }
                QTreeWidget::item:selected {
                    background-color: #1A1A1A;
                    color: #FFFFFF;
                }
                QHeaderView::section {
                    background-color: #3A3A3A;
                    color: #ebebeb;
                    padding: 5px;
                    border: 1px solid #2A2A2A;
                }
            """)
            
            self.tree_widget.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed)
            
            # Делаем все элементы редактируемыми
            root = self.tree_widget.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            
            self.enable_edit_btn.setText("Disable Editing")
            
            # Показываем панель редактирования если выбран элемент
            selected_items = self.tree_widget.selectedItems()
            if len(selected_items) == 1:
                self.on_selection_changed()
            
            self.status_bar.setText("Edit mode enabled. Use editor panel below or double-click cells")
        else:
            # Скрываем панель редактирования
            self.edit_panel.setVisible(False)
            self.current_editing_item = None
            
            self.tree_widget.setStyleSheet("""
                QTreeWidget {
                    border: 1px solid #2A2A2A;
                    border-radius: 5px;
                    background-color: #2A2A2A;
                    color: #ebebeb;
                    font-size: 13px;
                }
                QTreeWidget::item {
                    padding: 5px;
                }
                QTreeWidget::item:selected {
                    background-color: #1A1A1A;
                    color: #FFFFFF;
                }
                QHeaderView::section {
                    background-color: #3A3A3A;
                    color: #ebebeb;
                    padding: 5px;
                    border: 1px solid #2A2A2A;
                }
            """)
            
            self.tree_widget.setEditTriggers(QTreeWidget.NoEditTriggers)
            
            # Убираем флаг редактируемости
            root = self.tree_widget.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            
            self.enable_edit_btn.setText("Enable Editing")
            self.status_bar.setText("Edit mode disabled. Double-click for navigation.")
    def on_load_text_plus(self):
        print("on_load_text_plus called, timeline:", timeline)
        if not timeline:
            self.status_bar.setText("Error: No active timeline")
            return
        self.all_clips = []
        text_plus_clips = self.get_text_plus_clips()
        subtitle_clips = self.get_subtitle_clips()
        clips = text_plus_clips + subtitle_clips
        self.populate_tree(clips)

    def export_and_load_timeline(self):
        if not project or not timeline:
            self.status_bar.setText("Error: No current project or timeline")
            return
        
        # Создаём временный файл FCPXML с использованием tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fcpxml', delete=False) as temp_fcpxml:
            try:
                timeline.Export(temp_fcpxml.name, resolve.EXPORT_FCPXML_1_8)
                self.status_bar.setText(f"Exported to temporary FCPXML: {temp_fcpxml.name}")
                self.all_clips = []
                fcpxml_clips = self.parse_fcpxml(temp_fcpxml.name)
                text_plus_clips = self.get_text_plus_clips()
                subtitle_clips = self.get_subtitle_clips()
                clips = fcpxml_clips + text_plus_clips + subtitle_clips
                self.populate_tree(clips)
                self.fcpxml_path.setText(temp_fcpxml.name)
            except Exception as e:
                self.status_bar.setText(f"Error during export: {str(e)}")
            finally:
                if os.path.exists(temp_fcpxml.name):
                    os.remove(temp_fcpxml.name)
                    self.status_bar.setText(f"Temporary FCPXML removed: {temp_fcpxml.name}")

    def on_export_csv(self):
        if not self.all_clips:
            self.status_bar.setText("No data to export")
            return

        # Export only Text+, MultiText, Subtitle (exclude FCPXML and other types)
        export_types = {"Text+", "MultiText", "Subtitle"}
        clips_to_export = [c for c in self.all_clips if c.get("type") in export_types]
        if not clips_to_export:
            self.status_bar.setText("No Text+/MultiText/Subtitle clips to export")
            return

        default_filename = f"{timeline.GetName() or 'export'}.csv" if timeline else "export.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", default_filename, "CSV Files (*.csv)")
        if not file_path:
            self.status_bar.setText("Export canceled")
            return

        headers = ["unique_id", "element_type", "original_text", "edited_text", "timecode"]
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                for clip in clips_to_export:
                    timecode = self.frames_to_timecode(clip["start_frame"], clip.get("framerate", self.timeline_fps)) if "start_frame" in clip else clip.get("start_timecode", "")
                    row = {
                        "unique_id": self.generate_unique_id(clip),
                        "element_type": clip.get("type", ""),
                        "original_text": clip.get("text", ""),
                        "edited_text": clip.get("edited_text", clip.get("text", "")),
                        "timecode": timecode,
                    }
                    writer.writerow(row)
            self.status_bar.setText(f"✓ Exported {len(clips_to_export)} clips to CSV: {file_path}")
        except Exception as e:
            self.status_bar.setText(f"Error exporting CSV: {str(e)}")

    def show_import_dialog(self):
        """Show CSV import dialog."""
        if not self.all_clips:
            self.status_bar.setText("Load timeline first (Refresh)")
            QMessageBox.information(self, "Import CSV", "Load timeline data first by clicking Refresh.")
            return
        dlg = CSVImportDialog(self)
        dlg.exec_()

    def parse_import_csv(self, csv_path, text_column="edited_text", delimiter=None):
        """
        Parse CSV file for import. Returns dict {unique_id: {new_text, element_type, ...}}.
        Validates required columns: unique_id, element_type, and text_column.
        delimiter: "," ";" "\\t" "|" or None for auto-detect (e.g. Numbers/Excel files).
        """
        import_data = {}
        required = ["unique_id", "element_type", text_column]
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                if delimiter is None:
                    sample = f.read(4096)
                    f.seek(0)
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                        reader = csv.DictReader(f, dialect=dialect)
                    except csv.Error:
                        reader = csv.DictReader(f)
                else:
                    reader = csv.DictReader(f, delimiter=delimiter)
                if not reader.fieldnames:
                    return None, "CSV file is empty or has no headers"
                missing = [c for c in required if c not in reader.fieldnames]
                if missing:
                    return None, f"Missing required columns: {', '.join(missing)}"
                for row in reader:
                    uid = row.get("unique_id", "").strip()
                    if not uid:
                        continue
                    new_text = row.get(text_column, "").strip()
                    import_data[uid] = {
                        "new_text": new_text,
                        "element_type": row.get("element_type", ""),
                        "original_text": row.get("original_text", ""),
                    }
            return import_data, None
        except Exception as e:
            return None, str(e)

    def match_clips_with_import(self, import_data, type_filters):
        """
        Match all_clips with import_data by unique_id.
        type_filters: set of types to apply, e.g. {"Text+", "MultiText", "Subtitle"}
        Returns (matched_list, not_found_ids) where matched_list contains (clip, new_text) tuples.
        """
        matched = []
        not_found = []
        for uid, data in import_data.items():
            if not data.get("new_text"):
                continue
            elem_type = data.get("element_type", "")
            if elem_type and elem_type not in type_filters:
                continue
            found = False
            for clip in self.all_clips:
                if clip.get("type") not in type_filters:
                    continue
                if self.generate_unique_id(clip) == uid:
                    matched.append((clip, data["new_text"]))
                    found = True
                    break
            if not found:
                not_found.append(uid)
        return matched, not_found

    def on_apply_changes(self):
        if not self.all_clips:
            self.status_bar.setText("No subtitles to apply")
            return

        if not media_pool or not timeline:
            self.status_bar.setText("Error: Media Pool or Timeline not available")
            return

        # Получаем стартовый таймкод таймлинии и конвертируем в фреймы
        timeline_start_tc = timeline.GetStartTimecode() or "00:00:00:00"
        timeline_start_frame = self.smpte_to_frames(timeline_start_tc, self.timeline_fps)

        # Создаём временный файл SRT
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as temp_srt:
            try:
                # Записываем SRT файл с учетом смещения таймлинии
                subtitle_number = 1
                subtitle_clips = [clip for clip in self.all_clips if clip["type"] == "Subtitle"]
                subtitle_clips.sort(key=lambda x: x["start_frame"])

                for clip in subtitle_clips:
                    # Вычисляем относительное время (от начала таймлинии)
                    relative_start_frame = clip["start_frame"] - timeline_start_frame
                    relative_end_frame = clip["end_frame"] - timeline_start_frame
                    
                    # Конвертируем в таймкод SRT (начинается с 00:00:00,000)
                    start_timecode = self.frames_to_srt_timecode(max(0, relative_start_frame), clip["framerate"])
                    end_timecode = self.frames_to_srt_timecode(max(0, relative_end_frame), clip["framerate"])
                    
                    raw_text = clip.get("edited_text", clip["text"]).replace("\u2028", "\n").replace("\u2029", "\n")
                    lines = [line for line in raw_text.splitlines() if line.strip()]
                    final_text = "\n".join(lines)

                    temp_srt.write(f"{subtitle_number}\n")
                    temp_srt.write(f"{start_timecode} --> {end_timecode}\n")
                    temp_srt.write(f"{final_text}\n\n")
                    subtitle_number += 1

                temp_srt_path = temp_srt.name

            except Exception as e:
                self.status_bar.setText(f"Error creating SRT file: {str(e)}")
                return

        try:
            # Импортируем временный SRT файл в корневую папку
            import_options = {
                "ImportAsSubtitle": True,
                "TargetFolder": media_pool.GetRootFolder()
            }
            
            imported_items = media_pool.ImportMedia([temp_srt_path], import_options)
            if not imported_items:
                self.status_bar.setText("Error importing SRT file")
                return

            # Получаем ссылку на импортированный клип
            srt_clip = imported_items[0]

            # Отключаем все существующие subtitle tracks
            subtitle_track_count = timeline.GetTrackCount("subtitle")
            for track_index in range(1, subtitle_track_count + 1):
                timeline.SetTrackEnable("subtitle", track_index, False)

            # Создаем новый трек
            new_track_index = subtitle_track_count + 1
            timeline.AddTrack("subtitle")
            timeline.SetTrackEnable("subtitle", new_track_index, True)

            # Добавляем субтитры на таймлайн, начиная с начала таймлинии
            append_data = [{
                'mediaPoolItem': srt_clip,
                'startFrame': 0,  # Начинаем с начала таймлинии
                'mediaType': "subtitle",
                'recordFrame': 0  # Записываем с начала таймлинии
            }]
            
            if media_pool.AppendToTimeline(append_data):
                self.status_bar.setText(f"Subtitles applied successfully to track {new_track_index}")
                
                # Успешно добавили на таймлайн - теперь удаляем клип из медиапула
                media_pool.DeleteClips([srt_clip])
            else:
                self.status_bar.setText("Error: Failed to append subtitles to timeline")

        except Exception as e:
            self.status_bar.setText(f"Error applying changes: {str(e)}")
        finally:
            # Удаляем временный файл в любом случае
            if os.path.exists(temp_srt_path):
                try:
                    os.remove(temp_srt_path)
                except:
                    pass
        if self.editing_enabled:
                self.on_enable_editing(False)
    def show_context_menu(self, position):
        menu = QMenu()
        split_action = menu.addAction("Split Subtitle")
        merge_action = menu.addAction("Merge Subtitles")
        
        action = menu.exec_(self.tree_widget.mapToGlobal(position))
        if action == split_action:
            self.split_subtitle()
        elif action == merge_action:
            self.merge_subtitles()

    def split_subtitle(self):
        current_item = self.tree_widget.currentItem()
        if not current_item:
            self.status_bar.setText("No subtitle selected")
            return

        clip = current_item.data(0, Qt.UserRole)
        if clip["type"] != "Subtitle":
            self.status_bar.setText("Only subtitles can be split")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Split Subtitle")
        layout = QVBoxLayout(dialog)
        
        text_label = QLabel(f"Text: {clip['text']}")
        layout.addWidget(text_label)
        
        split_pos_input = QLineEdit()
        split_pos_input.setPlaceholderText("Enter split position (word number or 'auto')")
        layout.addWidget(split_pos_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() != QDialog.Accepted:
            self.status_bar.setText("Split canceled")
            return
        
        split_pos = split_pos_input.text().strip()
        
        original_text = clip.get("edited_text", clip["text"])
        words = original_text.split()
        if not words:
            self.status_bar.setText("Empty subtitle text")
            return
        
        if split_pos.lower() == "auto":
            split_idx = len(words) // 2
        else:
            try:
                split_idx = int(split_pos)
                if split_idx < 1 or split_idx >= len(words):
                    raise ValueError
            except ValueError:
                self.status_bar.setText("Invalid split position")
                return
        
        text1 = " ".join(words[:split_idx]).strip()
        text2 = " ".join(words[split_idx:]).strip()
        
        if not text1 or not text2:
            self.status_bar.setText("Cannot split: one part is empty")
            return
        
        duration = clip["end_frame"] - clip["start_frame"]
        mid_frame = clip["start_frame"] + duration // 2
        
        new_clip1 = clip.copy()
        new_clip1["text"] = text1
        new_clip1["edited_text"] = text1
        new_clip1["end_frame"] = mid_frame
        
        new_clip2 = clip.copy()
        new_clip2["text"] = text2
        new_clip2["edited_text"] = text2
        new_clip2["start_frame"] = mid_frame
        
        self.all_clips.remove(clip)
        self.all_clips.append(new_clip1)
        self.all_clips.append(new_clip2)
        
        self.populate_tree(self.all_clips)
        self.status_bar.setText(f"Subtitle split into two parts at frame {mid_frame}")

    def merge_subtitles(self):
        selected_items = self.tree_widget.selectedItems()
        if len(selected_items) < 2:
            self.status_bar.setText("Select at least two subtitles to merge")
            return
        
        clips = []
        for item in selected_items:
            clip = item.data(0, Qt.UserRole)
            if clip["type"] != "Subtitle":
                self.status_bar.setText("Only subtitles can be merged")
                return
            clips.append(clip)
        
        clips.sort(key=lambda x: x["start_frame"])
        
        max_gap_frames = int(2 * self.timeline_fps)
        for i in range(1, len(clips)):
            gap = clips[i]["start_frame"] - clips[i-1]["end_frame"]
            if gap > max_gap_frames:
                self.status_bar.setText(f"Too large gap between subtitles: {gap} frames")
                return
        
        merged_text = " ".join(clip.get("edited_text", clip["text"]) for clip in clips)
        
        new_clip = clips[0].copy()
        new_clip["text"] = merged_text
        new_clip["edited_text"] = merged_text
        new_clip["start_frame"] = clips[0]["start_frame"]
        new_clip["end_frame"] = clips[-1]["end_frame"]
        
        for clip in clips:
            self.all_clips.remove(clip)
        
        self.all_clips.append(new_clip)
        
        self.populate_tree(self.all_clips)
        self.status_bar.setText(f"Merged {len(clips)} subtitles into one")
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        if resolve:
            # Очистка ресурсов, связанных с Resolve
            pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Проверка, запущен ли скрипт внутри Resolve
    if resolve is None:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("This script must be run from within DaVinci Resolve")
        msg.setWindowTitle("Error")
        msg.exec_()
        sys.exit(1)
    
    window = SubtitleEditor()
    window.show()
    sys.exit(app.exec())