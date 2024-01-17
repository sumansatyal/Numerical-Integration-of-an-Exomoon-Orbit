# -*- coding: utf-8 -*-
"""testparticles_parallel.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_XE7I14i6HVvLe797eUU18Lstaa7j9qQ
"""

#!pip install rebound

import numpy as np
import rebound
import time
import multiprocessing
import warnings
# Import matplotlib
import matplotlib; matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import math
from rebound import hash as h
import csv
import pandas as pd
import glob


"""## Initial setup of system"""

def simsetup():
  """
  Sets up the active bodies: star and planet
  """
  #print("Active bodies only: Star and Planet")
  sim = rebound.Simulation()
  sim.units = ['Yr2pi','AU','Msun']   
  sim.integrator = "whfast"
  sim.ri_whfast.safe_mode = 0
  sim.dt = 0.0005          
  sim.add(m=1,hash="Sagarmatha")
  sim.add(m=0.0009543,a=1,e=0.36,hash="Laligurans")
  sim.move_to_com()
  #sim.integrator = "ias15"
  #sim.status()  
  return sim

def testparticles():
  """
  Sets up the parameters for the test particles 
  """
  # grid points along an axis
  Ngrid_a = 10   # 100 * 100 = 10000 particles
  Ngrid_e = 10
  par_a = np.linspace(0.01,0.03,Ngrid_a)  # semi-major axis values : 0.005 to 0.1
  par_e = np.linspace(0.0,0.9,Ngrid_e)  # eccentricity values  : 0.00005 to 0.9
  parameters = []
  for e in par_e:
    for a in par_a:
      #random true anomaly f=np.random.rand()*2.*np.pi if needed
      M = np.random.rand()*2.*np.pi  # Random mean anomaly if needed 
      #M = 0
      parameters.append((a,e,M))     # Smaxis, Ecc, MeanAnomaly
  return parameters,Ngrid_a,Ngrid_e

parameters,Ngrid_a,Ngrid_e = testparticles()
Nparticles = Ngrid_a * Ngrid_e
parameters;

def simtestparticles(par,status=False):
  """
  Adds the test particle with parameters par and simulates up to fulltime.
  Returns the maximum eccentricity and lifetime of the test particle
  """
  # Load the Star and Planet 
  sim = simsetup()
  # Add the test particle
  # mass of test particle is set to 0 by default
  sim.add(a=par[0],e=par[1],inc=0.00005,M=par[2],primary=sim.particles[1],hash=f'tp') 
  sim.N_active = 2   # Number of active particles in the simulation
  #print(sim.N)
  tparticle = sim.particles['tp']   
  orbit = tparticle.calculate_orbit(primary=sim.particles["Laligurans"])
  print(orbit.a,par[0],orbit.e,par[1],orbit.M,par[2])
  
  fulltime = 100*2.*np.pi    # Fulltime of the simulation: 100 years
  N_times = 10000              # Number of snapshots: 10000, snapshot every 100/10000 = 0.01 Earth years
  
  ### Array of time points of snapshots
  times = np.linspace(0, fulltime, N_times)

  ### Arrays for storing orbital parameters of the test particle
  xy     = np.zeros((N_times,2))
  smaxis = np.zeros(N_times)
  ecc    = np.zeros(N_times)
  inc    = np.zeros(N_times)
  reason = 0.5
  eject  = False
  print('Started simulation',par)
  for i,time in enumerate(times):
    sim.integrate(time,exact_finish_time=0)
    tparticle = sim.particles['tp']
    orbit     = tparticle.calculate_orbit(primary=sim.particles['Laligurans'])
    
    ### Ejection or collision checks
    if orbit.a > 0.2:
      reason = reason - 0.5 
      eject  = True
    else:
      eject  = False
    if orbit.e > 1:
      reason = reason + 0.5
      eject = True
    else:
      eject  = False
    
    ## For test particle not ejected, continue simulation
    if eject == False:
      ecc[i]    = orbit.e
      smaxis[i] = orbit.a
      inc[i]    = orbit.inc
      xy[i]     = [(sim.particles[1]-tparticle).x,(sim.particles[1]-tparticle).y]

    ## For ejected particle
    if eject:
      break    
  maxsmaxis = np.max(smaxis)
  maxecc    = np.max(ecc)
  maxinc    = np.max(inc)
  lifetime  = sim.t
  print('Completed simulation',par)
  if status:
    return sim
  else:
    return maxsmaxis,maxecc,maxinc,lifetime,par[0],par[1],par[2],reason

#simtestparticles(parameters[-1],status=True).status()

from rebound.interruptible_pool import InterruptiblePool
pool = InterruptiblePool()
t1=time.time()
results = pool.map(simtestparticles,parameters)   # maps the parameters to the simtestparticles function
t2=time.time()
print("Timer:",(t2-t1))

print(results)
type(results)

dt = np.dtype('float,float,float,float,float,float,float,float')
data = np.array(results,dtype=dt)
data.dtype.names = ['maxsm','maxecc','maxinc','time','sm','ecc','meananom','reason']
data

### Write to CSV file
filename = 'testparticles01.csv'    # specify name
with open(filename,'w') as csvfile:
  writer = csv.writer(csvfile,delimiter=',')
  writer.writerow(['Smaxis','InitialEcc','MeanAnomaly','MaxEcc','Lifetime','MaxInc','MaxSmaxis','Reason'])
  for index,datum in enumerate(data):
    print(datum[4],datum[5],datum[6],datum[1],datum[3],datum[2],datum[0],datum[7])
    writer.writerow([datum[4],datum[5],datum[6],datum[1],datum[3],datum[2],datum[0],datum[7]])

#!ls

## Plotting the maximum eccentricity and lifetime maps

################################
### Maximum Eccentricity map ###
################################

eccmax2d = np.array(data['maxecc']).reshape(Ngrid_e,Ngrid_a)
# same 90 eccs, 110 smaxis values

fig = plt.figure(figsize=(7,5))
ax = plt.subplot(111)
extent = [min(data['sm']),max(data['sm']),min(data['ecc']),max(data['ecc'])]

ax.set_xlim(extent[0],extent[1])
ax.set_xlabel("Initial semi-major axis ($au$)", fontsize=20)
ax.set_ylim(extent[2],extent[3])
ax.set_ylabel("Initial eccentricity ($e_0$)", fontsize=20)
#plt.text(0.005,0.95,r'Critical semi-major axis $a_{crit}$',fontsize=20)
ax.axvline(0.021,0.0,1,linestyle='--',linewidth=3,color='red')
plt.text(0.023,0.1,r'Critical semi-major axis'+'\n\t\t'+'$a_{crit}$',fontsize=20,rotation='vertical')
#plt.xticks(np.arange(extent[0],extent[1]+0.005,0.005),fontsize=20) 
#plt.yticks(np.arange(extent[2],extent[3]+0.1,0.1),fontsize=20)
ax.tick_params(axis='both', direction='in',length = 4.0, width = 4.0,grid_alpha=0,labelsize=20)   #grid_alpha=0 transparent

plt.xlim(0,0.03)

im = ax.imshow(eccmax2d, interpolation="none", vmin=0, vmax=1, cmap="cividis", origin="lower", aspect='auto', extent=extent)
cb = plt.colorbar(im, ax=ax) 
for t in cb.ax.get_yticklabels():
     t.set_fontsize(20)
cb.set_label("$e_{max}$",fontsize=20)
plt.savefig('maxeccmap.png',bbox_inches='tight')

##################################
########## Lifetime map ##########
##################################

#Ngrid = int(np.sqrt(len(data.index)))
lifetimes2d = (np.array(data['time']).reshape(Ngrid_e,Ngrid_a))/(2*np.pi)
# same Ngrid_e eccs, Ngrid_a smaxis values

fig = plt.figure(figsize=(7,5))
ax = plt.subplot(111)
extent = [min(data['sm']),max(data['sm']),min(data['ecc']),max(data['ecc'])]

ax.set_xlim(extent[0],extent[1])
ax.set_xlabel("Initial semi-major axis ($au$)", fontsize=20)
ax.set_ylim(extent[2],extent[3])
ax.set_ylabel("Initial eccentricity ($e_0$)", fontsize=20)
#plt.xticks(np.arange(extent[0],extent[1]+0.005,0.005),fontsize=20) 
#plt.yticks(np.arange(extent[2],extent[3]+0.1,0.1),fontsize=20)
ax.tick_params(axis='both', direction='in',length = 4.0, width = 4.0,grid_alpha=0,labelsize=20)   #grid_alpha=0 transparent
#plt.text(0.005,0.95,r'Critical semi-major axis $a_{crit}$',fontsize=20)
plt.text(0.023,0.1,r'Critical semi-major axis'+'\n\t\t'+'$a_{crit}$',fontsize=20,rotation='vertical')
ax.axvline(0.021,0.0,1,linestyle='--',linewidth=3,color='red')

plt.xlim(0,0.03)
#plt.axvline(0.0072,linestyle='--',color='orange')
#plt.axvline(0.0082,linestyle='--',color='r')
im = ax.imshow(lifetimes2d, interpolation="none", vmin=0, vmax=np.max(lifetimes2d),\
               cmap="YlGn", origin="lower", aspect='auto', extent=extent)   #YlGn
cb = plt.colorbar(im, ax=ax) 
for t in cb.ax.get_yticklabels():
     t.set_fontsize(20)
cb.set_label("Lifetime (Yr)",fontsize=20)
plt.savefig('Lifetime.png',bbox_inches='tight')


################################
### Initial eccentricity map ###
################################

ecc2d = np.array(data['ecc']).reshape(Ngrid_e,Ngrid_a)
# same Ngrid_e eccs, Ngrid_a smaxis values

fig = plt.figure(figsize=(7,5))
ax = plt.subplot(111)
extent = [min(data['sm']),max(data['sm']),min(data['ecc']),max(data['ecc'])]

ax.set_xlim(extent[0],extent[1])
ax.set_xlabel("Semi-major axis ($au$)", fontsize=20)
ax.set_ylim(extent[2],extent[3])
ax.set_ylabel("Eccentricity ($e_0$)", fontsize=20)
#plt.xticks(np.arange(extent[0],extent[1]+0.005,0.005),fontsize=20) 
#plt.yticks(np.arange(extent[2],extent[3]+0.1,0.1),fontsize=20)
ax.tick_params(axis='both', direction='in',length = 4.0, width = 4.0,grid_alpha=0,labelsize=20)   #grid_alpha=0 transparent
plt.xlim(0,0.03)

im = ax.imshow(ecc2d, interpolation="none", vmin=0, vmax=1, cmap="cividis", origin="lower", aspect='auto', extent=extent)
cb = plt.colorbar(im, ax=ax) 
for t in cb.ax.get_yticklabels():
     t.set_fontsize(20)
cb.set_label("Inital Eccentricity ($e_{0}$)",fontsize=20)
plt.savefig('initialeccmap.png',bbox_inches='tight')

###################################
### Initial semi-major axis map ###
###################################

smaxis2d = np.array(data['sm']).reshape(Ngrid_e,Ngrid_a)
# same Ngrid_e eccs, Ngrid_a smaxis values

fig = plt.figure(figsize=(7,5))
ax = plt.subplot(111)
extent = [min(data['sm']),max(data['sm']),min(data['ecc']),max(data['ecc'])]

ax.set_xlim(extent[0],extent[1])
ax.set_xlabel("Semi-major axis ($au$)", fontsize=20)
ax.set_ylim(extent[2],extent[3])
ax.set_ylabel("Eccentricity ($e_0$)", fontsize=20)
#plt.xticks(np.arange(extent[0],extent[1]+0.005,0.005),fontsize=20) 
#plt.yticks(np.arange(extent[2],extent[3]+0.1,0.1),fontsize=20)
ax.tick_params(axis='both', direction='in',length = 4.0, width = 4.0,grid_alpha=0,labelsize=20)   #grid_alpha=0 transparent

plt.xlim(0,0.03)

im = ax.imshow(smaxis2d, interpolation="none", vmin=np.min(smaxis2d), vmax=np.max(smaxis2d), cmap="cividis", origin="lower", aspect='auto', extent=extent)
cb = plt.colorbar(im, ax=ax) 
for t in cb.ax.get_yticklabels():
     t.set_fontsize(20)
cb.set_label("Starting Semi-major axis ($a_{0}$)",fontsize=20)
plt.savefig('initialsmaxismap.png',bbox_inches='tight')



