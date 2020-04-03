# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 14:12:56 2020

@author: JBriggs
"""

import pyodbc as db
import pandas as pd
from math import ceil

#100-#499 useful for integers
#500-#999 useful for values with four decimal precision


#pallets 2, stations 3


# using G54.1 - G54.8 to cover both pallets. G54.1 and G54.5 will be center of table
# for pallet 1 and pallet 2 respectively
# G54.1 will be center of station 2, pallet 1
# G54.5 will be center of station 2, pallet 2

machines = { 'Bruce':{'s1p1':[-16.359,-7.875],'s2p1':[-10.816,-7.877],'s3p1':[-5.340,-7.864],
                      's1p2':[-16.347,-7.875],'s2p2':[-10.841,-7.875],'s3p2':[-5.338,-7.875],
                      'table_z':5.527},
            'Chuck':{'s1p1':[-16.34,-7.87],'s2p1':[-10.837,-7.872],'s3p1':[-5.33,-7.86],
                     's1p2':[-16.339,-7.87],'s2p2':[-10.842,-7.875],'s3p2':[-5.342,-7.872],
                     'table_z':5.459},
            'VanDamme':{ 's1p1':[-16.314,-7.873],'s2p1':[-10.827,-7.871], 's3p1':[-5.324,-7.8595],
                         's1p2':[-16.326,-7.865],'s2p2':[-10.833,-7.866], 's3p2':[-5.339,-7.870],
                        'table_z':6.459},
            'LittleBro':{'s2p1':[0,0],'s1p1':[0,0],'s3p1':[0,0]}}
path = ''
backleft = path + 'glass_probe_backleft_template.txt'
backright = path + 'glass_probe_backright_template.txt'
frontleft = path + 'glass_probe_frontleft_template.txt'
frontright = path + 'glass_probe_frontright_template.txt'
center = path + 'center'

direction = {'Back Left':[-1,1,backleft],
                        'Back Right':[1,1,backright],
                        'Front Left':[-1,-1,frontleft],
                        'Front Right':[1,-1,frontright],
                        'Center':[0,0,center]}

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)    
    return new.join(li)

        
def whichPallet(pallet1, pallet2):
    if pallet1 and pallet2:
        return ['1','2']
    elif pallet1:
        return ['1']
    elif pallet2:
        return ['2']
    else:
        return ['None']
    
def create_strike_probe(selections):
    # get and set length, width, diameter for the job
    length, width, diameter, glass_thick, cust_name, cust_part_num = getPartData(selections)
    
    # data imported as strings, need to be floats
    length = float(length)
    width = float(width)
    diameter = float(diameter)
    glass_thick = float(glass_thick)
    
    # there are some data where width is longest dimension, need to swap
    if width > length:
        length, width = width, length
            
    # initialize vars
    
    offset_x = 1.75
    offset_y = 0
    jobnum = selections[0]
    machine = selections[1]
    pallets = selections[2]
    # pallet1 and pallet2 are boolean
    pallet1 = pallets[0]
    pallet2 = pallets[1]
    stations = selections[3]
    orientation = selections[4]
    probe_corner = selections[5]
    skew_check = [selections[7],orientation]
    s_or_p = selections[8]
    man_x = selections[6][0]
    man_y = selections[6][1]
    pallet = '1'
    # which pallet(s) are we striking/probing?
    pallet = whichPallet(pallet1,pallet2)
    
    if orientation == 'Vertical':
        # longest dimension is in Y, so variable length goes along Y
        X_dim = width
        Y_dim = length
    elif orientation == 'Horizontal':
        # longest dimension is in X, so variable length goes along X
        X_dim = length
        Y_dim = width
        
    if probe_corner != 'Center':
        mod_X_dim, mod_Y_dim, probepath = setGlassCorner(X_dim, Y_dim, probe_corner)        
    else:
        print('this is unique')
        mod_X_dim, mod_Y_dim = 0,0
        offset_x = [0.75, -0.75]
        offset_y = [0.75, -0.75]    
    
    for palnum in pallet:        
        if s_or_p == 'Striking':
            createPalletStrike(cust_name, cust_part_num, jobnum, palnum, stations, machine, X_dim, Y_dim, offset_x, offset_y, orientation)
            
        elif s_or_p == 'Probing':
            offset_x, offset_y = modifyOffsets(probe_corner)
            createPalletProbe(cust_name, cust_part_num, jobnum, palnum, stations, machine, mod_X_dim, mod_Y_dim, offset_x, offset_y,probepath, man_x, man_y, glass_thick,skew_check)
    #return 'Success'    
    
        
def createPalletStrike(cust_name, cust_part_num, jobnum, pallet_number, stations, machine, X_dim, Y_dim, offset_x, offset_y, orientation):
    
    created = ''
    striking = ''    
    if all(station == False for station in stations):
        # no stations selected.
        print('no stations selected')
        # return 'No station selected.'
    else:
        created = [created + stationStrike(machine, pallet_number, station_number, X_dim, Y_dim, offset_x, offset_y, orientation) for station_number, station in enumerate(stations) if station]
        strike_prog_name = str(jobnum) + '_pallet_' + str(pallet_number) + '_strike.nc'
    
    for each in created:
        striking += each
    
    striking = rreplace(striking, 'G100 T98\nM03 S12000\nM8\n', '', striking.count('G100 T98\nM03 S12000\nM8\n') -1)
    # add probe code in beginning.
    half_X_dim = X_dim/2
    half_Y_dim = Y_dim/2
    striking = addStrikeProbing(half_X_dim, half_Y_dim, machine, pallet_number, stations, orientation) + '\nM404\n' + striking + '\nM30\n'
    striking = '(' + cust_name.upper() + ' ' + cust_part_num.upper() + ' STRIKING)\n' + striking
    with open(strike_prog_name,'w') as file:
        file.write(striking)
        

def stationStrike(machine, pallet_number, station_number, X_dim, Y_dim, offset_x, offset_y, orientation):
    # here i need to know WCS, station #, x offset and y offset.
    # x and y are determined by station #, part length and width, and orientation
    station_number += 1    
    # wcs_string creates something like s1p1 which will pull data from dictionary at top of this file
    wcs_string = 's' + str(station_number) + 'p' + (pallet_number)
    # wcs gives center point of selected station and pallet based on which machine it is for
    wcs = machines[machine][wcs_string]
    # X and Y are adjustments to WCS center point to use as start for striking tool    
    if orientation == 'Horizontal':
        path_len = X_dim + 3.5
        num_passes = ceil(Y_dim/2.95)
    else:
        # the modifications below are useful in changing striking direction
        offset_x = 0
        offset_y = 1.75
        path_len = -1*(Y_dim + 3.5)
        num_passes = ceil(X_dim/2.95)
    #X should be negative as an adjustment to WCS. Statement valid for striking only
    X = (-1*X_dim/2) - offset_x
    #Y should be positive as an adjustment to WCS. Statement valid for striking only
    Y = (Y_dim/2) + offset_y        
    
    # wcs_modified is ready to be used as X,Y to get base code
    wcs_modified = [round(wcs[0]+X,3),round(wcs[1]+Y,3)]    
    # changes station number based on pallet, only for use in NC file
    if pallet_number == '2':
        station_number += 3
    #below code returns the code to strike a single station      
    code = modifyStrikeBase(num_passes, path_len, station_number, wcs_modified[0], wcs_modified[1], orientation)    
    return code

def modifyStrikeBase(num_passes, path_len, station_number, X, Y, orientation):
    
    if orientation == 'Horizontal':
        with open('strike_one_horizontal.txt', 'r') as file:
            code = file.read()        
    elif orientation == 'Vertical':
        with open('strike_one_vertical.txt', 'r') as file:
            code = file.read()        
        
    m_code = code
    
    #insert #100 = num_passes after (TRACK PASSES)
    passes = '#100 = ' + str(num_passes)
    # insert #501 = xpath after (SET X PATH LENGTH)
    path_len = '#501 = ' +  str(path_len)
    #insert G10L20PnXY
    wcs = 'G10L20P#104 X' + str(X) + 'Y' + str(Y)    
    m_code = m_code.replace('(WCS LINE)', wcs)
    # insert station number
    station_number_text = '#104 = 1' + str(station_number)
    m_code = m_code.replace('#104 = 10', station_number_text)
    # insert num y passes
    m_code = m_code.replace('#100 = 0', passes)
    # insert x path 
    m_code = m_code.replace('#501 = 0', path_len)
    
    return m_code

def addStrikeProbing(X_dim, Y_dim, machine, pallet_number, stations, orientation):       
        
    s_list = [station_number for station_number, station in enumerate(stations, start=1) if station]
    # machine and station # determines which WCS to use. Only need to probe first station in list
    first_pallet_station = 's' + str(s_list[0]) + 'p' + pallet_number    
    # set probe_x and probe_y. These will be using G53 for accurate positioning. 
    
    # #529, #530, #531 in NC
    vac_x = round(machines[machine][first_pallet_station][0],3)
    vac_y = round(machines[machine][first_pallet_station][1],3)    
    vac_z = round(machines[machine]['table_z'],3)
    
    #521 in NC
    probe_x = round(vac_x - X_dim,3)
    #522 in NC
    probe_y = round(vac_y + Y_dim,3)
    
    # station number between 1-6, can use for #103 and #104
    stnum_1to6 = s_list[0] + (3*(int(pallet_number)-1))   
    # loading modified data into a list for simpler data transfer
    # into modifier function
    xy_data = [vac_x,vac_y,vac_z,probe_x,probe_y,stnum_1to6]
    # orientation determines which side to approach fixture from
    # this should ensure to find rubber every time, regardless
    # of fixture shape
    # y_template and x_template are nearly identical
    # with the exception of travel direction and z probe
    # position assignment
    if orientation == 'Horizontal':        
        with open('strikeprobe_y_template.txt', 'r') as file1:
            templatexy = file1.read()
    else:
        with open('strikeprobe_x_template.txt', 'r') as file1:
            templatexy = file1.read()
    # strikeprobe_xy only needs to be called once for a given
    # fixture setup. All fixtures on the same setup
    # should be identical 
    strikeprobe_xy = modify_xy_code(templatexy,xy_data)
    # initialize strikeprobe_z as it needs to handle a variable
    # number of stations
    strikeprobe_z = ''
    # for each station in the setup, probe the z height of the rubber
    for s in s_list:
        strikeprobe_z = strikeprobe_z + modify_z_code(s)
    # need to put all the code together and add M30 to end it
    
    strikeprobe_code = strikeprobe_xy + strikeprobe_z

    return strikeprobe_code

def modify_xy_code(templatexy,xy_data):
    #xy_data[0-2] are vac x,y,z xy_data[3-4] is probe x,y xy_data[5] is station number
    # set station number for vacuum
    strikeprobe_xy = templatexy.replace('#103 = 20', '#103 = 2' + str(xy_data[5]))
    # set station number for fixture
    strikeprobe_xy = strikeprobe_xy.replace('#104 = 10', '#104 = 1' + str(xy_data[5]))
    # set vacuum wcs x 
    strikeprobe_xy = strikeprobe_xy.replace('#529 = 0', '#529 = ' + str(xy_data[0]))
    # set vacuum wcs y
    strikeprobe_xy = strikeprobe_xy.replace('#530 = 0', '#530 = ' + str(xy_data[1]))
    # set vacuum wcs z 
    strikeprobe_xy = strikeprobe_xy.replace('#531 = 0', '#531 = ' + str(xy_data[2]))
    # set probe x point. the 0.125 offset helps avoid hitting fixture prematurely
    strikeprobe_xy = strikeprobe_xy.replace('#521 = 0', '#521 = ' + str(xy_data[3]-0.125))
    # set probe y point. the 0.125 offset helps avoid hitting fixture prematurely
    strikeprobe_xy = strikeprobe_xy.replace('#522 = 0', '#522 = ' + str(xy_data[4]+0.125))    
    
    return strikeprobe_xy        

def modify_z_code(s):
    # the only modification to the z template is the station number entry. 
    # the rest of the data needed is obtained and set by the xy template
    # and stored in the machine at runtime
    with open('strikeprobe_z_template.txt', 'r') as file:
        template_z = file.read()
        
    strikeprobe_z = template_z.replace("#104 = 10", "#104 = 1" + str(s))
    return strikeprobe_z


    
def createPalletProbe(cust_name, cust_part_num, jobnum, palnum, stations, machine, mod_X_dim, mod_Y_dim, offset_x, offset_y,probepath, man_x, man_y, glass_thick,skew_check):      
    probing_program = ''
    probe_list = [createStationProbe(palnum, station_number, machine, mod_X_dim, mod_Y_dim, offset_x, offset_y,probepath, man_x, man_y, glass_thick,skew_check) for station_number,station in enumerate(stations, start=1) if station]
    for partial in probe_list:
        probing_program = probing_program + partial
    probing_program = '(' + cust_name.upper() + ' ' + cust_part_num.upper() + ' PROBING)\n'+ 'G100 T99\nM404\n' + probing_program + '\nM404\nM30\n'
    saveProbingProgram(jobnum, palnum, probing_program)
    
def createStationProbe(pallet_number, station_number, machine, mod_X_dim, mod_Y_dim, offset_x, offset_y,probepath, man_x, man_y, glass_thick,skew_check):
    sp = 's' + str(station_number) + 'p' + str(pallet_number)
    st_num = station_number + (int(pallet_number)-1)*3
    wcs = machines[machine][sp]
    wcs.append(machines[machine]['table_z'])
    # set glasscorner to store theoretical glass corner coordinates
    glasscorner = []    
    glasscorner.append(round(wcs[0] + mod_X_dim,3))
    glasscorner.append(round(wcs[1] + mod_Y_dim,3))
    
    if man_x == '':
        man_x = '0'
    if man_y == '':
        man_y = '0'
    x_start = round(glasscorner[0] + offset_x,3)
    y_start = round(glasscorner[1] + offset_y,3)
    
    rubber_height_var = str(7003 + ((st_num+9)*20))
    glass_thick = glass_thick / 25.4
    half_glass_thick = round(glass_thick / 2.0,3)
    
    with open(probepath,'r') as file:
        template = file.read()
    
    # set station number for vacuum
    template = template.replace("#103 = 20", "#103 = 2" + str(st_num))
    # set station number for glass
    template = template.replace("#109 = 0", "#109 = " + str(st_num))
    # set station vacuum wcs x
    template = template.replace("#529 = 0", "#529 = " + str(wcs[0]))
    # set station vacuum wcs y
    template = template.replace("#530 = 0", "#530 = " + str(wcs[1]))
    # set station vacuum wcx z
    template = template.replace("#531 = 0", "#531 = " + str(wcs[2]))
    # set manual entry x offset
    template = template.replace("#642 = 0", "#642 = " + man_x)
    # set manual entry y offset
    template = template.replace("#643 = 0", "#643 = " + man_y)
    # set theoretical glass corner x
    template = template.replace("#621 = 0", "#621 = " + str(glasscorner[0]))
    # set theoretical glass corner y
    template = template.replace("#622 = 0", "#622 = " + str(glasscorner[1]))
    # set probe x start point for probing x
    template = template.replace("#637 = 0", "#637 = " + str(x_start))
    # set probe x start point for probing x
    template = template.replace("#638 = 0", "#638 = " + str(y_start))
    
    # set minimum probe Z limit for glass top, height of fixture
    template = template.replace("#625 = #0", "#625 = #" + rubber_height_var)
    # set half glass thickness
    template = template.replace("#644 = 0","#644 = " + str(half_glass_thick))
    
    if skew_check[0]:
        skew_file = path + skew_check[1].lower() + '_skew_template.txt'
        with open(skew_file,'r') as file2:
            template = template + file2.read()
        
    return template
    
def modifyOffsets(probe_corner):
    
    offset_direction = [direction[probe_corner][0]*0.75,direction[probe_corner][1]*0.75]               
    return offset_direction[0],offset_direction[1]

def setGlassCorner(X_dim, Y_dim, probe_corner):
    mod_X_dim = X_dim * direction[probe_corner][0] / 2
    mod_Y_dim = Y_dim * direction[probe_corner][1] / 2
    probepath = direction[probe_corner][2]
    return mod_X_dim, mod_Y_dim, probepath

def saveProbingProgram(job_number, pallet_number, probing_program):
    prog_name = str(job_number) + '_pallet_' + str(pallet_number) + '_probe.nc'
    with open(prog_name,'w') as file:
        file.write(probing_program)
    
def getPartData(selections):
    if selections[0] == 'None':
        return '0','0','0'
    
    # this procedure is used to obtain blank size for parts
    jobnum = "'" + selections[0].upper() + "' "   
    
    
    # read sql database login info from file 
    with open('sql_access.txt', 'r') as file:
        access = file.readlines()    

    # create db connection
    conn = db.connect('Driver={SQL Server};'
                      'Server=SVR-APP\\SQLEXPRESS;'
                      + access[0] +
                      'Trusted_Connect=yes;')
    
    # query db for blank length, width, diameter and store in "data" dataframe
    data = pd.read_sql_query("SELECT Jobs.IdealBlankLength1, Jobs.IdealBlankWidth1, "
                             "Jobs.PartSizeDiameterMid, Jobs.MaterialThickness "
                             "FROM QssCatiJobTrack.dbo.Jobs "
                             "WHERE Jobs.JobNum = " + jobnum, conn)
    
    # query db for customer name, customer part #
    cust_data = pd.read_sql_query("SELECT Parts.CustName, Parts.CustPartNum "
                                  "FROM QssCatiJobTrack.dbo.Parts, QssCatiJobTrack.dbo.Jobs " 
                                  "WHERE Parts.PartID = Jobs.PartID "
                                  "AND Jobs.JobNum = " + jobnum, conn)
    
    
    conn.close()
    
    # return length, width, diameterMid, customer name, customer part number as strings
    return data.iloc[0][0], data.iloc[0][1], data.iloc[0][2], data.iloc[0][3], cust_data.iloc[0][0], cust_data.iloc[0][1]


if __name__ == "__main__":    
    print("banana")