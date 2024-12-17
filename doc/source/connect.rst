How to start BAC0
===================================================
Intro
----------------------------------------

BAC0 is a library that will allow you to interact with BACnet devices. It relies on bacpypes3 and take advantages of the features of asyncio to provide fast and efficient communication with BACnet devices.

To start using BAC0, you will need to import the library and create a BAC0 object. This object will be the main object that will allow you to interact with the BACnet network.

More than one BAC0 object can be created but only one connection by interface is supported.

Typically, we'll call this object 'bacnet' to illustrate that it represents the access point to the BACnet network. But you can call it like you want.

This object will be used to interact with the BACnet network. It will be used to discover devices, read and write properties, trend points, etc.

This object will also be used as a BACnet device itself, serving BACnet objects to the network.

To create a BAC0 object, you will need to use the start() function. This function will create the object and connect it to the network.

.. note :: 
    Legacy BAC0 was available in 2 flavours : lite and complete. This is not the case anymore. I have merged the two versions into one. All web services have been deprecated letting other softwares like Grafana or InfluxDB to take care of the trending features.

When creating the connection to the network, BAC0 needs to know the ip network of the interface on which it will work. It also needs to know the subnet mask (as BACnet operations often use broadcast messages).If you don't provide one, BAC0 will try to detect the interface for you.

.. note::
    Legacy BAC0 have been tested with Pythonista (iOS) to a certain point. This is not the case for this version where I haven't tested this and have no plan to support it.

How to run async code
----------------------------------------

To run async code interactively (so you can explore the library or your BACnet network), you can use different ways. Running standalone scripts are somewhat different and we'll cover that later.

The first way is to use the REPL by calling : `python -m asyncio`. This will start the asyncio REPL and you will be able to run async code. This is the recommended way to run async code interactively.

Another way is to use a Jupyter Notebook. This is also a good way to run async code interactively. They can even run directly inside your browser or code editor using .ipynb files.

Define a bacnet application
----------------------------------------

Example::

    import BAC0
    bacnet = BAC0.start()
    # or specify the IP you want to use / bacnet = BAC0.start(ip='192.168.1.10/24')
    # by default, it will attempt an internet connection and use the network adapter
    # connected to the internet.
    # Specifying the network mask will allow the usage of a local broadcast address
    # like 192.168.1.255 instead of the global broadcast address 255.255.255.255
    # which could be blocked in some cases.

Dependencies and nice to hace features
--------------------------------------------
BAC0 is a library that relies on several other libraries to function effectively. The main library is bacpypes3, a BACnet stack that facilitates interaction with BACnet devices. BAC0 serves as a wrapper around bacpypes3, simplifying these interactions.

In this new version, rich is used to enhance console output, making it more readable. While not required, it improves the user experience. Similarly, Pandas is utilized for handling historical data, easing the process of working with such data.

Additionally, python-dotenv is employed to load environment variables from a .env file, simplifying the management of these variables. For data storage, sqlite3 is used to maintain a local database when devices are disconnected, and InfluxDB is used for storing data in a time series database. Both are optional but provide convenient data storage solutions.

Asynchronous programming
**************************
BAC0 is based on the new bacpypes3 which highly relies on asyncio. This means that you will have to use the asyncio library to interact with BAC0. This is not a big deal as asyncio is now part of the standard library and is easy to use. But it brings some changes in the way you will write your code.
Typically, all requests to read information on the network will be required to be awaited. This is done to allow the event loop to continue to run and not block the execution of the program. Some functions will not require to be awaited, for example, write requests for which we don't need to receive an message back. 

Asynchronous programming brings some overhead in the way you will write your code. But it also brings a lot of advantages. For example, you can now write code that will be able to do multiple things at the same time. This is really useful when you want to read multiple points on the network at the same time. Your code will run faster.

Lite vs Complete vs connect vs start
*****************
This version of BAC0 present only one way to create a BAC0 object. The function `start()` is the preferred way to create a BAC0 object. This function will create a BAC0 object and connect it to the network. To maintain compatibility with previous versions, the functions `connect()` and `lite()` are still available. They are exact equivalent of `start()`.


Start
.............

When you start BAC0, you will have a BAC0 object that will be able to interact with the BACnet network. This object will be able to discover devices, read and write properties, trend points, etc. But before doing so, you will need to know some details about the network you want to connect to.
Using the same subnet is really important as BACnet relies on broadcast messages to communicate. If you don't know the subnet, BAC0 will try to find it for you. But it is always better to provide it.
If you need to connect to a network that is not on the same subnet as the one you are on, you will need to provide the IP address of a BBMD (BACnet Broadcast Management Device) that will be able to route the messages to the network you want to connect to. 

BAC0 can act as a BBMD itself and route messages to other networks. But in simple cases where you will only want to explore the network, being configured as a foreign device is enough. 

Details about configuring BAC0 as a foreign device or a BBMD are available in the documentation.

To do so, use the syntax::

    bacnet = BAC0.start(ip='xxx.xxx.xxx.xxx/mask')


> Device ID 
> 
> It's possible to define the device ID you want in your BAC0 instance by
> using the `deviceId` argument `bacnet = BAC0.start(ip='xxx.xxx.xxx.xxx/mask', deviceId=1234)`.
    

Use BAC0 on a different subnet (Foreign Device)
***************************************************
In some situations (like using BAC0 with a VPN using TUN) your BAC0 instance
will run on a different subnet than the BACnet/IP network.

BAC0 support being used as a foreign device to cover those cases.

You must register to a BBMD (BACnet Broadcast Management Device) that will organize
broadcast messages so they can be sent through diferent subnet and be available for BAC0.

To do so, use the syntax::

    my_ip = '10.8.0.2/24'
    bbmdIP = '192.168.1.2:47808'
    bbmdTTL = 900
    bacnet = BAC0.start(ip='xxx.xxx.xxx.xxx/mask', bbdmAddress=bbmdIP, bbmdTTL=bbmdTTL)
    
Discovering devices on a network
*********************************
BACnet protocole relies on "whois" and "iam" messages to search and find devices. Typically, 
those are broadcast messages that are sent to the network so every device listening will be 
able to answer to whois requests by a iam request.

By default, BAC0 will use "local broadcast" whois message. This mean that in some situation,
you will not see by default the global network. Local broadcast will not traverse subnets and 
won't propagate to MSTP network behind BACnet/IP-BACnet/MSTP router that are on the same subnet
than BAC0.

This is done on purpose because using "global broadcast" by default will create a great amount
of traffic on big BACnet network when all devices will send their "iam" response at the same
time.

Instead, it is recommended to be careful and try to find devices on BACnet networks one at a time.
For that though, you have to "already know" what is on your network. Which is not always the case.
This is why BAC0 will still be able to issue global broadcast whois request if explicitly told to do so.

The recommended function to use is ::

    bacnet.discover(networks=['listofnetworks'], limits=(0,4194303), global_broadcast=False)
    # networks can be a list of integers, a simple integer, or 'known'
    # By default global_broadcast is set to False 
    # By default, the limits are set to any device instance, user can choose to request only a
    # range of device instances (1000,1200) for instance


This function will trigger the whois function and get you results. It will also emit a special request
named 'What-si-network-number' to try to learn the network number actually in use for BAC0. As this function
have been added in the protocole 2008, it may not be available on all networks.

BAC0 will store all network number found in the property named `bacnet.known_network_numbers`. User can then 
use this list to work with discover and find everything on the network without issuing global broadcasts.
To make a discover on known networks, use ::

    bacnet.discover(networks='known')

Also, all found devices can be seen in the property `bacnet.discoveredDevices`. This list is filled with all
the devices found when issuing whois requests.

BAC0 also provide a special functions to get a device table with details about the found devices. This function
will try to read on the network for the manufacturer name, the object name, and other informations to present 
all the devices in a pandas dataframe. This is for presentation purposes and if you want to explore the network, 
I recommend using discover. 

Devices dataframe ::

    await bacnet.devices

.. note::
    WARNING. `await bacnet.devices` may in some circumstances, be a bad choice when you want to discover
    devices on a network. A lot of read requests are made to look for manufacturer, object name, etc
    and if a lot of devices are on the network, it is recommended to use whois() and start from there.

BAC0 also support the 'Who-Is-Router-To-Network' request so you can ask the network and you will see the address
of the router for this particular BACnet network. The request 'Initialize-Router-Table' will be triggered on the 
reception of the 'I-Am-Router-To-Network' answer.

Once BAC0 will know which router leads to a network, the requests for the network inside the network will be 
sent directly to the router as unicast messages. For example ::

    # if router for network 3 is 192.168.1.2
    bacnet.whois('3:*') 
    # will send the request to 192.168.1.2, even if by default, a local broadcast would sent the request
    # to 192.168.1.255 (typically with a subnet 255.255.255.0 or /24)

Ping devices (monitoring feature)
**********************************
BAC0 includes a way to ping constantly the devices that have been registered. 
This way, when devices go offline, BAC0 will disconnect them until they come back
online. This feature can be disabled if required when declaring the network ::

    bacnet = BAC0.start(ping=False)
    
By default, the feature is activated.

When reconnecting after being disconnected, a complete rebuild of the device is done.
This way, if the device have changed (a download have been done and point list changed)
new points will be available. Old one will not.

.. note::
    WARNING. When BAC0 disconnects a device, it will try to save the device to SQL.

Routing Table
***************
BACnet communication trough different networks is made possible by the different 
routers creating "routes" between the subnet where BAC0 live and the other networks.
When a network discovery is made by BAC0, informations about the detected routes will
be saved (actually by the bacpypes stack itself) and for reference, BAC0 offers a way 
to extract the information ::

    await bacnet.routing_table

This will return a dict with all the available information about the routes in this form : 

await bacnet.routing_table
Out[5]: {'192.168.211.3': Source Network: None | Address: 192.168.211.3 | Destination Networks: {303: 0} | Path: (1, 303)}
