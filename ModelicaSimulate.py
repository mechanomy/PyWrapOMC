# MIT License
# Copyright (c) 2023 Mechanomy LLC
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import os
import glob
import gc
import json
import pprint
import numpy as np
pp = pprint.PrettyPrinter(indent=2)
import copy
import re
from OMPython import OMCSessionZMQ
import time
import datetime
import tempfile #create a temporary directory
import shutil #copying files
import time
from multiprocessing import Pool

# sys.path.append('.')
from ModelicaResult import ModelicaResult

class ModelicaScriptingWrapper: 
    """Wrap the OMC scripting api to stop tripping over formats.  The reference to OMC is the only state.
    """

    omc = {} #reference to the OMC ZMQ server
    tempDir = {} # temporary directory

    def __init__(self):
        self.omc = OMCSessionZMQ()  # starts an OMC server, often throws an error if immediately shut down..

        self.tempDir = tempfile.TemporaryDirectory()
        # print(self.tempDir)
        # self.tempDir = tempfile.TemporaryDirectory(prefix='ModelicaSimulate_') # leads to relative path crossing drives error https://stackoverflow.com/questions/40448938/valueerror-path-is-on-mount-c-start-on-mount-f-while-django-migrations-i
        self.tempDir = tempfile.TemporaryDirectory(prefix='ModelicaSimulate_', dir='./test/') 
        print('made tempDir[' + self.tempDir.name + ']')
        # self.tempDir = {'name':'test'}
        self.setWorkingDirectory(self.tempDir.name)
        # print(self.getWorkingDirectory())

    def getModelicaPath(self):
        ret = self.omc.sendExpression('getModelicaPath()')
        return ret
    def setModelicaPath(self, newPath):
        ret = self.omc.sendExpression('setModelicaPath("{0}")'.format(newPath))
        if ret is False:
            # warnings.warn('setModelicaPath to [' + newPath +'] failed')
            print('setModelicaPath to [' + newPath +'] failed')
        return ret
    def addModelicaPath(self, newPath):
        orig = self.getModelicaPath()
        ret = self.omc.sendExpression('setModelicaPath("{0}")'.format(orig + ':' + newPath))
        return ret

    def cd(self, newPath = ''):
        ret = self.omc.sendExpression('cd("./{0}")'.format( newPath ) )
        return ret
    def getWorkingDirectory(self): #wraps cd()
        return self.cd('')
    def setWorkingDirectory(self, newPath): #wraps cd(newPath)
        # return self.cd(self.getRelativePathFromWorkingDirectory(newPath) )
        return self.cd(os.path.abspath(newPath))

    def getRelativePathFromWorkingDirectory(self, path): #return a path relative to Modelica's working directory
        path = os.path.expanduser(path)
        if os.path.exists(path):
            moPath = self.getWorkingDirectory()
            rel = os.path.relpath(path, moPath)
            # print('getRelative: path[{0}] mo[{1}] = rel[{2}]'.format(path,moPath,rel))
            return rel
        else:
            print('getRelative: path[{0}] does not exist'.format(path))
            return False

    def loadModelicaStandardLibrary(self): #load the ModelicaStandardLibrary installed with OMC
        ret = self.omc.sendExpression('loadModel(Modelica)')
        return ret

    def loadFile(self, filePath): #load some other *.mo file, True = load success, False = failed
        relPath = self.getRelativePathFromWorkingDirectory( filePath ) #file path must be RELATIVE to Modelica's working directory, absolute do not work
        if relPath:
            ret = self.omc.sendExpression('loadFile("./{0}")'.format( relPath ) )
            if not ret:
                print('Modelica.loadFile(): on filePath[' + filePath +'] relPath[' + relPath +'] returned',ret)
        else:
            print('loadFile: relPath failed', relPath)
            ret = False

        if ret is False :
            print('loadFile [' + filePath +'] failed')

        return ret

    def loadModel(self, modelName):
        ret = self.omc.sendExpression(f"loadModel({modelName})")
        if not ret:
            print('loadModel', ret )
        return ret

    def getModelParameterNames(self,modelName): #this fails
        ret = self.omc.sendExpression('getParameterNames({})'.format(modelName))
        print('getModelParameterNames() returned', ret, 'probably failed for ?reasons?')
        return ret

    def getModelParameterValue(self,modelName,parameterName): #this fails
        ret = self.omc.sendExpression('getParameterNames({}, "{}")'.format(modelName,parameterName))
        print('getModelParameterValue() returned', ret, 'probably failed for ?reasons?')
        return ret

    def checkModel(self, modelName): #check the already-loaded model file for errors
        checkModelString = self.omc.sendExpression('checkModel({0})'.format(modelName))
        # pp.pprint(checkModelString)
        # print descriptive error messages
        return self.parseCheckModelString( checkModelString )

    def parseCheckModelString(self, checkModelString):
        checkInfo = {}

        a = re.search(r'.*completed\Wsuccessfully.*', checkModelString)
        if a is None:
            # print('a none', a)
            checkInfo['success'] = False
        else:
            # print('a', a)
            checkInfo['success'] = True

        rexpr = r'.*has\W(\d*)\Wequation\(s\)\Wand\W(\d*)\Wvariable.*'
        n = re.search( rexpr, checkModelString) #find which line
        if n is not None:
            o = re.match( rexpr, n.group()) #find the numbers
            if o is not  None:
                checkInfo['nEquations'] = int(o.groups(0)[0])
                checkInfo['nVariables'] = int(o.groups(0)[1])
            else:
                print('checkModel: equation o is none')
        else:
            print('checkModel: equation n is none')

        rexpr = r'(\d*)\Wof\Wthese\Ware\Wtrivial.*'
        n = re.search( rexpr, checkModelString) #find which line
        if n is not None:
            o = re.match( rexpr, n.group()) #find the numbers
            if o is not None:
                checkInfo['nTrivial'] = int(o.groups(0)[0])
            else:
                print('checkModel: trivial o is none')
        else:
            print('checkModel: trivial n is none')

        # pp.pprint(checkInfo)
        return checkInfo

    def getErrorString(self):
        ret = self.omc.sendExpression('getErrorString()')
        # print('getErrorString()', ret)
        return ret

    def buildModel(self, modelName, buildOptions):
        if buildOptions == None:
            # return {'startTime':0, 'stopTime':1, 'numberOfIntervals':100, 'tolerance':1e-3, 'method':'\"dassl\"', 'cflags':'\"--debug\"' } #210831 dassl not found by omc...?
            return {'startTime':0, 'stopTime':1, 'numberOfIntervals':100, 'tolerance':1e-3, 'cflags':'\"--debug\"' }
        cmd = {'command':'buildModel', 'modelName':modelName, 'separateByCommas':buildOptions }
        ret = self.executeCommand( cmd ) #buildModel returns a tuple for some lame reason, really need to fix OMPython

        print('buildModel: [{}], returned'.format(cmd))
        pp.pprint(ret)

        if isinstance(ret['executeCommand'], tuple):
            return {'modelExecutablePath': ret['executeCommand'][0], 'modelXMLPath':ret['executeCommand'][1], 'success':True}
        else:
            return {'success':False}

    def getSimulationOptionsFromExperimentAnnotation(self, filePath): #if filePath is to an overall package, this fails
        #read the simulation options from the experiment() annotation
        # simopt = {'startTime':0, 'stopTime':1, 'interval':0.01, 'numberOfIntervals':20, 'tolerance':1e-3, 'method':'dassl'} #sensible defaults
        simopt = {'startTime':0, 'stopTime':1, 'interval':0.01, 'numberOfIntervals':20, 'tolerance':1e-3 } #210831 dassl not found?
        # simopt = {'startTime':0, 'stopTime':1, 'interval':0.01, 'numberOfIntervals':20, 'tolerance':1e-3, 'solver':'dassl'} #sensible defaults
        simoptSetFromExperiment = False

        with open( filePath, 'r') as file:
            mtxt = file.read()
            # pp.pprint(mtxt)

            mat = re.findall( r'experiment\s?\(.*StartTime\s?=\s?([\d\w\.\-\+]+)', mtxt )
            if mat:
                simopt['startTime'] = float(mat[0])
                simoptSetFromExperiment = True
            mat = re.findall( r'experiment\s?\(.*StopTime\s?=\s?([\d\w\.\-\+]+)', mtxt )
            if mat:
                simopt['stopTime'] = float(mat[0])
                simoptSetFromExperiment = True

            mat = re.findall( r'experiment\s?\(.*Interval\s?=\s?([\d\w\.\-\+]+)', mtxt )
            if mat:
                simopt['interval'] = float(mat[0])
                simopt['numberOfIntervals'] = int( (simopt['stopTime']-simopt['startTime'])/simopt['interval'] )
                simoptSetFromExperiment = True

            mat = re.findall( r'experiment\s?\(.*NumberOfIntervals\s?=\s?([\d\w\.\-\+]+)', mtxt )
            if mat:
                simopt['interval'] = (simopt['stopTime']-simopt['startTime'])/simopt['numberOfIntervals']
                simopt['numberOfIntervals'] = int(mat[0])
                simoptSetFromExperiment = True

            mat = re.findall( r'experiment\s?\(.*Tolerance\s?=\s?([\d\w\.\-\+]+)', mtxt )
            if mat:
                simopt['tolerance'] = float(mat[0])
                simoptSetFromExperiment = True

            mat = re.findall( r'experiment\s?\(.*Method\s?=\s?[\'"]([\w]+)', mtxt )
            if mat:
                simopt['method'] = mat[0]
                simoptSetFromExperiment = True

        if (not simoptSetFromExperiment and len(sys.argv) != 3):
            # simopt = {'startTime':0, 'stopTime':0.93, 'numberOfIntervals':100, 'tolerance':1e-6, 'method':'dassl'}
            simopt = {'startTime':0, 'stopTime':0.93, 'numberOfIntervals':100, 'tolerance':1e-6} #210831 dassl not found?
            print('Simulation options not specified, using default: ' + simopt.__str__() + '\n');

        if (not simoptSetFromExperiment and len(sys.argv) == 3):
            simopt = json.loads( sys.argv[2] ) #simopt always has all simulation options!
            print('Simulation options specified on command line: ' + simopt.__str__() + '\n');

        return simopt

    def getSimulateCommandDict(self):
        cmdDict = {'command':'simulate',
                'modelName':'BouncingBall',
                'startTime':0,
                'stopTime':1,
                'numberOfIntervals':100,
                'tolerance':1e-3,
                # 'method':'\"dassl\"',
                # 'outputFormat':'\"mat\"',
                # 'cflags':'\"--debug\"',
                'cflags':'"-Os -fPIC -falign-functions -mfpmath=sse -fno-dollars-in-identifiers"',
                'options':'\"-v -abortSlowSimulation -steadyState -alarm=10 -logFormat=xml -lv=LOG_INIT --simplifyLoops\"', #note "" include for Modelica
                }
        return cmdDict

    def buildCommandFromDict(self, cmdDict): #cmdDict should be a single-level dictionary
        byCommas = ''
        for key in cmdDict:
            if key != 'modelName' and key != 'command' and key != 'interval':
                byCommas += '{}={}, '.format(key, cmdDict[key])
                # print(byCommas+'\n',end='')

        # print('byCommas', byCommas)
        cmd = '{}({}, {})'.format(cmdDict['command'], cmdDict['modelName'], byCommas[:-2]) #remove the last comma and space
        # print('cmd', cmd)

        return cmd

    def executeCommand( self, cmdDict ):
        cd = self.buildCommandFromDict( cmdDict )
        #simulate(DriveShaftCompareTerminalVoltage, startTime=0.0, stopTime=0.4, interval=0.0001,
        # numberOfIntervals=4000, tolerance=0.001, method=dassl, cflags="--debug",
        # options="-v -abortSlowSimulation -steadyState -alarm=10 -logFormat=xml -lv=LOG_INIT --simplifyLoops")

        # cd2 = 'simulate(DriveShaftCompareTerminalVoltage, startTime=0.0, stopTime=0.4, numberOfIntervals=4000, tolerance=0.001, method=dassl, cflags="--debug", options="-v -abortSlowSimulation -steadyState -alarm=10 -logFormat=xml -lv=LOG_INIT --simplifyLoops" )'
        # print('executeCommand=[\n'+cd+'\n'+cd2+'\n]')
        ret = self.omc.sendExpression( cd )
        # print('executeCommand: ret=', ret)
        # print('executeCommand:')
        # pp.pprint(ret)

        retDict = {'command':cd}
        if ret is None:
            retDict['success']=False
        elif isinstance(ret,dict):
            retDict.update(ret)
            retDict['success'] = True
        else:
            retDict['executeCommand']=ret
            retDict['success'] = True
        return retDict

    def simulate(self, modelName, simOptions): #={'startTime':0, 'stopTime':1, 'numberOfIntervals':20, 'tolerance':1e-3, 'method':'dassl'}):
        simOptions['command'] = 'simulate'
        simOptions['modelName'] = modelName

        if not simOptions.get('method'):
            simOptions['method'] = '"dassl"'
        # if not simOptions.get('solver'):
        #     simOptions['solver'] = '"dassl"'
        # if not simOptions.get('outputFormat'):
        #     simOptions['outputFormat'] = '"mat"'
        if not simOptions.get('cflags'):
            # simOptions['cflags'] = '"--debug"'
            simOptions['cflags'] = '"-Os -fPIC -falign-functions -mfpmath=sse -fno-dollars-in-identifiers"'#note "" include for Modelica
        if not simOptions.get('options'):
            simOptions['options'] = '"-v -abortSlowSimulation -steadyState -alarm=10 -logFormat=xmltcp -lv=LOG_INIT,LOG_STATS,LOG_STATS_V,LOG_DEBUG,LOG_SOLVER,LOG_SUCCESS --simplifyLoops --tearingStrictness=veryStrict"' #note "" include for Modelica

        # print('MSW.simulate.simOptions', simOptions )
        # cd['simflags'] = '\"-override R=1.35,Lw=6e-3\"'

        simDict = self.executeCommand( simOptions )
        print('simDict:')
        pp.pprint(simDict)

        if simDict is None:
            return {'success':False}
        if not simDict.get('messages'):
            return simDict

        a = re.search(r'LOG_SUCCESS', simDict['messages']) #overwrite command success with simulation success
        if a:
            simDict['success'] = True
        else:
            simDict['success'] = False

        return simDict

    def elaborateParamList(self, paramDict): #take the start/stop/inc parameter list and return an array over all combinations
        # paramDict = { 'cor':{'start':0.1,'stop':0.9,'increment':0.1}, 'h':{'start':1,'stop':9,'increment':1} }
        # returns [ {'cor':0.1, 'h':1'}, {'cor':0.1, 'h':2'}, {'cor':0.1, 'h':3'}, ... {'cor':0.2, 'h':1'},...{'cor':0.9, 'h':9'}]
        # use with: 
            # paramDict.update(makeParameterStartStopN('termR', 40, 60, 5)) #
            # paramDict.update(makeParameterStartStopLogN('ra_dRotor', -2, 1, 30)) #
            # paramDict.update(makeParameterStartStopInc('J', 1e-5, 1e-4,  1e-5)) #2e-5 in model

        # print('elaborateParamList', paramDict)
        lst = []
        for key in paramDict:
            pl = paramDict[key]
            if pl.get('increment'):
                pl['range'] = np.arange(pl['start'], pl['stop'], pl['increment'] )

            if pl.get('n'):
                if pl['n'] == 1:
                    pl['range'] = np.array([pl['start']])
                else:
                    pl['range'] = np.linspace(pl['start'], pl['stop'], pl['n'] )

            if pl.get('logN'):
                if pl['logN'] == 1:
                    pl['range'] = np.array([pl['start']])
                else:
                    pl['range'] = np.logspace(pl['start'], pl['stop'], pl['logN'] )

            # print(pl['range'].size)
            if 0<pl['range'].size:
                lst = self.elaborateRangesDict( lst, key=key, rng=pl['range'] )
            else:
                print(f"failed to make range for [{key}] from [{pl['start']}] to [{pl['stop']}] inc[{pl['increment']}]")
                for l in lst:
                    l.update({key: pl['start']})
        # pp.pprint(lst)
        # print('elaborateParamList: len(lst)=', len(lst))
        return lst

    def elaborateRangesDict(self, lst, key, rng): #create a new list with every element in rng added to lst
        if len(lst) == 0:
            ret = []
            for r in rng:
                ret.append({key:r})
            return ret
        else:
            ret = []
            for l in lst:
                for r in rng:
                    a = copy.deepcopy(l)
                    a[key] = r
                    ret.append( a )
            return ret

    def overrideParamDict2String(self, over):
        overout = ''
        for key in over:
            # overout += '{}={}, '.format(key, over[key])
            val = over[key]
            if isinstance(val, float):
                overout += '{}={:3.3e},'.format(key, over[key])
            else:
                overout += '{}={},'.format(key, over[key])
        return overout[:-1] #remove trailing [, ]

    def writeOverrideFile(self, paramDict ): #write an overrideFile for overriding model parameters
        #https://www.openmodelica.org/doc/OpenModelicaUsersGuide/latest/simulationflags.html#simflag-override
        # paramDict = {'cor':0.1, 'h':1'}
        # returns override path
        opath = os.path.join( self.tempDir.name, 'override.txt')
        with open(opath, 'w' ) as f:
            for key in paramDict:
                f.write('{}={}'.format(key, paramDict[key] ))

        return opath

    def copyFromTemp(self, fileName, newName='', newPath='./'): #copy files from the temporary directory to python's current directory
        fpath = os.path.join(self.tempDir.name, fileName)
        if os.path.exists(os.path.join(newPath,newName)):
            npath = os.path.join(newPath, newName)
        else:
            npath = os.path.join(newPath, os.path.basename(fileName))

        # if newName == '':
        #     npath = os.path.join(newPath, os.path.basename(fileName))
        # else:
        #     npath = os.path.join(newPath, newName)
        print('fpath', fpath, 'npath', npath)

        if os.path.exists(fpath):
            try:
                return shutil.copy2( fpath, npath  ) #returns the new paht
            except OSError as err:
                print('caught OSError copying ['+ fpath+ '] to ['+ npath +']', err)
            except Exception as err:
                print('caught some exception copying ['+ fpath+ '] to ['+ npath +']', err)
        else:
            print('copyFromTemp: path does not exist', fpath)
        return False

def test_MSW_loadFile():
    #test loading a single modelica file:
    msw = ModelicaScriptingWrapper()
    msw.loadFile('./test/dampedPendulum/dampedPendulum.mo')


msw = ModelicaScriptingWrapper() #one instance for all simulation methods lest we keep spinning up omc servers

fullPath = ''
diretoryPath = ''
modelFileName = ''
retLoadMSL = False
retLoadLibraries=True
retLoadModel=False
retCheckModel=False
simOps = {}
def ModelicaOptimize( modelPath, modelName, libraryPaths=[], modelParameters={}, resultDir='.', reinit=True ):
    if reinit:
        fullPath = os.path.expanduser(modelPath)
        directoryPath, modelFileName = os.path.split( fullPath )

        retLoadMSL = msw.loadModelicaStandardLibrary()
        if not retLoadMSL:
            sys.exit(1)

        retLoadLibraries = True
        for lib in libraryPaths:
            retLoadLibraries &= os.path.exists( os.path.expanduser(lib) )
            retLoadLibraries &= msw.loadFile( lib )
            if not retLoadLibraries:
                print('Library [', lib, '] does not exist, specify correct path')
        if not retLoadLibraries:
            sys.exit(1)

        retLoadModel = msw.loadFile( fullPath )
        if not retLoadModel:
            sys.exit(1)
        retCheckModel = msw.checkModel(modelName)
        if not retCheckModel['success']:
            sys.exit(1)

        simOps = msw.getSimulationOptionsFromExperimentAnnotation(fullPath)

    if modelParameters:
        overstring = msw.overrideParamDict2String( modelParameters )
        simOps.update({'simflags':'\"-override {}\"'.format(overstring)} )

    simInfo = msw.simulate(modelName, simOps)
    # if simInfo['success']:
        # resultDestination = msw.copyFromTemp(simInfo['resultFile'])
        # simInfo['resultFile'] = resultDestination
    return simInfo

def ModelicaSimulate( modelPath, modelName, libraryPaths=[], modelParameters={}, resultPath='.' ): # compile and simulate the given model, returning the result path
    """Simulate the given file, producing Modelica result [.mat] and [.log] files.
    modelPath='' relative or absolute path to the Modelica model, eg '~/test/BouncingBall/BouncingBall.mo' 
    modelName='' name of the model when parsed by Modelica, eg 'BouncingBall' 
    libraryPaths=[] libraries to include; the Modelica Standard Library is automatically loaded, eg ['~/lib/MMR_SpringDamper_Limited.mo', '~/lib/MMR_SpringDamper_Unlimited.mo']
    modelParameters={} override the simulation parameters written in the experiment annotation, eg {'ra_jLoad': -5}. See also ModelicaSimulate.makeParameterStartStopN()...
    resultPath='.' optional directory for the results, eg './test/BouncingBall/BouncingBall_res.mat'
    """
    fullPath = ''
    diretoryPath = ''
    modelFileName = ''

    fullPath = os.path.expanduser(modelPath)
    directoryPath, modelFileName = os.path.split( fullPath )

    retLoadMSL = msw.loadModelicaStandardLibrary()
    if not retLoadMSL:
        print('loadMSL:',msw.getErrorString())
        sys.exit(1)
    # print('loadMSL:',msw.getErrorString())

    retLoadLibraries = True
    for lib in libraryPaths:
        retLoadLibraries &= os.path.exists( os.path.expanduser(lib) )
        retLoadLibraries &= msw.loadFile( lib )
        if not retLoadLibraries:
            print('Library [', lib, '] does not exist, specify correct path')
            print(msw.getErrorString())
    if not retLoadLibraries:
        print('loadLibraries:', msw.getErrorString())
        sys.exit(1)
    # print('loadLibraries:', msw.getErrorString())

    retLoadModel = msw.loadFile( fullPath )
    if not retLoadModel:
        print('loadFile:',msw.getErrorString())
        sys.exit(1)
    # print('loadFile:', retLoadModel, msw.getErrorString())

    retCheckModel = msw.checkModel(modelName)
    if not retCheckModel['success']:
        print('checkModel:', msw.getErrorString())
        # sys.exit(1)

    simOps = msw.getSimulationOptionsFromExperimentAnnotation(fullPath)
    # print('simOps:')
    # pp.pprint(simOps)

    if modelParameters:
        overstring = msw.overrideParamDict2String( modelParameters )
        simOps.update({'simflags':'\"-override={}\"'.format(overstring)} )

    simInfo = msw.simulate(modelName, simOps)
    if not simInfo['success']:
        print('simInfo:')
        pp.pprint(simInfo)
        # print(simInfo['simulationOptions'])
        # print(simInfo['command'])
        print('simulate:', msw.getErrorString())

    mname = modelName + '.log'
    simInfo['logFile'] = msw.copyFromTemp( mname, newName=mname, newPath=resultPath )

    # print('Waiting for Enter:')
    # input() #use to capture build files from /tmp
    if len(simInfo['resultFile']) == 0:
        print('resultFile length is 0, simulation failed to complete')
        simInfo['success'] = False

    if simInfo['success'] and simInfo['resultFile']:
        mname = modelName + '.log'
        resultDestination = msw.copyFromTemp( simInfo['resultFile'], newName=os.path.basename(simInfo['resultFile']), newPath=resultPath )
        pp.pprint(resultDestination)
        simInfo['resultFile'] = resultDestination
    return simInfo

def ModelicaSimulateSweep( modelPath, modelName, libraryPaths, sweepParameters, resultDir='.'): # compile and simulate the given model, returning the result path; rebuilds the model for _every_ parameter since <override> fails
    fullPath = ''
    diretoryPath = ''
    modelFileName = ''

    fullPath = os.path.expanduser(modelPath)
    directoryPath, modelFileName = os.path.split( fullPath )

    retLoadMSL = msw.loadModelicaStandardLibrary()
    if not retLoadMSL:
        print('retLoadMSL')
        sys.exit(1)

    retLoadLibraries = True
    for lib in libraryPaths:
        retLoadLibraries &= os.path.exists( os.path.expanduser(lib) )
        retLoadLibraries &= msw.loadFile( lib )
        if not retLoadLibraries:
            print('Library [', lib, '] does not exist, specify correct path')
    if not retLoadLibraries:
        print('retLoadLibraries')
        sys.exit(1)

    retLoadModel = msw.loadFile( fullPath )
    if not retLoadModel:
        print('retLoadModel')
        sys.exit(1)
    retCheckModel = msw.checkModel(modelName)
    if not retCheckModel['success']:
        print('retCheckModel')
        mname = modelName + '.log'
        msw.copyFromTemp( os.path.join(resultDir,mname), mname )
        sys.exit(1)

    sweepInfo = []
    flatParamList = msw.elaborateParamList(sweepParameters)
    nf = len(flatParamList)
    cnt = 0
    tstart = datetime.datetime.now()
    for pl in flatParamList:
        simOps = msw.getSimulationOptionsFromExperimentAnnotation(fullPath)

        # cd['simflags'] = '\"-override R=1.35,Lw=6e-3\"'
        overstring = msw.overrideParamDict2String( pl )

        simOps.update({'simflags':'\"-override {}\"'.format(overstring)} )
        # print('MSS.simOps:')
        # pp.pprint(simOps)

        simInfo = msw.simulate(modelName, simOps)
        simInfo.update({'paramList':pl})
        # print('MSS.simInfo:')
        # pp.pprint(simInfo)
        # print('MSS.simInfo.command: ', simInfo['command'])

        overstring = overstring.replace(' ', '')
        simInfo['overrideString'] = overstring
        # mname = modelName + '.log'
        # simInfo['logFile'] = msw.copyFromTemp( mname, mname.replace('.log', '_'+overstring+'.log') )

        cnt += 1
        telap = (datetime.datetime.now() - tstart).total_seconds()
        remain = telap/cnt*(nf-cnt)/60
        status = f"{cnt:3d}:{nf:3d} remain[{remain:3.1f}]m"
        if simInfo['success']:
            rpath = os.path.join( resultDir, os.path.basename( simInfo['resultFile'] ).replace('.mat', '_'+overstring+'.mat'))
            simInfo['resultFile'] = msw.copyFromTemp(simInfo['resultFile'], rpath)
            print(status+' result path:', simInfo['resultFile'])
        else:
            print(status+'simInfo sayz not succssful, cant copy results')
            pp.pprint(simInfo)

        sweepInfo.append(simInfo)
    return sweepInfo

def ModelicaSimulateAnalyzeSweep( modelPath, modelName, libraryPaths, sweepParameters, nKeep=100, resultDir='.'): # compile and simulate the given model, returning the result path; rebuilds the model for _every_ parameter since <override> fails
    fullPath = ''
    diretoryPath = ''
    modelFileName = ''

    # msw = ModelicaScriptingWrapper()
    mre = ModelicaResult()

    fullPath = os.path.expanduser(modelPath)
    directoryPath, modelFileName = os.path.split( fullPath )

    retLoadMSL = msw.loadModelicaStandardLibrary()
    if not retLoadMSL:
        print("Couldn't load MSL")
        sys.exit(1)

    retLoadLibraries = True
    for lib in libraryPaths:
        retLoadLibraries &= os.path.exists( os.path.expanduser(lib) )
        retLoadLibraries &= msw.loadFile( lib )
        if not retLoadLibraries:
            print('Library [', lib, '] does not exist, specify correct path')
    if not retLoadLibraries:
        sys.exit(1)

    retLoadModel = msw.loadFile( fullPath )
    if not retLoadModel:
        print("Couldn't load model")
        sys.exit(1)
    retCheckModel = msw.checkModel(modelName)
    if not retCheckModel['success']:
        print("Couldn't check model")
        sys.exit(1)

    sweepInfo = []
    flatParamList = msw.elaborateParamList(sweepParameters)
    nf = len(flatParamList)
    if nKeep < 0:
        nKeep = nf
    cnt = 0
    best = []


    for pl in flatParamList:
    # pool = multiprocessing.Pool(4)
        simOps = msw.getSimulationOptionsFromExperimentAnnotation(fullPath)

        overstring = msw.overrideParamDict2String( pl )
        simOps.update({'simflags':'\"-override {}\"'.format(overstring)} )
        # print('MSS.simOps:')
        # pp.pprint(simOps)

        simInfo = msw.simulate(modelName, simOps)
        # print('MSS.simInfo:')
        # pp.pprint(simInfo)
        # print('MSS.simInfo.command: ', simInfo['command'])

        overstring = overstring.replace(' ', '')
        simInfo['overrideString'] = overstring
        mname = modelName + '.log'

        status = '{:3d}:{:3d}'.format(cnt,nf)

        if simInfo['success']:
            ret = mre.loadResult( simInfo['resultFile'] )
            rname = os.path.basename( simInfo['resultFile'] ).replace('.mat', '_'+overstring+'.mat')

            if ret:
                a = mre.getData('diffVa')
                b = mre.getData('diffVb')

                agood = isinstance(a, np.ndarray)
                bgood = isinstance(b, np.ndarray)
                if agood and bgood:
                    sab = np.sum(abs(a)) + np.sum(abs(b))
                    aab = np.sum(np.abs( np.angle(mre.getData('kysan.vA')+mre.getData('kysan.vB')*1j) / np.angle(mre.getData('ain0200.y[1]')+mre.getData('ain1200.y[1]')*1j) ))

                    simInfo['sumDiffAB'] = sab
                    simInfo['sumAngleAB'] = aab
                    simInfo['resultFile'] = msw.copyFromTemp(simInfo['resultFile'], os.path.join(resultDir,rname))

                    if len(best) < nKeep+1:
                        best.append(sab)
                        simInfo['sumDiffAB'] = sab
                        simInfo['sumAngleAB'] = aab
                        simInfo['resultFile'] = msw.copyFromTemp(simInfo['resultFile'], os.path.join(resultDir,rname))
                    elif sab < best[nKeep]:
                        best.append(sab)
                        best.sort()
                        simInfo['sumDiffAB'] = sab
                        simInfo['sumAngleAB'] = aab
                        simInfo['resultFile'] = msw.copyFromTemp(simInfo['resultFile'], os.path.join(resultDir,rname))

                    print(f'{status} {sab:3.3f} {simInfo["resultFile"]}')
        else:
            print(status+'simInfo sayz not succssful, cant copy results')
            pp.pprint(simInfo)
            simInfo['logFile'] = msw.copyFromTemp( mname, os.path.join(resultDir, mname.replace('.log', '_'+overstring+'.log')) )

        sweepInfo.append(simInfo)

        cnt +=1
        if cnt%100 == 0:
            gc.collect()

    return sweepInfo

def makeParameterStartStopInc(paramName, startValue, stopValue, increment):
    return { paramName:{'start':startValue,'stop':stopValue,'increment':increment} }

def makeParameterStartStopN(paramName, startValue, stopValue, N):
    return { paramName:{'start':startValue,'stop':stopValue,'n':N } }

def makeParameterStartStopLogN(paramName, startValue, stopValue, N):
    return { paramName:{'start':startValue,'stop':stopValue,'logN':N } }

#from ModelicaSimulate import resimulate
def resimulate( modelPath, resultPath ): #given paths to the Modelica model and result, returns True if the results are out of date and need to be resimulated
    """Compares the mtimes of modelPath and resultPath to determine if the model needs to be resimulated.
    modelPath -- path to the model file (*.mo)
    resultPath -- path to the result file (*.mat), usually provided by the return from ModelicaSimulate().
    If the result path not found or result mtime < model mtime, returns true to resimulate the model.
    """
    modelPath = os.path.expanduser( modelPath )
    resultPath = os.path.expanduser( resultPath )
    # print('resimulate() given modelPath['+modelPath + '] and resultPath['+resultPath+']')

    # if os.path.exists( modelPath ) and os.path.exists( resultPath ) and 1 == len(glob.glob(resultPath+'*.mat')):
    #     print('all ok')
    #     return os.path.getmtime(resultPath) < os.path.getmtime(modelPath) #True == model is NEWER than result, results are out of date
    # else: #one of the given paths does not exist
    #     if os.path.exists( modelPath ): #if the model exists we can simulate, True
    #         print('Given resultPath['+resultPath +'] does not exist, resimulating\n')
    #         return True
    #     elif os.path.exists( resultPath ):
    #         print('Given modelPath['+modelPath+'] does not exist, can only plot\n')
    #         return False
    #     else:
    #         print('Neither modelPath['+modelPath+'] nor resultPath['+resultPath+'] exist, quitting\n')
    #         return None #None == False, sloppy

    if os.path.exists(modelPath):
        if os.path.exists( resultPath ): #resultPath may be a directory or a file
            
            if os.path.splitext( resultPath )[1] == '.mat':#resultPath is a result file
                return os.path.getmtime(resultPath) < os.path.getmtime(modelPath) #True == model is NEWER than result, results are out of date
            elif 1 == len(glob.glob(resultPath+'*.mat')): #resultPath is a directory that contains a result file
                g = glob.glob(resultPath+'*.mat')
                resultPath = g[0]
                ret = os.path.getmtime(resultPath) < os.path.getmtime(modelPath) #True == model is NEWER than result, results are out of date
                # print('mtimes',ret)
                return ret
            else:
                print('Given resultPath['+resultPath+'] does not have a result *.mat, simulating\n')
                return True
        else:
            print('Given resultPath['+resultPath+'] does not exist, simulating\n')
            return True
    else:
        print('Given modelPath['+modelPath+'] does not exist\n')
        return False



# test_MSW_loadFile()
