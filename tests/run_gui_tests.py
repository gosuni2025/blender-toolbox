"""Run in a NEW factory-startup Blender process, never a user's open document.

blender --factory-startup --python tests/run_gui_tests.py
"""
import os
from pathlib import Path
import runpy
import sys
import traceback
import bpy


def run_tests():
    status = 0
    try:
        runpy.run_path(str(Path(__file__).with_name('blender_integration.py')), run_name='__main__')
        runpy.run_path(str(Path(__file__).with_name('gpu_filters.py')), run_name='__main__')
    except BaseException:
        traceback.print_exc()
        status = 1
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        # This isolated process was created for the test. It contains no user file.
        os._exit(status)


def prepare_editor():
    area = bpy.context.screen.areas[0]
    area.type = 'IMAGE_EDITOR'
    area.ui_type = 'UV'
    bpy.app.timers.register(run_tests, first_interval=0.5)


bpy.app.timers.register(prepare_editor, first_interval=1.0)
