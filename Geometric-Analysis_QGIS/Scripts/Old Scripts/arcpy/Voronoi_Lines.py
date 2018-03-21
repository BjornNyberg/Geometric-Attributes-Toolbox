#==================================
#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uni.no
#Copyright 2013
#Modified from http://ceg-sense.ncl.ac.uk/geoanorak/code/pythontransects.html
#==================================

'''This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.'''
#==================================

import arcpy,os
import multiprocessing,shutil
from progressbar import ProgressBar,Bar,ETA,Percentage
arcpy.env.overwriteOutput= True

def main(inShp,pools,TempFolder,Output):
    try:

        if not os.path.exists(TempFolder):
            os.mkdir(TempFolder)
        Count = int(arcpy.GetCount_management(inFC).getOutput(0))
        widgets = ['Processing %s Features'%(Count),Percentage(),Bar(),ETA()]
        pbar = ProgressBar(widgets=widgets,maxval=Count).start()

        ## ***Multiprocessing***
        temp = os.path.join(TempFolder,'temp.lyr')
        pool = multiprocessing.Pool(pools)
            
        Out_Files =[]
        jobs = []

        arcpy.CalculateField_management(inFC, 'ID', "!FID!", "PYTHON_9.3", "")
        
        for n in xrange(Count):
            arcpy.MakeFeatureLayer_management(inFC, temp)          
            arcpy.SelectLayerByAttribute_management(temp, "NEW_SELECTION", '"FID" = %s'%(n))  
            TempOut = os.path.join(TempFolder,'temp_%s.shp'%(n))   
            arcpy.CopyFeatures_management(temp,TempOut)
            name = os.path.basename(TempOut)[:-4]
            Temp = os.path.join(TempFolder,name)
            if not os.path.exists(Temp):
                os.mkdir(Temp)
            jobs.append(pool.apply_async(execute,(TempOut,Temp,n)))
        for enum,job in enumerate(jobs):
            Value = job.get()
            if isinstance(Value[1],int):
                desc = arcpy.Describe(Value[0])
                if desc.shapeType == "Polyline": ##Check to make sure its a polyline
                    Out_Files.append(Value[0])
                widgets[0] = '%s of %s Features Complete'%(enum,Count)
                pbar.update(enum)
            else: 
                widgets[0] = '%s of %s Features Complete'%(enum,Count)
                pbar.update(enum)
        pool.close()       
        arcpy.Merge_management(Out_Files,Output)
        pbar.finish()
 
    except Exception, e:
        print 'Main Error:',e
    finally:
        try:
            shutil.rmtree(TempFolder)
        except Exception,e:
            pass

def execute(inFC,TempFolder,Counter):
    try:
        arcpy.env.scratchWorkspace = TempFolder
        arcpy.env.workspace = TempFolder
     
        #Variables
        temp = os.path.join(TempFolder,'temp.shp')
        temp2 = os.path.join(TempFolder,'temp2.shp')
        temp3 = os.path.join(TempFolder,'temp3.shp')
        
        arcpy.FeatureVerticesToPoints_management(inFC, temp, "ALL")

        arcpy.CreateThiessenPolygons_analysis(temp, temp2, "ONLY_FID")
 
        arcpy.Intersect_analysis([temp2, inFC], temp, "")
   
        arcpy.PolygonToLine_management(temp, temp2)

        arcpy.PolygonToLine_management(inFC, temp)

        arcpy.SymDiff_analysis(temp2, temp, temp3, "ALL", "")
        fieldNames = []
        for field in arcpy.ListFields(temp3):
            if not field.required:
                fieldNames.append(field.name)
        arcpy.AddField_management(temp3,"ID",'LONG')  
        arcpy.CalculateField_management(temp3,"ID","%s"%(Counter))    
        arcpy.DeleteField_management(temp3,fieldNames)

    except Exception,e:
        return (1,e)
    return (temp3,1)


if __name__ == "__main__":        
    ###Inputs###
    inFC = r'G:\SampleDatasets\Congo_Bars.shp'
    Pools = 1
    TempFolder = r'G:\SampleDatasets\test'
    Output = r'G:\temp3\temp\VL.shp'

    main(inFC,Pools,TempFolder,Output)
