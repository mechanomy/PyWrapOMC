# MIT License
# Copyright (c) 2023 Mechanomy LLC
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# -*- coding: utf-8 -*-

import DyMat
import numpy as np
import re
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
from pprint import pprint

fname = 'temp/ViseGrip_res.mat'
dat = DyMat.DyMatFile(fname)
# print(dat.abscissa(1,True)) #time axis...

def findName(str):
    names = list(dat.names())
    names.sort()
    for i in np.arange(len(names)):
        # if str == names[i]:
        if str in names[i]:
            return names[i]
    print('Did not find [{}] in names'.format(str))
    return -1

def plotXY_frame(ax, frameName, color='k', line='none', marker='none'):
    if not ax:
        plt.figure()
        ax = plt.gca()
    names = list(dat.names())
    names.sort()

    xname = ''
    yname = ''

    if frameName+'.r_0[1]' in names:
        xname = frameName+'.r_0[1]'
    if frameName+'.r_0[2]' in names:
        yname = frameName+'.r_0[2]'

    if frameName+'frame_a.r_0[1]' in names:
        xname = frameName+'frame_a.r_0[1]'
    if frameName+'frame_a.r_0[2]' in names:
        yname = frameName+'frame_a.r_0[2]'

    if frameName in names and 'r_0[1]' in frameName:
        xname = frameName
        yname = frameName.replace('r_0[1]','r_0[2]')
    if frameName in names and 'r_0[2]' in frameName:
        yname = frameName
        xname = frameName.replace('r_0[2]','r_0[1]')

    if xname and yname:
        x = dat.data(xname)
        y = dat.data(yname)

        if np.max(x) < 1000 and np.max(y)<1000:
            ax.plot(x, y, label=frameName, c=color, ls=line, marker=marker)
        else:
            print('max too big for ' +frameName)
        return ax
    # else:
        # print('didnt find ['+frameName+']: xname',xname,' yname', yname)


def plotXYZ_frame(ax, frameName, color='k', line='none', marker='none'):
    if not ax:
        plt.figure()
        ax = plt.axes(projection='3d')
    x = dat.data(frameName+'.r_0[1]')
    y = dat.data(frameName+'.r_0[2]')
    z = dat.data(frameName+'.r_0[3]')
    ax.plot3D(x, y, z, label=frameName, c=color, ls=line, marker=marker)
    return ax

def plotAll(ax=[]):
    if not ax:
        plt.figure()
        ax = plt.gca()
    plotXY_frame(ax, 'lowerHandleBody.frame_a', 'k', 'none', '.')
    plotXY_frame(ax, 'lowerHandleBody.frame_b', 'k', 'none', '.')
    plotXY_frame(ax, 'slideBarBody.frame_b', 'b', 'none', '.')
    plotXY_frame(ax, 'upperHandleBody.frame_b', 'g', 'none', '.')
    plotXY_frame(ax, 'upperHandleBody.frame_b', 'g', 'none', '.')
    plotXY_frame(ax, 'upperJawBody.frame_b', 'r', 'none', '.')
    plotXY_frame(ax, 'upperJawBody.frame_b', 'r', 'none', '.')

    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal')
    ax.set_title('Plotting allTime')
    return ax


def plotTimeStep(time, ax=[], c='b'):
    ind = np.where( time<=dat.abscissa(2,True) )[0][0] #where() returns a 2D array..
    # print(time, ind)

    if not ax:
        plt.figure()
        ax = plt.gca()

    ax.set_title('Plotting at t='+ str(time))
    x = np.array([ dat.data('lowerHandleBody.frame_a.r_0[1]')[ind], \
                   dat.data('lowerHandleBody.frame_b.r_0[1]')[ind], \
                   dat.data('slideBarBody.frame_b.r_0[1]')[ind],    \
                   dat.data('upperHandleBody.frame_b.r_0[1]')[ind], \
                   dat.data('upperJawBody.frame_b.r_0[1]')[ind],    \
                   dat.data('lowerHandleBody.frame_a.r_0[1]')[ind]  ])
    y = np.array([ dat.data('lowerHandleBody.frame_a.r_0[2]')[ind], \
                   dat.data('lowerHandleBody.frame_b.r_0[2]')[ind], \
                   dat.data('slideBarBody.frame_b.r_0[2]')[ind],    \
                   dat.data('upperHandleBody.frame_b.r_0[2]')[ind], \
                   dat.data('upperJawBody.frame_b.r_0[2]')[ind],    \
                   dat.data('lowerHandleBody.frame_a.r_0[2]')[ind]  ])
    ax.plot(x,y, marker='.')

def plotMovement(ax):
    if not ax:
        plt.figure()
        ax = plt.gca()
    cmap = plt.get_cmap('hsv')
    # plotTimeStep(0.1, ax, c=cmap(0.1))
    # plotTimeStep(1, ax, c=cmap(0.2))
    # plotTimeStep(2, ax, c=cmap(0.3))
    # plotTimeStep(3, ax, c=cmap(0.4))
    # plotTimeStep(3.8, ax, c=cmap(0.9))

    time = dat.abscissa(2,True)
    # for t in np.linspace(0,0.05, 10):
    # for t in time:
    for t in np.linspace(0,time[-1], 100):
        plotTimeStep(t, ax, c=cmap(t/time[-1]))
    ax.grid(True)
    ax.set_aspect('equal')
    return ax

def plotAllFrameMovements(ax=[]): #plots any entity with a moving frame
    if not ax:
        plt.figure()
        ax = plt.gca()

    names = list(dat.names())
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
        plotXY_frame( ax, f, cmap(indf/len(hasFrame)), '', '.' )

    ax.legend(bbox_to_anchor=(1.01,1))
    ax.grid(True)
    ax.set_aspect('equal')
    ax.set_title('Plotting AllFrameMovements')

    return ax

# print( dat.data('world.frame_a.r_0[1]'), dat.data('world.frame_a.r_0[1]'), dat.data('world.frame_a.r_0[1]'))
# print( dat.data('world.frame_b.r_0[1]'), dat.data('world.frame_b.r_0[1]'), dat.data('world.frame_b.r_0[1]'))



# ax = plotXY_frame([], 'slideBarBody', 'b', 'none', '.')
# plotXY_frame(ax, 'slideBarBody.frame_a', 'g', 'none', '.')
# plotXY_frame(ax, 'slideBarBody.frame_b', 'r', 'none', '.')
# plotXYZ_frame([], 'slideBarBody', 'b', 'none', '.')

# ax = plotAll()
# plotMovement(ax)
plotAllFrameMovements()
plt.show()

