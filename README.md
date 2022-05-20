SlicerWeb with Websocket Support
=========
An Extension of the SlicerWeb module that allows for WebSocket and WebSocket Secure communication

original module can be found here:
https://github.com/pieper/SlicerWeb


Installation
============

This module can now be run from any slicer 4.2 binary download (release or nightly).

Simply run slicer with these arguments:

 ./path/to/Slicer --additional-module-paths path/to/SlicerWeb/WebServer

where 'path/to' is replaced with the appropriate paths.  You could alternatively
register the path/to/SlicerWeb/WebServer in the Module paths of the Application Settings dialog.

Usage
=====

Go to the Servers->WebServer module tp load in the module

Select Start Server to launch the web server. If a private key and certificate are provided in the auth folder the server will automatically start in HTTPS mode and use WSS communication.

At the index page select WebSocket Demo to use the interactive WebSocket ui. a slice must be loaded into slicer. 
There is also a latency tester provided. This can be used to check the latency of the connection by comparing the time in browser to the time in slicer when the request was received. 

Access http://localhost:2016 or https://localhost:2016 with a web browser or alternatively use the static page launchers in the module.

NOTE: In order to use WSS with a self signed certificate you must first navigate to the index static page and accept/import the certificate. Some browsers such as chrome will still refuse a WSS connection with a self signed certificate so you must make sure the following flag is enabled:
chrome://flags/#allow-insecure-localhost

NOTE: some demos require a WebGL compatible browser.

Direct API access:
 
* get a json dump of the names of all nodes in mrml:

 http://localhost:2016/slicer/mrml

* get a png image of the threeD View

 http://localhost:2016/slicer/threeD

* get a png image of the yellow slice view

 http://localhost:2016/slicer/slice?view=yellow
 
 These endpoints are also available over websocket by connection to wss://localhost:2016/websocket, and communicating the remainder of the url 
 for example: slicer/slice?view=yellow or slicer/mrml 
 most results will need to be decoded to be useful as they will be sent in binary format


