from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.concentration import Concentration
from Experiment import worklist, reagents, decklayout, clock, logging
from Experiment import globals

import os
import sys
import math
import argparse

maxVolumePerWell=150

reagents.add("MT7",well="A1",conc=2.5,extraVol=30)
reagents.add("MPosRT",well="B1",conc=2,extraVol=30)
reagents.add("MKlenow",well="C1",conc=2,extraVol=30)
reagents.add("MPCR",well="D1",conc=3)
reagents.add("MLigase",well="E1",conc=3,extraVol=30)
reagents.add("EDTA",well="A2",conc=Concentration(40,4,'mM'))
reagents.add("MSET7W-Beads",well="B2",conc=5,extraVol=30,hasBeads=True)
reagents.add("MSET7B-Beads",well="C2",conc=5,extraVol=30,hasBeads=True)
reagents.add("MSET7W-NB",well="D2",conc=5,extraVol=30)
reagents.add("MSET7B-NB",well="E2",conc=5,extraVol=30)
reagents.add("SSD",well="A4",conc=10.0)
reagents.add("NaOH",well="B4",conc=1.0)
reagents.add("BeadBuffer",well="C4",conc=1)
reagents.add("Dynabeads",well="D4",conc=4,hasBeads=True)
reagents.add("TE8",well="E4",conc=None)

reagents.add("EvaUSER",well="A5",conc=2)
reagents.add("P-TR",well="B5",conc=4)
reagents.add("P-T7BX",well="C5",conc=4)
reagents.add("P-T7WX",well="D5",conc=4)
reagents.add("P-T7X",well="A6",conc=4)
reagents.add("P-WX",well="B6",conc=4)
reagents.add("P-BX",well="C6",conc=4)
reagents.add("P-MX",well="D6",conc=4)
reagents.add("P-REF",well="E6",conc=4)
    
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
            result.append([i]*n)
    return result

def diluteName(name,dilution):
    # Create a name for a dilution of another sample
    # Collapses any current dilution
    components = name.split('.')
    curdil=1
    replicate=1
#    if len(components[-1])==1:
#        replicate=int(components[-1])
#        components=components[:-1]
        
    if components[-1][0]=='D':
        olddilstr=components[-1][1:]
        curdil=float(olddilstr.replace("_",".").replace('#',''))
        if curdil==0:
            curdil=1
        else:
            components=components[:-1]
    dilstr="%.2f"%(curdil*dilution)
    while dilstr[-1]=='0':
        dilstr=dilstr[:-1]
    if dilstr[-1]=='.':
        dilstr=dilstr[:-1]
    dilstr=dilstr.replace(".","_")
    result=".".join(components) + ".D"+dilstr
#    if replicate!=1:
#        result=result+"."+"%d"%replicate
#    print "%s diluted %.2f -> %s"%(name,dilution,result)
    return result

class TRP(object):
    def __init__(self):
        'Create a new TRP run'
            
    def reset(self):
        'Reset this experiment so we can generate it again after adjusting the reagent initial volumes and total time'
        totalTime=clock.elapsed()
        clock.reset(totalTime)
        #print "After reset, elapsed=%d"%clock.elapsed()
        worklist.reset()
        self.e=Experiment()
        self.e.setreagenttemp(globals.dewpoint)
        self.e.sanitize(3,50)    # Heavy sanitize
        reagents.reset()
        Sample.clearall()
        decklayout.initWellKnownSamples()
        
    def addTemplates(self,names,stockconc,finalconc=None,units="nM",plate=decklayout.EPPENDORFS,looplengths=None):
        'Add templates as "reagents", return the list of them'
        if finalconc is None:
            logging.warning("final concentration of template not specified, assuming 0.6x (should add to addTemplates() call")
            [names,stockconc]=listify([names,stockconc])
            finalconc=[0.6*x for x in stockconc]
        else:
            [names,stockconc,finalconc]=listify([names,stockconc,finalconc])

        r=[]
        if looplengths is not None:
            assert(len(names)==len(looplengths))
        for i in range(len(names)):
            if looplengths is None:
                r.append(reagents.add(names[i],plate=plate,conc=Concentration(stockconc[i],finalconc[i],units),extraVol=30))
            else:
                r.append(reagents.add(names[i],plate=plate,conc=Concentration(stockconc[i],finalconc[i],units),extraVol=30,extrainfo=looplengths[i]))
                
        return r
    
    def finish(self):
        self.e.lihahome()
        worklist.userprompt("Process complete. Continue to turn off reagent cooler")
        self.e.setreagenttemp(None)

        #Sample.printallsamples("At completion")
        hasError=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc is not None and not s.hasBeads:
                logging.error("Insufficient volume for ", s," need at least ",1.0-s.volume," ul additional",fatal=False)
                #hasError=True
            elif s.volume<2.5 and s.conc is not None:
                logging.warning("Low final volume for "+ s.name)
            elif s.volume>s.plate.maxVolume:
                logging.erorr("Excess final volume  (",s.volume,") for ",s,", maximum is ",s.plate.maxVolume,fatal=False)
                hasError=True
                
        if hasError:
            logging.error("NO OUTPUT DUE TO ERRORS")
            
        print "Wells used:  samples: %d, dilutions: %d, qPCR: %d"%(Sample.numSamplesOnPlate(decklayout.SAMPLEPLATE),Sample.numSamplesOnPlate(decklayout.DILPLATE),Sample.numSamplesOnPlate(decklayout.QPCRPLATE))
        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt")
        Sample.savematlab(scriptname+".m")
        
    ########################
    # Save samples to another well
    ########################
    def saveSamps(self,src,vol,dil,tgt=None,dilutant=None,plate=None,mix=(True,False)):
        [src,vol,dil]=listify([src,vol,dil])
        if plate is None:
            plate=decklayout.REAGENTPLATE
        if tgt is None:
            tgt=[Sample(diluteName(src[i].name,dil[i]),plate) for i in range(len(src))]

        if any([d!=1.0 for d in dil]):
            if dilutant is None:
                dilutant=decklayout.WATER
            self.e.multitransfer([vol[i]*(dil[i]-1) for i in range(len(vol))],dilutant,tgt,(False,False))

        self.e.shakeSamples(src,returnPlate=True)
        for i in range(len(src)):
            self.e.transfer(vol[i],src[i],tgt[i],mix)
            tgt[i].conc=Concentration(1.0/dil[i])
            
        return tgt
    
    def distribute(self,src,dil,vol,wells,tgt=None,dilutant=None,plate=decklayout.SAMPLEPLATE):
        if tgt is None:
            tgt=[Sample("%s.dist%d"%(src[0].name,j),plate) for j in range(wells)]
        
        if dilutant is None:
            dilutant=decklayout.WATER
        self.e.multitransfer([vol*(dil-1) for i in range(wells)],dilutant,tgt)
        self.e.multitransfer([vol for i in range(wells)],src[0],tgt)
        return tgt


    ########################
    # Dilute samples in place
    ########################
    def diluteInPlace(self,tgt,dil=None,finalvol=None):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil,finalvol]=listify([tgt,dil,finalvol])
        dilutant=decklayout.WATER
        for i in range(len(tgt)):
            if finalvol[i] is not None and dil[i] is None:
                self.e.transfer(finalvol[i]-tgt[i].volume,dilutant,tgt[i],mix=(False,False))
            elif finalvol[i] is None and dil[i] is not None:
                self.e.transfer(tgt[i].volume*(dil[i]-1),dilutant,tgt[i],mix=(False,False))
            else:
                logging.error("diluteInPlace: cannot specify both dil and finalvol")

        #print "after dilute, tgt[0]=",str(tgt[0]),",mixed=",tgt[0].isMixed()
        return tgt   #  The name of the samples are unchanged -- the predilution names

    ########################
    # Run a reaction in place
    ########################
    def runRxInPlace(self,src,vol,master,returnPlate=True,finalx=1.0):
        'Run reaction on beads in given total volume'
        [vol,src,master]=listify([vol,src,master])
        mastervol=[vol[i]*finalx/master[i].conc.dilutionneeded() for i in range(len(vol))]
        watervol=[vol[i]-src[i].volume-mastervol[i] for i in range(len(vol))]
        if any([w < -0.01 for w in watervol]):
            logging.error("runRxInPlace: negative amount of water needed: %.1f"%w)

        for i in range(len(src)):
            if  watervol[i]>=0.1:
                self.e.transfer(watervol[i],decklayout.WATER,src[i],(False,False))
        for i in range(len(src)):
            self.e.transfer(mastervol[i],master[i],src[i],(True,False))
        self.e.shakeSamples(src,returnPlate=returnPlate)

    ########################
    # T7 - Transcription
    ########################
    def runT7Setup(self,theo,src,vol,srcdil,tgt=None,rlist=["MT7"]):
        [theo,src,tgt,srcdil]=listify([theo,src,tgt,srcdil])
        for i in range(len(src)):
            if tgt[i] is None:
                if theo[i]:
                    tgt[i]=Sample("%s.T+"%src[i].name,decklayout.SAMPLEPLATE)
                else:
                    tgt[i]=Sample("%s.T-"%src[i].name,decklayout.SAMPLEPLATE)


        worklist.comment("runT7: source=%s"%[str(s) for s in src])

        rvols=[reagents.getsample(x).conc.volneeded(vol) for x in rlist]
        rtotal=sum(rvols)
        sourcevols=[vol*1.0/s for s in srcdil]
        if any(theo):
            theovols=[(vol*1.0/reagents.getsample("Theo").conc.dilutionneeded() if t else 0) for t in theo]
            watervols=[vol-theovols[i]-sourcevols[i]-rtotal for i in range(len(src))]
        else:
            watervols=[vol-sourcevols[i]-rtotal for i in range(len(src))]

        if any([w<-1e-10 for w in watervols]):
            logging.error("runT7Setup: Negative amount of water required: "+str(watervols))

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols,decklayout.WATER,tgt)
        for ir in range(len(rlist)):
            self.e.multitransfer([rvols[ir] for s in tgt],reagents.getsample(rlist[ir]),tgt)
        if any(theo):
            self.e.multitransfer([tv for tv in theovols if tv>0.01],reagents.getsample("Theo"),[tgt[i] for i in range(len(theovols)) if theovols[i]>0],ignoreContents=True)
        for i in range(len(src)):
            self.e.transfer(sourcevols[i],src[i],tgt[i])
        self.e.shakeSamples(tgt,returnPlate=True)
        for t in tgt:
            t.ingredients['BIND']=1e-20*sum(t.ingredients.values())
        return tgt
    
    def runT7Pgm(self,vol,dur):
        if dur<100:
            pgm="TRP37-%d"%dur
        else:
            pgm="T37-%d"%dur
        worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
        print "Running T7 at 37C for %d minutes"%dur
        self.e.runpgm(pgm,dur, False,vol)

    def runT7Stop(self,theo,tgt,stopmaster=None,srcdil=2):
        [theo,tgt,stopmaster,srcdil]=listify([theo,tgt,stopmaster,srcdil])
        if stopmaster is None:
            stopmaster=["MStpS_NT" if t==0 else "MStpS_WT" for t in theo]
            
        # Adjust source dilution
        for i in range(len(tgt)):
            tgt[i].conc=Concentration(srcdil[i],1)

        ## Stop
        sstopmaster=[reagents.getsample(s) for s in stopmaster]
        for i in range(len(tgt)):
            stopvol=tgt[i].volume/(sstopmaster[i].conc.dilutionneeded()-1)
            finalvol=tgt[i].volume+stopvol
            self.e.transfer(finalvol-tgt[i].volume,sstopmaster[i],tgt[i])
            
        self.e.shakeSamples(tgt,returnPlate=True)

        return tgt

    def addEDTA(self,tgt,finalconc=4):
        edta=reagents.getsample("EDTA")
        edta.conc.final=finalconc
        srcdil=edta.conc.stock*1.0/(edta.conc.stock-finalconc)
        for t in tgt:
            t.conc=Concentration(srcdil,1)
            v=t.volume*finalconc/(edta.conc.stock-finalconc)
            self.e.transfer(v,edta,t,mix=(False,False))
        self.e.shakeSamples(tgt,returnPlate=True)
        
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15,stopmaster=None):
        [theo,src,tgt,srcdil,stopmaster]=listify([theo,src,tgt,srcdil,stopmaster])
        tgt=self.runT7Setup(theo,src,vol,srcdil,tgt)
        self.runT7Pgm(vol,dur)
        tgt=self.runT7Stop(theo,tgt,stopmaster)
        return tgt

    ########################
    # Beads
    ########################
    def bindBeads(self,src,beads=None,beadConc=None,bbuffer=None,incTime=60,addBuffer=False):
        if beads is None:
            beads=reagents.getsample("Dynabeads")
        if bbuffer is None:
            bbuffer=reagents.getsample("BeadBuffer")
            
        [src,beads,bbuffer,beadConc]=listify([src,beads,bbuffer,beadConc])

        for s in src:
            if s.plate!=decklayout.SAMPLEPLATE:
                logging.error( "runBeadCleanup: src "+s+" is not in sample plate.")

            s.conc=None		# Can't track concentration of beads
            
        self.e.moveplate(src[0].plate,"Home")		# Make sure we do this off the magnet

        # Calculate volumes needed
        beadConc=[beads[i].conc.final if beadConc[i] is None else beadConc[i] for i in range(len(beads))]
        beadDil=beads[i].conc.stock/beadConc[i]
        if addBuffer:
            totalvol=[s.volume/(1-1.0/beadDil-1.0/bbuffer[i].conc.dilutionneeded()) for s in src]
            buffervol=[totalvol[i]/bbuffer[i].conc.dilutionneeded() for i in range(len(src))]
            # Add binding buffer to bring to 1x (beads will already be in 1x, so don't need to provide for them)
            for i in range(len(src)):
                self.e.transfer(buffervol[i],bbuffer[i],src[i])
        else:
            buffervol=[0.0 for i in range(len(src))]
            totalvol=[s.volume/(1-1.0/beadDil) for s in src]

        beadvol=[t/beadDil for t in totalvol]

        # Transfer the beads
        for i in range(len(src)):
            self.e.transfer(beadvol[i],beads[i],src[i],(True,False))	# Mix beads before

        self.e.shakeSamples(src,dur=incTime,returnPlate=False)

    def sepWait(self,src,sepTime=None):
        if sepTime is None:
            maxvol=max([s.volume for s in src])
            if maxvol > 50:
                sepTime=50
            else:
                sepTime=30
            sepTime=120
        self.e.pause(sepTime)	# Wait for separation
        
    def beadWash(self,src,washTgt=None,sepTime=None,residualVolume=0.1,keepWash=False,numWashes=2,wash=None,washVol=50,keepFinal=False,finalTgt=None,keepVol=4.2,keepDil=5,shakeWashes=False):
        # Perform washes
        # If keepWash is true, retain all washes (combined)
        # If keepFinal is true, take a sample of the final wash (diluted by keepDil)
        if wash is None:
            wash=decklayout.WATER
        [src,wash]=listify([src,wash])
        # Do all washes while on magnet
        assert(len(set([s.plate for s in src]))==1)	# All on same plate
        if keepWash:
            if washTgt is None:
                washTgt=[]
                for i in range(len(src)):
                    if s[i].volume-residualVolume+numWashes*(washVol-residualVolume) > decklayout.DILPLATE.maxVolume-20:
                        logging.notice("Saving %.1f ul of wash in eppendorfs"%(numWashes*washVol))
                        washTgt.append(Sample("%s.Wash"%src[i].name,decklayout.EPPENDORFS))
                    else:
                        washTgt.append(Sample("%s.Wash"%src[i].name,decklayout.DILPLATE))

        if keepFinal:
            if finalTgt is None:
                finalTgt=[]
                for i in range(len(src)):
                    finalTgt.append(Sample("%s.Final"%src[i].name,decklayout.DILPLATE))

        if any([s.volume>residualVolume for s in src]):
            # Separate and remove supernatant
            self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
            self.sepWait(src,sepTime)

            # Remove the supernatant
            for i in range(len(src)):
                if src[i].volume > residualVolume:
                    amt=src[i].amountToRemove(residualVolume)
                    if keepWash:
                        self.e.transfer(amt,src[i],washTgt[i])	# Keep supernatants
                        washTgt[i].conc=None	# Allow it to be reused
                    else:
                        self.e.dispose(amt,src[i])	# Discard supernatant
                
        # Wash

        for washnum in range(numWashes):
            if src[0].plate.curloc!="Home" and src[0].plate.curloc!="Magnet":
                self.e.moveplate(src[0].plate,"Home")
            if keepFinal and washnum==numWashes-1:
                'Retain sample of final'
                for i in range(len(src)):
                    src[i].conc=None
                    self.e.transfer(washVol-src[i].volume,wash[i],src[i],mix=(False,True))	# Add wash
                self.e.shakeSamples(src,returnPlate=True)
                self.saveSamps(src=src,tgt=finalTgt,vol=keepVol,dil=keepDil,plate=decklayout.DILPLATE)
            else:
                for i in range(len(src)):
                    src[i].conc=None
                    self.e.transfer(washVol-src[i].volume,wash[i],src[i],mix=(False,False))	# Add wash, no need to pipette mix since some heterogenity won't hurt here
                if shakeWashes:
                    self.e.shakeSamples(src,returnPlate=False)

            self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
                
            self.sepWait(src,sepTime)
                
            for i in range(len(src)):
                amt=src[i].amountToRemove(residualVolume)
                if keepWash:
                    self.e.transfer(amt,src[i],washTgt[i],mix=(False,False))	# Remove wash
                    washTgt[i].conc=None	# Allow it to be reused
                else:
                    self.e.dispose(amt,src[i])	# Remove wash

        #self.e.moveplate(src[0].plate,"Home")

        # Should only be residualVolume left with beads now
        result=[]
        if keepWash:
            result=result+washTgt
        if keepFinal:
            result=result+finalTgt

        return result

    def beadAddElutant(self,src,elutant=None,elutionVol=30,eluteTime=60,returnPlate=True,temp=None):
        if elutant is None:
            elutant=decklayout.WATER
        [src,elutionVol,elutant]=listify([src,elutionVol,elutant])
        for i in range(len(src)):
            if elutionVol[i]<30:
                logging.warning("elution from beads of %s with %.1f ul < minimum of 30ul"%(src[i].name,elutionVol[i]))
            self.e.moveplate(src[i].plate,"Home")
            self.e.transfer(elutionVol[i]-src[i].volume,elutant[i],src[i],(False,True))	
        if temp is None:
            for plate in set([s.plate for s in src]):
                self.e.shake(plate,dur=eluteTime,returnPlate=returnPlate,force=True)
        else:
            self.e.shakeSamples(src,dur=30,returnPlate=False)
            worklist.pyrun('PTC\\ptcsetpgm.py elute TEMP@%d,%d TEMP@25,2'%(temp,eluteTime))
            self.e.runpgm("elute",eluteTime/60,False,elutionVol[0])
            if returnPlate:
                self.e.moveplate(src[0].plate,"Home")

    def beadSupernatant(self,src,tgt=None,sepTime=None,residualVolume=0.1,plate=None):
        if plate is None:
            plate=decklayout.SAMPLEPLATE
        if tgt is None:
            tgt=[]
            for i in range(len(src)):
                tgt.append(Sample("%s.SN"%src[i].name,plate))
        [src,tgt]=listify([src,tgt])

        if any([s.plate!=src[0].plate for s in src]):
            logging.error("beadSupernatant: Attempt to magsep on multiple plates at the same time")

        self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
        self.sepWait(src,sepTime)

        for i in range(len(src)):
            self.e.transfer(src[i].amountToRemove(residualVolume),src[i],tgt[i],(False,False))	# Transfer elution to new tube

        self.e.moveplate(src[0].plate,"Home")
        return tgt

    def beadCombine(self,src,residualVolume=0.1,suspendVolume=150,sepTime=None):
        'Combine everything in the src wells into a the first well; assumes that there are enough beads in that well for all the combination'
        tgt=src[0]
        for s in src[1:]:
            # Combine s with tgt
            if tgt.volume>residualVolume:
                self.e.moveplate(tgt.plate,"Magnet")	# Move to magnet
                self.sepWait([tgt],sepTime)
                self.e.dispose(tgt.amountToRemove(residualVolume),tgt)
            self.e.moveplate(tgt.plate,"Home")	
            if s.volume<suspendVolume:
                self.e.transfer(suspendVolume-s.volume,decklayout.WATER,s,(False,False))
            vol=s.volume-residualVolume-1
            s.conc=None
            self.e.transfer(vol,s,tgt,mix=(True,True))

        self.e.moveplate(tgt.plate,"Home")	
        return src[0:1]
    
    ########################
    # RT - Reverse Transcription
    ########################
    def runRT(self,src,vol,srcdil,tgt=None,dur=20,heatInactivate=False,hiTemp=None,incTemp=37):
        result=self.runRTSetup(src,vol,srcdil,tgt)
        self.runRTPgm(dur,heatInactivate=heatInactivate,hiTemp=hiTemp,incTemp=incTemp)
        return result
    
    def runRTInPlace(self,src,vol,dur=20,heatInactivate=False,hiTemp=None,incTemp=37):
        'Run RT on beads in given volume'

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=None

        self.runRxInPlace(src,vol,reagents.getsample("MPosRT"),returnPlate=False)
        self.runRTPgm(dur,heatInactivate=heatInactivate,hiTemp=hiTemp,incTemp=incTemp)
        
    def runRTSetup(self,src,vol,srcdil,tgt=None,rtmaster=None):
        if rtmaster is None:
            rtmaster=reagents.getsample("MPosRT")
        if tgt is None:
            tgt=[Sample(s.name+".RT+",decklayout.SAMPLEPLATE) for s in src]

        [src,tgt,vol,srcdil]=listify([src,tgt,vol,srcdil])

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)
            
        self.e.stage('RTPos',[rtmaster],[src[i] for i in range(len(src)) ],[tgt[i] for i in range(len(tgt)) ],[vol[i] for i in range(len(vol))],destMix=False)
        #self.e.shakeSamples(tgt,returnPlate=True)
        return tgt

    def runRTPgm(self,dur=20,heatInactivate=False,hiTemp=None,incTemp=37):
        pgm="RT-%d"%dur
        if heatInactivate:
            if hiTemp is None:
                hiTemp=95
                print "Assuming RT heat inactivation temperature of ",hiTemp
            hidur=2
            worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@%d,%d TEMP@%d,%d TEMP@25,2 RATE 0.5'%(pgm,incTemp,dur*60,hiTemp,hidur*60))
            self.e.runpgm(pgm,dur+hidur+2.5,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
            print "Running RT at %dC for %d min, followed by heat inactivation/refold at %dC for %d minutes"%(incTemp,dur,hiTemp,hidur)
        else:
            worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@%d,%d TEMP@25,2'%(pgm,incTemp,dur*60))
            self.e.runpgm(pgm,dur,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
            print "Running RT at %dC for %d min without heat inactivation"%(incTemp,dur)
 
    ########################
    # Incubation - run a single temp incubation followed by inactivation
    ########################
    def runIncubation(self,src=None,vol=None,srcdil=None,tgt=None,enzymes=None,incTemp=37,incTime=15,hiTemp=None,hiTime=0,inPlace=False):
        if len(enzymes)!=1:
            logging.error("runIncubation only supports a single master mix")
        if inPlace:
            if tgt is not None:
                logging.error("tgt specified for in-place incubation")
        elif tgt is None:
            tgt=[Sample("%s.%s"%(src[i].name,enzymes[0].name),decklayout.SAMPLEPLATE) for i in range(len(src))]

        if srcdil==None:
            # Minimum dilution (no water)
            srcdil=1/(1-sum([1/e.conc.dilutionneeded() for e in enzymes]))

        if vol is None and inPlace:
            vol=[s.volume*srcdil for s in src]
            
        [src,tgt,vol,srcdil]=listify([src,tgt,vol,srcdil])

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)

        if inPlace:
            self.runRxInPlace(src,vol,enzymes[0],returnPlate=False)
            tgt=src
        else:
            self.e.stage('Incubation',enzymes,src,tgt,vol,destMix=False)
            self.e.shakeSamples(tgt,returnPlate=(incTime is None))

        if incTime is None:
            print "Setup only of incubation with %s"%enzymes[0].name
        else:
            if hiTemp is None:
                worklist.pyrun('PTC\\ptcsetpgm.py INC TEMP@%.0f,%.0f TEMP@25,30'%(incTemp,incTime*60))
                print "Incubating at %dC for %d minutes without heat inactivation"%(incTemp, incTime)
            else:
                assert(hiTime>0)
                worklist.pyrun('PTC\\ptcsetpgm.py INC TEMP@%.0f,%.0f TEMP@%.0f,%.0f TEMP@25,30'%(incTemp,incTime*60,hiTemp,hiTime*60))
                print "Incubating at %dC for %d minutes followed by heat inactivate at %dC for %d minutes"%(incTemp,incTime,hiTemp,hiTime)
            self.e.runpgm("INC",incTime+hiTime+2,False,max(vol),hotlidmode="TRACKING",hotlidtemp=10)

        return tgt

    ########################
    # USER - USER enzyme digestion
    ########################
    def runUser(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,inPlace=False):
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,enzymes=[reagents.getsample("MUser")],inPlace=inPlace)
        
    ########################
    # Klenow extension
    ########################
    def runKlenow(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=20,hiTemp=75,inPlace=False):
        assert(inPlace or vol is not None)
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=hiTemp,hiTime=hiTime,enzymes=[reagents.getsample("MKlenow")],inPlace=inPlace)

    ########################
    # Ligation
    ########################
    def runLig(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=10,hiTemp=65,inPlace=False):
        assert(inPlace or vol is not None)
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=hiTemp,hiTime=hiTime,enzymes=[reagents.getsample("MLigase")],inPlace=inPlace)

    ########################
    # DNase digestion
    ########################
    def runDNase(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=10,inPlace=False):
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=75,hiTime=hiTime,enzymes=[reagents.getsample("MDNase")],inPlace=inPlace)

    ########################
    # PCR
    ########################
    def runPCR(self,primers,src,vol,srcdil,tgt=None,ncycles=20):
        ## PCR
        [primers,src,tgt,vol,srcdil]=listify([primers,src,tgt,vol,srcdil])
        for i in range(len(tgt)):
            if tgt[i] is None:
                tgt[i]=Sample("%s.P%s"%(src[i].name,primers[i]),src[i].plate)

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)
        
        logging.notice( "primer="+str(primers))
        for up in set(primers):
            s="P-%s"%up
            if not reagents.isReagent(s):
                reagents.add(name=s,conc=4,extraVol=30)
            self.e.stage('PCR%s'%up,[reagents.getsample("MPCR"),reagents.getsample(s)],[src[i] for i in range(len(src)) if primers[i]==up],[tgt[i] for i in range(len(tgt)) if primers[i]==up],[vol[i] for i in range(len(vol)) if primers[i]==up],destMix=False)
        pgm="PCR%d"%ncycles
        self.e.shakeSamples(tgt,returnPlate=False)
        #        worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@57,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        self.e.shakeSamples(tgt,returnPlate=True)
        return tgt

    def runPCRInPlace(self,prefix,src,vol,ncycles,suffix,annealtemp=57,save=None):
        [prefix,src,vol,suffix]=listify([prefix,src,vol,suffix])

        primer=[reagents.getsample("MPCR"+prefix[i]+suffix[i]) for i in range(len(prefix))]
        self.runRxInPlace(src,vol,primer,returnPlate=(save is not None))
        if save is not None:
            self.saveSamps(src=src,vol=5,dil=10,tgt=save,plate=decklayout.DILPLATE,dilutant=decklayout.SSDDIL)

        pgm="PCR%d"%ncycles
        #        worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        worklist.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@%f,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,annealtemp,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
    
    ########################
    # qPCR
    ########################
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False,pipMix=False,dilutant=decklayout.SSDDIL):
        [src,vol,srcdil]=listify([src,vol,srcdil])
        vol=[float(v) for v in vol]
        if tgt is None:
            if dilPlate:
                tgt=[Sample(diluteName(src[i].name,srcdil[i]),decklayout.DILPLATE) for i in range(len(src))]
            else:
                tgt=[Sample(diluteName(src[i].name,srcdil[i]),decklayout.SAMPLEPLATE) for i in range(len(src))]

        srcvol=[vol[i]/srcdil[i] for i in range(len(vol))]
        watervol=[vol[i]-srcvol[i] for i in range(len(vol))]
        if len(watervol) > 4 and sum(watervol)>800:
            logging.notice("Could optimize distribution of "+str(len(watervol))+" moves of "+dilutant.name+": vol=["+str(["%.1f"%w for w in watervol])+"]")
        self.e.multitransfer(watervol,dilutant,tgt,(False,False))
        
        self.e.shakeSamples(src,returnPlate=True)
        for i in range(len(src)):
            tgt[i].conc=None		# Assume dilutant does not have a concentration of its own
            # Check if we can align the tips here
            if i<len(src)-3 and tgt[i].well+1==tgt[i+1].well and tgt[i].well+2==tgt[i+2].well and tgt[i].well+3==tgt[i+3].well and tgt[i].well%4==0 and self.e.cleanTips!=15:
                #print "Aligning tips"
                self.e.sanitize()
            self.e.transfer(srcvol[i],src[i],tgt[i],(not src[i].isMixed(),pipMix))
            if tgt[i].conc != None:
                tgt[i].conc.final=None	# Final conc are meaningless now
            
        return tgt
        
    def runQPCR(self,src,vol,primers,nreplicates=1,enzName="EvaUSER"):
        ## QPCR setup
        worklist.comment("runQPCR: primers=%s, source=%s"%([p for p in primers],[s.name for s in src]))
        [src,vol,nreplicates]=listify([src,vol,nreplicates])
        self.e.shakeSamples(src,returnPlate=True)

        # Build a list of sets to be run
        torun=[]
        for repl in range(max(nreplicates)):
            for p in primers:
                for i in range(len(src)):
                    if nreplicates[i]<=repl:
                        continue
                    if repl==0:
                        sampname="%s.Q%s"%(src[i].name,p)
                    else:
                        sampname="%s.Q%s.%d"%(src[i].name,p,repl+1)
                    s=Sample(sampname,decklayout.QPCRPLATE)
                    torun=torun+[(src[i],s,p,vol[i])]

        # Add enzyme
        e=reagents.getsample(enzName)
        v=[a[3]/e.conc.dilutionneeded() for a in torun]
        t=[a[1] for a in torun]
        self.e.multitransfer(v,e,t)

        # Make the target have 'none' concentration so we can multiadd to it again
        for s in t:
            s.conc=None

        # Fill the master mixes
        dil={}
        for p in primers:
            mname="P-%s"%p
            if not reagents.isReagent(mname):
                reagents.add(name=mname,conc=4,extraVol=30)
            mq=reagents.getsample(mname)
            t=[a[1] for a in torun if a[2]==p]
            v=[a[3]/mq.conc.dilutionneeded() for a in torun if a[2]==p]
            assert(v>0)
            self.e.multitransfer(v,mq,t,(False,False))
            dil[p]=1.0/(1-1/e.conc.dilutionneeded()-1/mq.conc.dilutionneeded())
            
        # Add the samples
        self.e.sanitize()		# In case we are aligned
        for a in torun:
            s=a[0]
            t=a[1]
            p=a[2]
            v=a[3]/dil[p]
            t.conc=None		# Concentration of master mix is irrelevant now
            self.e.transfer(v,s,t)
            
        return [a[1] for a in torun]

    def setup(self):
        'Setup for experiment -- run once.  Usually overridden by actual experiment'
        worklist.setOptimization(True)

    def pgm(self):
        'Actual robot code generation -- may be run multiple times to establish initial volumes.  Overridden by actual experiment'

    def run(self):
        parser=argparse.ArgumentParser(description="TRP")
        parser.add_argument('-v','--verbose',help='Enable verbose output',default=False,action="store_true")
        parser.add_argument('-D','--dewpoint',type=float,help='Dew point',default=10.0)
        args=parser.parse_args()
        
        print "Estimating evaporation for dew point of %.1f C"%args.dewpoint
        globals.dewpoint=args.dewpoint

        self.reset()

        self.setup()
        if args.verbose:
            print '------ Preliminary runs to set volume -----'
        else:
            sys.stdout=open(os.devnull,'w')
        self.pgm()
        self.reset()
        self.pgm()
        if args.verbose:
            globals.verbose=True
            print '------ Main run -----'
        else:
            sys.stdout=sys.__stdout__
        self.reset()
        self.pgm()
        self.finish()
