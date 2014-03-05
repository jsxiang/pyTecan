% Collect together the Ct's for each sample 
function result=getct(data,sampname)
if nargin<2
  sampnames={data.samps(strcmp({data.samps.plate},'qPCR')).name};
  for i=1:length(sampnames)
    qpos=strfind(sampnames{i},'.Q');
    if length(qpos)~=1
      error('Unable to find ".Q" in %s\n',sampnames{i});
    end
    sampnames{i}=sampnames{i}(1:qpos-1);
  end
  sampnames=unique(sampnames);
  result={};
  for i=1:length(sampnames)
    result{end+1}=getct(data,sampnames{i});
  end
  return;
end

% Locate samples
sel=find(strncmp({data.samps.name},[sampname,'.Q'],length(sampname)+2));
if length(sel)==0
  fprintf('Unable to locate %s.Q*\n', sampname);
  result=struct();
  return;
end
result=struct('name',sampname);
% Split based on dots
dots=find([sampname,'.']=='.');
parts={};
pdot=1;
for i=1:length(dots)
  pt=sampname(pdot:dots(i)-1);
  if pt(1)~='D'
    parts{end+1}=pt;
  end
  pdot=dots(i)+1;
end
result.tmpl=parts{1};
if length(parts)==1
  result.type='tmpl';
  result.cond='tmpl';
else
  if parts{2}(end)=='-'
    result.cond='-';
  elseif parts{2}(end)=='+'
    result.cond=parts{2};
  else
    result.cond='?';
  end

  if length(parts)==2
    result.type='T7';
  else
    if parts{end}(1)=='L'
      result.type='Lig';
      result.ligsuffix=parts{end}(2:end);
    else
      result.type=parts{end};
    end
  end
end

if ~data.useminer && isfield(data,'opd')
  if ~isfield(data.opd,'ct')
    data.opd=ctcalc(data.opd);
  end
end
  
for i=1:length(sel)
  samp=data.samps(sel(i));
  v=struct('samp',samp);
  if ~strcmp(v.samp.plate,'qPCR')
    error('%s is on plate %s, not qPCR plate\n', v.name, v.plate);
  end
  v.primer=samp.name(length(sampname)+3:end);
  v.well=wellnames2pos({samp.well});
  if isfield(data,'md')
    v.ctm=data.md.CT(v.well+1);
  end
  if isfield(data,'opd')
    v.cti=data.opd.ct(v.well+1);
  end

  if data.useminer
    v.ct=v.ctm;
  elseif isfield(v,'cti')
    v.ct=v.cti;
  else
    fprintf('No data to find Ct\n');
    v.ct=nan;
  end

  if isfield(result,v.primer) && ~isempty(result.(v.primer))
    fprintf('Have multiple samples for primer %s\n', v.primer);
  end
  
  % Calculation dilution based on volumes of ingredients
  [vols,o]=sort(samp.volumes,'descend');
  for k=1:length(o)
    nmk=samp.ingredients{o(k)};
    if ~any(strcmp(nmk,{'Water','SSD','MPosRT'})) && ~strncmp(nmk,'MQ',2)  && ~strncmp(nmk,'MLig',4) && ~strncmp(nmk,'MStp',4)
      if nmk(1)=='M'
        rdilstr=data.samps(find(strcmp({data.samps.name},nmk))).concentration;
        if rdilstr(end)~='x'
          error('Uninterpretable dilution string for %s: %s\n', nmk, rdilstr);
        end
        rdil=str2num(rdilstr(1:end-1));
        nmk=nmk(2:end);
      else
        rdil=1;
      end
      dilution=sum(vols)/vols(k)/rdil;

      if isfield(result,'dilution')
        if result.dilution~=dilution || ~strcmp(result.dilrelative,nmk)
          error('Inconsistent dilution information for %s\n',v.name);
        end
      else
        result.dilution=dilution;
        result.dilrelative=nmk;
      end
      break;
    end
  end
  if ~isfield(result,'dilution')
    result.dilution=1;
    result.dilrelative='None';
  end
  % Calculate concentrations
  p=data.primers.(v.primer);
  if isfinite(v.ct)
    v.conc=p.eff^-v.ct*p.ct0*result.dilution;
  else
    v.conc=nan;
  end

  result.(v.primer)=v;
end

% Calculate cleavage, yield, theofrac
% Cleavage
if isfield(result,'A') && isfield(result,'B')
  if ~isempty(strfind(result.name,'.LB'))
    result.cleavage=result.B.conc/(result.A.conc+result.B.conc);
  elseif ~isempty(strfind(result.name,'.LA'))
    result.cleavage=result.A.conc/(result.A.conc+result.B.conc);
  else
    result.cleavage=-min(result.A.conc,result.B.conc)/(result.A.conc+result.B.conc);
  end
  result.yield=result.A.conc+result.B.conc;
end

if isfield(result,'T') && isfield(result,'M')
  result.theofrac=result.T.conc/result.M.conc;
end
  