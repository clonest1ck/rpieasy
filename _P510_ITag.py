#!/usr/bin/env python3
#############################################################################
####################### BLE iTag plugin for RPIEasy #########################
#############################################################################
#
# Can be used when BLE compatible Bluetooth dongle, and BluePy is installed.
# Do a BLE scan for the iTag ID, it's button can be used as an input.
#
# Copyright (C) 2018-2019 by Alexander Nagy - https://bitekmindenhol.blog.hu/
#
import plugin
import webserver
import rpieGlobals
import rpieTime
import misc
from bluepy import btle
import threading
import time
import lib.lib_blehelper as BLEHelper

class Plugin(plugin.PluginProto):
 PLUGIN_ID = 510
 PLUGIN_NAME = "Input - BLE iTag"
 PLUGIN_VALUENAME1 = "Button"
 PLUGIN_VALUENAME2 = "Connected"

 ITAG_UUID_SVC_GENERIC  = "00001800-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_NAME         = "00002a00-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_SVC_ALARM    = "00001802-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_ALARM        = "00002a06-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_SVC_BATTERY  = "0000180f-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_BATTERY      = "00002a19-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_SVC_KEPYRESS = "0000ffe0-0000-1000-8000-00805f9b34fb"
 ITAG_UUID_KEYPRESS     = "0000ffe1-0000-1000-8000-00805f9b34fb"

 def __init__(self,taskindex): # general init
  plugin.PluginProto.__init__(self,taskindex)
  self.dtype = rpieGlobals.DEVICE_TYPE_BLE
  self.vtype = rpieGlobals.SENSOR_TYPE_DUAL
  self.valuecount = 2
  self.senddataoption = True
  self.recdataoption = False
  self.timeroption = True
  self.timeroptional = True
  self.connected = False
  self.BLEPeripheral = False
  self.keypressedhandle = False
  self.cproc = False
  self.waitnotifications = False
  self.conninprogress = False
  self.blestatus = None

 def webform_load(self): # create html page for settings
  bledevs = BLEHelper.find_hci_devices()
  options = []
  optionvalues = []
  if bledevs:
   for bd in bledevs:
    options.append(bd)
    try:
     optionvalues.append(int(bd[3:]))
    except:
     optionvalues.append(bd[3:])
  webserver.addFormSelector("Local Device","plugin_510_dev",len(options),options,optionvalues,None,int(self.taskdevicepluginconfig[3]))
  webserver.addFormTextBox("Device Address","plugin_510_itagaddr",str(self.taskdevicepluginconfig[0]),20)
  webserver.addFormNote("Enable blueetooth then <a href='blescanner'>scan iTag address</a> first.")
  webserver.addFormNote("This plugin needs continous connection so WILL NOT WORK WITH scanner plugin on the same dongle!")
  webserver.addFormNumericBox("Reconnect time","plugin_510_reconnect",self.taskdevicepluginconfig[1],5,240)
  webserver.addUnit("s")
  options = ["Button+Connection","Button","Connection"]
  optionvalues = [0,1,2]
  webserver.addFormSelector("Return state of","plugin_510_ret",len(options),options,optionvalues,None,self.taskdevicepluginconfig[2])
  return True

 def webform_save(self,params): # process settings post reply
  self.taskdevicepluginconfig[0] = str(webserver.arg("plugin_510_itagaddr",params)).strip()
  try:
   self.taskdevicepluginconfig[1] = int(webserver.arg("plugin_510_reconnect",params))
  except:
   self.taskdevicepluginconfig[1] = 30
  if self.taskdevicepluginconfig[1] < 5:
   self.taskdevicepluginconfig[1] = 5
  try:
   self.taskdevicepluginconfig[2] = int(webserver.arg("plugin_510_ret",params))
  except Exception as e:
   print(e)
   self.taskdevicepluginconfig[2] = 0
  try:
   self.taskdevicepluginconfig[3] = int(webserver.arg("plugin_510_dev",params))
  except:
   self.taskdevicepluginconfig[3] = 0
  self.plugin_init()
  return True

 def plugin_init(self,enableplugin=None):
  plugin.PluginProto.plugin_init(self,enableplugin)
  self.decimals[0]=0
  self.decimals[1]=0
  if self.enabled:
   self.ports = str(self.taskdevicepluginconfig[0])
   if (self.connected): # check status at startup
    self.isconnected()
   if (self.connected):
    self.conninprogress = False
   if self.taskdevicepluginconfig[2]==0:
    self.vtype = rpieGlobals.SENSOR_TYPE_DUAL
    self.valuecount = 2
   else:
    self.vtype = rpieGlobals.SENSOR_TYPE_SWITCH
    self.valuecount = 1
#   self.set_value(1,0,False)
#   self.set_value(2,self.connected,False)       # advertise status at startup
   try:
     devnum = int(self.taskdevicepluginconfig[3])
     self.blestatus  = BLEHelper.BLEStatus[devnum]
   except:
     pass
   self.handlevalue(0,self.connected)
   self.plugin_senddata()
   if (self.connected == False and self.enabled): # connect if not connected
    self.handshake = False
    self.waitnotifications = False
    if len(self.taskdevicepluginconfig[0])>10:
     self.cproc = threading.Thread(target=self.connectproc)
     self.cproc.daemon = True
     self.cproc.start()
  else:
   self.ports = ""
   self.__del__()

 def handlevalue(self,state=0,conn=0,battery=255):
   if state==-1:
     state = self.uservar[0]
   if self.taskdevicepluginconfig[2]==0:
    if battery != 255:
     self.set_value(1,state,False,susebattery=battery)
    else:
     self.set_value(1,state,False)
    if conn==0:
     self.set_value(2,0,False,suserssi=-100,susebattery=0)
    else:
     self.set_value(2,conn,False)
   elif self.taskdevicepluginconfig[2]==1:
    if conn==0:
     self.set_value(1,state,False,suserssi=-100,susebattery=0)
    else:
     if battery != 255:
      self.set_value(1,state,False,susebattery=battery)
     else:
      self.set_value(1,state,False)
   elif self.taskdevicepluginconfig[2]==2:
    if conn==0:
     self.set_value(1,0,False,suserssi=-100,susebattery=0)
    else:
     if battery != 255:
      self.set_value(1,conn,False,susebattery=battery)
     else:
      self.set_value(1,conn,False)

 def connectproc(self):
   try:
    if self.blestatus.isscaninprogress():
     self.blestatus.requeststopscan(self.taskindex)
     return False
   except Exception as e:
    return False
   self.blestatus.registerdataprogress(self.taskindex)    
   prevstate = self.connected
   self.conninprogress = True
   try:
    misc.addLog(rpieGlobals.LOG_LEVEL_INFO,"BLE connection initiated to "+str(self.taskdevicepluginconfig[0]))
    self.BLEPeripheral = btle.Peripheral(str(self.taskdevicepluginconfig[0]),iface=self.taskdevicepluginconfig[3])
    self.connected = True
    self.afterconnection()
   except:
    self.setdisconnectstate()   # disconnected!
   self.conninprogress = False
   self.isconnected()
   publishchange = (self.connected != prevstate)
   if self.connected:
#    self.set_value(2,self.connected,publishchange)
    self.handlevalue(-1,self.connected)
   else:
    self.handlevalue(0,0)
#    self.set_value(1,0,False)
#    self.set_value(2,0,False,suserssi=-100,susebattery=0)
    if publishchange:
     self.plugin_senddata()
    misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"BLE connection failed "+str(self.taskdevicepluginconfig[0]))
    return False
   if self.connected and self.handshake:
    misc.addLog(rpieGlobals.LOG_LEVEL_INFO,"BLE connected to "+str(self.taskdevicepluginconfig[0]))
    self.waitnotifications = True
    while self.waitnotifications:
     try:
      self.BLEPeripheral.waitForNotifications(0.5)
     except Exception as e:
      self.waitnotifications = False
      self.setdisconnectstate()   # disconnected!
    self.setdisconnectstate(False)   # disconnected!

 def reconnect(self,tid):
  if self.enabled and self.conninprogress==False and self.isconnected()==False:
#     self.connected = False
     if len(self.taskdevicepluginconfig[0])>10:
      self.cproc = threading.Thread(target=self.connectproc)
      self.cproc.daemon = True
      self.cproc.start()

 def isconnected(self):
  if self.connected:
   try:
    namechar = self.BLEPeripheral.getServiceByUUID(self.ITAG_UUID_SVC_GENERIC).getCharacteristics(self.ITAG_UUID_NAME)[0]
    self.connected = True
   except:
    self.connected = False
  return self.connected

 def afterconnection(self):
   if self.connected and self.enabled:
    if self.handshake==False:
     compat = False
     name = ""
     try:
       namechar = self.BLEPeripheral.getServiceByUUID(self.ITAG_UUID_SVC_GENERIC).getCharacteristics(self.ITAG_UUID_NAME)[0]
       name = namechar.read().decode("utf-8")
     except Exception as e:
       misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"BLE Name error: "+str(e))
       self.setdisconnectstate(False)   # disconnected!
     if (str(name).upper()[:4] == "ITAG"):
      compat = True #      print("Supported tag: ",str(name))
     else:
      compat = False#      print("Not supported tag: ",str(name))
      misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"BLE Name not supported: "+str(name))
     if compat:
      try:
       self.batterychar = self.BLEPeripheral.getCharacteristics(1,0xFF,self.ITAG_UUID_BATTERY)[0]
      except:
       misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"Battery service error")
      try:
       kpchar = self.BLEPeripheral.getCharacteristics(1,0xFF,self.ITAG_UUID_KEYPRESS)[0]
       self.keypressedhandle = kpchar.getHandle()
      except:
       misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"Keypress service error")
     self.handshake = True
    if self.keypressedhandle:
       self.BLEPeripheral.setDelegate( BLEEventHandler(self.callbackfunc,self.keypressedhandle) )

 def setdisconnectstate(self,tryreconn=True):
  self.blestatus.unregisterdataprogress(self.taskindex)
  if self.connected:
    self.connected = False
    self.handlevalue(0,0)
#    self.set_value(1,0,False)
#    self.set_value(2,0,False,suserssi=-100,susebattery=0)
    self.plugin_senddata()
  if tryreconn and self.enabled:
   rpieTime.addsystemtimer(int(self.taskdevicepluginconfig[1]),self.reconnect,[-1])

 def callbackfunc(self,data="",data2=None):
  if self.enabled:
   battery = self.report_battery()
   aval = self.uservar[0]
   try:
    aval = float(aval)
   except:
    aval = 0
   if aval==0:
    aval=1
   else:
    aval=0
#   if float(self.uservar[1])!=1:
#    self.set_value(2,1,False)
   self.handlevalue(aval,self.connected,battery)
#   self.set_value(1,aval,False,susebattery=battery)
   self.plugin_senddata()

 def __del__(self):
  self.waitnotifications = False
  try:
   self.blestatus.unregisterdataprogress(self.taskindex)
   self.BLEPeripheral.disconnect()
   self.cproc._stop()
  except:
   pass

 def plugin_exit(self):
  try:
   self.__del__()
  except:
   pass
  return True

# def __exit__(self,type,value,traceback):
#  self.__del__()

 def report_battery(self): # imlemented but as i tested device always returns 99% battery no matter what
  battery = 255
  if (self.connected):
   try:
    if self.batterychar != None:
     battres = self.batterychar.read()
     battery = battres[0]
    else:
     battery = 255
   except:
    battery = 255
    self.setdisconnectstate()
  return float(battery)

class BLEEventHandler(btle.DefaultDelegate):
    def __init__(self,keypressed_callback,KPHANDLE):
        self.keypressed_callback = keypressed_callback
        self.keypressed_handle = KPHANDLE
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        if (cHandle==self.keypressed_handle):
         self.keypressed_callback(data[0]) # print("Button pressed")
