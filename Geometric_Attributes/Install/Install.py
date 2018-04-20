#==================================
#Author Bjorn Burr Nyberg 
#University of Bergen
#Contact bjorn.nyberg@uib.no
#Copyright 2016
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

##ArcGIS 10.4>

import os,sys,subprocess,pip

dirname = os.path.split(os.path.dirname(sys.executable))
folder = dirname[1].replace('x64','')

python_exe = os.path.join(dirname[0],folder,'python.exe')

modules = ['pip','scipy','pandas','networkx==1.8','xlsxwriter']

for module in modules:
    try:
        subprocess.check_call([python_exe,'-m', 'pip', 'install','--upgrade', module])
    except Exception,e:
        print e
        continue
     
def main(python_exe):

    try:
        python_exe = sys.executable.replace('w','')
        for module in modules:
            try:
                subprocess.check_call([python_exe,'-m', 'pip', 'install','--upgrade', module])
            except Exception,e:
                print e
                continue

        print 'Finished'
    except Exception,e:
        print e
        
if __name__ == "__main__":

    
    main(sys.executable)

