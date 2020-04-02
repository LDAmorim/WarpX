#!/usr/bin/env python3

# Copyright 2020 L. Diana Amorim
#
# This file is part of WarpX.
#
# License: BSD-3-Clause-LBNL

# This file is part of the WarpX automated test suite. It is used to test the
# injection of a particle beam from an external openPMD format file.
#
# - Generate an input openPMD file with 5 physical electrons.
# - Run the WarpX simulation for 2 iterations.
# - Compare the elecrons weight, position and velocity between file and plotfile
#
# Note that this test assumes that the openPMD file uses the Geant4 unit system:
# MeV/c^2, mm and ns (http://geant4.web.cern.ch/sites/geant4.web.cern.ch/files/geant4/collaboration/working_groups/electromagnetic/gallery/units/SystemOfUnits.html).

import yt
import numpy as np
import openpmd_api as api
import scipy.constants as cte
import glob, os

######################################
# Maximum error accepted for this test
######################################
relative_error_weigth_threshold = 1.e-4
relative_error_position_threshold = 1.e-4
relative_error_velocity_threshold = 1.e-4

#############################
# Particle species properties
#############################
nparts = 5
charge=cte.e
mass=cte.m_e
x,y,z,vx,vy,vz=[[] for n in range(6)]
for i in range(1,nparts+1,1):
    x.append(1.e-6*i)
    y.append(1.5e-6*i)
    z.append(10.e-6*i)
    vx.append(2.9e-8*i)
    vy.append(3.0e-8*i)
    vz.append(3.1e-8*i)
#Using numpy arrays for compatibility with openPMD
position = np.matrix(x,y,z)
velocity = np.matrix(vx,vy,vz)

##############################
# openPMD input file for WarpX
##############################
fname="./electrons_opmd.h5"
series = openpmd_api.Series(fname, openpmd_api.Access_Type.create)
#store only 1 iteration in species
iteration = series.iterations[1]
electrons = iteration.particles["electrons"]
#Set records properties
dataset_scalar = openpmd_api.Dataset(openpmd_api.Datatype.DOUBLE,[1])
dataset = openpmd_api.Dataset(position[0].dtype,position[0].shape)
#Store electrons charge and mass
electrons["mass"][openpmd_api.Mesh_Record_Component.SCALAR].reset_dataset(dataset_scalar)
electrons["mass"][openpmd_api.Mesh_Record_Component.SCALAR].make_constant(mass)
electrons["charge"][openpmd_api.Mesh_Record_Component.SCALAR].reset_dataset(dataset_scalar)
electrons["charge"][openpmd_api.Mesh_Record_Component.SCALAR].make_constant(charge)
series.flush()
#Store the electrons position and velocity
position_list=["x","y","z"]
for i in range(3):
    f = electrons["position"][position_list[i]].reset_dataset(dataset)
    f.store_chunk(position[i])
    series.flush()
    f_v = electrons["velocity"]["v"+position_list[i]].reset_dataset(dataset)
    f_v.store_chunk(velocity[i])
    series.flush()
del series

##############################
# Getting input physical_q_tot
##############################
with open("input", 'r') as fi:
    text = fi.read().splitlines()
    for li in range(len(text)):
        line = text[li].split("=")
        if (li[0]=="physical_q_tot"):
            physical_q_tot=li[1]

#############################
# Output from WarpX plotfiles
#############################
pn="./diags/plotfiles/plt00000"
ds = yt.load(pn)
extent=[ds.domain_left_edge[0], ds.domain_right_edge[0],ds.domain_left_edge[1],
        ds.domain_right_edge[1],ds.domain_left_edge[2],ds.domain_right_edge[2]]
if ("beam", 'particle_weight') in ds.field_list:
    #print("Has beam!")
    ad = ds.all_data()
    wpx_w=ad["beam", 'particle_weight'].v
    wpx_position=[]
    for i in range(3):
        wpx_position.append(ad["beam", 'particle_position_'+position_list[i]].v)
        wpx_momentum.append(ad["beam", 'particle_momentum_'+position_list[i]].v)
    wpx_vx=[]
    wpx_vy=[]
    wpx_vz=[]
    for pi in range(ux.size):
        beta=math.sqrt((ux[pi]**2+uy[pi]**2+uz[pi]**2))/cte.c
        gamma=1/math.sqrt(1-beta**2)
        wpx_vx.append(ux[pi]/(gamma*cte.m_e))
        wpx_vy.append(uy[pi]/(gamma*cte.m_e))
        wpx_vz.append(uz[pi]/(gamma*cte.m_e))
    wpx_vx=np.asarray(wpx_vx)
    wpx_vy=np.asarray(wpx_vy)
    wpx_vz=np.asarray(wpx_vz)
    wpx_velocity=[wpx_vx,wpx_vy,wpx_vz]

###############################
# Converting Geant4 units to SI
###############################
opmd_w=(physical_q_tot/(nparts*charge*cte.e)) #using input physical_q_tot
for i in range(3):
    position[i]=position[i]*1.e-3
    velocity[i]=velocity[i]*1.e6

#################################
# Comparison of input/output data
#################################
relative_error_weight=np.abs((opmd_w-wpx_w[0])/opmd_w)
print("Relative error weight: ",relative_error_weight)
assert(relative_error_weight < relative_error_weigth_threshold)
for i in range(3):
    relative_error_position=np.abs((position[i]-wpx_position[i])/position[i])
    print("Relative error position",position_list[i],": ",relative_error_position)
    assert(relative_error_position < relative_error_position_threshold)
    relative_error_velocity=np.abs((velocity[i]-wpx_velocity[i])/velocity[i])
    print("Relative error velocity",velocity_list[i],": ",relative_error_velocity)
    assert(relative_error_velocity < relative_error_velocity_threshold)
