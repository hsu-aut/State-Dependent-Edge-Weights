from openpyxl import load_workbook
import os
import mysql.connector
from time import sleep
import pandas as pd
import opcua
from opcua import Server, ua, uamethod, Client
from opcua.server.user_manager import UserManager
import socket

class MySqlTable:
   def __init__(self, TableName, TableList, MysqlDatabase):
      self.TableName = TableName
      self.ColNames = TableList
      self.ArchiveName = "historical_sequence"
      self.DB = MysqlDatabase
      self.cursor = MysqlDatabase.cursor()

   def init_table(self):
      query = "CREATE TABLE IF NOT EXISTS " + self.TableName +"("
      num_cols = 0
      for name in self.ColNames:
         query+=name+" INT NOT NULL,"
         num_cols += 1
      query = query[:-1]+");"
      self.num_cols = num_cols
      self.cursor.execute(query)

   def archive_table(self):
      counter = 0
      while True:
         try:
            cursor.execute("SELECT if(EXISTS(table hist_sequ"+ counter +"),1,0) AS result;")
         except:
            self.cursor.execute("RENAME TABLE "+self.TableName+" TO "+self.ArchiveName)
            self.init_table
            break
         else:
            counter+=1

   def append_values(self, values):
      #lenCN = self.ColNames
      try:
         if True:#len(values) == self.num_cols:
            query = "INSERT INTO " + self.TableName + "("# xmv1 = CONCAT('145000');"
            for name in self.ColNames:
               query += name + ", "
            query = query[:-2] + ") VALUES ("
            for value in values:
               query += str(value) + ", "
         print(query[:-2] + ")")
         self.cursor.execute(query[:-2] + ")")
         print("Append Success")
         self.DB.commit()
      except Exception as e:
         print("Append Failed with error message:", e)
         self.DB.rollback()
         

def createNameList(inputList,indices):
   counter = 0
   outList = ['']*len(inputList)
   for name in inputList:
      for i in indices:
         if outList[counter] == None:
            outList[counter]+=name[i]
         else:
            outList[counter]+=name[i]
      counter+=1
   return outList  

def initialize_table(tableName, columnNameList, mysqlcursor):
   query = "CREATE TABLE IF NOT EXISTS " + tableName +"("
   for name in columnNameList:
      query+=name+" INT NOT NULL,"
   query = query[:-1]+");"
   #query+=");"#"PRIMARY KEY());"
   mysqlcursor.execute(query)

class MyOPCUAClient:
   def __init__(self,ClientAdress) -> None:
      self.client = Client(ClientAdress)
      self.client.connect()
      self.client.get_namespace_array()
      self.objects = self.client.get_objects_node()
      self.simTimeNode = self.client.get_node('ns=2;s=SIMULINK_Time')
      self.simHaultNode = self.client.get_node('ns=2;s=SIMULINK_Halt')
      #self.currentvalues = []
      self.nodes = []

   def getnodes(self, namespace, namelist):
      self.namelist = namelist
      self.namespace = namespace
      #self.nodes = len(namelist)*[None]
      #self.currentValues = len(namelist)*[None]
      counter = 0
      #self.nodes = [:len(self.namelist)]
      for name in self.namelist:
         #try:
            tempnode = self.client.get_node(f'ns={namespace};s={name}')
            #self.nodes[counter]=tempnode
            self.nodes.append(tempnode)
            print(name)
            counter+=1
         #except:
            #pass
      self.currentValues = len(namelist)*[0]
      

   def getcurrentvalues(self):
      tempValues = []
      counter = 0
      for node in self.nodes:
         try:
            #self.currentValues[counter] = node.get_value()
            #print(node.get_value())
            tempValues.append(node.get_value())
            #print("Value= "+str(self.currentValues[counter]))
         except:
            #self.currentValues[counter] = 0
            #print("Value= "+str(self.currentValues[counter]))
            tempValues.append(0)
         counter+=1
      self.currentValues = tempValues
      #print(tempValues)
      #for value in self.currentValues:
         #print(value)


######################### MAIN #########################
if __name__ == "__main__":
   wb = load_workbook(filename='D:\AutoML_Data\TEP_Designations.xlsx')
   ws = wb.active
   counter = 0
   d = {}
   for row in list(ws.rows)[1:]:
      if str(row[1].value) != 'None' and str(row[2].value) != 'None':
         d[row[0].value] = [str(c.value) for c in row[1:]]
         #print(d[row[0].value])
         counter+=1
   dList = createNameList(list(d.values()),[0,1,4])


   ######################### MySQL #########################

   mydb = mysql.connector.connect(
   host="localhost",
   user="TEP_User",
   password=os.environ.get("TEP_DB_PASSWORD", ""),
   database="tep_datahistorian"
   )
   cursor = mydb.cursor(buffered=True)


   #print(list(range(1,31)))

   initialize_table('manipulated_variables', dList, cursor)

   cursor.execute("update manipulated_variables set FIR100_Flow = 100")


   mysqltable = MySqlTable('manipulated_variables', dList, mydb)
   mysqltable.init_table()
   #for i in range (0,100):
   #   j=i*30
   #   mysqltable.append_values(list(range(1+j,31+j)))
   #mysqltable.archive_table()



######################### OPCUA #########################
   hostname=socket.gethostname()   
   IPAddr=socket.gethostbyname(hostname)  
   myopcua = MyOPCUAClient(f"opc.tcp://{IPAddr}:4840")
   myopcua.getnodes(2,dList)
   #print(myopcua.namelist)
   #my_client = Client("opc.tcp://192.168.179.27:4840")
   #my_client.connect()
   #my_client.get_namespace_array()
   #objects = my_client.get_objects_node()
   #
   #var1_node = my_client.get_node("ns=2;s=TIR100_Temperature")
   #
   #var1_value = var1_node.get_value()
   #print(var1_value)


   #for t in range (0,1000):
   #   myopcua.getcurrentvalues()
   #   mysqltable.append_values(myopcua.currentvalues)
   #   sleep(1)

   myopcua.simHaultNode.set_value(False)
   CurrentSimTime = 0.0

   while True:
      
      if CurrentSimTime< myopcua.simTimeNode.get_value():
         myopcua.getcurrentvalues()
         mysqltable.append_values(myopcua.currentValues)
         myopcua.simHaultNode.set_value(True)
         CurrentSimTime = myopcua.simTimeNode.get_value()
         sleep(0.001)
         myopcua.simHaultNode.set_value(False)
      if CurrentSimTime>=4.0:
         break

   myopcua.simHaultNode.set_value(False)
   exit()