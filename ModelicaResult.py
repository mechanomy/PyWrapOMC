# MIT License
# Copyright (c) 2023 Mechanomy LLC
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import DyMat
import numpy as np
import re
# from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import matplotlib.cm as cmap
import pprint
pp = pprint.PrettyPrinter(indent=2)

class ModelicaResult:
    resultPath = ''
    dat = []

    def loadResult(self, resultFilePath): #loads the given results for analysis
        if os.path.exists( resultFilePath ):
            self.resultPath = os.path.expanduser(resultFilePath)
            self.dat = DyMat.DyMatFile(self.resultPath)
            return True
        else:
            print('ModelicaResult.__init__: resultFilePath does not exist, exit', resultFilePath )
            return False

    def __str__(self):
        return self.resultPath

    def printNames(self, stub=''):
        if self.dat != []:
            names = list(self.dat.names())
            names.sort()
            if stub == '':
                pp.pprint(names)
            else:
                for n in names:
                    if stub in n:
                        print(n)
        else:
            print('ModelicaResult.dat is empty')

    def findName(self, name):
        names = list(self.dat.names())
        names.sort()
        for i in np.arange(len(names)):
            if name == names[i]:
                return names[i]
        # print(f'findName: did not find [{name}] in names')
        return False

    def findPartialName(self, stub, names=[]): #names=[] searches over self.dat.names()
        if names == []:
            names = list(self.dat.names())
            names.sort()
        nm = []
        for n in names:
            if isinstance(stub, str) and isinstance(n, str) and stub in n:
                nm.append(n)
            # else:
            #     print(f'Did not find [{stub}] in n[{n}], type(stub)=[{type(stub)}], type(n)=[{type(n)}]')
        # if len(nm) < 1:
        #     print('findPartialName: did not find [{}] in names'.format(stub))
        return nm

    def findNamesWithFields(self, fields, names=[], verbose=False):
        if names == []:
            names = list(self.dat.names())
            names.sort()

        found = []
        for ifield,field in enumerate(fields):
            pnames = self.findPartialName(names=names, stub=field)
            nnew = []
            for n in pnames:
                parts = n.split('.')
                for ip,p in enumerate(parts): #B.frameTranslation.height = [B, frameTranslation, height]
                    if field in p:
                        parent =  '.'.join(parts[:ip])
                        nnew.append(parent)
                        if verbose:
                            print('a', ip, n, p, parent, parts)
            if verbose:
                print('b', nnew)

            if 0 < ifield:
                found = list( set.intersection( set(found), set(nnew) ))
            else:
                found = nnew

            if verbose:
                print('c', ifield, field, ':')
                pp.pprint(found)
        return found

    def getTime(self):
        # if isinstance(self.dat, dict) and self.dat.get('abscissa'):
        if True:
            ret = self.dat.abscissa(2,True)
            if isinstance(ret, np.ndarray):
                return ret
        print(f'{self.resultPath} has no abscissa, dat is {type(self.dat)}')
        pp.pprint(self.dat)
        return None

    def getIndexAtTime(self, t0=0):
        time = self.getTime()
        if time[0] <= t0 and t0 <= time[-1]:
            return np.argmax(t0<=time) #find index at or just beyond t0
        else:
            return False

    def getData(self, name, t0=[]):
        nm = self.findName(name)
        # print(nm)
        if nm:
            if isinstance(t0, int) or isinstance(t0, float):
                ind = self.getIndexAtTime(t0)
                if isinstance(ind, np.int64): 
                    dat = (self.dat.data(nm))
                    if ind < len(dat):
                        return float(dat[ind])
                    else:
                        return float(dat[0]) #constants only have start and end
                else:
                    return float(self.dat.data(nm))
            else:
                return (self.dat.data(nm))
        else:
            pnames = self.findPartialName(stub=name)
            if 0 < len(pnames):
                dat = {} 
                for pn in pnames:
                    dat[pn] = self.getData(pn, t0=t0)
                return dat
            else:
                return False

        # print(f'getData did not find name [{name}]')
        return False

    def getVector(self, name, t0=-1):
        namex = self.findName(name+'[1]')
        namey = self.findName(name+'[2]')
        namez = self.findName(name+'[3]')
        if not namex:
            namex = self.findName(name+',1]')
        if not namey:
            namey = self.findName(name+',2]')
        if not namez:
            namez = self.findName(name+',3]')

        if namex and namey and namez:
            time = self.getTime()
            if t0 < time[0] or time[-1] < t0:  #return a matrix in time x; y; z
                return np.array( [self.getData(namex), self.getData(namey), self.getData(namez)] )
            else: #return a vector at time t0
                return np.array( [self.getData(namex, t0), self.getData(namey,t0), self.getData(namez,t0) ] )

        print(f'getVector did not find [{name}]: xname[{namex}] yname[{namey}] zname[{namez}] in result names')
        return False

    #spatial plotting

    def plot2D_vector(self, ax, name, atName='', t0=[], axes='xy', color='k', line='-', marker='.', alpha=0.5, scale=1):
        vec = self.getVector( name, t0=t0 )*scale
        vat = self.getVector( atName, t0=t0 )
        if isinstance(vec,(np.ndarray)) and isinstance(vat,(np.ndarray)):
            if vec.ndim == 1: #plot at instant
                x = np.array([vat[0],vat[0]+vec[0]])
                y = np.array([vat[1],vat[1]+vec[1]])
                ax.plot(x, y, label=f'{name}@{atName}', c=color, ls=line, marker=marker, alpha=alpha)
        else:
            print('not yet')

    def plot2DInstant_frame(self, ax, frameName, t0, xyxzyz, color='k', line='-', marker='.'):
        if not ax:
            plt.figure()
            ax = plt.gca()
        names = list(self.dat.names())
        names.sort()

        xname = ''
        yname = ''
        zname = ''

        #find the frame names
        if frameName+'.r_0[1]' in names:
            xname = frameName+'.r_0[1]'
        if frameName+'.r_0[2]' in names:
            yname = frameName+'.r_0[2]'
        if frameName+'.r_0[3]' in names:
            zname = frameName+'.r_0[3]'

        if frameName+'frame_a.r_0[1]' in names:
            xname = frameName+'frame_a.r_0[1]'
        if frameName+'frame_a.r_0[2]' in names:
            yname = frameName+'frame_a.r_0[2]'
        if frameName+'frame_a.r_0[3]' in names:
            zname = frameName+'frame_a.r_0[3]'

        if frameName+'frame_b.r_0[1]' in names:
            xname = frameName+'frame_b.r_0[1]'
        if frameName+'frame_b.r_0[2]' in names:
            yname = frameName+'frame_b.r_0[2]'
        if frameName+'frame_b.r_0[3]' in names:
            zname = frameName+'frame_b.r_0[3]'

        #find the other frame names
        if frameName in names and 'r_0[1]' in frameName:
            xname = frameName
            yname = frameName.replace('r_0[1]','r_0[2]')
            zname = frameName.replace('r_0[1]','r_0[3]')
        if frameName in names and 'r_0[2]' in frameName:
            yname = frameName
            zname = frameName.replace('r_0[2]','r_0[3]')
            xname = frameName.replace('r_0[2]','r_0[1]')
        if frameName in names and 'r_0[3]' in frameName:
            zname = frameName
            xname = frameName.replace('r_0[3]','r_0[1]')
            yname = frameName.replace('r_0[3]','r_0[2]')

        #plot
        if xname and yname and zname:
            ind = self.getIndexAtTime( t0 )
            x = self.dat.data(xname)[ind]
            y = self.dat.data(yname)[ind]
            if   xyxzyz[0] == 'x':
                x = self.dat.data(xname)[ind]
            elif xyxzyz[0] == 'y':
                x = self.dat.data(yname)[ind]
            else: #xyxzyz[0] == 'z':
                x = self.dat.data(zname)[ind]
            if   xyxzyz[1] == 'x':
                y = self.dat.data(xname)[ind]
            elif xyxzyz[1] == 'y':
                y = self.dat.data(yname)[ind]
            else: #xyxzyz[1] == 'z':
                y = self.dat.data(zname)[ind]

            if np.max(x) < 1000 and np.max(y)<1000:
                ax.plot(x, y, label=frameName, c=color, ls=line, marker=marker)
                # ax.xlabel = 'x'
                # ax.xlabel = 'y'
            else:
                print('max too big for ' +frameName)
            return ax
        else:
            print('didnt find ['+frameName+']: xname',xname,' yname', yname,' zname', zname, ' in result names')
            return ax

    def plot2D_frame(self, ax, frameName, xyxzyz, color='k', line='-', marker='.'):
        if not ax:
            plt.figure()
            ax = plt.gca()
        names = list(self.dat.names())
        names.sort()

        xname = ''
        yname = ''
        zname = ''

        if frameName+'.r_0[1]' in names:
            xname = frameName+'.r_0[1]'
        if frameName+'.r_0[2]' in names:
            yname = frameName+'.r_0[2]'
        if frameName+'.r_0[3]' in names:
            zname = frameName+'.r_0[3]'

        if frameName+'frame_a.r_0[1]' in names:
            xname = frameName+'frame_a.r_0[1]'
        if frameName+'frame_a.r_0[2]' in names:
            yname = frameName+'frame_a.r_0[2]'
        if frameName+'frame_a.r_0[3]' in names:
            zname = frameName+'frame_a.r_0[3]'

        if frameName in names and 'r_0[1]' in frameName:
            xname = frameName
            yname = frameName.replace('r_0[1]','r_0[2]')
            zname = frameName.replace('r_0[1]','r_0[3]')
        if frameName in names and 'r_0[2]' in frameName:
            yname = frameName
            zname = frameName.replace('r_0[2]','r_0[3]')
            xname = frameName.replace('r_0[2]','r_0[1]')
        if frameName in names and 'r_0[3]' in frameName:
            zname = frameName
            xname = frameName.replace('r_0[3]','r_0[1]')
            yname = frameName.replace('r_0[3]','r_0[2]')

        if xname and yname and zname:
            x = self.dat.data(xname)
            y = self.dat.data(yname)
            if xyxzyz == 'xz':
                x = self.dat.data(xname)
                y = self.dat.data(zname)
            elif xyxzyz == 'yz':
                x = self.dat.data(yname)
                y = self.dat.data(zname)

            if np.max(x) < 1000 and np.max(y)<1000:
                ax.plot(x, y, label=frameName, c=color, ls=line, marker=marker)
                # ax.xlabel = 'x'
                # ax.xlabel = 'y'
            else:
                print('max too big for ' +frameName)
            return ax
        else:
            print('didnt find ['+frameName+']: xname',xname,' yname', yname,' zname', zname, ' in result names')
            return ax

    def plotXY_frame(self, ax, frameName, color='k', line='-', marker='.'):
        return self.plot2D_frame(ax, frameName, 'xy', color, line, marker)
    def plotXZ_frame(self, ax, frameName, color='k', line='-', marker='.'):
        return self.plot2D_frame(ax, frameName, 'xz', color, line, marker)
    def plotYZ_frame(self, ax, frameName, color='k', line='-', marker='.'):
        return self.plot2D_frame(ax, frameName, 'yz', color, line, marker)
    def plotXYZ_frame(self, ax, frameName, color='k', line='-', marker='.'):
        if not ax:
            plt.figure()
            ax = plt.axes(projection='3d')
        x = self.dat.data(frameName+'.r_0[1]')
        y = self.dat.data(frameName+'.r_0[2]')
        z = self.dat.data(frameName+'.r_0[3]')
        ax.plot3D(x, y, z, label=frameName, c=color, ls=line, marker=marker)
        return ax
    def plotAllFramesSpatial(self, xyxzyz = 'xy', ax=[]): #plots any entity with a moving frame
        if not ax:
            plt.figure()
            ax = plt.gca()

        print(self.dat)
        names = list(self.dat.names())
        names.sort()

        hasFrame = []
        for n in names:
            if 'der(' in n: #skip derivative plotting
                n = ''
            if 'frame_a.r_0[1]' in n:
                hasFrame.append(n)
            # if 'frame_b.r_0' in n: #skip ys, implied by x
            #     hasFrame.append(n)

        # pprint(hasFrame)

        # cmap = plt.get_cmap('hsv')
        cmap = plt.get_cmap('prism')
        # for f in hasFrame:
        for indf,f in enumerate(hasFrame):
            # self.plotXY_frame( ax, f, cmap(indf/len(hasFrame)), '', '.' )
            if xyxzyz == 'xz':
                self.plotXZ_frame( ax, f, cmap(indf/len(hasFrame)), '', '.' )
            elif xyxzyz == 'yz':
                self.plotYZ_frame( ax, f, cmap(indf/len(hasFrame)), '', '.' )
            else:
                self.plotXY_frame( ax, f, cmap(indf/len(hasFrame)), '', '.' )

        ax.legend(bbox_to_anchor=(1.01,1))
        ax.grid(True)
        ax.set_aspect('equal')
        ax.set_title('plotAllFrameMovements')

        plt.show()
        return ax

    def plotKnownFrames(self, xyxzyz='xy', ax=[]):
        if not ax:
            plt.figure()
            ax = plt.gca()

        self.plot_bodyBox(ax)
        
        return ax

    def plot_bodyBox(self, ax):
        names = list(self.dat.names())
        names.sort()

        # #build tree:
        # tree = []
        # for n in self.dat.names:
        #     parts = n.split('.') #variable names separated by .: revA.frame_a.t[1]
           
        
            
        #bodyBox has variables:
        uvars = ['height','innerHeight', 'width','innerWidth', 'density'] 

    def findBodyBox(self):
        names = list(self.dat.names())
        names.sort()

        a = self.findPartialName('height')
        b = self.findPartialName('innerHeight')
        c = self.findPartialName('width')
        d = self.findPartialName('innerWidth')
        e = self.findPartialName('density')
        #now, above follow some higher component, so split each and intersect, knowing that the precedent is the component name
        
        componentNames = []
        for an in a:
            b = an.split('.')
            for ib in enumerate(b):
                if b[ib] == 'height':
                    componentNames.append(b[ib-1])
        pp.pprint(componentNames)
                    

            

        
        # for n in names:
        #     p = n.splt('.')
        #     if

    #temporal plotting
    def plotTimeVar(self, ax, varName, color='', line='-', linewidth=1, marker='', label=''):
        name = self.findName(varName)

        if name:
            time = self.getTime()
            y = self.dat.data(name)
            if len(y) < len(time):
                y = time*0+y[0]
            # print('plotTimeVar found name with length [{}], plotting'.format(len(y)))
            # print(y)

            if not ax:
                plt.figure()
                ax = plt.gca()
            if color == '':
                cmap = plt.get_cmap('hsv')
                color = cmap( np.random.rand() )
            if label == '':
                label = name

            ax.plot(time, y, c=color, ls=line, linewidth=linewidth, marker=marker, label=label)

        else:
            print('plotTimeVar did not find varName[{}]'.format(varName))
        return ax

    def plotTimeStep(self, time, ax=[], c='b'):
        ind = np.where( time<=self.dat.abscissa(2,True) )[0][0] #where() returns a 2D array..
        # print(time, ind)

        if not ax:
            plt.figure()
            ax = plt.gca()

        ax.set_title('Plotting at t='+ str(time))
        x = np.array([ self.dat.data('lowerHandleBody.frame_a.r_0[1]')[ind], \
                    self.dat.data('lowerHandleBody.frame_b.r_0[1]')[ind], \
                    self.dat.data('slideBarBody.frame_b.r_0[1]')[ind],    \
                    self.dat.data('upperHandleBody.frame_b.r_0[1]')[ind], \
                    self.dat.data('upperJawBody.frame_b.r_0[1]')[ind],    \
                    self.dat.data('lowerHandleBody.frame_a.r_0[1]')[ind]  ])
        y = np.array([ self.dat.data('lowerHandleBody.frame_a.r_0[2]')[ind], \
                    self.dat.data('lowerHandleBody.frame_b.r_0[2]')[ind], \
                    self.dat.data('slideBarBody.frame_b.r_0[2]')[ind],    \
                    self.dat.data('upperHandleBody.frame_b.r_0[2]')[ind], \
                    self.dat.data('upperJawBody.frame_b.r_0[2]')[ind],    \
                    self.dat.data('lowerHandleBody.frame_a.r_0[2]')[ind]  ])
        ax.plot(x,y, marker='.')
    def plotAllFramesTime(self, varName, ax=[]):
        if not ax:
            plt.figure()
            ax = plt.gca()

        cmap = plt.get_cmap('hsv')
        time = self.dat.abscissa(2,True)


        ax.grid(True)
        ax.set_aspect('equal')
        return ax

def gatherResultNames( dirname, fileRegex='.*mat\Z' ):
    allfiles = os.listdir(dirname)
    dats = []
    for f in allfiles:
        mat = re.match(fileRegex, f)
        if mat:
            dats.append(os.path.join(dirname,f) )
    print('gathered {} results'.format(len(dats)))
    return dats

def getCmap( i, n, alpha=0.5):
    cm = cmap.get_cmap('jet') #cm( [0-1] )
    (r,g,b,a) = cm(i/n)
    return (r,g,b, alpha )

def iNext(i, n):
    if n < i+1:
        return 1
    else:
        return i+1
def iLast(i, n):
    if i-1 < 1:
        return n
    else:
        return i-1