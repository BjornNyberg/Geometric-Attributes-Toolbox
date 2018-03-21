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

import os

try:
    pip_install = True
    import pip
except Exception:
    dirname = os.path.dirname(os.path.realpath('__file__'))
    fname = os.path.join(dirname,'get-pip.py')
    os.system(fname)
    import pip

def main():
    try:
        pip.main( ["install","networkx"] )
        pip.main( ["install","scipy"] )            
        print '\n Finished'
    except Exception,e:
        print e
        
if __name__ == "__main__":

    main()

