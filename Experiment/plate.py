import math
import globals
import logging

_Plate__allplates=[]

def interpolate(dict,x0):
    'Interpolate a dictionary of x:y values at given x0 value using linear interpolation'
    lowbound=None
    highbound=None
    for x,y in dict.iteritems():
        if x<=x0 and (lowbound is None or lowbound[0]<x):
            lowbound=(x,y)
        if x>=x0 and (highbound is None or highbound[0]>x):
            highbound=(x,y)
    if lowbound is None or highbound is None:
        return None

    if highbound[0]==lowbound[0]:
        y0=(highbound[1]+lowbound[1])/2.0
    else:
        y0=(x0-lowbound[0])/(highbound[0]-lowbound[0])*(highbound[1]-lowbound[1]) + lowbound[1]
    #print "x0=",x0,", y0=",y0,", low=",lowbound,", high=",highbound
    #print "interp(",dict,",",x0,")=",y0
    return y0


class Plate(object):
    "An object representing a microplate or other container on the deck; includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200,zmax=None,angle=None,r1=None,h1=None,v0=None,gemDepth=None,gemArea=None,gemHOffset=None,gemShape=None,vectorName=None,maxspeeds=None,glycerolmaxspeeds=None,glycerol=None,minspeeds=None,liquidTemp=22.7,slopex=0,slopey=0,backupPlate=None):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.unusableVolume=unusableVolume
        self.homegrid=grid
        self.homepos=pos
        self.homeUnusableVolume=unusableVolume
        self.nx=nx
        self.ny=ny
        self.wells=[i*ny+j for i in range(nx) for j in range(ny) ]		# List of wells, can be modified to skip particular wells
        self.pierce=pierce
        self.maxVolume=maxVolume
        self.warned=False
        self.curloc="Home"
        self.zmax=zmax
        if angle is None:
            self.angle=None
        else:
            self.angle=angle*math.pi/180
        self.r1=r1
        self.h1=h1
        self.v0=v0
        self.slopex=slopex  # Slope of plate in mm/well; +ve indicates right edge is higher than left edge
        self.slopey=slopey  # Slope of plate in mm/well; +ve indicates bottom edge is higher than top edge
        self.gemDepth=gemDepth		  # Values programmed into Gemini so we can foretell what volumes Gemini will come up with for a given height
        self.gemArea=gemArea
        self.gemShape=gemShape
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
        self.maxspeeds=maxspeeds
        self.glycerolmaxspeeds=glycerolmaxspeeds
        self.glycerol=glycerol			# Glycerol fraction for above speeds
        self.minspeeds=minspeeds
        self.liquidTemp=liquidTemp
        self.backupPlate=backupPlate	   # Backup plate to use when this one is full
        global __allplates
        __allplates.append(self)

    @classmethod
    def lookup(cls,grid,pos):
        global __allplates
        for p in __allplates:
            if p.grid==grid and p.pos==pos:
                return p
        return None

    @classmethod
    def reset(cls):
        global __allplates
        for p in __allplates:
            p.movetoloc("Home")

    def movetoloc(self,dest,newloc=None):
        self.curloc=dest
        if  dest=="Home":
            self.grid=self.homegrid
            self.pos=self.homepos
            self.unusableVolume=self.homeUnusableVolume
        else:
            assert newloc!=None
            self.grid=newloc.grid
            self.pos=newloc.pos
            self.unusableVolume=newloc.unusableVolume

    def getliquidheight(self,volume):
        'Get liquid height in mm above ZMax'
        if self.angle is None:
            if self.gemShape=='flat':
                return volume/self.gemArea
            if not self.warned:
                logging.warning("No liquid height equation for plate %s"%self.name)
                self.warned=True
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if volume>=v1:
            height=(volume-v1)/(math.pi*self.r1*self.r1)+self.h1
        elif volume+self.v0<0:
            height=h0
        else:
            height=((volume+self.v0)*(3/math.pi)*((self.h1-h0)/self.r1)**2)**(1.0/3)+h0
            #        print "%s,vol=%.1f, height=%.1f"%(self.name,volume,height)
        return height

    def getliquidarea(self,volume):
        'Get surface area of liquid in mm^2 when filled to given volume'
        if self.angle is None:
            if self.gemShape=='flat':
                return self.gemArea
            if not self.warned:
                logging.warning("No liquid height equation for plate %s"%self.name)
                self.warned=True
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if volume>=v1:
            radius=self.r1
        elif volume+self.v0<0:
            radius=0
        else:
            height=((volume+self.v0)*(3/math.pi)*((self.h1-h0)/self.r1)**2)**(1.0/3)+h0
            radius=(height-h0)/(self.h1-h0)*self.r1
        area=math.pi*radius*radius
        #print "%s,vol=%.1f, radius=%.1f, area=%.1f"%(self.name,volume,radius,area)
        return area

    def mixingratio(self,dewpoint):
        B=0.6219907  # kg/kg
        Tn=240.7263
        m=7.591386
        A=6.116441
        Pw=A*10.0**(m*dewpoint/(Tn+dewpoint))
        Ptot=1013   # Atmospheric pressure
        mr=B*Pw/(Ptot-Pw)
        return mr

    def getevaprate(self,volume,vel=0):
        'Get rate of evaporation of well in ul/min with given volume at specified self.dewpoint'
        assert volume>=0
        EVAPFUDGE=0.69		# Fudge factor -- makes computed evaporation match up with observed
        area=self.getliquidarea(volume)
        x=self.mixingratio(globals.dewpoint)
        xs=self.mixingratio(self.liquidTemp)
        #print "vol=",volume,", area=",area
        if area is None:
            return 0
        theta=25+19*vel
        evaprate=theta*area/1000/1000*(xs-x)*1e6
        #print "Air temp=%.1fC, DP=%.1fC, x=%.3f, xs=%.3f, vol=%.1f ul, area=%.0f mm^2, evaprate=%.3f ul/h"%(self.liquidTemp,self.dewpoint,x,xs,volume,area,evaprate)
        return evaprate*EVAPFUDGE

    def getliquidvolume(self,height):
        'Compute liquid volume given height above zmax in mm'
        if self.angle is None:
            if self.gemShape=='flat':
                return self.gemArea*height
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume

    def getgemliquidvolume(self,height):
        'Compute liquid volume given height above zmax in mm the way Gemini will do it'
        if height is None:
            volume=None
        elif self.gemShape=='flat':
            volume=self.gemArea*height
        elif self.gemShape=='v-shaped':
            r0=math.sqrt(self.gemArea/math.pi)
            if height<self.gemDepth:
                'conical'
                r=height/self.gemDepth*r0
                volume=1.0/3*math.pi*r*r*height
            else:
                volume=1.0/3*math.pi*r0*r0*self.gemDepth+self.gemArea*(height-self.gemDepth)
        else:
            volume=None
        return volume

    def getgemliquidheight(self,volume):
        'Compute liquid height above zmax in mm given volume the way Gemini will do it'
        if volume is None:
            height=None
        elif self.gemShape=='flat':
            height=volume/self.gemArea
        elif self.gemShape=='v-shaped':
            r0=math.sqrt(self.gemArea/math.pi)
            conevolume=1.0/3*math.pi*r0*r0*self.gemDepth
            if volume<conevolume:
                'conical'
                height=math.pow(volume*3/math.pi*(self.gemDepth/r0)**2,1.0/3)
            else:
                height=(volume-conevolume)/self.gemArea+self.gemDepth
        else:
            height=None
        return height

    def wellname(self,well):
        if well is None:
            return "None"
        col=int(well/self.ny)
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)

    def wellnumber(self,wellname):
        'Convert a wellname, such as "A3" to a well index -- inverse of wellname()'
        for i in range(self.nx*self.ny):
            if self.wellname(i)==wellname:
                return i
        logging.error("Illegal well name, %s, for plate %s"%(wellname, self.name))

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

