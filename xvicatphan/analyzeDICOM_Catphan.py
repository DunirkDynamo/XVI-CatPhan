

import pydicom
import os
from datetime import datetime
import time
import shutil
import string
from pathlib import Path

# IPv4 Address. . . . . . . . . . . : 10.244.171.198

#to launch dicom listening script go in miniconda prompt, activate dqast, cd to pathfrom below and type python -m pynetdicom storescp 104"

#####################################################################

jgbpc=0

#####################################################################
# Testing block - comment out when done testing
# Hardcoding main_path for testing:
mainpath1 = 'C:\TOH Data\CATPHAN'

#####################################################################
#####################################################################
# Real block - uncomment when done testing:
'''
if jgbpc ==0:
    mainpath1=Path(r"\\Civic1.ottawahospital.on.ca\medphys\Research\Equipment Software\dicomreceiver")
else:
    mainpath1=Path(r"C:\dicomreceiver")
''' 
    
pathfrom=Path(mainpath1,'newdata') 

# this is where data received will be dumped with appropriate patientid and time folder
pathtoQA        =Path(mainpath1,'dicomQA')  
pathtoOTHER     =Path(mainpath1,'dicomOTHER')   
pathtoAnalysis  =Path(mainpath1,'toanalyze')  
#####################################################################


done               = 0
sleeping           = 5 # number of seconds to wait between checking for new files
ncycles_toanalysis = 8 # if no new files received in 8 steps or 40 seconds then attempt analysis
steps              = 0 # number of time checking for new file so far since script was launched
stepsAnalysis      = 0 # number of steps checking for new files and not finding any (after receiving some files)
nfilesOLD          = 0 # number of file received so far

while done == 0:
    #check if path is available
    pathisworking = 1
    try:
        testingfiles  = os.listdir(pathfrom)
        pathisworking = 1
    except:
        print("path not available")
        pathisworking = 0
    
    
    if pathisworking == 1:
        
        #find all files
        files1 = []
        files1 = os.listdir(pathfrom) #from the newdata directory
        
        #select only dicom files
        files    = []  
        filesprm = []
        
        for file in files1:
            
            if os.path.isfile(Path(pathfrom,file)) and 'RTDIR.dir' in file:
                
                os.remove(Path(pathfrom,file))
            
            if  os.path.isfile(Path(pathfrom,file)) and (pydicom.misc.is_dicom(Path(pathfrom,file)) or 'CT' in file.split('.')[0]):
                
                if 'CT' in file.split('.')[0] and file.split('.')[-1]=='dir':
                    
                    os.remove(Path(pathfrom,file))
                    
                else:
                    
                    files.append(file)
                
            if  os.path.isfile(Path(pathfrom,file)) and file.split('.')[-1]=='prm':    #file=files1[12]
                filesprm.append(file)
        
        print('found x dicom files', len(files) )
        print('found x prm files', len(filesprm) )
         
        #if found file
        if len(files)+len(filesprm)!=0: #start streaming
            
            #received new dicom files
            
            #get time stamp
            timestampStr = datetime.now().strftime("%d%b%Y")
            timestampStr2 = datetime.now().strftime("%d%b%Y_%H%M%S")
            
            #if received new files since last check update number of file received so far in this stream
            if len(files) + len(filesprm) > nfilesOLD :
                #receiving new files
                stepsAnalysis=1
                nfilesOLD=len(files)+len(filesprm)
            
            #if not receiving new files anymore, waiting to see if more will arrive
            if len(files) +len(filesprm) == nfilesOLD :
    
                stepsAnalysis=stepsAnalysis+1
                
                
            a=1
            #if no more files coming for ncycles_toanalysis steps, lets lets transfer and analyze
            if stepsAnalysis==ncycles_toanalysis :
                
                print('starting transfer')
                
                #reset our flags
                nfilesOLD=0
                stepsAnalysis==0
    
                #check if more than one stream was received (perhaps two people exporting at the same time)
                FilePatientid={}
                
                for file in files:
                    
                    if 'CT' in file.split('.')[0] and not file.split('.')[-1]=='dcm' and not file.split('.')[-1]=='dir':

                        patientid = 'cat_' + pydicom.dcmread(Path(pathfrom,file),force=True).StationName
                    
                    else:

                         patientid = pydicom.dcmread(Path(pathfrom,file)).PatientID

    
                    if patientid in FilePatientid.keys(): 
                    
                        FilePatientid[patientid].append(file)
                    
                    else: #new patient id, create list ehn append
                        
                        FilePatientid[patientid]=[]
                        FilePatientid[patientid].append(file)
                        
                for file in filesprm:
                    
                    patientid = file.split('_')[0] + 'prof' #u23
    
                    if patientid in FilePatientid.keys(): 
                    
                        FilePatientid[patientid].append(file)
                    
                    else: #new patient id, create list ehn append
                        
                        FilePatientid[patientid]=[]
                        FilePatientid[patientid].append(file)
                  
             
                for patientid in FilePatientid.keys():
                    
                    patientid_filter1 = patientid[0:min(20,len(patientid))]
                    patientid_filter2 = "".join(x for x in patientid_filter1 if x.isalnum() or x=='_' or x ==' ') 
                    #create directory if not already done
                    if 'mlc' in patientid.lower() or 'iso' in patientid.lower() or 'prof' in patientid.lower() or 'cat' in patientid.lower():            
                 
                        copyfileDir =  Path(pathtoQA,patientid_filter2 + '_' + timestampStr2)  
                   
                    else:
                            
                        copyfileDir =  Path(pathtoOTHER,patientid_filter2 + '_' + timestampStr2  )  
                       
                        
                    os.makedirs(copyfileDir, exist_ok=True)
    
    
                    #transfer all files
                    for file in FilePatientid[patientid]:
                        
                                 #copy file name
                                 copyfileName =  Path(copyfileDir,file)
                          
                                 #add dicom extension if needed
                                 if file.split('.')[-1] != 'dcm' and file.split('.')[-1] != 'prm':
                          
                                     copyfileName =  Path(copyfileDir,file+'.dcm'    )         
                                      
                                 print('transfer file',  copyfileName)
                                 shutil.move(Path(pathfrom,file), copyfileName)
                                 
                    #add a flag to perform analysis on this folder
                    if 'mlc' in patientid.lower() or 'iso' in patientid.lower() or 'prof' in patientid.lower() or 'cat' in patientid.lower():    
                        
                        with open(Path(pathtoAnalysis,patientid_filter2 + '_' + timestampStr2), 'w') as f:
                            f.write(patientid_filter2 + '_' + timestampStr2)
                            
                        print('flag for analyzing ',copyfileDir )
                    
    time.sleep(sleeping)
    steps=steps+1    
            
            
    print('completed steps--------------------------------------',steps)    
