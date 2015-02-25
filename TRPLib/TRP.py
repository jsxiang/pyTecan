from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import os
import sys

maxVolumePerWell=150

class Reagents:
    MT7=Sample("MT7",Experiment.REAGENTPLATE,None,2.5)
    MPosRT=Sample("MPosRT",Experiment.REAGENTPLATE,None,2)
    MNegRT=Sample("MNegRT",Experiment.REAGENTPLATE,None,2)
    MLigAT7=Sample("MLigAT7",Experiment.REAGENTPLATE,None,3)
    MLigBT7W=Sample("MLigBT7W",Experiment.REAGENTPLATE,None,3)
    MLigase=Sample("MLigase",Experiment.REAGENTPLATE,None,3)

    Theo=Sample("Theo",Experiment.REAGENTPLATE,None,Concentration(25,7.5,'mM'))
    #EDTA=Sample("EDTA",Experiment.REAGENTPLATE,None,Concentration(50.0,4,'mM'))
    #BT43=Sample("BT43",Experiment.REAGENTPLATE,None,Concentration(10,0.5,'uM'))
    #EVA=Sample("EvaGreen",Experiment.REAGENTPLATE,None,2)
    #BT47=Sample("BT047",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT29=Sample("BT029",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT30=Sample("BT030",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    MStopX=Sample("MStpX",Experiment.REAGENTPLATE,None,2)
    MQRef=Sample("MQREF",Experiment.REAGENTPLATE,None,10.0/6)
    MQAX=Sample("MQAX",Experiment.REAGENTPLATE,None,10.0/6)
    MQBX=Sample("MQBX",Experiment.REAGENTPLATE,None,10.0/6)
    PCRAX=Sample("MPCRAX",Experiment.REAGENTPLATE,None,4.0/3)
    PCRBX=Sample("MPCRBX",Experiment.REAGENTPLATE,None,4.0/3)
    MQMX=Sample("MQMX",Experiment.REAGENTPLATE,None,10.0/6)
    MQWX=Sample("MQWX",Experiment.REAGENTPLATE,None,10.0/6)
    SSD=Sample("SSD",Experiment.REAGENTPLATE,None,10.0)
    MLigAT7W=Sample("MLigAT7W",Experiment.REAGENTPLATE,None,3)
#    MLIGBOTH=Sample("MLigBoth",Experiment.REAGENTPLATE,None,3.0)
    DuplexBuffer=Sample("DuplexBuffer",Experiment.REAGENTPLATE,None,None)
    all=[MT7,MPosRT,MNegRT,MLigAT7,MLigBT7W,MLigase,Theo,MStopX,MQRef,MQAX,MQBX,PCRAX,PCRBX,MQMX,SSD,MLigAT7W,MQWX,DuplexBuffer]
    UNUSED=Sample("Leaky",Experiment.SAMPLEPLATE,None,0)
    
def listify(x):
    'Convert a list of (lists or scalars) into a list of equal length lists'
    n=1
    for i in x:
        if isinstance(i,list):
            n=max(n,len(i))
    result=[]
    for i in x:
        if isinstance(i,list):
            assert(len(i)==n or len(i)==0)
            result.append(i)
        else:
            result.append([i for j in range(n)])
    return result

# Make sure all target names are uniques
def uniqueTargets(tgts):
    for i in range(len(tgts)):
        if tgts[i] in tgts[:i]:
            for k in range(100):
                nm="%s.%d"%(tgts[i],k+2)
                if nm not in tgts:
                    tgts[i]=nm
                    break
    return tgts

def findsamps(x,createIfMissing=True,plate=Experiment.SAMPLEPLATE):
    'Find or create samples for given sample names'
    s=[]
    for i in x:
        t=Sample.lookup(i)
        if t==None:
            if createIfMissing:
                t=Sample(i,plate)
            else:
                print "Unable to locate sample '%s'"%i
                assert(False)
        s.append(t)
    return s

def adjustSrcDil(src,srcdil):
    'Adjust source concentration to give desired dilution'
    for i in range(len(src)):
        if src[i].conc==None:
            #            src[i].conc=Concentration(srcdil[i],1)
            pass
        else:
            src[i].conc.final=src[i].conc.stock*1.0/srcdil[i]

class TRP(object):
           
    def __init__(self):
        'Create a new TRP run'
        self.e=Experiment()
        self.r=Reagents()
        self.e.setreagenttemp(6.0)
        self.e.sanitize(3,50)    # Heavy sanitize
            
    def addTemplates(self,names,stockconc,finalconc=1.0,units="nM",plate=Experiment.REAGENTPLATE):
        for s in names:
            Sample(s,plate,None,Concentration(stockconc,finalconc,units))

    def finish(self):
        self.e.lihahome()
        self.e.w.userprompt("Process complete. Continue to turn off reagent cooler")
        self.e.setreagenttemp(None)

        #Sample.printallsamples("At completion")
        hasError=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc!=None and not s.hasBeads:
                print "ERROR: Insufficient volume for ", s," need at least ",1.0-s.volume," ul additional"
                hasError=True
            elif s.volume<2.5 and s.conc!=None:
                print "WARNING: Low final volume for ", s
            elif s.volume>s.plate.maxVolume:
                print "ERROR: Excess final volume  (",s.volume,") for ",s,", maximum is ",s.plate.maxVolume
                hasError=True
            elif s.initvolume>s.plate.maxVolume:
                print "ERROR: Excess initial volume (",s.initvolume,") for ",s,", maximum is ",s.plate.maxVolume
                hasError=True
                
        if hasError:
            print "NO OUTPUT DUE TO ERRORS"
            assert(False)
            
        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt")
        Sample.savematlab(scriptname+".m")
        
    def saveSamps(self,src,vol,dil,tgt=None,dilutant=None,plate=None):
        if tgt==None:
            tgt=[]
        [src,vol,dil]=listify([src,vol,dil])
        if len(tgt)==0:
            tgt=["%s.D%.0f"%(src[i],dil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if plate==None:
            plate=self.e.REAGENTPLATE
            
        stgt=findsamps(tgt,True,plate)
        ssrc=findsamps(src,False)

        origdil=[x.conc.stock/x.conc.final for x in ssrc]
        # print "About to dilute ",str(ssrc[0])," by ",dil[0]," using ",vol[0]," ul, origdil=",origdil[0]
        adjustSrcDil(ssrc,dil)
        if dilutant!=None:
            if dilutant.conc==None:
                self.e.stage('SAVE',[],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))],dilutant=dilutant)
            else:
                self.e.stage('SAVE',[dilutant],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))])
        else:
            self.e.stage('SAVE',[],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))])
        # Back out the dilution
        adjustSrcDil(ssrc,origdil)
        return tgt
            
    def runT7Setup(self,theo,src,vol,srcdil,tgt):
        [theo,src,tgt,srcdil]=listify([theo,src,tgt,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if theo[i]:
                    tgt.append("%s.T+"%src[i])
                else:
                    tgt.append("%s.T-"%src[i])

        tgt=uniqueTargets(tgt)

        # Convert sample names to actual samples
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        self.e.w.comment("runT7: source=%s"%[str(s) for s in ssrc])

        MT7vol=vol*1.0/self.r.MT7.conc.dilutionneeded()
        sourcevols=[vol*1.0/s.conc.dilutionneeded() for s in ssrc]
        theovols=[(vol*1.0/self.r.Theo.conc.dilutionneeded() if t else 0) for t in theo]
        watervols=[vol-theovols[i]-sourcevols[i]-MT7vol for i in range(len(ssrc))]

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols,self.e.WATER,stgt,(False,False))
        self.e.multitransfer([MT7vol for s in stgt],self.r.MT7,stgt,(False,False))
        self.e.multitransfer([tv for tv in theovols if tv>0.01],self.r.Theo,[stgt[i] for i in range(len(theovols)) if theovols[i]>0],(False,False),ignoreContents=True)
        for i in range(len(ssrc)):
            self.e.transfer(sourcevols[i],ssrc[i],stgt[i],(True,True))
        return tgt
    
    def runT7Pgm(self,vol,dur):
        pgm="TRP37-%d"%dur
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
        self.e.runpgm(pgm,dur, False,vol)

    def runT7Stop(self,theo,vol,tgt,stopmaster=None):
        [theo,tgt,stopmaster]=listify([theo,tgt,stopmaster])
        if stopmaster==None:
            stopmaster=["MStpS_NT" if t==0 else "MStpS_WT" for t in theo]
            
        stgt=findsamps(tgt)
        ## Stop
        self.e.dilute(stgt,2)

        sstopmaster=findsamps(stopmaster,False)
        for i in range(len(stgt)):
            self.e.transfer(vol,sstopmaster[i],stgt[i],(False,True))

        return tgt
    
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15,stopmaster=None):
        if tgt==None:
            tgt=[]
        [theo,src,tgt,srcdil,stopmaster]=listify([theo,src,tgt,srcdil,stopmaster])
        tgt=self.runT7Setup(theo,src,vol,srcdil,tgt)
        self.runT7Pgm(vol,dur)
        tgt=self.runT7Stop(theo,vol,tgt,stopmaster)
        return tgt

    def runBeadCleanup(self,src,tgt=None,beadFactor=1.0,beads="Streptavidin+BT1200",wash="DuplexBuffer",elutant="DuplexBuffer",elutionVol=30,washVol=50,incTime=60,sepTime=60,washTime=60,numWashes=2,eluteTime=60,leaveOn=True,keepWash=False):
        if leaveOn:
            if tgt!=None:
                print "runBeadCleanup: specified a target, but also leaveOn is True"
                assert(0)
            tgt=src

        if tgt==None:
            tgt=[]

        [src,tgt,elutionVol,beadFactor,elutant,wash,beadlist]=listify([src,tgt,elutionVol,beadFactor,elutant,wash,beads])
        if len(tgt)==0:
            for i in range(len(src)):
                tgt.append("%s.BC"%src[i])

        if keepWash:
            washTgt=[]
            for i in range(len(src)):
                washTgt.append("%s.Wash"%src[i])
            sWashTgt=findsamps(washTgt)
            
        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        for s in ssrc:
            if s.plate!=self.e.SAMPLEPLATE:
                print "runBeadCleanup: src ",s," is not in sample plate."
                assert(0)
            
        if beads!=None:
            sbeads=findsamps(beadlist,False)

        # Change the liquid class for the source tube to prevent side-touching
        for s in ssrc:
            s.setHasBeads()	# Mark the source tubes as having beads to change condition, liquid classes

        origIngredients=[s.ingredients for s in ssrc]
        origVolumes=[s.volume for s in ssrc]
        origConcs=[s.conc for s in ssrc]
        if beads!=None:
            # Transfer the beads
            for i in range(len(ssrc)):
                sbeads[i].isMixed=False	# Force a mix
                ssrc[i].dilute(beadFactor[i]+1)
                self.e.transfer(ssrc[i].volume*beadFactor[i],sbeads[i],ssrc[i],(True,True))	# Mix beads before and after

            self.e.pause(incTime)		# Wait for binding

        residualVolume=10 		# Amount to leave behind during removal of supernatant (and subsequent replacements)
            
        if any([s.volume>residualVolume]):
            # Separate and remove supernatant
            self.e.magmove(True)	# Move to magnet
            self.e.pause(sepTime)	# Wait for separation

            # Remove the supernatant
            for i in range(len(ssrc)):
                if ssrc[i].volume > residualVolume:
                    if keepWash:
                        self.e.transfer(ssrc[i].volume-residualVolume,ssrc[i],sWashTgt[i])	# Keep supernatants
                        sWashTgt[i].conc=None	# Allow it to be reused
                    else:
                        self.e.dispose(ssrc[i].volume-residualVolume,ssrc[i])	# Discard supernatant
                
            # Wash
            swash=findsamps(wash,False)
            for washnum in range(numWashes):
                self.e.magmove(False)	# Take off magnet
                for i in range(len(ssrc)):
                    self.e.transfer(washVol-ssrc[i].volume,swash[i],ssrc[i],mix=(False,True))	# Add wash

                self.e.pause(washTime)
                self.e.magmove(True)	# Back to magnet
                self.e.pause(sepTime)

                for i in range(len(ssrc)):
                    if keepWash:
                        self.e.transfer(ssrc[i].volume-residualVolume,ssrc[i],sWashTgt[i])	# Remove wash
                        sWashTgt[i].conc=None	# Allow it to be reused
                    else:
                        self.e.dispose(ssrc[i].volume-residualVolume,ssrc[i])	# Remove wash

            # Should only be residualVolume left with beads now
        
            # Remove from magnet
            self.e.magmove(False)

        # Added elutant
        selutant=findsamps(elutant,False)
        for i in range(len(ssrc)):
            if elutionVol[i]<30:
                print "Warning: elution from beads with %.1f ul < minimum of 30ul"%elutionVol[i]
            self.e.transfer(elutionVol[i]-ssrc[i].volume,selutant[i],ssrc[i],(False,True))	# Add elution buffer and mix

        # Go through some cycles of waiting, mixing
        nEluteCycles=2
        for i in range(nEluteCycles):
            self.e.pause(eluteTime/nEluteCycles)

            # Mix some more
            for s in ssrc:
                self.e.mix(s,nmix=4)

        # Restore the ingredients list
        for i in range(len(ssrc)):
            ssrc[i].ingredients={}
            for k in origIngredients[i]:
                ssrc[i].ingredients[k]=origIngredients[i][k]*ssrc[i].volume/origVolumes[i]
            ssrc[i].conc=origConcs[i]
            ssrc[i].dilute(ssrc[i].volume/origVolumes[i])
            
        if not leaveOn:
            self.e.magmove(True)	# Move back to magnet
            self.e.pause(sepTime)	# Wait for separation

            for i in range(len(ssrc)):
                self.e.transfer(elutionVol[i]-residualVolume,ssrc[i],stgt[i])	# Transfer elution to new tube

            self.e.magmove(False)

        return tgt

    def runRT(self,pos,src,vol,srcdil,tgt=None):
        if tgt==None:
            tgt=[]
        [pos,src,tgt,vol,srcdil]=listify([pos,src,tgt,vol,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if pos[i]:
                    tgt.append("%s.RT+"%src[i])
                else:
                    tgt.append("%s.RT-"%src[i])

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)

        #    e.stage('MPosRT',[self.r.MOSBuffer,self.r.MOS],[],[self.r.MPosRT],ASPIRATEFACTOR*(self.vol.RT*nRT/2)/2+self.vol.Extra+MULTIEXCESS,2)
        #    e.stage('MNegRT',[self.r.MOSBuffer],[],[self.r.MNegRT],ASPIRATEFACTOR*(self.vol.RT*negRT)/2+self.vol.Extra+MULTIEXCESS,2)
        if any(p for p in pos):
            self.e.stage('RTPos',[self.r.MPosRT],[ssrc[i] for i in range(len(ssrc)) if pos[i]],[stgt[i] for i in range(len(stgt)) if pos[i]],[vol[i] for i in range(len(vol)) if pos[i]])
        if any(not p for p in pos):
            self.e.stage('RTNeg',[self.r.MNegRT],[ssrc[i] for i in range(len(ssrc)) if not pos[i]],[stgt[i] for i in range(len(stgt)) if not pos[i]],[vol[i] for i in range(len(vol)) if not pos[i]])
        dur=20
        pgm="TRP37-%d"%dur
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
        self.e.runpgm("TRP37-%d"%dur,dur,False,max(vol))
        return tgt
 
    def runLig(self,prefix=None,src=None,vol=None,srcdil=None,tgt=None,master=None,anneal=True,ligtemp=25):
        if tgt==None:
            tgt=[]
        if master==None:
            master=["MLigAN7" if p=='A' else "MLigBN7" for p in prefix]

        #Extension
        # e.g: trp.runLig(prefix=["B","B","B","B","B","B","B","B"],src=["1.RT-","1.RT+","1.RTNeg-","1.RTNeg+","2.RT-","2.RT-","2.RTNeg+","2.RTNeg+"],tgt=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=[10,10,10,10,10,10,10,10],srcdil=[2,2,2,2,2,2,2,2])
        [src,tgt,vol,srcdil,master]=listify([src,tgt,vol,srcdil,master])
        if len(tgt)==0:
            tgt=["%s.%s"%(src[i],master[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        smaster=findsamps(master,False)

        # Need to check since an unused ligation master mix will not have a concentration
        minsrcdil=1/(1-1/smaster[0].conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
        for i in srcdil:
            if i<minsrcdil:
                print "runLig: srcdil=%.2f, but must be at least %.2f"%(i,minsrcdil)
                assert(False)

        adjustSrcDil(ssrc,srcdil)

        i=0
        while i<len(stgt):
            lasti=i+1
            while lasti<len(stgt) and smaster[i]==smaster[lasti]:
                lasti=lasti+1
            self.e.stage('LigAnneal',[smaster[i]],ssrc[i:lasti],stgt[i:lasti],[vol[j]/1.5 for j in range(i,lasti)],1.5)
            i=lasti
            
        if anneal:
            self.e.runpgm("TRPANN",5,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        self.e.stage('Ligation',[self.r.MLigase],[],stgt,vol)
        if ligtemp==25:
            pgm="LIG15RT"
        else:
            pgm="LIG15-%.0f"%ligtemp
            self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@%.0f,900 TEMP@65,600 TEMP@25,30'%(pgm,ligtemp))
        
        self.e.runpgm(pgm,27,False,max(vol),hotlidmode="TRACKING",hotlidtemp=10)
        return tgt
 
    def runPCR(self,prefix,src,vol,srcdil,tgt=None,ncycles=20,suffix='S'):
        if tgt==None:
            tgt=[]
        ## PCR
        # e.g. trp.runPCR(prefix=["A"],src=["1.RT+"],tgt=["1.PCR"],vol=[50],srcdil=[5])
        [prefix,src,tgt,vol,srcdil,suffix]=listify([prefix,src,tgt,vol,srcdil,suffix])
        if len(tgt)==0:
            tgt=["%s.P%c%c"%(src[i],prefix[i],suffix[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        #print "stgt[0]=",str(stgt[0])
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        
        primer=[prefix[i]+suffix[i] for i in range(len(prefix))]
        #print "primer=",primer
        if any(p=='AS' for p in primer):
               self.e.stage('PCRAS',[self.r.PCRAS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AS'],[vol[i] for i in range(len(vol)) if primer[i]=='AS'])
        if any(p=='BS' for p in primer):
               self.e.stage('PCRBS',[self.r.PCRBS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BS'],[vol[i] for i in range(len(vol)) if primer[i]=='BS'])
        if any(p=='AX' for p in primer):
               self.e.stage('PCRAX',[self.r.PCRAX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AX'],[vol[i] for i in range(len(vol)) if primer[i]=='AX'])
        if any(p=='BX' for p in primer):
               self.e.stage('PCRBX',[self.r.PCRBX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BX'],[vol[i] for i in range(len(vol)) if primer[i]=='BX'])
        pgm="PCR%d"%ncycles
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@57,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        return tgt
    
    def diluteInPlace(self,tgt,dil):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil]=listify([tgt,dil])
        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,False)
        adjustSrcDil(stgt,dil)
        self.e.stage('Dilute',[],[],stgt,[stgt[i].volume*dil[i] for i in range(len(stgt))])
        return tgt   #  The name of the samples are unchanged -- the predilution names
        
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False):
        if isinstance(srcdil,list) and ( not isinstance(src,list) or len(srcdil)!=len(src)):
            print "Cannot have multiple dilutions for a single sample"
            assert(False)
            
        if tgt==None:
            tgt=[]
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        [src,vol,srcdil]=listify([src,vol,srcdil])
        if len(tgt)==0:
            tgt=["%s.D%.0f"%(src[i],srcdil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if dilPlate:
            stgt=findsamps(tgt,True,Experiment.DILPLATE)
        else:
            stgt=findsamps(tgt,True,Experiment.QPCRPLATE)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])
        
        self.e.stage('QPCRDIL',[Reagents.SSD],ssrc,stgt,max(vol))
        return tgt
        
    def runQPCR(self,src,vol,srcdil,primers=["A","B"],nreplicates=1):
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        self.e.w.comment("runQPCR: primers=%s, source=%s"%([p for p in primers],[s for s in src]))
        [src,vol,srcdil]=listify([src,vol,srcdil])
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])

        # Build a list of sets to be run
        all=[]
        for repl in range(nreplicates):
            for i in range(len(ssrc)):
                for p in primers:
                    if repl==0:
                        sampname="%s.Q%s"%(src[i],p)
                    else:
                        sampname="%s.Q%s.%d"%(src[i],p,repl+1)
                    tgt=findsamps([sampname],True,Experiment.QPCRPLATE)
                    all=all+[(ssrc[i],tgt[0],p,vol[i])]

        # Fill the master mixes
        dil={}
        for p in primers:
            mq=findsamps(["MQ%s"%p],False)[0]
            t=[a[1] for a in all if a[2]==p]
            v=[a[3]/mq.conc.dilutionneeded() for a in all if a[2]==p]
            self.e.multitransfer(v,mq,t,(False,False))
            dil[p]=1.0/(1-1/mq.conc.dilutionneeded())
            
        # Add the samples
        for s in ssrc:
            t=[a[1] for a in all if a[0]==s]
            v=[a[3]/dil[a[2]] for a in all if a[0]==s]
            for i in range(len(t)):
                self.e.transfer(v[i],s,t[i],(False,False))
        
        return [a[1] for a in all]
