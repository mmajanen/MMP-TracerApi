import clientConfig as cConf
import Pyro4
from mmp_tracer_api import objID
from comsol_api import MMPComsolDummy
from mupif import PyroUtil, Property, PropertyID, FieldID, ValueType
import logging
logger = logging.getLogger()


import time as timeTime
start = timeTime.time()
logger.info('Timer started')

# locate nameserver
ns = PyroUtil.connectNameServer(nshost=cConf.nshost,
                                nsport=cConf.nsport,
                                hkey=cConf.hkey)
logger.info('NS connected: %s' % str(ns))


# Tunnels to different machines machine
mieTunnel = PyroUtil.sshTunnel(remoteHost=cConf.mieServer,
                               userName=cConf.mieUser,
                               localPort=cConf.mieNatPort,
                               remotePort=cConf.miePort,
                               sshClient=cConf.sshClient,
                               options=cConf.options,
                               sshHost=cConf.sshHost)
tracerTunnel = PyroUtil.sshTunnel(remoteHost=cConf.tracerServer,
                                  userName=cConf.tracerUser,
                                  localPort=cConf.tracerNatPort,
                                  remotePort=cConf.tracerPort,
                                  sshClient=cConf.sshClient,
                                  options=cConf.options,
                                  sshHost=cConf.sshHost)

comsolTunnel = PyroUtil.sshTunnel(remoteHost=cConf.mieServer,
                                  userName=cConf.mieUser,
                                  localPort=cConf.mieNatPort,
                                  remotePort=cConf.miePort,
                                  sshClient=cConf.sshClient,
                                  options=cConf.options,
                                  sshHost=cConf.sshHost)



mieApp = PyroUtil.connectApp(ns, cConf.mieID)
tracerApp = PyroUtil.connectApp(ns, cConf.tracerID)
comsolApp = PyroUtil.connectApp(ns, cConf.comsolID)

# Point data conversion to false. Speeds up testing
#tracerApp._convertPointData = False #does not work over pyro4... not exposed

logger.info('Applications loaded:')
print(mieApp)
print(tracerApp)
print(comsolApp)


# Connect fields
logger.info('Connecting Fields...')
# old way to connect fields:
fHeatSurf = comsolApp.getField(FieldID.FID_Thermal_absorption_surface, 0)
fHeatVol = comsolApp.getField(FieldID.FID_Thermal_absorption_volume, 0)

tracerApp.setField(fHeatSurf)
tracerApp.setField(fHeatVol)
logger.info('Fields connected')

# Connect properties

# Emission spectrum
import numpy as np

a = {}
A = np.loadtxt('../../mmp_tracer_api/data/EM_GREEN.dat')
a['wavelengths'] = A[:, 0]
a['intensities'] = A[:, 1]
em = Property.Property(value=a,
                       propID=PropertyID.PID_EmissionSpectrum,
                       valueType=ValueType.Scalar,
                       time=0.0,
                       units=None,
                       objectID=objID.OBJ_PARTICLE_TYPE_1)
tracerApp.setProperty(em)

# Excitation spectrum
b = {}
B = np.loadtxt('../../mmp_tracer_api/data/EX_GREEN.dat')
b['wavelengths'] = B[:, 0]
b['intensities'] = B[:, 1]
ex = Property.Property(value=b,
                       propID=PropertyID.PID_ExcitationSpectrum,
                       valueType=ValueType.Scalar,
                       time=0.0,
                       units=None,
                       objectID=objID.OBJ_PARTICLE_TYPE_1)
tracerApp.setProperty(ex)

# Absorption spectrum
c = {}
C = np.loadtxt('../../mmp_tracer_api/data/Abs_GREEN.dat')
c['wavelengths'] = C[:, 0]
c['intensities'] = C[:, 1]
aabs = Property.Property(value=c,
                         propID=PropertyID.PID_AsorptionSpectrum,
                         valueType=ValueType.Scalar,
                         time=0.0,
                         units=None,
                         objectID=objID.OBJ_PARTICLE_TYPE_1)
tracerApp.setProperty(aabs)




# Particle density
logger.info('Setting Properties...')
vDens = 0.00000003400
pDens = Property.Property(value=vDens,
                          propID=PropertyID.PID_ParticleNumberDensity,
                          valueType=ValueType.Scalar,
                          time=0.0,
                          units=None,
                          objectID=objID.OBJ_CONE)
tracerApp.setProperty(pDens)

# Number of rays to trace
pRays = Property.Property(value=100,
                          propID=PropertyID.PID_NumberOfRays,
                          valueType=ValueType.Scalar,
                          time=0.0,
                          units=None,
                          objectID=objID.OBJ_CONE)
tracerApp.setProperty(pRays)
logger.info('Properties set!')

# Solve mie
mieApp.solveStep(0)

# Connect mie properties to tracer
logger.info('Connecting Mie properties...')
pScat = mieApp.getProperty(PropertyID.PID_ScatteringCrossSections, 0,
                           objID.OBJ_PARTICLE_TYPE_1)

pPhase = mieApp.getProperty(PropertyID.PID_InverseCumulativeDist, 0,
                            objID.OBJ_PARTICLE_TYPE_1)

logger.info('Props received...')
tracerApp.setProperty(pScat, objID.OBJ_PARTICLE_TYPE_1)
tracerApp.setProperty(pPhase, objID.OBJ_PARTICLE_TYPE_1)
logger.info('Props connected')

# Solve tracer
tracerApp.solveStep(0, runInBackground=False)

# Connect tracer back to comsol
fHeatSurf = tracerApp.getField(FieldID.FID_Thermal_absorption_surface, 0)
fHeatVol = tracerApp.getField(FieldID.FID_Thermal_absorption_volume, 0)
comsolApp.setField(fHeatSurf)
comsolApp.setField(fHeatVol)

# Solve comsol
comsolApp.solveStep(0)

# Plot data to file
# logger.info("Saving vtk")
# v = fHeatVol.field2VTKData()
# v.tofile('testHeat.vtk')
'''

# Kill tunnels.
mieTunnel.kill()
tracerTunnel.kill()
# comsolTunnel.kill()
'''
