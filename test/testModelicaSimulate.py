# MIT License
# Copyright (c) 2023 Mechanomy LLC
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import sys
sys.path.append('.')

from ModelicaSimulate import ModelicaSimulate
from ModelicaSimulate import resimulate
from ModelicaResult import ModelicaResult

# nb: paths are relative to the terminal, not to this file
modelPath = './test/dampedPendulum/dampedPendulum.mo' 
modelName = 'dampedPendulum'
resultPath = './test/dampedPendulum/dampedPendulum_res.mat' 

ms = {}
if resimulate(modelPath, resultPath):
    ms = ModelicaSimulate(modelPath=modelPath, modelName=modelName, resultPath=resultPath )
else:
    print('Using existing file at ${0}'.format(resultPath))
    ms = {'resultFile':resultPath}

# print('ms = ',ms)
 
if ms['success']:
    mr = ModelicaResult()
    mr.loadResult(resultPath)
    mr.plotAllFramesSpatial()

