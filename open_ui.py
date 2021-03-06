# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 08:49:27 2020

@author: JBriggs
"""

import sys
import generator
import pyodbc
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets, uic



class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        path = "G://3 - Production Departments//4 - Grinding//0 - Department Documents//4 - Programs & Software//1 - Operating Software//striker_gen//"
        uic.loadUi(path + "Probe_UI.ui", self)        
        self.pallet_1_checkbox.setChecked(True)
        self.pallet_2_checkbox.setChecked(True)
        self.x_offset_entry_box.setText("0.0")
        self.y_offset_entry_box.setText("0.0")     
        self.blank_length_entry_box.setText("0.0")
        self.blank_width_entry_box.setText("0.0")
        self.striking_pushbutton.clicked.connect(self.createStriking)        
        self.probing_pushbutton.clicked.connect(self.createProbing)        
    
    def getSelections(self):
        job = self.getJob()        
        machine = self.getMachine()
        pallets = self.getPallets()
        stations = self.getStations()
        orientation = self.getFixtureOrientation()
        probepoint = self.getProbePoint()
        xy_offsets = self.getProbeXYOffset()
        skew_check = self.getSkewCheck()
        length, width = self.getBlankSize()
        data_list = [job, machine, pallets, stations, orientation, probepoint,xy_offsets,skew_check,length,width]
        return data_list
    
    def getJob(self):
        # retrieve value in job_number_entry_box
        job = str(self.job_number_entry_box.toPlainText())
        #job_number_entry_box is a QTextEdit Widget
        if not self.checkJob(job):
            failed = ['getJob',job, 'None', 'None']
            self.showDialog(failed)
            return 'None'
        return job        
    
    def getMachine(self):
        # retrieve value in machine_select_combobox
        machine = str(self.machine_select_combobox.currentText())
        return machine
    
    def getPallets(self):
        # retrieve which pallet(s) to generate data for
        pallet1 = self.pallet_1_checkbox.isChecked()
        pallet2 = self.pallet_2_checkbox.isChecked()
        return [pallet1,pallet2]
    
    def getStations(self):
        # retrieve which station(s) to generate data for
        station1 = self.station_1_checkbox.isChecked()
        station2 = self.station_2_checkbox.isChecked()
        station3 = self.station_3_checkbox.isChecked()
        return [station1,station2,station3]
    
    def getFixtureOrientation(self):
        # retrieve fixture orientation
        orientation = str(self.orientation_combobox.currentText())
        return orientation
    
    def getProbePoint(self):
        # retrieve which corner or center to probe
        probepoint = str(self.wcs_select_combobox.currentText())
        return probepoint
    
    def getProbeXYOffset(self):
        #retrieve manual x and y offset for probe point
        probe_x_offset = str(self.x_offset_entry_box.toPlainText())
        probe_y_offset = str(self.y_offset_entry_box.toPlainText())     
        
        return [probe_x_offset, probe_y_offset]
    
    def getSkewCheck(self):
        # retrieve checkbox value of skew checkbox
        skew_check = self.skew_check_box.isChecked()
        return skew_check
    
    def getBlankSize(self):
        # retrieve entered blank size
        length = float(self.blank_length_entry_box.toPlainText())
        width = float(self.blank_width_entry_box.toPlainText())
        return length, width
    
    def createStriking(self):
        # action to take when Create Striking button is pressed
        selections = self.getSelections()
        selections.append("Striking")
        
        report = ['createStriking']
        for e in selections:
            report.append(e)
        
        report = self.checkBlankSize(report)
        
        if report[1] != 'None':
            self.showDialog(report)
            generator.create_strike_probe(selections)
        pass
    
    def createProbing(self):
        # action to take when Create Probing button is pressed
        selections = self.getSelections()
        selections.append("Probing")
        
        report = ['createProbing']
        for e in selections:
            report.append(e)
            
        report = self.checkBlankSize(report)
        
        if report[1] != 'None':
            self.showDialog(report)
            generator.create_strike_probe(selections)
            self.reset_defaults()
        pass
    
    def checkJob(self, jobnum):
        jobnum = "'" + jobnum.upper() + "'"
        path = "G://3 - Production Departments//4 - Grinding//0 - Department Documents//4 - Programs & Software//1 - Operating Software//striker_gen//"
        with open(path + 'sql_access.txt', 'r') as file:
            access = file.readlines()
        
        jobpresent = True #boolean initialization
        count = 0 #counter to determine if we have data from the cursor
        conn = pyodbc.connect('Driver={SQL Server};'
                              'Server=SVR-APP\\SQLEXPRESS;'
                              + access[0] +
                              'Trusted_Connect=yes;') #connection string, connects to DB
        
        cursor = conn.cursor() #creates cursor object
        #the query below 
        cursor.execute("SELECT Jobs.JobNum "
                       "FROM QssCatiJobTrack.dbo.Jobs "
                       "WHERE Jobs.JobNum= " + jobnum + " ") #query matches the jobnumber exactly. Will return nothing if None
    
        for row in cursor:
            count = count +1
        
        if count > 0:
            jobpresent = True
        else:
            jobpresent = False
        cursor.close()
        conn.close()    
        return jobpresent
    
    def checkBlankSize(self, report):
        if report[1] == 'None':
            return report
        jobnum = "'" + report[1].upper() + "'"
        path = "G://3 - Production Departments//4 - Grinding//0 - Department Documents//4 - Programs & Software//1 - Operating Software//striker_gen//"
        with open(path + 'sql_access.txt', 'r') as file:
            access = file.readlines()
            
        length = 0
        width = 0
        diameter = 0
        
        conn = pyodbc.connect('Driver={SQL Server};'
                              'Server=SVR-APP\\SQLEXPRESS;'
                              + access[0] +
                              'Trusted_Connect=yes;')
        cursor = conn.cursor()
        
        data = pd.read_sql_query("SELECT Jobs.PartSizeLengthMid, Jobs.PartSizeWidthMid, "
                                 "Jobs.PartSizeDiameterMid "
                                 "FROM QssCatiJobTrack.dbo.Jobs "
                                 "WHERE Jobs.JobNum = " + jobnum, conn)
        
        conn.close()
        
        length = float(data.iloc[0][0]) + 0.08
        width = float(data.iloc[0][1]) + 0.08
        diameter = float(data.iloc[0][2]) + 0.08
                                                                
        if length == 0.08 or width == 0.08 and diameter > 0.08:
            length, width = diameter, diameter
        
        if length != report[9] or width != report[10]:            
            modified_report = report
            modified_report[0] = report[0] + ' verifyblank'            
        else:
            return report
        
        return modified_report
    
    def showDialog(self,report):
        key = report[0]        
        reports = {'getJob': 'Job # ' + report[1] + ' not found.',
                   'createStriking': 'Striking created for job # ' + report[1] + ' on ' + report[2] + '.',
                   'createStriking verifyblank': 'Striking created for job # ' + report[1] + ' on ' + report[2] + '.\r\n Verify blank size.',
                   'createProbing': 'Probing created for job # ' +report[1] + ' on ' + report[2] + '.',
                   'createProbing verifyblank': 'Probing created for job # ' +report[1] + ' on ' + report[2] + '.\r\n Verify blank size.'}
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText(reports[key])
        msgBox.setWindowTitle("For Your Information")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        
        returnValue = msgBox.exec()
    
    def reset_defaults(self):
        self.x_offset_entry_box.setText("0.0")
        self.y_offset_entry_box.setText("0.0")

if __name__ == '__main__':
    
    app = QtWidgets.QApplication(sys.argv)
    ex = MainWindow()    
    ex.show()    
    sys.exit(app.exec_())

