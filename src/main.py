import os
import sys
import time
from collections import deque

# PATCH: Add nvidia CUDA DLLs to PATH (cublas, etc.)
_nvidia_bin = os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', 'cublas', 'bin')
if os.path.isdir(_nvidia_bin):
    os.environ['PATH'] = _nvidia_bin + os.pathsep + os.environ.get('PATH', '')
    os.add_dll_directory(_nvidia_bin)

# PATCH: Load CUDA model BEFORE PyQt5 to avoid segfault (Qt OpenGL + CUDA conflict)
from utils import ConfigManager
ConfigManager.initialize()
_preloaded_model = None
if ConfigManager.config_file_exists():
    model_options = ConfigManager.get_config_section('model_options')
    if not model_options.get('use_api'):
        from transcription import create_local_model
        print('Pre-loading CUDA model before Qt...')
        _preloaded_model = create_local_model()
        print('Model pre-loaded OK')

from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox

from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from ui.history_window import HistoryWindow
from transcription import create_local_model
from input_simulation import InputSimulator


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon(os.path.join('assets', 'ww-logo.png')))

        ConfigManager.initialize()

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)

        if ConfigManager.config_file_exists():
            self.initialize_components()
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def initialize_components(self):
        """
        Initialize the components of the application.
        """
        self.input_simulator = InputSimulator()

        # PATCH: Transcription history for replay feature
        self.last_transcription = None
        self.transcription_history = deque(maxlen=10)
        self.history_index = -1  # for Shift+F10 cycling (-1 = most recent)

        # Main key listener (record)
        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        # PATCH: Replay key listener — re-types last transcription (F10)
        self.replay_listener = KeyListener(
            activation_key=ConfigManager.get_config_value('recording_options', 'replay_key') or 'f10'
        )
        self.replay_listener.add_callback("on_activate", self.on_replay_activation)

        # PATCH: History cycling listener — Shift+F10 cycles through older transcriptions
        self.history_cycle_listener = KeyListener(activation_key='shift+f10')
        self.history_cycle_listener.add_callback("on_activate", self.on_history_cycle)

        model_options = ConfigManager.get_config_section('model_options')
        model_path = model_options.get('local', {}).get('model_path')
        self.local_model = _preloaded_model if _preloaded_model else (create_local_model() if not model_options.get('use_api') else None)

        self.result_thread = None

        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self._start_all_listeners)
        self.main_window.closeApp.connect(self.exit_app)

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.status_window = StatusWindow()

        # PATCH: History window
        self.history_window = HistoryWindow()
        self.history_window.replaySignal.connect(self._replay_from_history)

        self.create_tray_icon()
        self.main_window.show()

    def create_tray_icon(self):
        """
        Create the system tray icon and its context menu.
        """
        self.tray_icon = QSystemTrayIcon(QIcon(os.path.join('assets', 'ww-logo.png')), self.app)

        tray_menu = QMenu()

        show_action = QAction('WhisperWriter Main Menu', self.app)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        history_action = QAction('History', self.app)
        history_action.triggered.connect(self.history_window.show)
        tray_menu.addAction(history_action)

        settings_action = QAction('Open Settings', self.app)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        exit_action = QAction('Exit', self.app)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _start_all_listeners(self):
        """Start all key listeners (record, replay, history cycle)."""
        self.key_listener.start()
        self.replay_listener.start()
        self.history_cycle_listener.start()

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if hasattr(self, 'replay_listener') and self.replay_listener:
            self.replay_listener.stop()
        if hasattr(self, 'history_cycle_listener') and self.history_cycle_listener:
            self.history_cycle_listener.stop()
        if self.input_simulator:
            self.input_simulator.cleanup()

    def exit_app(self):
        """
        Exit the application.
        """
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        """Restart the application to apply the new settings."""
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        """
        If settings is closed without saving on first run, initialize the components with default values.
        """
        if not os.path.exists(os.path.join('src', 'config.yaml')):
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        """
        Called when the activation key combination is pressed.
        """
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        self.start_result_thread()

    def on_deactivation(self):
        """
        Called when the activation key combination is released.
        """
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        """
        Start the result thread to record audio and transcribe it.
        """
        if self.result_thread and self.result_thread.isRunning():
            return

        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.status_window.closeSignal.connect(self.stop_result_thread)
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def stop_result_thread(self):
        """
        Stop the result thread.
        """
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, type the result and start listening for the activation key again.
        """
        # PATCH: Save transcription for replay + history
        if result and result.strip():
            self.last_transcription = result
            self.transcription_history.append(result)
            self.history_index = -1  # reset cycling position
            self.history_window.add_entry(result)
            ConfigManager.console_print(f'Transcription saved to history ({len(self.transcription_history)} entries)')

            # PATCH: Copy to clipboard if enabled
            if ConfigManager.get_config_value('recording_options', 'copy_to_clipboard'):
                QApplication.clipboard().setText(result.strip())
                ConfigManager.console_print('Transcription copied to clipboard')

        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def on_replay_activation(self):
        """
        PATCH: Called when the replay key (F10) is pressed. Re-types the last transcription.
        """
        if not self.last_transcription:
            ConfigManager.console_print('Replay: no transcription in history')
            return

        self.history_index = -1  # F10 always replays the most recent
        ConfigManager.console_print(f'Replaying last transcription: {self.last_transcription[:50]}...')
        self.input_simulator.typewrite(self.last_transcription)

    def on_history_cycle(self):
        """
        PATCH: Called when Shift+F10 is pressed. Cycles backward through transcription history.
        Each press goes one entry further back. After the oldest, wraps to the newest.
        """
        if not self.transcription_history:
            ConfigManager.console_print('History cycle: no transcriptions in history')
            return

        # Move backward (0 = most recent, 1 = second most recent, etc.)
        self.history_index += 1
        if self.history_index >= len(self.transcription_history):
            self.history_index = 0  # wrap around

        # History is a deque with most recent at the end, so reverse index
        reverse_idx = len(self.transcription_history) - 1 - self.history_index
        text = self.transcription_history[reverse_idx]

        pos = self.history_index + 1
        total = len(self.transcription_history)
        ConfigManager.console_print(f'History [{pos}/{total}]: {text[:50]}...')
        self.input_simulator.typewrite(text)

    def _replay_from_history(self, text):
        """
        PATCH: Called when user clicks an entry in the history window.
        Adds a small delay to let the window hide before typing.
        """
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(300, lambda: self.input_simulator.typewrite(text))

    def run(self):
        """
        Start the application.
        """
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    app = WhisperWriterApp()
    app.run()
