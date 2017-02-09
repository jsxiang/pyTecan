# Generic selection progam
import debughook
import math

from Experiment.concentration import Concentration
from Experiment.sample import Sample
from Experiment import worklist, reagents, decklayout, logging
from TRPLib.TRP import TRP
from TRPLib.QSetup import QSetup
from pcrgain import pcrgain

class PGMSelect(TRP):
    '''Selection experiment'''
    
    def __init__(self,inputs,nrounds,firstID,pmolesIn,doexo=False,doampure=False,directT7=True,templateDilution=0.3,tmplFinalConc=50,saveDil=24,qpcrWait=False,allLig=False,qpcrStages=["negative","template","ext","finalpcr"],finalPlus=True, cleaveOnly=False,t7dur=30,columnclean=False,douser=False,usertime=10,pcrdil=None,exotime=120):
        # Initialize field values which will never change during multiple calls to pgm()
        for i in range(len(inputs)):
            if 'name' not in inputs[i]:
                inputs[i]['name']='%s_%d_R%d_%s'%(inputs[i]['prefix'],inputs[i]['ID'],inputs[i]['round'],inputs[i]['ligand'])
        self.inputs=inputs
        self.nrounds=nrounds
        self.doexo=doexo
        self.exotime=exotime
        self.doampure=doampure
        self.directT7=directT7
        self.tmplFinalConc=tmplFinalConc
        self.templateDilution=templateDilution
        self.pmolesIn=pmolesIn
        self.firstID=firstID
        self.saveDil=saveDil
        self.qpcrWait=qpcrWait
        self.allLig=allLig
        self.qpcrStages=qpcrStages
        self.finalPlus=finalPlus
        self.cleaveOnly=cleaveOnly
        self.t7dur=t7dur
        self.columnclean=columnclean
        self.douser=douser
        self.usertime=usertime				# USER incubation time in minutes
        
        # General parameters
        self.qConc = 0.025			# Target qPCR concentration in nM (corresponds to Ct ~ 10)
        self.rnaConc=2000		    # Expectec concentration of RNA
        self.pcrSave=True		    # Save PCR products
        self.savedilplate=True	# Save PCR products on dilutions plate
        self.rtSave=False			# True to save RT product from uncleaved round and run ligation during cleaved round
        self.dopcr=True			    # Run PCR of samples
        self.cleavage=0.40			# Estimated cleavage (for computing dilutions of qPCRs)
        self.exopostdil=2
        self.extpostdil=2
        
        # Computed parameters
        if pcrdil is None:
            self.pcrdil1=80.0/self.extpostdil/(self.exopostdil if self.doexo else 1)
            self.pcrdil2=self.pcrdil1/2
        else:
            self.pcrdil1=pcrdil
            self.pcrdil2=pcrdil

        self.t7vol1a=max(20+5.4,self.pmolesIn*1000/tmplFinalConc)  # Extra vol for first round to compensate for qPCR removals
        self.rtvol1=max(8,self.pmolesIn*2*1e-12/1.0e-6*1e6)    # Compute volume so that full utilization of RT primers results in 2 * input diversity
        self.pcrvol1=max(100,self.pmolesIn*1000/(self.rnaConc*0.9/4)*self.pcrdil1)    # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup
        # Use at least 100ul so the evaporation of the saved sample that occurs during the run will be relatively small
        self.pcrcycles1=10
        
        self.t7vol2=max(22,self.pmolesIn*1000/self.tmplFinalConc)
        self.rtvol2=max(9,self.pmolesIn*2*1e-12/1.0e-6*1e6)    # Compute volume so that full utilization of RT primers results in 2 * input diversity
        self.pcrvol2=max(100,self.pmolesIn*1000/(self.rnaConc*0.9/4/1.25)*self.pcrdil2)  # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup and Ligation
        self.pcrcycles2=10

        # Add templates
        if self.directT7:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.SAMPLEPLATE,looplengths=[inp['looplength'] for inp in inputs],initVol=self.t7vol1a*templateDilution,extraVol=0)
        else:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.DILPLATE,looplengths=[inp['looplength'] for inp in inputs],extraVol=15) 
        
    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=16,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)
        t7in = [s.getsample()  for s in self.srcs]
        
        if "negative" in self.qpcrStages:
            qpcrPrimers=["REF","MX","T7X","T7AX","T7BX","T7WX"]
            q.addSamples(decklayout.SSDDIL,1,qpcrPrimers,save=False)   # Negative controls
        
        # Save RT product from first (uncleaved) round and then use it during 2nd (cleaved) round for ligation and qPCR measurements
        self.rndNum=0
        self.nextID=self.firstID
        curPrefix=[inp['prefix'] for inp in self.inputs]

        while self.rndNum<self.nrounds:
            prefixOut=["A" if p=="W" else "B" if p=="A" else "W" if p=="B" else "BADPREFIX" for p in curPrefix]
            print "prefixIn=",curPrefix
            print "prefixOut=",prefixOut

            if not self.cleaveOnly:
                self.rndNum=self.rndNum+1
                if self.rndNum==1:
                    self.t7vol1=self.t7vol1a
                else:
                    self.t7vol1=max(20,self.pmolesIn*1000/min([inp.conc.final for inp in t7in])) # New input volueme
                r1=self.oneround(q,t7in,prefixOut,prefixIn=curPrefix,keepCleaved=False,rtvol=self.rtvol1,t7vol=self.t7vol1,cycles=self.pcrcycles1,pcrdil=self.pcrdil1,pcrvol=self.pcrvol1,dolig=self.allLig)
                # pcrvol is set to have same diversity as input 
                for i in range(len(r1)):
                    r1[i].name="%s_%d_R%dU_%s"%(curPrefix[i],self.nextID,self.inputs[i]['round']+self.rndNum,self.inputs[i]['ligand'])
                    self.nextID+=1
                    r1[i].conc.final=r1[i].conc.stock*self.templateDilution
                if self.rndNum>=self.nrounds:
                    logging.warning("Warning: ending on an uncleaved round")
                    break
            else:
                r1=t7in
                
            self.rndNum=self.rndNum+1
            
            if self.rndNum==1:
                self.t7vol2=self.t7vol1a
            else:
                self.t7vol2=max(20,self.pmolesIn*1000/min([inp.conc.final for inp in r1]))
            r2=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=True,rtvol=self.rtvol2,t7vol=self.t7vol2,cycles=self.pcrcycles2,pcrdil=self.pcrdil2,pcrvol=self.pcrvol2,dolig=True)
            # pcrvol is set to have same diversity as input = (self.t7vol2*self.templateDilution/rnagain*stopdil*rtdil*extdil*exodil*pcrdil)
            for i in range(len(self.inputs)):
                r2[i].name="%s_%d_R%dC_%s"%(prefixOut[i],self.nextID,self.inputs[i]['round']+self.rndNum,self.inputs[i]['ligand'])
                self.nextID+=1
                r2[i].conc.final=r2[i].conc.stock*self.templateDilution
            t7in=r2
            curPrefix=prefixOut
        if "finalpcr" in self.qpcrStages:
            for i in range(len(r2)):
                q.addSamples(src=r2[i],needDil=r2[i].conc.stock/self.qConc,primers=["T7X","T7"+prefixOut[i]+"X"])
            
        print "######### qPCR ###########"
        #q.addReferences(mindil=4,nsteps=6,primers=["T7X","MX","T7AX"])
        if self.qpcrWait:
            worklist.userprompt('Continue to setup qPCR')
        q.run()
        
    def oneround(self,q,input,prefixOut,prefixIn,keepCleaved,t7vol,rtvol,pcrdil,cycles,pcrvol,dolig):
        if keepCleaved:
            print "Starting new cleavage round, will add prefix: ",prefixOut
            assert(dolig)
        else:
            print "Starting new uncleaved round, will retain prefix: ",prefixIn

        if self.rtSave:
            assert(dolig)
            
        names=[i.name for i in input]
            
        print "######## T7 ###########"
        print "Inputs:  (t7vol=%.2f)"%t7vol
        inconc=[inp.conc.final for inp in input]
        for inp in input:
            print "    %s:  %.1ful@%.1f nM, use %.1f ul (%.3f pmoles)"%(inp.name,inp.volume,inp.conc.stock,t7vol/inp.conc.dilutionneeded(), t7vol*inp.conc.final/1000)
            # inp.conc.final=inp.conc.stock*self.templateDilution
        needDil = max([inp.conc.stock for inp in input])*1.0/self.qConc
        if self.directT7 and  self.rndNum==1:
            # Just add ligands and MT7 to each well
            if not keepCleaved:
                for i in range(len(input)):
                    ligand=reagents.getsample(self.inputs[i]['ligand'])
                    self.e.transfer(t7vol/ligand.conc.dilutionneeded(),ligand,input[i],mix=(False,False))
            mconc=reagents.getsample("MT7").conc.dilutionneeded()
            for i in range(len(input)):
                watervol=t7vol*(1-1/mconc)-input[i].volume
                if watervol>0.1:
                    self.e.transfer(watervol,decklayout.WATER,input[i],mix=(False,False))
                self.e.transfer(t7vol/mconc,reagents.getsample("MT7"),input[i],mix=(False,False))
                assert(abs(input[i].volume-t7vol)<0.1)
            rxs=input
        elif self.rndNum==self.nrounds and self.finalPlus:
            rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            rxs += self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            prefixIn+=prefixIn
            prefixOut+=prefixOut
            names+=["%s+"%n for n in names]
        elif keepCleaved:
            rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
        else:
            rxs = self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            
        for i in range(len(rxs)):
            rxs[i].name="%s.rx"%names[i]

        if self.rndNum==1 and "template" in self.qpcrStages:
            # Initial input 
            for i in range(len(rxs)):
                q.addSamples(src=rxs[i],needDil=needDil,primers=["T7X","REF","T7"+prefixIn[i]+"X"],names=["%s.T-"%names[i]])
        
        needDil = needDil*max([inp.conc.dilutionneeded() for inp in input])
        self.runT7Pgm(dur=self.t7dur,vol=t7vol)
        self.rnaConc=min(40,inconc)*self.t7dur*65/30
        print "Estimate RNA concentration in T7 reaction at %.0f nM"%self.rnaConc

        print "######## Stop ###########"
        #self.saveSamps(src=rxs,vol=5,dil=10,plate=decklayout.EPPENDORFS,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check [RNA] on Qubit, bioanalyzer

        self.e.lihahome()

        print "Have %.1f ul before stop"%rxs[0].volume
        preStopVolume=rxs[0].volume
        self.addEDTA(tgt=rxs,finalconc=2)	# Stop to 2mM EDTA final
        
        stop=["Unclvd-Stop" if (not dolig) else "A-Stop" if n=="A" else "B-Stop" if n=="B" else "W-Stop" if n=="W" else "BADPREFIX" for n in prefixOut]

        stopDil=rxs[0].volume/preStopVolume
        needDil = self.rnaConc/self.qConc/stopDil
        if "stopped" in self.qpcrStages:
            q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","T7X","REF"],names=["%s.stopped"%r.name for r in rxs])
        
        print "######## RT  Setup ###########"
        rtDil=4
        hiTemp=95
        rtDur=20

        rxs=self.runRT(src=rxs,vol=rtvol,srcdil=rtDil,heatInactivate=True,hiTemp=hiTemp,dur=rtDur,incTemp=50,stop=[reagents.getsample(s) for s in stop])    # Heat inactivate also allows splint to fold
        print "RT volume= ",[x.volume for x in rxs]
        needDil /= rtDil
        if "rt" in self.qpcrStages:
            q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","REF"],names=["%s.rt"%r.name for r in rxs])

        rtSaveDil=10
        rtSaveVol=3.5

        if self.rtSave and not keepCleaved:
            # Also include RT from a prior round from here on
            for r in self.lastSaved:
                newsamp=Sample("%s.samp"%r.name,decklayout.SAMPLEPLATE)
                self.e.transfer(rxs[0].volume,r,newsamp,(False,False))
                rxs.append(newsamp)
            
        if dolig:
            print "######## Ligation setup  ###########"
            extdil=5.0/4
            reagents.getsample("MLigase").conc=Concentration(5)
            rxs=self.runLig(rxs,inPlace=True)

            print "Ligation volume= ",[x.volume for x in rxs]
            needDil=needDil/extdil
            if self.extpostdil>1:
                print "Dilution after extension: %.2f"%self.extpostdil
                self.diluteInPlace(tgt=rxs,dil=self.extpostdil)
                needDil=needDil/self.extpostdil
                    
            if self.saveDil is not None:
                ext=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.ext"%n,decklayout.DILPLATE) for n in names],mix=(False,True))   # Save cDNA product for subsequent NGS
                if "ext" in self.qpcrStages:
                    for i in range(len(ext)):
                        # Make sure we don't take more than 2 more steps
                        maxdil=q.MAXDIL*q.MAXDIL
                        if needDil/self.saveDil>maxdil:
                            logging.notice( "Diluting ext by %.0fx instead of needed %.0f to save steps"%(maxdil,needDil/self.saveDil))
                        q.addSamples(src=[ext[i]],needDil=min(maxdil,needDil/self.saveDil),primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]],save=False)
            else:
                if "ext" in self.qpcrStages:
                    for i in range(len(input)):
                        q.addSamples(src=[rxs[i]],needDil=needDil,primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]])
                        isave=i+len(input)
                        if isave<len(rxs):
                            # samples restored
                            q.addSamples(src=[rxs[isave]],needDil=needDil/rtSaveDil,primers=["T7"+rxs[isave].name[0]+"X","T7"+("B" if rxs[isave].name[0]=="A" else "W" if rxs[isave].name[0]=="B" else "A")+"X","MX","T7X","REF"])

            if self.doexo:
                print "######## Exo ###########"
                prevvol=rxs[0].volume
                rxs=self.runExo(rxs,incTime=self.exotime,inPlace=True,hiTemp=95,hiTime=20)
                print "Exo volume=[%s]"%",".join(["%.1f"%r.volume for r in rxs])
                exoDil=rxs[0].volume/prevvol
                needDil/=exoDil
                needDil/=7   #  Anecdotal based on Ct's -- large components (MX) reduced by exo digestion
                if self.exopostdil>1:
                    print "Dilution after exo: %.2f"%self.exopostdil
                    self.diluteInPlace(tgt=rxs,dil=self.exopostdil)
                    needDil=needDil/self.exopostdil

                exo=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.exo"%n,decklayout.DILPLATE) for n in names])   # Save cDNA product
                if "exo" in self.qpcrStages:
                    q.addSamples(src=exo,needDil=needDil/self.saveDil,primers=["T7AX","T7BX","T7WX","MX","T7X","REF"],names=["%s.exo"%n for n in names])
            else:
                exoDil=1
                self.exopostdil=1
                exo=[]
        else:
            extdil=1
            self.extpostdil=1
            self.exopostdil=1
            exoDil=1
            
        if self.doampure:
            print "######## Ampure Cleanup ###########"
            ratio=1.8
            elutionVol=30
            needDil=needDil*rxs[0].volume/elutionVol
            print "Ampure cleanup of [%s] into %.1f ul"%(",".join(["%.1f"%r.volume for r in rxs]),elutionVol)
            clean=self.runAmpure(src=rxs,ratio=ratio,elutionVol=elutionVol)
            if "ampure" in self.qpcrStages:
                q.addSamples(src=clean,needDil=needDil,primers=["T7AX","T7BX","T7WX","MX","T7X","REF"],names=["%s.amp"%n for n in names])
            rxs=clean   # Use the cleaned products for PCR

        if self.columnclean:
            print "######## Column Cleanup ###########"
            elutionVol=30
            cleaned=[Sample("%s.cln"%r.name,decklayout.SAMPLEPLATE,volume=elutionVol,ingredients=r.ingredients) for r in rxs]
            columnDil=elutionVol/rxs[0].volume
            print "Column cleanup of [%s] into %.1f ul"%(",".join(["%.1f"%r.volume for r in rxs]),elutionVol)
            inwells=",".join([r.plate.wellname(r.well) for r in rxs])
            outwells=",".join([r.plate.wellname(r.well) for r in cleaned])
            msg="Run column cleanup of wells [%s], elute in %.1f ul and put products into wells [%s]"%(inwells,elutionVol,outwells)
            print msg
            worklist.userprompt(msg)
            needDil=needDil/columnDil
            rxs=cleaned
            if "column" in self.qpcrStages:
                q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","T7BX","T7WX","MX","T7X","REF"],names=["%s.cln"%n for n in names])
        else:
            columnDil=1
            
        if self.douser:
            print "######## User ###########"
            prevvol=rxs[0].volume
            self.runUser(rxs,incTime=self.usertime,inPlace=True)
            print "USER volume=[%s]"%",".join(["%.1f"%r.volume for r in rxs])
            userDil=rxs[0].volume/prevvol
            needDil/=userDil
            if "user" in self.qpcrStages:
                q.addSamples(src=rx,needDil=needDil,primers=["T7AX","T7BX","T7WX","MX","T7X","REF"],names=["%s.user"%n for n in names])
        else:
            userDil=1

        totalDil=stopDil*rtDil*extdil*self.extpostdil*exoDil*self.exopostdil*columnDil*userDil
        fracRetained=rxs[0].volume/(t7vol*totalDil)
        print "Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,rtDil,extdil,self.extpostdil,exoDil,self.exopostdil,columnDil,userDil,totalDil,fracRetained*100)

        if self.rtSave and not keepCleaved:
            # Remove the extra samples
            assert(len(self.lastSaved)>0)
            rxs=rxs[:len(rxs)-len(self.lastSaved)]
            self.lastSaved=[]

        if len(rxs)>len(input):
            rxs=rxs[0:len(input)]    # Only keep -target products
            prefixOut=prefixOut[0:len(input)]
            prefixIn=prefixIn[0:len(input)]
            
        if self.dopcr:
            print "######### PCR #############"
            print "PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(pcrvol, pcrdil,",".join(["%.1f"%r.volume for r in rxs]))
            maxSampleVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)

            initConc=needDil*self.qConc/pcrdil
            if keepCleaved:
                if self.doexo:
                    initConc=initConc*7*self.cleavage		# Back out 7x dilution in exo step, but only use cleaved as input conc
                else:
                    initConc=initConc*self.cleavage		# Only use cleaved as input conc
            else:
                initConc=initConc*(1-self.cleavage)
                
            gain=pcrgain(initConc,400,cycles)
            finalConc=initConc*gain
            print "Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc,cycles,finalConc)
            nsplit=int(math.ceil(pcrvol*1.0/maxSampleVolume))
            print "Split each PCR into %d reactions"%nsplit
            minsrcdil=1/(1-1.0/3-1.0/4)
            sampNeeded=pcrvol/pcrdil
            if self.rtSave and keepCleaved:
                sampNeeded+=rtSaveVol
            maxvol=max([r.volume for r in rxs]);
            minvol=min([r.volume for r in rxs]);
            predil=min(75/maxvol,(40+1.4*nsplit)/(minvol-sampNeeded))  # Dilute to have 40ul left -- keeps enough sample to allow good mixing
            if keepCleaved and self.rtSave and predil>rtSaveDil:
                print "Reducing predil from %.1f to %.1f (rtSaveDil)"%(predil, rtSaveDil)
                predil=rtSaveDil
            if pcrdil/predil<minsrcdil:
                predil=pcrdil/minsrcdil	  # Need to dilute at least this into PCR
            if predil>1:
                self.diluteInPlace(rxs,predil)
                self.e.shakeSamples(rxs)
                print "Pre-diluting by %.1fx into [%s] ul"%(predil,",".join(["%.1f"%r.volume for r in rxs]))
            if keepCleaved and self.rtSave:
                assert(len(rxs)==len(rtSave))
                print "Saving %.1f ul of each pre-PCR sample (@%.1f*%.1f dilution)"%(rtSaveVol ,predil, rtSaveDil/predil)
                self.lastSaved=[Sample("%s.sv"%x.name,decklayout.DILPLATE) for x in rxs]
                for i in range(len(rxs)):
                    # Save with rtSaveDil dilution to reduce amount of RT consumed (will have Ct's 2-3 lower than others)
                    self.e.transfer(rtSaveVol*predil,rxs[i],self.lastSaved[i],(False,False))
                    self.e.transfer(rtSaveVol*(rtSaveDil/predil-1),decklayout.WATER,self.lastSaved[i],(False,True))  # Use pipette mixing -- shaker mixing will be too slow

            pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil*1.0/predil,ncycles=cycles,primers=["T7%sX"%x for x in (prefixOut if keepCleaved else prefixIn)]*nsplit,usertime=self.usertime if keepCleaved and not self.douser else None,fastCycling=False,inPlace=False)
                
            needDil=finalConc/self.qConc
            print "Projected final concentration = %.0f nM"%(needDil*self.qConc)
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc,final=None,units='nM')

            if self.pcrSave:
                # Save samples at 1x (move all contents -- can ignore warnings)
                if self.savedilplate:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume for x in pcr[:len(rxs)]],dil=1,plate=decklayout.DILPLATE,atEnd=True)
                else:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume for x in pcr[:len(rxs)]],dil=1,plate=decklayout.EPPENDORFS)
                if nsplit>1:
                    # Combine split
                    for i in range(len(rxs),len(rxs)*nsplit):
                        self.e.transfer(pcr[i].volume-16.4,pcr[i],sv[i%len(sv)],mix=(False,i>=len(rxs)*(nsplit-1)))
                    # Correct concentration (above would've assumed it was diluted)
                    for i in range(len(sv)):
                        sv[i].conc=pcr[i].conc

                if "pcr" in self.qpcrStages:
                    for i in range(len(sv)):
                        q.addSamples(sv[i],needDil,["T7%sX"%prefixOut[i]])

                processEff=0.5   # Estimate of overall efficiency of process
                print "Saved %.2f pmoles of product (%.0f ul @ %.1f nM)"%(sv[0].volume*sv[0].conc.stock/1000,sv[0].volume,sv[0].conc.stock)
                return sv
            else:
                return pcr[:len(rxs)]
        else:
            return rxs
    

    
