#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2020-2023 Eduard Permyakov 
#
#  Permafrost Engine is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Permafrost Engine is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
#  Linking this software statically or dynamically with other modules is making 
#  a combined work based on this software. Thus, the terms and conditions of 
#  the GNU General Public License cover the whole combination. 
#  
#  As a special exception, the copyright holders of Permafrost Engine give 
#  you permission to link Permafrost Engine with independent modules to produce 
#  an executable, regardless of the license terms of these independent 
#  modules, and to copy and distribute the resulting executable under 
#  terms of your choice, provided that you also meet, for each linked 
#  independent module, the terms and conditions of the license of that 
#  module. An independent module is a module which is not derived from 
#  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
#  extend this exception to your version of Permafrost Engine, but you are not 
#  obliged to do so. If you do not wish to do so, delete this exception 
#  statement from your version.
#

import sys

import pf


if sys.version_info[0] >= 3:

    _active_tasks = []
    _handler_installed = False

    def _ensure_handler():
        global _handler_installed
        if not _handler_installed:
            pf.register_event_handler(pf.EVENT_UPDATE_START, _on_update_start, None)
            _handler_installed = True

    def _remove_handler_if_idle():
        global _handler_installed
        if _handler_installed and not _active_tasks:
            pf.unregister_event_handler(pf.EVENT_UPDATE_START, _on_update_start)
            _handler_installed = False

    def _on_update_start(_, event):
        del event

        frame_ms = pf.prev_frame_ms()
        active = []

        for task in _active_tasks:
            if task.completed:
                continue

            frac_done = task._elapsed / float(task.duration)
            bounds = (
                task.bounds[0],
                int(task.bounds[1] - task.travel * frac_done),
                task.bounds[2],
                task.bounds[3],
            )
            color = tuple(list(task.color[:-1]) + [int(task.color[3] * (1.0 - frac_done))])

            pf.draw_text(task.text, bounds, color)

            task._elapsed += frame_ms
            task.completed = task._elapsed >= task.duration
            if not task.completed:
                active.append(task)

        _active_tasks[:] = active
        _remove_handler_if_idle()

    class DisappearingTextTask(object):

        def __init__(self, text, bounds, color, duration, travel=50):
            self.text = text
            self.bounds = bounds
            self.color = color
            self.duration = duration
            self.travel = travel
            self._elapsed = 0
            self.completed = duration <= 0

        def run(self):
            if self.completed or self in _active_tasks:
                return
            _active_tasks.append(self)
            _ensure_handler()

else:

    class DisappearingTextTask(pf.Task):

        def __init__(self, text, bounds, color, duration, travel=50):
            self.text = text
            self.bounds = bounds
            self.color = color
            self.duration = duration
            self.travel = travel

        def __run__(self):
            elapsed = 0
            while elapsed < self.duration:

                frac_done = elapsed / float(self.duration)
                bounds = (self.bounds[0], int(self.bounds[1] - self.travel * frac_done), self.bounds[2], self.bounds[3])
                color = tuple(list(self.color[:-1]) + [int(self.color[3] * (1.0 - frac_done))])

                pf.draw_text(self.text, bounds, color)
                self.await_event(pf.EVENT_UPDATE_START)
                elapsed += pf.prev_frame_ms()
