#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 by Christian Tremblay, P.Eng <christian.tremblay@servisys.com>
# Licensed under LGPLv3, see file LICENSE in this source tree.
#
"""
TaskManager.py - creation of threads used for repetitive tasks.

A key building block for point simulation.
"""
import time
import asyncio
from random import random

from ..core.io.IOExceptions import DeviceNotConnected

# --- 3rd party modules ---
# --- this application's modules ---
from ..core.utils.notes import note_and_log

# ------------------------------------------------------------------------------


async def stopAllTasks():
    Task._log.info("Stopping all tasks")
    for each in Task.tasks:
        each.aio_task.cancel()
    Task._log.info("Ok all tasks stopped")
    Task.clean_tasklist()
    return True


@note_and_log
class Task(object):
    tasks = []
    high_latency = 60

    @classmethod
    def clean_tasklist(cls):
        cls._log.debug("Cleaning tasks list")
        cls.tasks = []

    @classmethod
    def number_of_tasks(cls):
        return len(cls.tasks)

    def __init__(self, fn=None, name=None, delay=0):
        # delay = 0 -> one shot
        self.id = id(self)
        self.name = name if name is not None else f"Task_{self.id}"
        if isinstance(fn, tuple):
            self.fn, self.args = fn
        else:
            self.fn = fn
            self.args = None

        if delay > 0:
            self.delay = delay if delay >= 5 else 5
        else:
            self.delay = 0
        self.previous_execution = None
        self.average_execution_delay = 0
        self.average_latency = 0
        self.next_execution = time.time() + delay + (random() * 10)
        self.execution_time = 0.0
        self.count = 0

        self._kwargs = None
        self._task = None
        self.aio_task = None

    async def task(self):
        raise NotImplementedError("Must be implemented")

    async def execute(self):
        if self.delay > 0:
            while True:
                self.count += 1
                _start_time = time.time()
                self._log.debug(f"Executing : {self.name} | Count : {self.count}")
                self._log.debug(f"Start Time : {_start_time}")
                if self.previous_execution:
                    self._log.debug(f"Previous execution : {self.previous_execution}")
                else:
                    self._log.debug(f"First Run")

                self.average_latency = (
                    self.average_latency + (_start_time - self.next_execution)
                ) / 2
                if self.fn and self.args is not None:
                    await self.fn(self.args)
                elif self.fn:
                    await self.fn()
                else:
                    if self._kwargs is not None:
                        await self.task(**self._kwargs)
                    else:
                        await self.task()
                if self.previous_execution:
                    _total = self.average_execution_delay + (
                        _start_time - self.previous_execution
                    )
                    self.average_execution_delay = _total / 2
                else:
                    self.average_execution_delay = self.delay

                # self._log.info('Stat for task {}'.format(self))
                if self.average_latency > Task.high_latency:
                    self._log.warning("High latency for {}".format(self.name))
                    self._log.warning("Stats : {}".format(self))

                self.execution_time = time.time() - _start_time
                self._log.debug(f"Execution Time : {self.execution_time}")
                self.previous_execution = _start_time
                self.next_execution = time.time() + self.delay
                await asyncio.sleep(self.delay)
        else:  # one shot
            if self.fn and self.args is not None:
                await self.fn(self.args)
            elif self.fn:
                await self.fn()
            else:
                if self._kwargs is not None:
                    await self.task(**self._kwargs)
                else:
                    await self.task()

    def start(self):
        self.aio_task = asyncio.create_task(self.execute(), name=f"aio{self.name}")
        Task.tasks.append(self)

    def stop(self):
        self._task.cancel()

    @property
    def done(self):
        if self.aio_task is not None:
            return self.aio_task.done()
        else:
            return False

    @property
    def last_time(self):
        return time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(self.previous_execution)
        )

    @property
    def next_time(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.next_execution))

    @property
    def latency(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.average_latency))

    def is_alive(self):
        return

    def __repr__(self):
        return "{:<40} | Avg exec delay : {:.2f} sec | Avg latency : {:.2f} sec | last executed : {} | Next Time : {}".format(
            self.name,
            self.average_execution_delay,
            self.average_latency,
            self.last_time,
            self.next_time,
        )

    def __lt__(self, other):
        # list sort use __lt__... little cheat to reverse list already
        return self.next_execution > other.next_execution

    def __eq__(self, other):
        # list remove use __eq__... so compare with id
        if isinstance(other, Task):
            return self.id == other.id
        else:
            return self.id == other


@note_and_log
class OneShotTask(Task):
    def __init__(self, fn=None, args=None, name="Oneshot"):
        super().__init__(name=name, delay=0)
