# -*- coding: utf-8 -*-

from __future__ import division
import numpy as np
import datetime
import csv
import pickle
import time,calendar,datetime
import warnings
import sys
import os
import random
import string
from copy import deepcopy
from collections import OrderedDict

import namelist #parser for fortran namelist files

try: 
	import numexpr as ne
	neAvail = True
except:
	warnings.warn("numexpr not available", Warning)
	neAvail = False

import meteoSI
try: 
	from pyPamtraLibWrapper import PamtraFortranWrapper
except: 
	warnings.warn("pyPamtraLib not available", Warning)

try:
	import pp
except:
	warnings.warn("parallel python not available", Warning)

missingNumber=-9999.

class pyPamtra(object):
	'''
	Class for pamtra calculations. Initalisations fill dictonary 'set' with default values and 
	also fills 'dimensions' and 'units'
	
	'''
	def __init__(self):
		#set setting default values
	
		self.nmlSet = OrderedDict() #settings which are required for the nml file. keeping the order is important for Fortran""

		self.nmlSet["verbose_mode"] = dict()
		self.nmlSet["inoutput_mode"] = dict()
		self.nmlSet["output"] = dict()
		self.nmlSet["run_mode"] = dict()
		self.nmlSet["surface_params"] = dict()
		self.nmlSet["gas_abs_mod"] = dict()
		self.nmlSet["hyd_opts"] = dict()
		self.nmlSet["cloud_params"] = dict()
		self.nmlSet["ice_params"] = dict()
		self.nmlSet["rain_params"] = dict()
		self.nmlSet["snow_params"] = dict()
		self.nmlSet["graupel_params"] = dict()
		self.nmlSet["hail_params"] = dict()
		self.nmlSet["moments"] = dict()
		
		self.nmlSet["verbose_mode"]["verbose"] = 0
		
		self.nmlSet["inoutput_mode"]["dump_to_file"]=False
		self.nmlSet["inoutput_mode"]["tmp_path"]='/tmp/'
		self.nmlSet["inoutput_mode"]["data_path"]='/home/mech/models/pamtra/data/'
		self.nmlSet["inoutput_mode"]["crm_case"]=''
		self.nmlSet["inoutput_mode"]["crm_data"]=''
		self.nmlSet["inoutput_mode"]["crm_data2"]=''
		self.nmlSet["inoutput_mode"]["crm_constants"]=''
		self.nmlSet["inoutput_mode"]["jacobian_mode"]=False #profile 1,1 is reference, for all other collums only layers with different values are calculated
		
		self.nmlSet["output"]["obs_height"]=833000.
		self.nmlSet["output"]["units"]='T'
		self.nmlSet["output"]["outpol"]='VH'
		self.nmlSet["output"]["creator"]='pyPamtrauser'
		self.nmlSet["output"]["zeSplitUp"]=True # only locally in PYpamtra
		self.nmlSet["output"]["activeLogScale"]=True

		self.nmlSet["run_mode"]["active"]=True
		self.nmlSet["run_mode"]["passive"]=True
		self.nmlSet["run_mode"]["rt_mode"]="rt4"
		
		self.nmlSet["surface_params"]["ground_type"]='S'
		self.nmlSet["surface_params"]["salinity"]=33.0
		self.nmlSet["surface_params"]["emissivity"]=0.6

		self.nmlSet["gas_abs_mod"]["lgas_extinction"]=True
		self.nmlSet["gas_abs_mod"]["gas_mod"]='R98'

		self.nmlSet["hyd_opts"]["lhyd_extinction"]=True
		self.nmlSet["hyd_opts"]["lphase_flag"]= True

		self.nmlSet["cloud_params"]["SD_cloud"]='C'
		
		self.nmlSet["ice_params"]["SD_ice"]='C'
		self.nmlSet["ice_params"]["EM_ice"]='mieic'
		
		self.nmlSet["rain_params"]["SD_rain"]='C' 
		self.nmlSet["rain_params"]["N_0rainD"]=8.0
		self.nmlSet["rain_params"]["use_rain_db"]=False
		
		self.nmlSet["snow_params"]["SD_snow"]='C' 
		self.nmlSet["snow_params"]["use_snow_db"]=False		
		self.nmlSet["snow_params"]["as_ratio"]=0.5		
		self.nmlSet["snow_params"]["N_0snowDsnow"]=7.628 
		self.nmlSet["snow_params"]["EM_snow"]='densi' 
		self.nmlSet["snow_params"]["snow_density"]=200.
		self.nmlSet["snow_params"]["SP"]=0.2 
		self.nmlSet["snow_params"]["isnow_n0"]=1
		self.nmlSet["snow_params"]["liu_type"]=8

		self.nmlSet["graupel_params"]["SD_grau"]='C' 
		self.nmlSet["graupel_params"]["N_0grauDgrau"]=4.0 
		self.nmlSet["graupel_params"]["EM_grau"]='densi'
		self.nmlSet["graupel_params"]["graupel_density"]=400.

		self.nmlSet["hail_params"]["SD_hail"]='C' 
		self.nmlSet["hail_params"]["N_0hailDhail"]=4.0 
		self.nmlSet["hail_params"]["EM_hail"]='densi'
		self.nmlSet["hail_params"]["hail_density"]=917.

		self.nmlSet["moments"]["n_moments"]=1
		self.nmlSet["moments"]["moments_file"]='snowCRYSTAL'
		
		#all settings which do not go into the nml file go here:
		self.set = dict()
		self.set["pyVerbose"] = 0
		self.set["freqs"] = []
		self.set["nfreqs"] = 0
		self.set["namelist_file"] = "pyPamtra_namelist_"+''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(5))+".nml.tmp"

				
		self._nmlDefaultKeys = list()
		for keyGr in self.nmlSet.keys()	:  
			for key in self.nmlSet[keyGr].keys():
				self._nmlDefaultKeys.append(key)
		
		self._nmlDefaultValues = deepcopy(self.nmlSet)
		    
		self.dimensions = dict()
		
		self.dimensions["unixtime"] = ["ngridx","ngridy"]
		
		self.dimensions["ngridx"] = []
		self.dimensions["ngridy"] = []
		self.dimensions["nlyrs"] = ["ngridx","ngridy"]
		
		self.dimensions["model_i"] = ["ngridx","ngridy"]
		self.dimensions["model_j"] = ["ngridx","ngridy"]
		self.dimensions["lat"] = ["ngridx","ngridy"]
		self.dimensions["lon"] = ["ngridx","ngridy"]
		self.dimensions["lfrac"] = ["ngridx","ngridy"]
		self.dimensions["wind10u"] = ["ngridx","ngridy"]
		self.dimensions["wind10v"] = ["ngridx","ngridy"]
		
		self.dimensions["iwv"] = ["ngridx","ngridy"]
		self.dimensions["cwp"] = ["ngridx","ngridy"]
		self.dimensions["iwp"] = ["ngridx","ngridy"]
		self.dimensions["rwp"] = ["ngridx","ngridy"]
		self.dimensions["swp"] = ["ngridx","ngridy"]
		self.dimensions["gwp"] = ["ngridx","ngridy"]
		self.dimensions["hwp"] = ["ngridx","ngridy"]
		
		self.dimensions["hgt_lev"] = ["ngridx","ngridy","max_nlyrs+1"]
		self.dimensions["temp_lev"] = ["ngridx","ngridy","max_nlyrs+1"]
		self.dimensions["p_lev"] = ["ngridx","ngridy","max_nlyrs+1"]
		self.dimensions["relhum_lev"] = ["ngridx","ngridy","max_nlyrs+1"]
		
		self.dimensions["cwc_q"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["iwc_q"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["rwc_q"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["swc_q"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["gwc_q"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["hwc_q"] = ["ngridx","ngridy","max_nlyrs"]
		
		self.dimensions["cwc_n"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["iwc_n"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["rwc_n"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["swc_n"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["gwc_n"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["hwc_n"] = ["ngridx","ngridy","max_nlyrs"]
		
		self.dimensions["hgt"] = ["ngridx","ngridy","max_nlyrs"]
		self.dimensions["Ze"] = ["gridx","gridy","lyr","frequency"]
		self.dimensions["Att_hydros"] = ["gridx","gridy","lyr","frequency"]
		self.dimensions["Att_atmo"] = ["gridx","gridy","lyr","frequency"]
		self.dimensions["tb"] = ["gridx","gridy","outlevels","angles","frequency","stokes"]

		
		self.units = dict()
		
		self.units["unixtime"] = "seconds since 1970-01-01 00:00"
		
		self.units["ngridx"] = "-"
		self.units["ngridy"] = "-"
		self.units["nlyrs"] = "-"
		
		self.units["model_i"] = "-"
		self.units["model_j"] = "-"
		self.units["lat"] = "deg.dec"
		self.units["lon"] = "deg.dec"
		self.units["lfrac"] = "-"
		self.units["wind10u"] = "m/s"
		self.units["wind10v"] = "m/s"
		
		self.units["iwv"] = "kg/m^2"
		self.units["cwp"] = "kg/m^2"
		self.units["iwp"] = "kg/m^2"
		self.units["rwp"] = "kg/m^2"
		self.units["swp"] = "kg/m^2"
		self.units["gwp"] = "kg/m^2"
		self.units["hwp"] = "kg/m^2"
		
		self.units["hgt_lev"] = "m"
		self.units["temp_lev"] = "K"
		self.units["p_lev"] = "Pa"
		self.units["relhum_lev"] = "1"
		
		self.units["cwc_q"] = "kg/kg"
		self.units["iwc_q"] = "kg/kg"
		self.units["rwc_q"] = "kg/kg"
		self.units["swc_q"] = "kg/kg"
		self.units["gwc_q"] = "kg/kg"
		self.units["hwc_q"] = "kg/kg"

		self.units["cwc_n"] = "#/kg"
		self.units["iwc_n"] = "#/kg"
		self.units["rwc_n"] = "#/kg"
		self.units["swc_n"] = "#/kg"
		self.units["gwc_n"] = "#/kg"
		self.units["hwc_n"] = "#/kg"
		
		self.units["hgt"] = "m"
		self.units["Ze"] = "dBz OR mm^6 m^-3"
		self.units["Att_hydros"] = "dB OR linear"
		self.units["Att_atmo"] = "dB OR linear"
		self.units["tb"] = "K"
	
		self._nstokes = 2
		self._noutlevels = 2
		self._nangles = 32
		
		self.p = dict()
		self._helperP = dict()
		self.r = dict()
		
	def writeNmlFile(self,nmlFile):
		for keygr in self.nmlSet.keys():
			for key in self.nmlSet[keygr].keys():
				if key not in self._nmlDefaultKeys:
					warnings.warn("Warning can not parse setting: "+str(key))
					
					
		f = open(nmlFile,"w")
		for keygr in self.nmlSet.keys():
			f.write("&%s\n\r"%keygr)
			for key in self.nmlSet[keygr].keys():
				if self.set["pyVerbose"] > 1: print "write: ", keygr, key
				if type(self._nmlDefaultValues[keygr][key])==bool:
					value = str(self.nmlSet[keygr][key]).lower()
					f.write("%s=.%s.\n\r"%(key,value,))
				elif type(self._nmlDefaultValues[keygr][key]) in [int,np.int32,np.int64]:
					value = int(self.nmlSet[keygr][key])
					f.write("%s=%i\n\r"%(key,value,))	
				elif type(self._nmlDefaultValues[keygr][key]) in [float,np.float32,np.float64]:
					value = np.float64(self.nmlSet[keygr][key])
					f.write("%s=%f\n\r"%(key,value,))	
				elif type(self._nmlDefaultValues[keygr][key]) in [str]:
					value = str(self.nmlSet[keygr][key])
					f.write("%s='%s'\n\r"%(key,value,))
				else:
					raise ValueError("cannot determine type of nml key "+ key)
			f.write("/\n\r")
		f.close()

	def readNmlFile(self,inputFile):
		"""
		read classical Pamtra Namelist File from inputFile
		"""
		
		nmlFile = namelist.Namelist(inputFile)
		if nmlFile == {}:
			raise IOError("file not found: "+inputFile)
		
		for key in nmlFile.keys():
			for subkey in nmlFile[key]["par"][0].keys():
				if subkey in self._nmlDefaultKeys:
					if nmlFile[key]["par"][0][subkey][0] == ".true.": value = True
					elif nmlFile[key]["par"][0][subkey][0] == ".false.": value = False
					else: value = nmlFile[key]["par"][0][subkey][0]
					self.nmlSet[key][subkey] = value
					if self.set["pyVerbose"] > 1: print subkey, ":", value
				elif self.set["pyVerbose"] > 0:
					print "Setting '"+ subkey +"' from '"+ inputFile +"' skipped."
		if self.set["pyVerbose"] > 1: print "reading nml file done: ", inputFile
		return
		
	def readPamtraProfile(self,inputFile):
		"""
		read classical pamtra profile from file
		"""
		
		f = open(inputFile,"r")
		g = csv.reader(f,delimiter=" ",skipinitialspace=True)
		year,month,day,time, self.p["ngridx"], self.p["ngridy"], self.p["nlyrs"], self.p["deltax"], self.p["deltay"] = g.next()
		
		self.p["unixtime"] = calendar.timegm(datetime.datetime(year = int(year), month = int(month), day = int(day), hour = int(time[0:2]), minute = int(time[2:4]), second = 0).timetuple())
		
		self.p["ngridx"] = int(self.p["ngridx"])
		self.p["ngridy"] = int(self.p["ngridy"])
		self.p["nlyrs"] = int(self.p["nlyrs"])
		self.p["max_nlyrs"] = deepcopy(self.p["nlyrs"])
		
		if self.p["max_nlyrs"] > 200:
			warnings.warn("Too many layers for pamtra (max:200): " + str(self.p["max_nlyrs"]),Warning)
		
		
		self._shape2D = (self.p["ngridx"],self.p["ngridy"],)
		self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["nlyrs"],)
		self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["nlyrs"]+1,)
		
		self.p["model_i"] = np.zeros(self._shape2D)
		self.p["model_j"] = np.zeros(self._shape2D)
		self.p["lat"] = np.zeros(self._shape2D)
		self.p["lon"] = np.zeros(self._shape2D)
		self.p["lfrac"] = np.zeros(self._shape2D)
		self.p["wind10u"] = np.zeros(self._shape2D)
		self.p["wind10v"] = np.zeros(self._shape2D)
		
		self.p["iwv"] = np.zeros(self._shape2D)
		self.p["cwp"] = np.zeros(self._shape2D)
		self.p["iwp"] = np.zeros(self._shape2D)
		self.p["rwp"] = np.zeros(self._shape2D)
		self.p["swp"] = np.zeros(self._shape2D)
		self.p["gwp"] = np.zeros(self._shape2D)
		self.p["hwp"] = np.zeros(self._shape2D)
		
		self.p["hgt_lev"] = np.zeros(self._shape3Dplus)
		self.p["temp_lev"] = np.zeros(self._shape3Dplus)
		self.p["press_lev"] = np.zeros(self._shape3Dplus)
		self.p["relhum_lev"] = np.zeros(self._shape3Dplus)
		
		self.p["cwc_q"] = np.zeros(self._shape3D)
		self.p["iwc_q"] = np.zeros(self._shape3D)
		self.p["rwc_q"] = np.zeros(self._shape3D)
		self.p["swc_q"] = np.zeros(self._shape3D)
		self.p["gwc_q"] = np.zeros(self._shape3D)
		
		if int(self.nmlSet["moments"]["n_moments"]) == 1:
			self.p["hwc_q"] = np.ones(self._shape3D)*missingNumber
			self.p["cwc_n"] = np.ones(self._shape3D)*missingNumber
			self.p["iwc_n"] = np.ones(self._shape3D)*missingNumber
			self.p["rwc_n"] = np.ones(self._shape3D)*missingNumber
			self.p["swc_n"] = np.ones(self._shape3D)*missingNumber
			self.p["gwc_n"] = np.ones(self._shape3D)*missingNumber
			self.p["hwc_n"] = np.ones(self._shape3D)*missingNumber
			
			for x in np.arange(self.p["ngridx"]):
				for y in np.arange(self.p["ngridy"]):
					self.p["model_i"][x,y], self.p["model_j"][x,y] = np.array(np.array(g.next()),dtype=int)
					self.p["lat"][x,y], self.p["lon"][x,y], self.p["lfrac"][x,y],self.p["wind10u"][x,y],self.p["wind10v"][x,y]  = np.array(np.array(g.next()),dtype=float)
					self.p["iwv"][x,y],self.p["cwp"][x,y],self.p["iwp"][x,y],self.p["rwp"][x,y],self.p["swp"][x,y],self.p["gwp"][x,y] = np.array(np.array(g.next()),dtype=float)
					self.p["hgt_lev"][x,y,0],self.p["press_lev"][x,y,0],self.p["temp_lev"][x,y,0],self.p["relhum_lev"][x,y,0] = np.array(np.array(g.next()),dtype=float)
					for z in np.arange(self.p["nlyrs"]):
						self.p["hgt_lev"][x,y,z+1],self.p["press_lev"][x,y,z+1],self.p["temp_lev"][x,y,z+1],self.p["relhum_lev"][x,y,z+1],self.p["cwc_q"][x,y,z],self.p["iwc_q"][x,y,z],self.p["rwc_q"][x,y,z],self.p["swc_q"][x,y,z],self.p["gwc_q"][x,y,z] = np.array(np.array(g.next()),dtype=float)

		elif int(self.nmlSet["moments"]["n_moments"]) == 2:
			self.p["hwc_q"] = np.zeros(self._shape3D)
			self.p["cwc_n"] = np.zeros(self._shape3D)
			self.p["iwc_n"] = np.zeros(self._shape3D)
			self.p["rwc_n"] = np.zeros(self._shape3D)
			self.p["swc_n"] = np.zeros(self._shape3D)
			self.p["gwc_n"] = np.zeros(self._shape3D)
			self.p["hwc_n"] = np.zeros(self._shape3D)
			
			for x in np.arange(self.p["ngridx"]):
				for y in np.arange(self.p["ngridy"]):
					self.p["model_i"][x,y], self.p["model_j"][x,y] = np.array(np.array(g.next()),dtype=int)
					self.p["lat"][x,y], self.p["lon"][x,y], self.p["lfrac"][x,y],self.p["wind10u"][x,y],self.p["wind10v"][x,y]  = np.array(np.array(g.next()),dtype=float)
					self.p["iwv"][x,y],self.p["cwp"][x,y],self.p["iwp"][x,y],self.p["rwp"][x,y],self.p["swp"][x,y],self.p["gwp"][x,y],self.p["hwp"][x,y] = np.array(np.array(g.next()),dtype=float)
					self.p["hgt_lev"][x,y,0],self.p["press_lev"][x,y,0],self.p["temp_lev"][x,y,0],self.p["relhum_lev"][x,y,0] = np.array(np.array(g.next()),dtype=float)
					for z in np.arange(self.p["nlyrs"]):
						self.p["hgt_lev"][x,y,z+1],self.p["press_lev"][x,y,z+1],self.p["temp_lev"][x,y,z+1],self.p["relhum_lev"][x,y,z+1],self.p["cwc_q"][x,y,z],self.p["iwc_q"][x,y,z],self.p["rwc_q"][x,y,z],self.p["swc_q"][x,y,z],self.p["gwc_q"][x,y,z],self.p["hwc_q"][x,y,z],self.p["cwc_n"][x,y,z],self.p["iwc_n"][x,y,z],self.p["rwc_n"][x,y,z],self.p["swc_n"][x,y,z],self.p["gwc_n"][x,y,z],self.p["hwc_n"][x,y,z] = np.array(np.array(g.next()),dtype=float)
		else:
			raise IOError("n_moments mus be 1 or 2")


		#in PyPamtra I want relhum not in %
		self.p["relhum_lev"] = self.p["relhum_lev"]/100.

		#finally make an array from nlyrs and unixtime
		self.p["nlyrs"] = np.ones(self._shape2D,dtype=int)*self.p["nlyrs"]
		self.p["unixtime"] = np.ones(self._shape2D,dtype=int)*self.p["unixtime"]

		f.close()

	def createProfile(self,**kwargs):
		'''
		Function to create Pamtra Profiles.
		
		Variables ending on _lev mean level values, variables without are layer values (height vector one entry shorter!)!
		
		Everything is needed in SI units, relhum is in Pa/PA not %
		
		The following variables are mandatroy:
		hgt_lev, temp_lev, press_lev and (relhum_lev OR q)
		
		The following variables are optional and guessed if not provided:	"timestamp","lat","lon","lfrac","wind10u","wind10v","hgt_lev","cwc_q","iwc_q","rwc_q","swc_q","gwc_q"
		
		The integrated values are skipped if not provided, they have no effect on pamtra!:
		"iwv","cwp","iwp","rwp","swp","gwp"
		
		The following variables are only needed together with the 2 moments scheme!
		"hwc_q","hwp", "cwc_n","iwc_n","rwc_n","swc_n","gwc_n","hwc_n"
		'''
		allVars=["timestamp","lat","lon","lfrac","wind10u","wind10v","iwv","cwp","iwp","rwp","swp","gwp","hwp","hgt_lev","press_lev","temp_lev","relhum_lev","q","cwc_q","iwc_q","rwc_q","swc_q","gwc_q","hwc_q","cwc_n","iwc_n","rwc_n","swc_n","gwc_n","hwc_n"]
			
		for key in kwargs.keys():
			if key not in allVars:
				raise TypeError("Could not parse "+key)
		
		if not ("hgt_lev" in kwargs.keys() and "temp_lev" in kwargs.keys() and "press_lev" in kwargs.keys() and ("relhum_lev" in kwargs.keys() or "q" in kwargs.keys())):
			raise TypeError("I need hgt_lev and temp_lev and press_lev and (relhum_lev or q)!")
		
		noDims = len(np.shape(kwargs["hgt_lev"]))
		
		if noDims == 1:
			self.p["ngridx"] = 1
			self.p["ngridy"] = 1
		elif noDims == 2:
			self.p["ngridx"] = np.shape(kwargs["hgt_lev"])[0]
			self.p["ngridy"] = 1
		elif noDims == 3:
			self.p["ngridx"] = np.shape(kwargs["hgt_lev"])[0]
			self.p["ngridy"] = np.shape(kwargs["hgt_lev"])[1]
		else:
			print "Too many dimensions!"
			raise IOError
		
		self.p["max_nlyrs"] = np.shape(kwargs["hgt_lev"])[-1] -1
		
		if self.p["max_nlyrs"] > 200:
			warnings.warn("Too many layers for pamtra (max:200): " + str(self.p["max_nlyrs"]),Warning)
		
		#if np.any(self.p["nlyrs"] != self.p["max_nlyrs"]):
			#self._radiosonde = True
		#else:
			#self._radiosonde = False
			
		self._shape2D = (self.p["ngridx"],self.p["ngridy"],)
		self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],)
		self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"]+1,)
		
		self.p["nlyrs"] = np.sum(kwargs["hgt_lev"]!=missingNumber,axis=-1) -1
		self.p["nlyrs"] = self.p["nlyrs"].reshape(self._shape2D)
		
		self.p["hgt_lev"] = kwargs["hgt_lev"].reshape(self._shape3Dplus)
		self.p["temp_lev"] = kwargs["temp_lev"].reshape(self._shape3Dplus)
		self.p["press_lev"] = kwargs["press_lev"].reshape(self._shape3Dplus)

		self.p["deltax"] = 0.
		self.p["deltay"] = 0.

		self.p["model_i"] = np.array(np.where(self.p["press_lev"][:,:,0])[0]).reshape(self._shape2D) +1
		self.p["model_j"] = np.array(np.where(self.p["press_lev"][:,:,0])[1]).reshape(self._shape2D) +1

		if "timestamp" not in kwargs.keys():
			self.p["unixtime"] = np.ones(self._shape2D)* int(time.time())
			warnings.warn("timestamp set to now", Warning)
		else:
			if type(kwargs["timestamp"]) in (int,np.int32,np.int64,float,np.float32,np.float64) :
				self.p["unixtime"] = np.ones(self._shape2D,dtype=int)*kwargs["timestamp"]
			elif (type(kwargs["timestamp"]) == np.ndarray) or (type(kwargs["timestamp"]) == np.ma.masked_array):
				if kwargs["timestamp"].dtype in (int,np.int32,np.int64,float,np.float32,np.float64):
					self.p["unixtime"] = kwargs["timestamp"].reshape(self._shape2D)
				else:
					raise TypeError("timestamp entries have to be int or float objects")
			elif (type(kwargs["timestamp"]) == datetime):
				self.p["unixtime"] = np.ones(self._shape2D,dtype=int)*calendar.timegm(kwargs["timestamp"].timetuple())
			else:
				raise TypeError("timestamp has to be int, float or datetime object")
			
		for environment, preset in [["lat",50.938056],["lon",6.956944],["lfrac",1],["wind10u",0],["wind10v",0]]:
			if environment not in kwargs.keys():
				self.p[environment] = np.ones(self._shape2D)*preset
				warnings.warn("%s set to %s"%(environment,preset,), Warning)
			else:
				if type(kwargs[environment]) in (int,np.int32,np.int64,float,np.float32,np.float64):
					self.p[environment] = np.ones(self._shape2D) * kwargs[environment]
				else:
					self.p[environment] = kwargs[environment].reshape(self._shape2D)
		
		for qValue in ["cwc_q","iwc_q","rwc_q","swc_q","gwc_q","hwc_q"]:
			if qValue not in kwargs.keys():
				self.p[qValue] = np.zeros(self._shape3D)
				warnings.warn(qValue + " set to 0", Warning)
			else:
				self.p[qValue] = kwargs[qValue].reshape(self._shape3D)
				
		for hydroNo in ["cwc_n","iwc_n","rwc_n","swc_n","gwc_n","hwc_n"]:
			if hydroNo not in kwargs.keys():
				self.p[hydroNo] = np.ones(self._shape3D) * missingNumber
				warnings.warn(hydroNo + " set to -9999", Warning)
			else:
				self.p[hydroNo] = kwargs[hydroNo].reshape(self._shape3D)


		if "q" in kwargs.keys():
			self._helperP["q"] = kwargs["q"].reshape(self._shape3D)

		if "relhum_lev" in kwargs.keys():
			self.p["relhum_lev"] = kwargs["relhum_lev"].reshape(self._shape3Dplus)
		else:
			self._calcRelhum_lev()

		#clean up: remove all nans
		for key in self.p.keys():
			#apply only to arrays, lists or tupels
			if np.sum(np.shape(self.p[key])) > 0:
				self.p[key][np.isnan(self.p[key])] = missingNumber
		
		return


		
		
	def _calcPressTempRelhum(self):
		if set(("temp","relhum","press","dz")).issubset(self._helperP.keys()):
			return
		else:
			if self.set["pyVerbose"] > 0:
				print 'calculating "temp","relhum","press","dz"'
			self._helperP["temp"] = (self.p["temp_lev"][...,0:-1] + self.p["temp_lev"][...,1:])/2.
			self._helperP["relhum"] = (self.p["relhum_lev"][...,0:-1] + self.p["relhum_lev"][...,1:])/2.
			dz = np.diff(self.p["hgt_lev"],axis=-1)
			self._helperP["dz"] = dz
			
			#if not self._radiosonde:

				#p0 = self.p["press_lev"][...,0:-1]
				#p1 = self.p["press_lev"][...,1:]
				#xp = ne.evaluate("-1.*log(p1/p0)/dz")

			#else: #to allow array operations, cases with varying heights or invalid data have to be treated a bit differently:

			dz[dz<=0]=9999
			self._helperP["relhum"][self._helperP["relhum"]<=0] = 1
			self._helperP["temp"][self._helperP["temp"]<=0] = 1
			
			press_lev1 = deepcopy(self.p["press_lev"])
			press_lev1[press_lev1==missingNumber]=1
			
			p0 = press_lev1[...,0:-1]
			p1 = press_lev1[...,1:]
			
			if neAvail: xp = ne.evaluate("-1.*log(p1/p0)/dz")
			else: xp = -1.*np.log(p1/p0)/dz
			
			xp[xp==0] = 9999
				
			if neAvail: self._helperP["press"] = ne.evaluate("-1.*p0/xp*(exp(-xp*dz)-1.)/dz")
			else: self._helperP["press"] = -1.*p0/xp*(np.exp(-xp*dz)-1.)/dz
			
			del p0,p1,xp
				
			return

	def _calcQ(self):
		
		if set(("q",)).issubset(self._helperP.keys()):
			return
		else:
			self._calcPressTempRelhum()
			
			if self.set["pyVerbose"] > 0:
				print 'calculating "q"'
			self._helperP["q"] = meteoSI.rh2q(self._helperP["relhum"],self._helperP["temp"],self._helperP["press"])
			return

	def _calcQ_lev(self):
		if set(("q_lev",)).issubset(self._helperP.keys()):
			return
		else:
			if self.set["pyVerbose"] > 0:
				print 'calculating "q_lev"'
			qBot = self._helperP["q"][...,0:1] + 0.25*(self._helperP["q"][...,0:1]-self._helperP["q"][...,1:2])
			qTop = self._helperP["q"][...,-1:] + 0.25*(self._helperP["q"][...,-1:]-self._helperP["q"][...,-2:-1])
			qMid = (self._helperP["q"][...,0:-1] + self._helperP["q"][...,1:])/2.
			
			self._helperP["q_lev"] = np.concatenate((qBot,qMid,qTop),axis=-1)
			return

	def _calcMoistRho(self):
		if set(("rho_moist",)).issubset(self._helperP.keys()):
			return
		else:
			self._calcQ()
			self._calcPressTempRelhum()
			
			if self.set["pyVerbose"] > 0:
				print 'calculating "rho_moist"'

			self._helperP["rho_moist"] = meteoSI.moist_rho_q(self._helperP["press"],self._helperP["temp"],self._helperP["q"],self.p["cwc_q"],self.p["iwc_q"],self.p["rwc_q"],self.p["gwc_q"],self.p["swc_q"])
			return

	def _calcRelhum_lev(self):
		if set(("relhum_lev",)).issubset(self.p.keys()):
			return
		else:
			self._calcQ_lev()
			
			if self.set["pyVerbose"] > 0:
				print 'calculating "relhum_lev"'
				
			self.p["relhum_lev"] = meteoSI.q2rh(self._helperP["q_lev"],self.p["temp_lev"],self.p["press_lev"])
			return

	def _checkData(self):
		maxLimits = {"relhum_lev":2,"swc_q":0.05,"rwc_q":0.05,"cwc_q":0.05,"iwc_q":0.05,"gwc_q":0.05,"hwc_q":0.05,"temp_lev":320,"press_lev":110000}
		minLimits = {"relhum_lev":0,"swc_q":0,   "rwc_q":0,   "cwc_q":0,   "iwc_q":0   ,"gwc_q":0   ,"hwc_q":0   ,"temp_lev":170,"press_lev":1}
		for key in maxLimits.keys():
			if np.max(self.p[key]) > maxLimits[key]:
				raise ValueError("unrealistic value for "+ key + ": " +str(np.max(self.p[key])) + ", maximum is " + str(maxLimits[key]))
		for key in minLimits.keys():
			if len(self.p[key][self.p[key] != missingNumber]) > 0:
				if np.min(self.p[key][self.p[key] != missingNumber]) < minLimits[key]:
					raise ValueError("unrealistic value for "+ key + ": " +str(np.min(self.p[key])) + ", minimum is " + str(minLimits[key]))

	def filterProfiles(self,condition):
		'''
		discard profiles, which do not fullfill "condition" (2D boolean array)
		
		Note: If the initial field is a 2D grid, the field is flattend after application
		
		Applicate between CreateProfile and runPamtra
		
		'''
		if condition.shape != self._shape2D and condition.shape != (self._shape2D[0]*self._shape2D[1],):
			raise ValueError("shape mismatch, shape of condition must be 2D field!")
		
		condition = condition.reshape(self._shape2D)
		
		#create a new shape!
		self.p["ngridx"] = np.sum(condition)
		self.p["ngridy"] = 1
		
		self._shape2D = (self.p["ngridx"],self.p["ngridy"],)
		self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],)
		self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"]+1,)

		for key in ["unixtime","nlyrs","lat","lon","lfrac","model_i","model_j","wind10u","wind10v"]:
			self.p[key] = self.p[key][condition].reshape(self._shape2D)
			
		for key in ["iwv","cwp","iwp","rwp","swp","gwp","hwp"]:
			if key in self.p.keys():
				self.p[key] = self.p[key][condition].reshape(self._shape2D)

		for key in ["cwc_q","iwc_q","rwc_q","swc_q","gwc_q","hwc_q","cwc_n","iwc_n","rwc_n","swc_n","gwc_n","hwc_n"]:
			self.p[key] = self.p[key][condition].reshape(self._shape3D)
			
		for key in ["hgt_lev","temp_lev","press_lev","relhum_lev"]:
			self.p[key] = self.p[key][condition].reshape(self._shape3Dplus)
		
		for key in ['q_lev', 'temp', 'q', 'dz', 'press', 'relhum', 'rho_moist']:
			if key in self._helperP.keys():
				if key in ['q_lev']:
					self._helperP[key] = self._helperP[key][condition].reshape(self._shape3Dplus)
				if key in ['temp', 'q', 'dz', 'press', 'relhum', 'rho_moist']:
					self._helperP[key] = self._helperP[key][condition].reshape(self._shape3D)
		return

	def rescaleHeights(self,new_hgt_lev):
	
		# sort height vectors
		old_hgt_lev = self.p["hgt_lev"]
		new_hgt = (new_hgt_lev[...,1:] + new_hgt_lev[...,:-1])/2.
		old_hgt = (old_hgt_lev[...,1:] + old_hgt_lev[...,:-1])/2.
		
		self.p["max_nlyrs"] = len(new_hgt_lev) -1
		
		#new shape
		self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],)
		self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"]+1,)
		

		for key in ["cwc_q","iwc_q","rwc_q","swc_q","gwc_q","hwc_q","cwc_n","iwc_n","rwc_n","swc_n","gwc_n","hwc_n"]:
			#make new array
			newP = np.ones(self._shape3D) * missingNumber
			for x in xrange(self._shape2D[0]):
				for y in xrange(self._shape2D[1]):
					#interpolate!
					newP[x,y] = np.interp(new_hgt,old_hgt[x,y],self.p[key][x,y])
			#save new array
			self.p[key] = newP
			#and mark all entries below -1 as missing Number!
			self.p[key][self.p[key]<-1] = missingNumber
			
		for key in ["hgt_lev","temp_lev","relhum_lev"]:
			newP = np.ones(self._shape3Dplus) * missingNumber
			for x in xrange(self._shape2D[0]):
				for y in xrange(self._shape2D[1]):
					newP[x,y] = np.interp(new_hgt_lev,old_hgt_lev[x,y],self.p[key][x,y])
			self.p[key] = newP
			self.p[key][self.p[key]<-1] = missingNumber
			
		for key in ["press_lev"]:
			newP = np.ones(self._shape3Dplus) * missingNumber
			for x in xrange(self._shape2D[0]):
				for y in xrange(self._shape2D[1]):
					newP[x,y] = np.exp(np.interp(new_hgt_lev,old_hgt_lev[x,y],np.log(self.p[key][x,y])))
			self.p[key] = newP
			self.p[key][self.p[key]<-1] = missingNumber

		self.p["nlyrs"] = np.sum(self.p["hgt_lev"] != missingNumber,axis=-1) -1
		
		if self.p["max_nlyrs"] > 200:
			warnings.warn("Still too many layers for pamtra (max:200): " + str(self.p["max_nlyrs"]),Warning)


		return
		
	def addIntegratedValues(self):
	  
		for pDict,qValue,intValue in [[self._helperP,"q","iwv"],[self.p,"cwc_q","cwp"],[self.p,"iwc_q","iwp"],[self.p,"rwc_q","rwp"],[self.p,"swc_q","swp"],[self.p,"gwc_q","gwp"],[self.p,"hwc_q","hwp"]]:
			#now we need q!
			self._calcQ()
			#nothing to do without hydrometeors:
			if np.all(pDict[qValue]==0):
				self.p[intValue] = np.zeros(self._shape2D)
			else:
				self._calcMoistRho() #provides also temp,press,dz and q!
				self.p[intValue] =  np.sum(pDict[qValue]*self._helperP["rho_moist"]*self._helperP["dz"],axis=-1)
		return

	def addCloudShape(self):
		"""
		adds cloud base and cloud top to the data to an existing pamtra profile
		clouds are detected with rh >= 0.95 and T >= 253.15 K
		if multiple cloud layers are found, only the uppermost and the lowest one are saved.
		"""
		self.p["cloudTop"] = np.ones(self._shape2D)*missingNumber
		self.p["cloudBase"] = np.ones(self._shape2D)*missingNumber
		
		for x in xrange(self._shape2D[0]):
			for y in xrange(self._shape2D[1]):
				i_top, i_base, i_cloud =  meteoSI.detect_liq_cloud(self.p["hgt_lev"][x,y,0:self.p["nlyrs"][x,y]], self.p["temp_lev"][x,y,0:self.p["nlyrs"][x,y]], self.p["relhum_lev"][x,y,0:self.p["nlyrs"][x,y]])
				if len(i_top)> 0:
					self.p["cloudTop"][x,y] = self.p["hgt_lev"][x,y,i_top[-1]+1]
					self.p["cloudBase"][x,y] = self.p["hgt_lev"][x,y,i_base[0]]
		return

	def addPseudoAdiabaticLWC(self):
		"""
		adds liquid water content to the data to an existing pamtra profile
		using a simple cloud model with pseudo adiabatic lapse rate
		clouds are detected with rh >= 0.95 and T >= 253.15 K
		existing cwc_q values are overriden!
		"""

		#calculate CWC
		self.p["cwc_q"][:] = 0

		for x in xrange(self._shape2D[0]):
			for y in xrange(self._shape2D[1]):
				i_top, i_base, i_cloud =  meteoSI.detect_liq_cloud(self.p["hgt_lev"][x,y,0:self.p["nlyrs"][x,y]], self.p["temp_lev"][x,y,0:self.p["nlyrs"][x,y]], self.p["relhum_lev"][x,y,0:self.p["nlyrs"][x,y]])
				for k in np.arange(len(i_top)):
					i_cloud_k = np.arange(i_base[k],i_top[k]+1) 
					self.p["cwc_q"][x,y,i_cloud_k[:-1]] = meteoSI.mod_ad(self.p["temp_lev"][x,y,i_cloud_k], self.p["press_lev"][x,y,i_cloud_k], self.p["hgt_lev"][x,y,i_cloud_k], 1)

		self.p["cwp"][:] = 0
		
		self._calcMoistRho() #provides also temp,press,dz and q!
		self.p["cwp"][:] =  np.sum(self.p["cwc_q"]*self._helperP["rho_moist"]*self._helperP["dz"],axis=-1)

		return

	#def addPIA(self)
	#todo: make pia for all hydrometeortypes!
		#assert self.r["nmlSettings"]["output"]["activeLogScale"]
	  
		#Att_atmo = pam.r["Att_atmo"]
		#Att_atmo[Att_atmo==missingNumber] = 0
		#Att_hydro = pam.r["Att_hydro"]
		#Att_hydro[Att_hydro==missingNumber] = 0    
		#self.r["PIA"] = np.zeros(np.shape(Att_atmo))
		#for hh in range(self.p["max_nlyrs"]):
			#self.r["PIA"][:,:,hh,:] = Att_atmo[:,:,hh,:] +Att_hydro[:,:,hh,:] + 2*np.sum(Att_atmo[:,:,:hh,:] +Att_hydro[:,:,:hh,:],axis=2)#only half for the current layer
		#return

		
	def createFullProfile(self,timestamp,lat,lon,lfrac,wind10u,wind10v,
			iwv,cwp,iwp,rwp,swp,gwp,hwp,
			hgt_lev,press_lev,temp_lev,relhum_lev,
			cwc_q,iwc_q,rwc_q,swc_q,gwc_q,
			hwc_q,cwc_n,iwc_n,rwc_n,swc_n,gwc_n,hwc_n):
		
		'''
		create comple PAmtra Profile
		
		No Extras, no missing values are guessed. the Data is only reshaped
		'''
		
		
		noDims = len(np.shape(hgt_lev))
		
		if noDims == 1:
			self.p["ngridx"] = 1
			self.p["ngridy"] = 1
		elif noDims == 2:
			self.p["ngridx"] = np.shape(hgt_lev)[0]
			self.p["ngridy"] = 1
		elif noDims == 3:
			self.p["ngridx"] = np.shape(hgt_lev)[0]
			self.p["ngridy"] = np.shape(hgt_lev)[1]
		else:
			print "Too many dimensions!"
			raise IOError
		
		self.p["nlyrs"] = np.sum(hgt_lev!=missingNumber,axis=-1) -1
		self.p["max_nlyrs"] = np.shape(hgt_lev)[-1] -1
		
		if self.p["max_nlyrs"] > 200:
			warnings.warn("Too many layers for pamtra (max:200): " + str(self.p["max_nlyrs"]),Warning)
		
		self._shape2D = (self.p["ngridx"],self.p["ngridy"],)
		self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],)
		self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"]+1,)
		

		self.p["unixtime"] = timestamp.reshape(self._shape2D)
				
		self.p["deltax"] = 0.
		self.p["deltay"] = 0.
		self.p["lat"] = lat.reshape(self._shape2D)
		self.p["lon"] = lon.reshape(self._shape2D)
		self.p["lfrac"] = lfrac.reshape(self._shape2D)
		self.p["model_i"] = np.array(np.where(lat.reshape(self._shape2D))[0]).reshape(self._shape2D) +1
		self.p["model_j"] = np.array(np.where(lon.reshape(self._shape2D))[1]).reshape(self._shape2D) +1
		self.p["wind10u"] = wind10u.reshape(self._shape2D)
		self.p["wind10v"] = wind10v.reshape(self._shape2D)

		self.p["iwv"] = iwv.reshape(self._shape2D)
		self.p["cwp"] = cwp.reshape(self._shape2D)
		self.p["iwp"] = iwp.reshape(self._shape2D)
		self.p["rwp"] = rwp.reshape(self._shape2D)
		self.p["swp"] = swp.reshape(self._shape2D)
		self.p["gwp"] = gwp.reshape(self._shape2D)
		self.p["hwp"] = gwp.reshape(self._shape2D)
		
		self.p["hgt_lev"] = hgt_lev.reshape(self._shape3Dplus)
		self.p["temp_lev"] = temp_lev.reshape(self._shape3Dplus)
		self.p["press_lev"] = press_lev.reshape(self._shape3Dplus)
		self.p["relhum_lev"] = relhum_lev.reshape(self._shape3Dplus)
		
		self.p["cwc_q"] = cwc_q.reshape(self._shape3D)
		self.p["iwc_q"] = iwc_q.reshape(self._shape3D)
		self.p["rwc_q"] = rwc_q.reshape(self._shape3D)
		self.p["swc_q"] = swc_q.reshape(self._shape3D)
		self.p["gwc_q"] = gwc_q.reshape(self._shape3D)
		
		self.p["hwc_q"] = hwc_q.reshape(self._shape3D)
		self.p["cwc_n"] = cwc_n.reshape(self._shape3D)
		self.p["iwc_n"] = iwc_n.reshape(self._shape3D)
		self.p["rwc_n"] = rwc_n.reshape(self._shape3D)
		self.p["swc_n"] = swc_n.reshape(self._shape3D)
		self.p["gwc_n"] = gwc_n.reshape(self._shape3D)
		self.p["hwc_n"] = hwc_n.reshape(self._shape3D)

		
		
	def runParallelPamtra(self,freqs,pp_servers=(),pp_local_workers="auto",pp_deltaF=1,pp_deltaX=0,pp_deltaY = 0):
		'''
		run Pamtra analouge to runPamtra, but with with parallel python
		
		input:
		
		freqs: list with frequencies
		pp_servers: tuple with servers, ("*") activates auto detection
		pp_local_workers: number of local workers, "auto" is usually amount of cores
		pp_deltaF,pp_deltaX,pp_deltaY: length of the peaces in frequency,x and y direction. 0 means no slicing
		
		In my experience, smaller pieces (e.g. pp_deltaF=0,pp_deltaX=1,pp_deltaY=1) work much better than bigger ones, even though overhead might be bigger.
		
		output is collected by _ppCallback()
		'''
		tttt = time.time()
		
		self._checkData()
		
		
		
		#if the namelist file is empty, write it. Otherwise existing one is used.
		if not os.path.isfile(self.set["namelist_file"]):
			self.writeNmlFile(self.set["namelist_file"])
		else: 
			if self.set["namelist_file"].split(".")[-1] == "tmp": 
				raise ValueError("Namelitsfile "+ self.set["namelist_file"] +" ends with .tmp, but is existing already")
			elif self.set["pyVerbose"] > 0:
				print("NOT writing temporary nml file to run pamtra using exisiting nml file instead: "+self.set["namelist_file"])

		if pp_local_workers == "auto":
			self.job_server = pp.Server(ppservers=pp_servers,secret="pyPamtra") 
		else:
			self.job_server = pp.Server(pp_local_workers,ppservers=pp_servers,secret="pyPamtra") 
			
		if int(self.nmlSet["verbose_mode"]["verbose"]) > 0:	
			raise IOError('There is a weired bug if the fortran part prints anything (i.e. verbosity is larger than 0). Use the non-parallel pyPamtra version for debugging! verbose=', self.nmlSet["verbose_mode"]["verbose"])
		if self.set["pyVerbose"] > 0: 
			print "Starting pp with: "
			pp_nodes = self.job_server.get_active_nodes()
			for key in pp_nodes.keys():
				print key+": "+str(pp_nodes[key])+" nodes"
		
		if type(freqs) in (int,np.int32,np.int64,float,np.float32,np.float64): freqs = [freqs]
		
		self.set["freqs"] = freqs
		self.set["nfreqs"] = len(freqs)
		
		assert self.set["nfreqs"] > 0
		
		if pp_deltaF==0: pp_deltaF = self.set["nfreqs"]
		if pp_deltaX==0: pp_deltaX = self.p["ngridx"]
		if pp_deltaY==0: pp_deltaY = self.p["ngridy"]
		
		pp_ii = -1
		pp_jobs = dict()
		
		self.r["Ze"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_hydro"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_atmo"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		
		self.r["Ze_cw"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Ze_rr"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Ze_ci"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Ze_sn"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Ze_gr"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Ze_ha"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_cw"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_rr"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_ci"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_sn"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_gr"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber
		self.r["Att_ha"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.set["nfreqs"],))*missingNumber

		self.r["hgt"] = np.ones((self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],))*missingNumber
		self.r["tb"] = np.ones((self.p["ngridx"],self.p["ngridy"],self._noutlevels,self._nangles,self.set["nfreqs"],self._nstokes))*missingNumber
		
		self.pp_noJobs = len(np.arange(0,self.set["nfreqs"],pp_deltaF))*len(np.arange(0,self.p["ngridx"],pp_deltaX))*len(np.arange(0,self.p["ngridy"],pp_deltaY))
		self.pp_jobsDone = 0
		
		#fi = open("/tmp/pp_logfile.txt","w")
		#fi.write("Starting pp with %i jobs \n\r"%(self.pp_noJobs))
		#fi.close()
		
		self.hosts=[]
		
		for pp_startF in np.arange(0,self.set["nfreqs"],pp_deltaF):
			pp_endF = pp_startF + pp_deltaF
			if pp_endF > self.set["nfreqs"]: pp_endF = self.set["nfreqs"]
			pp_nfreqs = pp_endF - pp_startF
			for pp_startX in np.arange(0,self.p["ngridx"],pp_deltaX):
				pp_endX = pp_startX + pp_deltaX
				if pp_endX > self.p["ngridx"]: pp_endX = self.p["ngridx"]
				pp_ngridx = pp_endX - pp_startX
				for pp_startY in np.arange(0,self.p["ngridy"],pp_deltaY):
					pp_endY = pp_startY + pp_deltaY
					if pp_endY > self.p["ngridy"]: pp_endY = self.p["ngridy"]
					pp_ngridy = pp_endY - pp_startY
					
					pp_ii+=1
					
					pp_jobs[pp_ii] = self.job_server.submit(PamtraFortranWrapper, (
					#self.set
					self.set["namelist_file"],
					#input
					pp_ngridx,
					pp_ngridy,
					self.p["max_nlyrs"],
					self.p["nlyrs"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					pp_nfreqs,
					self.set["freqs"][pp_startF:pp_endF],
					self.p["unixtime"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["deltax"],self.p["deltay"],
					self.p["lat"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["lon"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["model_i"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["model_j"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["wind10u"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["wind10v"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["lfrac"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["relhum_lev"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["press_lev"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["temp_lev"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["hgt_lev"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["cwc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["iwc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["rwc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["swc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["gwc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["hwc_q"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["cwc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["iwc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["rwc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["swc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["gwc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist(),
					self.p["hwc_n"][pp_startX:pp_endX,pp_startY:pp_endY].tolist()
					),tuple(), ("pyPamtraLibWrapper","pyPamtraLib","os",),callback=self._ppCallback,
					callbackargs=(pp_startX,pp_endX,pp_startY,pp_endY,pp_startF,pp_endF,pp_ii,))
					
					if self.set["pyVerbose"] > 0: 
						sys.stdout.write("\r"+20*" "+"\r"+ "%i, %5.3f%% submitted"%(pp_ii+1,(pp_ii+1)/float(self.pp_noJobs)*100))
						sys.stdout.flush()

		if self.set["pyVerbose"] > 0: 
			print " "
			print self.pp_noJobs, "jobs submitted"


		if self.set["pyVerbose"] > 0: print " "; self.job_server.get_active_nodes()
		self.job_server.wait()
		
		self.r["nmlSettings"] = self.nmlSet

		self.r["pamtraVersion"] = self.r["pamtraVersion"].strip()
		self.r["pamtraHash"] = self.r["pamtraHash"].strip()
		
		if self.set["pyVerbose"] > 0: print " "; self.job_server.print_stats()
		self.job_server.destroy()
		del self.job_server
		
		#remove temporary nml file
		if self.set["namelist_file"].split(".")[-1] == "tmp": os.remove(self.set["namelist_file"])
		
		if self.set["pyVerbose"] > 0: print "pyPamtra runtime:", time.time() - tttt
	
	def _ppCallback(self,pp_startX,pp_endX,pp_startY,pp_endY,pp_startF,pp_endF,pp_ii,*results):
		'''
		Collect the data of parallel pyPamtra		
		'''
		(((
		self.r["pamtraVersion"],self.r["pamtraHash"], 
		self.r["Ze"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_cw"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_rr"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_ci"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_sn"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_gr"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Ze_ha"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_hydro"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_cw"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_rr"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_ci"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_sn"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_gr"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_ha"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["Att_atmo"][pp_startX:pp_endX,pp_startY:pp_endY,:,pp_startF:pp_endF], 
		self.r["hgt"][pp_startX:pp_endX,pp_startY:pp_endY,:],
		self.r["tb"][pp_startX:pp_endX,pp_startY:pp_endY,:,:,pp_startF:pp_endF,:], 
		self.r["angles"],
		),host,),) = results
		self.pp_jobsDone += 1
		if self.set["pyVerbose"] > 0: 
			sys.stdout.write("\r"+50*" "+"\r"+ "%s: %6i, %8.3f%% collected (#%6i, %s)"%(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),self.pp_jobsDone,(self.pp_jobsDone)/float(self.pp_noJobs)*100,pp_ii+1,host))
			sys.stdout.flush()
		if self.set["pyVerbose"] > 1: print " "; self.job_server.print_stats()
		#fi = open("/tmp/pp_logfile.txt","a")
		#fi.write("%s: %6i, %8.3f%% collected (#%6i, %s)\n\r"%(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),self.pp_jobsDone,(self.pp_jobsDone)/float(self.pp_noJobs)*100,pp_ii+1,host))
		#fi.close()
		
	def runPamtra(self,freqs):
		'''
		run Pamtra from python
		'''
		tttt = time.time()
		
		if type(freqs) == int in (int,np.int32,np.int64,float,np.float32,np.float64): freqs = [freqs]
		
		self.set["freqs"] = freqs
		self.set["nfreqs"] = len(freqs)
		assert self.set["nfreqs"] > 0
		
		self._checkData()

		if not os.path.isfile(self.set["namelist_file"]):
			self.writeNmlFile(self.set["namelist_file"])
		else: 
			if self.set["namelist_file"].split(".")[-1] == "tmp": 
				raise ValueError("Namelitsfile "+ self.set["namelist_file"] +" ends with .tmp, but is existing already")
			elif self.set["pyVerbose"] > 0:
				print("NOT writing temporary nml file to run pamtra using exisiting nml file instead: "+self.set["namelist_file"])
		
		#output
		(
		self.r["pamtraVersion"],
		self.r["pamtraHash"],
		self.r["Ze"], 
		self.r["Ze_cw"], 
		self.r["Ze_rr"], 
		self.r["Ze_ci"], 
		self.r["Ze_sn"], 
		self.r["Ze_gr"], 
		self.r["Ze_ha"], 
		self.r["Att_hydro"], 
		self.r["Att_cw"], 
		self.r["Att_rr"], 
		self.r["Att_ci"], 
		self.r["Att_sn"], 
		self.r["Att_gr"], 
		self.r["Att_ha"], 
		self.r["Att_atmo"], 
		self.r["hgt"],
		self.r["tb"],
		self.r["angles"],
		), host = \
		PamtraFortranWrapper(
		#self.set
		self.set["namelist_file"],
		#input
		self.p["ngridx"],self.p["ngridy"],self.p["max_nlyrs"],self.p["nlyrs"],self.set["nfreqs"],self.set["freqs"],
		self.p["unixtime"],
		self.p["deltax"],self.p["deltay"], self.p["lat"],self.p["lon"],self.p["model_i"],self.p["model_j"],
		self.p["wind10u"],self.p["wind10v"],self.p["lfrac"],
		self.p["relhum_lev"],self.p["press_lev"],self.p["temp_lev"],self.p["hgt_lev"],
		self.p["cwc_q"],self.p["iwc_q"],self.p["rwc_q"],self.p["swc_q"],self.p["gwc_q"],
		self.p["hwc_q"],self.p["cwc_n"],self.p["iwc_n"],self.p["rwc_n"],self.p["swc_n"],self.p["gwc_n"],self.p["hwc_n"])
				
		self.r["nmlSettings"] = self.nmlSet
		
		self.r["pamtraVersion"] = self.r["pamtraVersion"].strip()
		self.r["pamtraHash"] = self.r["pamtraHash"].strip()
		
		#for key in self.__dict__.keys():
			#print key
			#print self.__dict__[key]
		
		#remove temporary nml file
		if self.set["namelist_file"].split(".")[-1] == "tmp": os.remove(self.set["namelist_file"])
		
		if self.set["pyVerbose"] > 0: print "pyPamtra runtime:", time.time() - tttt


	def writeResultsToNumpy(self,fname):
		'''
		write the complete state of the session (profile,results,settings to a file
		'''
		f = open(fname, "w")
		pickle.dump([self.r,self.p,self._helperP,self.nmlSet,self.set], f)
		f.close()

	def loadResultsFromNumpy(self,fname):
		'''
		load the complete state of the session (profile,results,settings to a file
		'''
		try: 
			f = open(fname, "r")
			[self.r,self.p,self._helperP,self.nmlSet,self.set] = pickle.load(f)
			f.close()
			self._shape2D = (self.p["ngridx"],self.p["ngridy"],)
			self._shape3D = (self.p["ngridx"],self.p["ngridy"],self.p["nlyrs"],)
			self._shape3Dplus = (self.p["ngridx"],self.p["ngridy"],self.p["nlyrs"]+1,)
		except:
			raise IOError ("Could not read data")
		
	def writeResultsToNetCDF(self,fname,profileVars="all",ncForm="NETCDF3_CLASSIC"):
		'''
		write the results to a netcdf file
		
		Input:
		
		fname: str filename with path
		profileVars list of variables of the profile to be saved. "all" saves all implmented ones
		ncForm: str netcdf file format, possible values are NETCDF3_CLASSIC, NETCDF3_64BIT, NETCDF4_CLASSIC, and NETCDF4 for the python-netcdf4 package (netcdf3 gives netcdf4 files for newer ubuntu versions!!") NETCDF3 takes the "old" Scientific.IO.NetCDF module, which is a bit more convinient
		'''
		
		#most syntax is identical, but there is one nasty difference regarding the fillValue...
		if ncForm in ["NETCDF3_CLASSIC", "NETCDF3_64BIT", "NETCDF4_CLASSIC", "NETCDF4"]:
			import netCDF4 as nc
			pyNc = True
		elif ncForm in ["NETCDF3"]:
			try:
				import Scientific.IO.NetCDF as nc
				pyNc = False
			except:
				#fallback for cheops with the same syntax as netcdf4!
				import netCDF3 as nc
				pyNc = True
		else:
			raise ValueError("Unknown nc form "+ncForm)
		  
		try: 
			self.r
			self.r["pamtraVersion"]
		except:
			raise IOError ("run runPamtra first!")

		if pyNc: cdfFile = nc.Dataset(fname,"w",ncForm)
		else: cdfFile = nc.NetCDFFile(fname,"w")
		
		#write meta data
		cdfFile.history = "Created with pyPamtra (Version: "+self.r["pamtraVersion"]+", Git Hash: "+self.r["pamtraHash"]+") by "+self.nmlSet["output"]["creator"]+" (University of Cologne, IGMK) at " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		
		cdfFile.properties = str(self.r["nmlSettings"])
		#make frequsnions
		cdfFile.createDimension('grid_x',int(self.p["ngridx"]))
		cdfFile.createDimension('grid_y',int(self.p["ngridy"]))
		cdfFile.createDimension('frequency',int(self.set["nfreqs"]))
		
		if (self.r["nmlSettings"]["run_mode"]["passive"]):
			cdfFile.createDimension('angles',len(self.r["angles"]))
			cdfFile.createDimension('outlevels',int(self._noutlevels))
			cdfFile.createDimension('stokes',int(self._nstokes))
			
		if (self.r["nmlSettings"]["run_mode"]["active"]):
			cdfFile.createDimension('heightbins',int(self.p["max_nlyrs"]))
		
		dim2d = ("grid_x","grid_y",)
		dim3d = ("grid_x","grid_y","heightbins",)
		dim4d = ("grid_x","grid_y","heightbins","frequency")
		dim6d = ("grid_x","grid_y","outlevels","angles","frequency","stokes")
			
			
			
		if (self.r["nmlSettings"]["output"]["activeLogScale"]):
			attUnit = "dBz"
			zeUnit = "dBz"
		else:
			 attUnit = "linear"
			 zeUnit = "mm^6 m^-3"    
		#create and write dim variables
		
		fillVDict = dict()
		#little cheat to avoid hundreds of if, else...
		if pyNc: fillVDict["fill_value"] = missingNumber
		
		nc_frequency = cdfFile.createVariable('frequency','f',('frequency',),**fillVDict)
		nc_frequency.units = 'GHz'
		nc_frequency[:] = self.set["freqs"]
		if not pyNc: nc_frequency._FillValue =missingNumber
		
		nc_gridx = cdfFile.createVariable('grid_x','f',('grid_x',),**fillVDict)#= missingNumber)
		nc_gridx.units = '-'
		nc_gridx[:] = np.arange(self.p["ngridx"],dtype="f")
		if not pyNc: nc_gridx._FillValue =missingNumber
		
		nc_gridy = cdfFile.createVariable('grid_y','f',('grid_y',),**fillVDict)
		nc_gridy.units = '-'
		nc_gridy[:] = np.arange(self.p["ngridy"],dtype="f")
		if not pyNc: nc_gridy._FillValue =missingNumber
		
		
		
		if (self.r["nmlSettings"]["run_mode"]["active"]):

			nc_heightbins = cdfFile.createVariable('heightbins', 'i',("heightbins",),**fillVDict)
			nc_heightbins.units = "-"
			nc_heightbins[:] = np.arange(0,self.p["max_nlyrs"],dtype="i")
			if not pyNc: nc_heightbins._FillValue =int(missingNumber)

			nc_height = cdfFile.createVariable('height', 'f',dim3d,**fillVDict)
			nc_height.units = "m"
			nc_height[:] = np.array(self.r["hgt"],dtype="f")
			if not pyNc: nc_height._FillValue =missingNumber
			
		
		if (self.r["nmlSettings"]["run_mode"]["passive"]):
			nc_angle = cdfFile.createVariable('angles','f',('angles',),**fillVDict)
			nc_angle.units = 'deg'
			nc_angle[:] = np.array(self.r["angles"],dtype="f")
			if not pyNc: nc_angle._FillValue =missingNumber
			
			nc_stokes = cdfFile.createVariable('stokes', 'c',("stokes",),**fillVDict)
			nc_stokes.units = "-"
			nc_stokes[:] = "HV"
			
			nc_out = cdfFile.createVariable('outlevels', 'f',("outlevels",),**fillVDict)
			nc_out.units = "m over sea level (top of atmosphere value) OR m over ground (ground value)"
			nc_out[:] = np.array([self.r["nmlSettings"]["output"]["obs_height"],0],dtype="f")
			if not pyNc: nc_out._FillValue =missingNumber
			
		#create and write variables
		
		nc_model_i = cdfFile.createVariable('model_i', 'i',dim2d,**fillVDict)
		nc_model_i.units = "-"
		nc_model_i[:] = np.array(self.p["model_i"],dtype="i")
		if not pyNc: nc_model_i._FillValue =int(missingNumber)
		
		nc_model_j = cdfFile.createVariable('model_j', 'i',dim2d,**fillVDict)
		nc_model_j.units = "-"
		nc_model_j[:] = np.array(self.p["model_j"],dtype="i")
		if not pyNc: nc_model_j._FillValue =int(missingNumber)
			
		nc_nlyrs = cdfFile.createVariable('nlyr', 'i',dim2d,**fillVDict)
		nc_nlyrs.units = "-"
		nc_nlyrs[:] = np.array(self.p["nlyrs"],dtype="i")
		if not pyNc: nc_nlyrs._FillValue =int(missingNumber)
		
		nc_time = cdfFile.createVariable('datatime', 'i',dim2d,**fillVDict)
		nc_time.units = "seconds since 1970-01-01 00:00:00"
		nc_time[:] = np.array(self.p["unixtime"],dtype="i")
		if not pyNc: nc_time._FillValue =int(missingNumber)
		
		nc_longitude = cdfFile.createVariable('longitude', 'f',dim2d,**fillVDict)
		nc_longitude.units = "deg.dec"
		nc_longitude[:] = np.array(self.p["lon"],dtype="f")
		if not pyNc: nc_longitude._FillValue =missingNumber
		
		nc_latitude = cdfFile.createVariable('latitude', 'f',dim2d,**fillVDict)
		nc_latitude.units = "deg.dec"
		nc_latitude[:] = np.array(self.p["lat"],dtype="f")
		if not pyNc: nc_latitude._FillValue =missingNumber
			
		nc_lfrac = cdfFile.createVariable('lfrac', 'f',dim2d,**fillVDict)
		nc_lfrac.units = "-"
		nc_lfrac[:] = np.array(self.p["lfrac"],dtype="f")
		if not pyNc: nc_lfrac._FillValue =missingNumber
		
		
		if (self.r["nmlSettings"]["run_mode"]["active"]):
			
			if self.r["nmlSettings"]["output"]["zeSplitUp"]:

				nc_Ze_cw = cdfFile.createVariable('Ze_cloud_water', 'f',dim4d,**fillVDict)
				nc_Ze_cw.units = zeUnit
				nc_Ze_cw[:] = np.array(self.r["Ze_cw"],dtype='f')
				if not pyNc: nc_Ze_cw._FillValue =missingNumber
		
				nc_Ze_rr = cdfFile.createVariable('Ze_rain', 'f',dim4d,**fillVDict)
				nc_Ze_rr.units = zeUnit
				nc_Ze_rr[:] = np.array(self.r["Ze_rr"],dtype='f')
				if not pyNc: nc_Ze_rr._FillValue =missingNumber
		
				nc_Ze_ci = cdfFile.createVariable('Ze_cloud_ice', 'f',dim4d,**fillVDict)
				nc_Ze_ci.units = zeUnit
				nc_Ze_ci[:] = np.array(self.r["Ze_ci"],dtype='f')
				if not pyNc: nc_Ze_ci._FillValue = missingNumber
			
				nc_Ze_sn = cdfFile.createVariable('Ze_snow', 'f',dim4d,**fillVDict)
				nc_Ze_sn.units = zeUnit
				nc_Ze_sn[:] = np.array(self.r["Ze_sn"],dtype='f')
				if not pyNc: nc_Ze_sn._FillValue =missingNumber
		
				nc_Ze_gr = cdfFile.createVariable('Ze_graupel', 'f',dim4d,**fillVDict)
				nc_Ze_gr.units = zeUnit
				nc_Ze_gr[:] = np.array(self.r["Ze_gr"],dtype='f')
				if not pyNc: nc_Ze_gr._FillValue =missingNumber
		
				nc_Att_cw = cdfFile.createVariable('Attenuation_cloud_water', 'f',dim4d,**fillVDict)
				nc_Att_cw.units = attUnit
				nc_Att_cw[:] = np.array(self.r["Att_cw"],dtype='f')
				if not pyNc: nc_Att_cw._FillValue =missingNumber
		
				nc_Att_rrrs = cdfFile.createVariable('Attenuation_rain', 'f',dim4d,**fillVDict)
				nc_Att_rrrs.units = attUnit
				nc_Att_rrrs[:] = np.array(self.r["Att_rr"],dtype='f')
				if not pyNc: nc_Att_rrrs._FillValue =missingNumber
				
				nc_Att_ci = cdfFile.createVariable('Attenuation_cloud_ice', 'f',dim4d,**fillVDict)
				nc_Att_ci.units = attUnit
				nc_Att_ci[:] = np.array(self.r["Att_ci"],dtype='f')
				if not pyNc: nc_Att_ci._FillValue =missingNumber
				
				nc_Att_sn = cdfFile.createVariable('Attenuation_snow', 'f',dim4d,**fillVDict)
				nc_Att_sn.units = attUnit
				nc_Att_sn[:] = np.array(self.r["Att_sn"],dtype='f')
				if not pyNc: nc_Att_sn._FillValue =missingNumber
		
				nc_Att_gr = cdfFile.createVariable('Attenuation_graupel', 'f',dim4d,**fillVDict)
				nc_Att_gr.units = attUnit
				nc_Att_gr[:] = np.array(self.r["Att_gr"],dtype='f')
				if not pyNc: nc_Att_gr._FillValue =missingNumber
		
				if self.r["nmlSettings"]["moments"]["n_moments"]==2:

					nc_Ze_ha = cdfFile.createVariable('Ze_hail', 'f',dim4d,**fillVDict)
					nc_Ze_ha.units = zeUnit
					nc_Ze_ha[:] = np.array(self.r["Ze_ha"],dtype='f')
					if not pyNc: nc_Ze_ha._FillValue =missingNumber
		
					nc_Att_ha = cdfFile.createVariable('Attenuation_hail', 'f',dim4d,**fillVDict)
					nc_Att_ha.units = attUnit
					nc_Att_ha[:] = np.array(self.r["Att_ha"],dtype='f')
					if not pyNc: nc_Att_ha._FillValue =missingNumber
		
			else: 
				 
				nc_Ze = cdfFile.createVariable('Ze', 'f',dim4d,**fillVDict)
				nc_Ze.units = zeUnit
				nc_Ze[:] = np.array(self.r["Ze"],dtype='f')
				if not pyNc: nc_Ze._FillValue =missingNumber
		
				nc_Attenuation_Hydrometeors = cdfFile.createVariable('Attenuation_Hydrometeors', 'f',dim4d,**fillVDict)
				nc_Attenuation_Hydrometeors.units = attUnit
				nc_Attenuation_Hydrometeors[:] = np.array(self.r["Att_hydro"],dtype='f')
				if not pyNc: nc_Attenuation_Hydrometeors._FillValue =missingNumber
		
			nc_Attenuation_Atmosphere = cdfFile.createVariable('Attenuation_Atmosphere', 'f',dim4d,**fillVDict)
			nc_Attenuation_Atmosphere.units = attUnit
			nc_Attenuation_Atmosphere[:] = np.array(self.r["Att_atmo"],dtype='f')
			if not pyNc: nc_Attenuation_Atmosphere._FillValue =missingNumber
		
		if (self.r["nmlSettings"]["run_mode"]["passive"]):
			nc_tb = cdfFile.createVariable('tb', 'f',dim6d,**fillVDict)
			nc_tb.units = "K"
			nc_tb[:] = np.array(self.r["tb"],dtype='f')
			if not pyNc: nc_tb._FillValue =missingNumber
				
		#profile data
		
		if ("iwv" in profileVars or profileVars =="all") and ("iwv" in self.p.keys()):
			nc_iwv = cdfFile.createVariable('iwv', 'f',dim2d,**fillVDict)
			nc_iwv.units = "kg/m^2"
			nc_iwv[:] = np.array(self.p["iwv"],dtype="f")
			if not pyNc: nc_iwv._FillValue =missingNumber

		if ("cwp" in profileVars or profileVars =="all") and ("cwp" in self.p.keys()):
			nc_cwp= cdfFile.createVariable('cwp', 'f',dim2d,**fillVDict)
			nc_cwp.units = "kg/m^2"
			nc_cwp[:] = np.array(self.p["cwp"],dtype="f")
			if not pyNc: nc_cwp._FillValue =missingNumber
	
		if ("iwp" in profileVars or profileVars =="all") and ("iwp" in self.p.keys()):
			nc_iwp = cdfFile.createVariable('iwp', 'f',dim2d,**fillVDict)
			nc_iwp.units = "kg/m^2"
			nc_iwp[:] = np.array(self.p["iwp"],dtype="f")
			if not pyNc: nc_iwp._FillValue =missingNumber

		if ("rwp" in profileVars or profileVars =="all") and ("rwp" in self.p.keys()):
			nc_rwp = cdfFile.createVariable('rwp', 'f',dim2d,**fillVDict)
			nc_rwp.units = "kg/m^2"
			nc_rwp[:] = np.array(self.p["rwp"],dtype="f")
			if not pyNc: nc_rwp._FillValue =missingNumber

		if ("swp" in profileVars or profileVars =="all") and ("swp" in self.p.keys()):
			nc_swp = cdfFile.createVariable('swp', 'f',dim2d,**fillVDict)
			nc_swp.units = "kg/m^2"
			nc_swp[:] = np.array(self.p["swp"],dtype="f")
			if not pyNc: nc_swp._FillValue =missingNumber

		if ("gwp" in profileVars or profileVars =="all") and ("gwp" in self.p.keys()):
			nc_gwp = cdfFile.createVariable('gwp', 'f',dim2d,**fillVDict)
			nc_gwp.units = "kg/m^2"
			nc_gwp[:] = np.array(self.p["gwp"],dtype="f")
			if not pyNc: nc_gwp._FillValue =missingNumber

		if ("hwp" in profileVars or profileVars =="all") and ("hwp" in self.p.keys()):
			nc_hwp = cdfFile.createVariable('hwp', 'f',dim2d,**fillVDict)
			nc_hwp.units = "kg/m^2"
			nc_hwp[:] = np.array(self.p["hwp"],dtype="f")
			if not pyNc: nc_hwp._FillValue =missingNumber

		if ("cloudBase" in profileVars or profileVars =="all") and ("cloudBase" in self.p.keys()):
			nc_cb = cdfFile.createVariable('cloudBase', 'f',dim2d,**fillVDict)
			nc_cb.units = "m"
			nc_cb[:] = np.array(self.p["cloudBase"],dtype="f")
			if not pyNc: nc_cb._FillValue =missingNumber

		if ("cloudTop" in profileVars or profileVars =="all") and ("cloudTop" in self.p.keys()):
			nc_ct = cdfFile.createVariable('cloudTop', 'f',dim2d,**fillVDict)
			nc_ct.units = "m"
			nc_ct[:] = np.array(self.p["cloudTop"],dtype="f")
			if not pyNc: nc_ct._FillValue =missingNumber

		cdfFile.close()
		if self.set["pyVerbose"] > 0: print fname,"written"
