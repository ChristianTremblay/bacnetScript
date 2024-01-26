#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 by Christian Tremblay, P.Eng <christian.tremblay@servisys.com>
# Licensed under LGPLv3, see file LICENSE in this source tree.
#
"""
Lite is the base class to create a BACnet network
It uses provided args to register itself as a device in the network
and allow communication with other devices.

"""
import typing as t

# --- standard Python modules ---
import weakref
from collections import namedtuple

from BAC0.scripts.Base import Base

from ..core.devices.Device import RPDeviceConnected, RPMDeviceConnected
from ..core.devices.Points import Point
from ..core.devices.Trends import TrendLog
from ..core.devices.Virtuals import VirtualPoint
from ..core.functions import Calendar
from ..core.functions.Alias import Alias

# from ..core.functions.legacy.cov import CoV
# from ..core.functions.legacy.DeviceCommunicationControl import (
#    DeviceCommunicationControl,
# )
from ..core.functions.Discover import Discover
from ..core.functions.EventEnrollment import EventEnrollment
from ..core.functions.GetIPAddr import HostIP

# from ..core.functions.legacy.Reinitialize import Reinitialize
from ..core.functions.Schedule import Schedule
from ..core.functions.Text import TextMixin
from ..core.functions.TimeSync import TimeSync
from ..core.io.IOExceptions import (
    NoResponseFromController,
    NumerousPingFailures,
    Timeout,
    UnrecognizedService,
)
from ..core.io.Read import ReadProperty
from ..core.io.Simulate import Simulation
from ..core.io.Write import WriteProperty

# from ..core.io.asynchronous.Write import WriteProperty
from ..core.utils.notes import note_and_log
from ..infos import __version__ as version

# --- this application's modules ---
from ..tasks.RecurringTask import RecurringTask

# from ..tasks.legacy.UpdateCOV import Update_local_COV

try:
    from ..db.influxdb import ConnectionError, InfluxDB

    INFLUXDB = True
except ImportError:
    INFLUXDB = False

from bacpypes3.pdu import Address

# ------------------------------------------------------------------------------


@note_and_log
class Lite(
    Base,
    Discover,
    Alias,
    EventEnrollment,
    ReadProperty,
    WriteProperty,
    # Simulation,
    TimeSync,
    # Reinitialize,
    # DeviceCommunicationControl,
    # CoV,
    Schedule,
    # Calendar,
    TextMixin,
):
    """
    Build a BACnet application to accept read and write requests.
    [Basic Whois/IAm functions are implemented in parent BasicScript class.]
    Once created, execute a whois() to build a list of available controllers.
    Initialization requires information on the local device.

    :param ip='127.0.0.1': Address must be in the same subnet as the BACnet network
        [BBMD and Foreign Device - not supported]

    """

    def __init__(
        self,
        ip: t.Optional[str] = None,
        port: t.Optional[int] = None,
        mask: t.Optional[int] = None,
        bbmdAddress=None,
        bbmdTTL: int = 0,
        bdtable=None,
        ping: bool = True,
        ping_delay: int = 300,
        db_params: t.Optional[t.Dict[str, t.Any]] = None,
        **params,
    ) -> None:
        self._log.info(
            "Starting BAC0 version {} ({})".format(
                version, self.__module__.split(".")[-1]
            )
        )
        self._log.info("Use BAC0.log_level to adjust verbosity of the app.")
        self._log.info("Ex. BAC0.log_level('silence') or BAC0.log_level('error')")

        self._log.debug("Configurating app")
        self._registered_devices = weakref.WeakValueDictionary()

        # Ping task will deal with all registered device and disconnect them if they do not respond.

        self._ping_task = RecurringTask(
            self.ping_registered_devices, delay=ping_delay, name="Ping Task"
        )
        if ping:
            self._ping_task.start()

        if ip is None:
            host = HostIP(port)
            ip_addr = host.address
        else:
            try:
                ip, subnet_mask_and_port = ip.split("/")
                try:
                    mask_s, port_s = subnet_mask_and_port.split(":")
                    mask = int(mask_s)
                    port = int(port_s)
                except ValueError:
                    mask = int(subnet_mask_and_port)
            except ValueError:
                ip = ip

            if not mask:
                mask = 24
            if not port:
                port = 47808
            ip_addr = Address("{}/{}:{}".format(ip, mask, port))
        self._log.info(
            f"Using ip : {ip_addr} on port {ip_addr.addrPort} | broadcast : {ip_addr.addrBroadcastTuple[0]}"
        )

        Base.__init__(
            self,
            localIPAddr=ip_addr,
            bbmdAddress=bbmdAddress,
            bbmdTTL=bbmdTTL,
            bdtable=bdtable,
            **params,
        )
        self._log.info("Device instance (id) : {boid}".format(boid=self.Boid))
        self.bokehserver = False
        self._points_to_trend = weakref.WeakValueDictionary()

        # Announce yourself
        # self.iam()

        # Do what's needed to support COV
        # self._update_local_cov_task = namedtuple(
        #    "_update_local_cov_task", ["task", "running"]
        # )
        # self._update_local_cov_task.task = Update_local_COV(
        #    self, delay=1, name="Update Local COV Task"
        # )
        # self._update_local_cov_task.task.start()
        # self._update_local_cov_task.running = True
        # self._log.info("Update Local COV Task started (required to support COV)")

        # Activate InfluxDB if params are available
        if db_params and INFLUXDB:
            try:
                self.database = (
                    InfluxDB(db_params)
                    if db_params["name"].lower() == "influxdb"
                    else None
                )
                self._log.info(
                    "Connection made to InfluxDB bucket : {}".format(
                        self.database.bucket
                    )
                )
            except ConnectionError:
                self._log.error(
                    "Unable to connect to InfluxDB. Please validate parameters"
                )

    def register_device(
        self, device: t.Union[RPDeviceConnected, RPMDeviceConnected]
    ) -> None:
        oid = id(device)
        self._registered_devices[oid] = device

    def ping_registered_devices(self) -> None:
        """
        Registered device on a network (self) are kept in a list (registered_devices).
        This function will allow pinging thoses device regularly to monitor them. In case
        of disconnected devices, we will disconnect the device (which will save it). Then
        we'll ping again until reconnection, where the device will be bring back online.

        To permanently disconnect a device, an explicit device.disconnect(unregister=True [default value])
        will be needed. This way, the device won't be in the registered_devices list and
        BAC0 won't try to ping it.
        """
        for each in self.registered_devices:
            if isinstance(each, RPDeviceConnected) or isinstance(
                each, RPMDeviceConnected
            ):
                try:
                    self._log.debug(
                        "Ping {}|{}".format(
                            each.properties.name, each.properties.address
                        )
                    )
                    each.ping()
                    if each.properties.ping_failures > 3:
                        raise NumerousPingFailures

                except NumerousPingFailures:
                    self._log.warning(
                        "{}|{} is offline, disconnecting it.".format(
                            each.properties.name, each.properties.address
                        )
                    )
                    each.disconnect(unregister=False)

            else:
                device_id = each.properties.device_id
                addr = each.properties.address
                name = self.read("{} device {} objectName".format(addr, device_id))
                if name == each.properties.name:
                    each.properties.ping_failures = 0
                    self._log.info(
                        "{}|{} is back online, reconnecting.".format(
                            each.properties.name, each.properties.address
                        )
                    )
                    each.connect(network=self)
                    each.poll(delay=each.properties.pollDelay)

    @property
    def registered_devices(self):
        """
        Devices that have been created using BAC0.device(args)
        """
        return list(self._registered_devices.values())

    def unregister_device(self, device):
        """
        Remove from the registered list
        """
        oid = id(device)
        try:
            del self._registered_devices[oid]
        except KeyError:
            pass

    def add_trend(self, point_to_trend: t.Union[Point, TrendLog, VirtualPoint]) -> None:
        """
        Add point to the list of histories that will be handled by Bokeh

        Argument provided must be of type Point or TrendLog
        ex. bacnet.add_trend(controller['point_name'])
        """
        if (
            isinstance(point_to_trend, Point)
            or isinstance(point_to_trend, TrendLog)
            or isinstance(point_to_trend, VirtualPoint)
        ):
            oid = id(point_to_trend)
            self._points_to_trend[oid] = point_to_trend
        else:
            raise TypeError("Please provide point containing history")

    def remove_trend(
        self, point_to_remove: t.Union[Point, TrendLog, VirtualPoint]
    ) -> None:
        """
        Remove point from the list of histories that will be handled by Bokeh

        Argument provided must be of type Point or TrendLog
        ex. bacnet.remove_trend(controller['point_name'])
        """
        if (
            isinstance(point_to_remove, Point)
            or isinstance(point_to_remove, TrendLog)
            or isinstance(point_to_remove, VirtualPoint)
        ):
            oid = id(point_to_remove)
        else:
            raise TypeError("Please provide point or trendLog containing history")
        if oid in self._points_to_trend.keys():
            del self._points_to_trend[oid]

    @property
    async def devices(self) -> t.List[t.Tuple[str, str, str, int]]:
        """
        This property will create a good looking table of all the discovered devices
        seen on the network.

        For that, some requests will be sent over the network to look for name,
        manufacturer, etc and in big network, this could be a long process.
        """
        lst = []
        for device in list(self.discoveredDevices or {}):
            objId, addr = device
            devId = objId[1]  # you can do better

            try:
                deviceName, vendorName = await self.readMultiple(
                    f"{addr} device {devId} objectName vendorName"
                )
            except (UnrecognizedService, ValueError):
                self._log.warning(f"Unrecognized service for {addr} | {devId}")
                try:
                    deviceName = await self.read(f"{addr} device {devId} objectName")
                    vendorName = await self.read(f"{addr} device {devId} vendorName")
                except NoResponseFromController:
                    self._log.warning(f"No response from {addr} | {devId}")
                    continue
            except (NoResponseFromController, Timeout):
                self._log.warning(f"No response from {addr} | {devId}")
                continue
            lst.append((deviceName, vendorName, str(addr), devId))
        return lst  # type: ignore[return-value]

    @property
    def trends(self) -> t.List[t.Any]:
        """
        This will present a list of all registered trends used by Bokeh Server
        """
        return list(self._points_to_trend.values())

    def disconnect(self) -> None:
        self._log.debug("Disconnecting")
        for each in self.registered_devices:
            each.disconnect()
        super().disconnect()

    def __repr__(self) -> str:
        return "Bacnet Network using ip {} with device id {}".format(
            self.localIPAddr, self.Boid
        )

    def __getitem__(self, boid_or_localobject):
        item = self.this_application.app.objectName[boid_or_localobject]
        if item is None:
            for device in self._registered_devices:
                if str(device.properties.device_id) == str(boid_or_localobject):
                    return device
            self._log.error("{} not found".format(boid_or_localobject))
        else:
            return item
