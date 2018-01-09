# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json  
import MySQLdb
import time
import uuid
import datetime
import urllib
import zmq
from django.core.cache import cache

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.connect('tcp://39.106.27.51:12300') #test
#socket.connect('tcp://47.94.92.14:12300') #operative

def http_get(url,reqJson):
	reqJson = json.dumps(reqJson)
	url += reqJson
	#print "HTTP GET: " + url
	print '\033[1;31;40m' + "HTTP GET: " + url + '\033[0m'
	response = urllib.urlopen(url)
	return response.read()

def http_post(url,reqJson):
	reqJson = json.dumps(reqJson)
	url += reqJson
	#print "HTTP POST: " + url
	print '\033[1;31;40m' + "HTTP POST: " + url + '\033[0m'
	response = urllib.urlopen(url,"")
	return response.read()

#CanCheck flag
g_dicCanCheck = {}

def check_stock(vendorId,shopId):
	print "vendorId: " + vendorId + " shopId: " + shopId + " check_stock start..."
	result = {'result':[], 'ErrMsg':''}
	#time.sleep(10)
	global g_dicCanCheck
	key = vendorId + shopId #vendorId + shopId
	reqJson = {}
	reqJson['vendorId'] = vendorId
	reqJson['storeCode'] = shopId
	reqJson['skuInfo'] = ''
	response = http_post("https://erp.1015bar.com/api/exec?m=getSkustockByVenStoreSku&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
	#print "HTTP response: " + response
	#print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	response = json.loads(response)
	#print "HTTP response: " + response['returnMsg']
	print '\033[1;31;40m' + "HTTP response: " + response['returnMsg'] + '\033[0m'
	if response['returnCode'] == 10:
		conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
		sql = "select * from steelyard where steelyardId like '" + shopId + "______' and vendorId = '" + vendorId + "';"
		cur = conn.cursor(MySQLdb.cursors.DictCursor)
		n = cur.execute(sql)
		rows = cur.fetchall()
		dic = {} #shop stock
		for row in rows:
			#custom in, stop check_stock
			if key not in g_dicCanCheck:
				result['ErrMsg'] = 'Broken_check_stock'
				print "vendorId: " + vendorId + " shopId: " + shopId + " custom in, stop check_stock!"
				break
			skuCode = row['skuCode']
			if skuCode == "":
				continue
			#match skuCode
			sql = "select * from sku where (skuCode = '" + skuCode + "' or barcode = '" + skuCode + "') and vendorId = '" + vendorId + "';"
			#print sql
			n = cur.execute(sql)
			if n > 0:
				row0 = cur.fetchall()
				skuCode = row0[0]['skuCode']
			if skuCode in dic:
				dic[skuCode] = dic.get(skuCode) + round(float(row['skuNum'])) #shop stock sum
			else:
				dic[skuCode] = round(float(row['skuNum']))
		#for k in dic:
		#	print k,' ',dic[k]
		#match stock
		if key in g_dicCanCheck:
			print "<skuCode>  <skuNum>  <stock>  [diff]"
			for i in response['returnObject']:
				#time.sleep(5)
				#custom in, stop check_stock
				if key not in g_dicCanCheck:
					result['ErrMsg'] = 'Broken_check_stock'
					print "vendorId: " + vendorId + " shopId: " + shopId + " custom in, stop check_stock!"
					break
				stock = round(float(i['stock']))
				diff = 0.0
				if i['skuCode'] in dic:
					diff = dic[i['skuCode']] - stock
					print "<%s>\t<%d>\t<%d>\t[%d]" % (i['skuCode'], dic[i['skuCode']], stock, diff)
					#print "<" + i['skuCode'] + ">  <" + str(dic[i['skuCode']]) + ">  <" + str(stock) + ">  [" + str(diff) + "]"
					if diff != 0:
                                		res = {}
                                        	res['skuCode'] = i['skuCode']
                                        	res['skuName'] = i['skuName']
                                        	#res['skuNum'] = str(dic[i['skuCode']])
                                        	#res['stock'] = str(stock)
                                        	res['diff'] = str(diff)
                                        	result['result'].append(res)
				else:
					print "<%s>\t<none>\t<%d>\t[none]" % (i['skuCode'], stock)
					#print "<" + i['skuCode'] + ">  <none>  <" + str(stock) + ">  [none]"
		cur.close()
		conn.commit()
		conn.close()
	else:
		result['ErrMsg'] = 'Failed_query_erp'
		print "Failed to query the erp DB!!!"
		print "vendorId: " + vendorId + " shopId: " + shopId + " check_stock error!"
	if result['result'] != []:
		result['ErrMsg'] = 'Error_stock'
	#check_stock end, reset CanCheck flag
	if key in g_dicCanCheck:
		del g_dicCanCheck[key]
	print "vendorId: " + vendorId + " shopId: " + shopId + " check_stock end!"
	return result

def steelyard_get(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	result = {'result':[]}
	mList = req['steelyardIds']
	for i in mList:
		if i == "AllSteelyardId":
			sql = "select * from steelyard where steelyardId like '" + req['shopId'] + "______' and vendorId = '" + req['vendorId'] + "' and isEnable = '1';"
			print sql
			n = cur.execute(sql)
			rows = cur.fetchall()
			for row in rows:
				dic = {} 
				dic['steelyardId'] = row['steelyardId']
				dic['skuCode'] = row['skuCode']
				dic['posX'] = row['posX']
				dic['posY'] = row['posY']
				dic['posZ'] = row['posZ']
				dic['unitWeight'] = "0"
				if row['skuCode'] != "":
					sql = "select * from sku where (skuCode = '" + row['skuCode'] + "' or barcode = '" + row['skuCode'] + "') and vendorId = '" + req['vendorId'] + "';"
					print sql
					n = cur.execute(sql)
					if n > 0:
						row0 = cur.fetchall()
						dic['unitWeight'] = row0[0]['unitWeight']
					else:
						print "Failed to get unitWeight!!!  " + row['steelyardId'] + " " + row['skuCode']
				dic['currWeight'] = row['currWeight']
				dic['offsetWeight'] = row['offsetWeight']
				dic['status'] = row['status']
				result['result'].append(dic)
			break
		sql = "select * from steelyard where steelyardId like '" + i + "' and vendorId = '" + req['vendorId'] + "' and isEnable = '1';"
		print sql
		n = cur.execute(sql)
		if n > 0:
			row = cur.fetchall()
			dic = {} 
			dic['steelyardId'] = row['steelyardId']
			dic['skuCode'] = row['skuCode']
			dic['posX'] = row['posX']
			dic['posY'] = row['posY']
			dic['posZ'] = row['posZ']
			dic['unitWeight'] = "0"
			if row['skuCode'] != "":
				sql = "select * from sku where (skuCode = '" + row['skuCode'] + "' or barcode = '" + row['skuCode'] + "') and vendorId = '" + req['vendorId'] + "';"
				print sql
				n = cur.execute(sql)
				if n > 0:
					row0 = cur.fetchall()
					dic['unitWeight'] = row0[0]['unitWeight']
				else:
					print "Failed to get unitWeight!!!  " + row['steelyardId'] + " " + row['skuCode']
			dic['currWeight'] = row['currWeight']
			dic['offsetWeight'] = row['offsetWeight']
			dic['status'] = row['status']
			result['result'].append(dic)
		else:
			result = {'result':'Failure', 'ErrMsg':'Unknown_steelyardId'}
			print "The DB does not have this steelyardId!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def Alarm(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print '\033[1;31;40m' + "vendorId: " + vendorId + " shopId: " + shopId + " steelyardId: " + req['steelyardId'] + " running error!!!!!!" + '\033[0m'
	reqErrJson = {}
	reqErrJson['vendorId'] = vendorId
	reqErrJson['storeCode'] = shopId
	reqErrJson['type'] = '3'
	reqErrJson['errorMsg'] = req['steelyardId'] + " running error"
	response = http_post("https://base.1015bar.com/api/exec?m=errorSendMsg&token=H8DH9Snx9877SDER5667&reqJson=",reqErrJson)
	print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	result = {'result': 'Success'}
	return result

def ShopHeartBeat(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print "vendorId: " + vendorId + " shopId: " + shopId + " heart beat!"
	result = {'result': 'Success', 'shopIn':'', 'shopOut':''}
	reqJson = {}
	reqJson['vendorId'] = vendorId
	reqJson['storeCode'] = shopId
	response = http_post("https://base.1015bar.com/api/exec?m=storeMonitor&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
	print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	if req['in'] == 1:
		response = http_post("https://base.1015bar.com/api/exec?m=getInDoorStatus&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		response = json.loads(response)
		if response['returnCode'] == 10 and response['returnObject'] != {}:
		        result['shopIn'] = response['returnObject']['MemNo']
		else:
			print "Failed to getInDoorStatus from erp!"
	if req['out'] == 1:
		response = http_post("https://base.1015bar.com/api/exec?m=getPayMemNo&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		response = json.loads(response)
		if response['returnCode'] == 10 and response['returnObject'] != {}:
			result['shopOut'] = response['returnObject']['outMemNo']
		else:
			print "Failed to getPayMemNo from erp!"
	response = http_post("https://base.1015bar.com/api/exec?m=getCpuMessage&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
	#print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	response = json.loads(response)
	if response['returnCode'] == 10 and response['returnObject'] != {} and response['returnObject']['cmd'] != None and response['returnObject']['cmd'] != "":
		cmd = response['returnObject']['cmd']
		print "shopCmd: ", cmd
		if "upload" in cmd.lower() and ("log" in cmd.lower() or "client" in cmd.lower() or "trace" in cmd.lower()):
			result['shopCmd'] = cmd
			cmdArg = {}
			cmdArg['user'] = "administrator";
			cmdArg['pwd'] = "Gcwtled901";
			cmdArg['path'] = "ftp://47.95.242.148:21/pos_log/Debug/" #test
			#cmdArg['path'] = "ftp://47.95.242.148:21/pos_log/Release/" #operative
			result['shopCmdArg'] = cmdArg
		else:
			result['cmd'] = cmd
		reqJson['cmd'] = ""
		response = http_post("https://base.1015bar.com/api/exec?m=updateCpuByStoreCode&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	return result

def heartBeat(req,cmd,version):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print "vendorId: " + vendorId + " shopId: " + shopId + " heart beat!"
	result = {'result': []}
	reqMonitor = {}
	reqMonitor['cpuId'] = req['cpuId']
	response = http_post("https://base.1015bar.com/api/exec?m=boxMonitor&token=H8DH9Snx9877SDER5667&reqJson=",reqMonitor)
	print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	reqJson = {}
	reqJson['cpuId'] = req['cpuId']
	if 'lastCmd' in req:
		print "battery: %s  version: %s  lastCmd: %s" % (req['battery'], req['version'], req['lastCmd'])
		if req['lastCmd'].find('_Success') > 0:
			reqJson['cmd'] = ""
			cmd = ""
	else:
		print "battery: %s  version: %s" % (req['battery'], req['version'])
	if version != req['version']:
		reqJson['version'] = req['version']
	if 'cmd' in reqJson or 'version' in reqJson:
		response = http_post("https://base.1015bar.com/api/exec?m=updateCpuByCpuId&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "update steelyard set isError = '0' where shopId = '" + shopId + "' and isError != '0' and vendorId = '" + vendorId + "';"
	print sql
	cur.execute(sql)
	for i in req['isError']:
		sql = "update steelyard set isError = '" + i['grade'] + "' where steelyardId = '" + i['id'] + "' and isError != '" + i['grade'] + "' and vendorId = '" + vendorId + "' and shopId = '" + shopId + "';"
		print sql
		cur.execute(sql)
	cur.close()
	conn.commit()
	conn.close()
	if 'isShopping' in req and req['isShopping'] == "0":
		if req['isOpen'] == "1":
			print '\033[1;31;40m' + "vendorId: " + vendorId + " shopId: " + shopId + " door status error without shopping!!!!!!" + '\033[0m'
			reqErrJson = {}
			reqErrJson['vendorId'] = vendorId
			reqErrJson['storeCode'] = shopId
			reqErrJson['type'] = '2'
			reqErrJson['errorMsg'] = "door status error without shopping"
			response = http_post("https://base.1015bar.com/api/exec?m=errorSendMsg&token=H8DH9Snx9877SDER5667&reqJson=",reqErrJson)
			print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		reqJson = {}
		reqJson['cpuId'] = req['cpuId']
		response = http_post("https://base.1015bar.com/api/exec?m=getDoorStatus&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		response = json.loads(response)
		if response['returnCode'] == 10 and response['returnObject'] != {}:
			dic = {}
			dic['userId'] = response['returnObject']['memNo']
			dic['type'] = response['returnObject']['memberType']
			dic['status'] = response['returnObject']['status']
			#dic['doorStatus'] = response['returnObject']['doorStatus']
			result['result'].append(dic)
		else:
			print "Failed to getDoorStatus from erp!"
	if cmd == "update":
		result['cmd'] = cmd
		cmdArg = {}
		cmdArg['user'] = "administrator";
		cmdArg['pwd'] = "Gcwtled901";
		cmdArg['path'] = "ftp://47.95.242.148:21/box_firmware/Debug/ScaleWeightMsg_user_scan_qrcode" #test
		#cmdArg['path'] = "ftp://47.95.242.148:21/box_firmware/Release/ScaleWeightMsg_user_scan_qrcode" #operative
		result['cmdArg'] = cmdArg
	elif cmd == "uploadLog":
		result['cmd'] = cmd
		cmdArg = {}
		cmdArg['user'] = "administrator";
		cmdArg['pwd'] = "Gcwtled901";
		cmdArg['path'] = "ftp://47.95.242.148:21/box_log/Debug/" + vendorId + "_" + shopId + ".log" + datetime.datetime.now().strftime('%Y%m%d%H%M%S') #test
		#cmdArg['path'] = "ftp://47.95.242.148:21/box_log/Release/" + vendorId + "_" + shopId + ".log" + datetime.datetime.now().strftime('%Y%m%d%H%M%S') #operative
		result['cmdArg'] = cmdArg
	else:
		if cmd != "" and cmd != None:
			result['cmd'] = cmd
	return result

def heart_beat(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print "vendorId: " + vendorId + " shopId: " + shopId + " heart beat!"
	result = {'result': []}
	print "battery: %s  version: %s" % (req['battery'], req['version'])
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "update steelyard set isError = '0' where steelyardId like '" + shopId + "______' and isError != '0' and vendorId = '" + vendorId + "';"
	print sql
	cur.execute(sql)
	for i in req['isError']:
		sql = "update steelyard set isError = '-1' where steelyardId = '" + i + "' and isError != '-1' and vendorId = '" + vendorId + "';"
		print sql
		cur.execute(sql)
	cur.close()
	conn.commit()
	conn.close()
	if req['isOpen'] == "0":
		reqJson = {}
		reqJson['vendorId'] = vendorId
		reqJson['storeCode'] = shopId
		response = http_post("https://base.1015bar.com/api/exec?m=getStoreDoorStatus&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		response = json.loads(response)
		if response['returnCode'] == 10 and response['returnObject'] != {}:
			dic = {}
                        dic['userId'] = response['returnObject']['memNo']
			dic['type'] = response['returnObject']['memberType']
			dic['status'] = response['returnObject']['status']
			#dic['doorStatus'] = response['returnObject']['doorStatus']
			result['result'].append(dic)
		else:
			print "Failed to getStoreDoorStatus from erp!"
	return result

def shopEntry_in(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print "vendorId: " + vendorId + " shopId: " + shopId + " custom in, stop check_stock!"
	#notify algorithm
	cmd = "INOUT$" + req['customId']+ "$" + str(1) + "$" + req['timeStamp'] + "$" + vendorId + "$" + shopId
	print cmd
	socket.send(cmd.encode('ascii'))
	logFile = open('logFile.txt','a')
	logFile.write(cmd)
	logFile.write('\n')
	logFile.close()
	#reset CanCheck flag
	global g_dicCanCheck
	key = vendorId + shopId #vendorId + shopId
	if key in g_dicCanCheck:
		del g_dicCanCheck[key]
	else:
		print "vendorId: " + vendorId + " shopId: " + shopId + " not in check_stock!"
	result = {'result':'Success'}
	return result

def shopEntry_empty(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	print "vendorId: " + vendorId + " shopId: " + shopId + " empty! can check_stock!"
	global g_dicCanCheck
	key = vendorId + shopId #vendorId + shopId
	if key not in g_dicCanCheck:
		g_dicCanCheck[key] = 1
		#result = check_stock(vendorId,shopId)
		result = {'result':[], 'ErrMsg':''}
	else:
		result = {'result':[], 'ErrMsg':'Checking_stock'}
		print "vendorId: " + vendorId + " shopId: " + shopId + " in check_stock!"
	return result

def shopEntryHistory_insert(req):
	#notify algorithm
	cmd = "INOUT$" + req['customId']+ "$" + str(0) + "$" + req['timeStamp'] + "$" + req['vendorId'] + "$" + req['shopId']
	print cmd
	socket.send(cmd.encode('ascii'))
	logFile = open('logFile.txt','a')
	logFile.write(cmd)
	logFile.write('\n')
	logFile.close()
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into shopentryhistory values('" + req['entryTime'] + "','" + req['exitTime'] + "','" + req['customId'] + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_insert_shopEntryHistory'}
		print "Failed to insert shopentryhistory!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def customManager_get(req):
	reqJson = {}
	reqJson['vendorId'] = req['vendorId']
	reqJson['memNo'] = req['customId']
	response = http_post("https://mem.1015bar.com/api/qxMem?m=getMemberForBox&token=2CB1FB6F1D2F032000A1D807E17EC4DD&timeStamp=1503387111716&reqJson=",reqJson)
	#print "HTTP response: " + response
	print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	response = json.loads(response)
	if response['returnCode'] == 10:
		if response['returnObject'] != None and response['returnObject']['memNo'] != "":
			result = {'result':[]}
			dic = {}
			dic['userId'] = response['returnObject']['memNo']
			dic['type'] = response['returnObject']['memberType']
			dic['status'] = response['returnObject']['status']
			result['result'].append(dic)
		else:
			result = {'result':'Failure', 'ErrMsg':'Unknown_customId'}
			print "The erp DB does not have this customId!!!"
	elif response['returnCode'] == 20:
		result = {'result':'Failure', 'ErrMsg':'Unknown_customId'}
		print "The erp DB does not have this customId!!!"
	else:
		result = {'result':'Failure', 'ErrMsg':'"Failed_query_erp'}
		print "Failed to query the erp DB!!!"
	return result

def addskuStart(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into addsku(startTime,userId,skuMsgStart,vendorId,shopId) values('" + req['startTime'] + "','" + req['userId'] + "','" + str(req['skuMsg']) + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_start_addsku'}
		print "Failed to start addsku!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def AddskuStart(req):
	strSkuMsg = json.dumps(req['skuMsg']).replace('\r','').replace('\n','').replace('  ','')
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into addsku(startTime,userId,skuMsgStart,vendorId,shopId) values('" + req['startTime'] + "','" + req['userId'] + "','" + strSkuMsg + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_start_addsku'}
		print "Failed to start addsku!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def addskuEnd(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "update addsku set endTime = '" + req['endTime'] + "', skuMsgEnd = '" + req['skuMsg'] + "', status = '1' where userId = '" + req['userId'] + "' and shopId = '" + req['shopId'] + "' and status = '0' and vendorId = '" + req['vendorId'] + "';"
	print sql
	n = cur.execute(sql)
	n = 1
	if n > 0:
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_end_addsku'}
		print "Failed to end addsku!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def AddskuEnd(req):
	strSkuMsg = json.dumps(req['skuMsg']).replace('\r','').replace('\n','').replace('  ','')
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "update addsku set endTime = '" + req['endTime'] + "', skuMsgEnd = '" + strSkuMsg + "', status = '1' where userId = '" + req['userId'] + "' and shopId = '" + req['shopId'] + "' and status = '0' and vendorId = '" + req['vendorId'] + "';"
	n = cur.execute(sql)
	n = 1
	if n > 0:
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_end_addsku'}
		print "Failed to end addsku!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def ShoppingChart(req):
	result = {'result':'Success'}
	strSkuMsg = json.dumps(req['skuMsg']).replace('\r','').replace('\n','').replace('  ','')
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into shopping_chart(createTime,userId,skuMsg,vendorId,shopId) values('" + req['createTime'] + "','" + req['userId'] + "','" + strSkuMsg + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	cur.execute(sql)
	reqJson = {'payFlag':'0','saleDetailList':[]}
	reqJson['vendorId'] = int(req['vendorId'])
	reqJson['orderStore'] = req['shopId']
	reqJson['memberCode'] = req['userId']
	for i in req['skuMsg']:
		saleDetailList = {}
		saleDetailList['skuCode'] = i['skuCode']
		saleDetailList['skuNum'] = int(i['skuCount'])
		saleDetailList['steelyardId'] = i['steelyardId']
		reqJson['saleDetailList'].append(saleDetailList)
		sql = "select * from steelyard where steelyardId = '" + i['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "' and shopId = '" + req['shopId'] + "';"
		print sql
		n = cur.execute(sql)
		if n > 0:
			row = cur.fetchall()
			skuNum = int(row[0]['skuNum'])
			skuNum -= int(i['skuCount'])
			sql = "update steelyard set skuNum = '" + str(skuNum) + "' where steelyardId = '" + i['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "' and shopId = '" + req['shopId'] + "';"
			print sql
			cur.execute(sql)
	cur.close()
	conn.commit()
	conn.close()
	if reqJson['saleDetailList'] != []:
		#update custom status
		reqJson0 = {'status':'-1'}
		reqJson0['vendorId'] = int(req['vendorId'])
		reqJson0['memNo'] = req['userId']
		response = http_post("https://mem.1015bar.com/api/qxMem?m=updateMemStatus&token=2CB1FB6F1D2F032000A1D807E17EC4DD&timeStamp=1503387111716&reqJson=",reqJson0)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
		response = http_post("https://order.1015bar.com/api/exect?m=receiveOrderWithOutPay&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
		print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	return result

def shoppingChart(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into shopping_chart(createTime,userId,skuMsg,vendorId,shopId) values('" + req['createTime'] + "','" + req['userId'] + "','" + str(req['skuMsg']) + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':'Success'}
		strlist = req['skuMsg'].split(';')
		reqJson = {'payFlag':'0','saleDetailList':[]}
		reqJson['vendorId'] = int(req['vendorId'])
		reqJson['orderStore'] = req['shopId']
		reqJson['memberCode'] = req['userId']
		for i in strlist:
			if i != "": 
				strlist0 = i.split(':')
				if int(strlist0[1]) > 0:
					sql = "select * from sku where (skuCode = '" + strlist0[0] + "' or barcode = '" + strlist0[0] + "') and vendorId = '" + req['vendorId'] + "';"
					print sql
					n = cur.execute(sql)
					if n > 0:
						row = cur.fetchall()
						strlist0[0] = row[0]['skuCode']
						saleDetailList = {}
						saleDetailList['skuCode'] = strlist0[0]
						saleDetailList['skuNum'] = int(strlist0[1])
						reqJson['saleDetailList'].append(saleDetailList)
					else:
						saleDetailList = {}
						saleDetailList['skuCode'] = strlist0[0]
						saleDetailList['skuNum'] = int(strlist0[1])
						reqJson['saleDetailList'].append(saleDetailList)
						print "The DB does not have this skuCode!!!"
		if reqJson['saleDetailList'] != []:
			#update custom status
			reqJson0 = {'status':'-1'}
			reqJson0['vendorId'] = int(req['vendorId'])
			reqJson0['memNo'] = req['userId']
			response = http_post("https://mem.1015bar.com/api/qxMem?m=updateMemStatus&token=2CB1FB6F1D2F032000A1D807E17EC4DD&timeStamp=1503387111716&reqJson=",reqJson0)
			print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
			response = http_post("https://order.1015bar.com/api/exect?m=receiveOrderWithOutPay&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
			print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_insert_shopping_chart'}
		print "Failed to insert shopping_chart!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def shopping_chart(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "insert into shopping_chart(createTime,userId,skuMsg,vendorId,shopId) values('" + req['createTime'] + "','" + req['userId'] + "','" + str(req['skuMsg']) + "','" + req['vendorId'] + "','" + req['shopId'] + "');"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':'Success'}
		strlist = req['skuMsg'].split(';')
		reqJson = {'payFlag':'0','saleDetailList':[]}
		reqJson['vendorId'] = int(req['vendorId'])
		reqJson['orderStore'] = req['shopId']
		reqJson['memberCode'] = req['userId']
		for i in strlist:
			if i != "": 
				#print "skuMsg: " + i
				strlist0 = i.split(':')
				#print "skuCode: " + strlist0[0] + "  skuCount: " + strlist0[1]
				if int(strlist0[1]) > 0:
					sql = "select * from sku where (skuCode = '" + strlist0[0] + "' or barcode = '" + strlist0[0] + "') and vendorId = '" + req['vendorId'] + "';"
					print sql
					n = cur.execute(sql)
					if n > 0:
						row = cur.fetchall()
						strlist0[0] = row[0]['skuCode']
						saleDetailList = {}
						saleDetailList['skuCode'] = strlist0[0]
						saleDetailList['skuNum'] = int(strlist0[1])
						reqJson['saleDetailList'].append(saleDetailList)
					else:
						saleDetailList = {}
						saleDetailList['skuCode'] = strlist0[0]
						saleDetailList['skuNum'] = int(strlist0[1])
						reqJson['saleDetailList'].append(saleDetailList)
						print "The DB does not have this skuCode!!!"
		if reqJson['saleDetailList'] != []:
			#update custom status
			reqJson0 = {'status':'-1'}
			reqJson0['vendorId'] = int(req['vendorId'])
			reqJson0['memNo'] = req['userId']
			response = http_post("https://mem.1015bar.com/api/qxMem?m=updateMemStatus&token=2CB1FB6F1D2F032000A1D807E17EC4DD&timeStamp=1503387111716&reqJson=",reqJson0)
			#print "HTTP response: " + response
			print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
			response = http_post("https://order.1015bar.com/api/exect?m=receiveOrderWithOutPay&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
			#print "HTTP response: " + response
			print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
	else:
		result = {'result':'Failure', 'ErrMsg':'Failed_insert_shopping_chart'}
		print "Failed to insert shopping_chart!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def skuGet(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "select * from steelyard where shopId = '" + req['shopId'] + "' and skuCode != '' and vendorId = '" + req['vendorId'] + "' and isEnable = '1';"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':[]}
		rows = cur.fetchall()
		for row in rows:
			dic = {} 
			dic['steelyardId'] = row['steelyardId']
			dic['skuCode'] = row['skuCode']
			dic['unitWeight'] = "0"
			if row['skuCode'] != "":
				sql = "select * from sku where (skuCode = '" + row['skuCode'] + "' or barcode = '" + row['skuCode'] + "') and vendorId = '" + req['vendorId'] + "';"
				print sql
				n = cur.execute(sql)
				if n > 0:
					row0 = cur.fetchall()
					dic['unitWeight'] = row0[0]['unitWeight']
				else:
					print "Failed to get unitWeight!!!  " + row['steelyardId'] + " " + row['skuCode']
					continue
			else:
				continue
			dic['currWeight'] = row['currWeight']
			result['result'].append(dic)
	else:
		result = {'result':'Failure', 'ErrMsg':'no_match_steelyard'}
		print "The DB does not have this shopId data!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def sku_get(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "select * from steelyard where steelyardId like '" + req['shopId'] + "______' and skuCode != '' and vendorId = '" + req['vendorId'] + "' and isEnable = '1';"
	print sql
	n = cur.execute(sql)
	if n > 0:
		result = {'result':[]}
		rows = cur.fetchall()
		for row in rows:
			dic = {} 
			dic['steelyardId'] = row['steelyardId']
			dic['skuCode'] = row['skuCode']
			dic['unitWeight'] = "0"
			if row['skuCode'] != "":
				sql = "select * from sku where (skuCode = '" + row['skuCode'] + "' or barcode = '" + row['skuCode'] + "') and vendorId = '" + req['vendorId'] + "';"
				print sql
				n = cur.execute(sql)
				if n > 0:
					row0 = cur.fetchall()
					dic['unitWeight'] = row0[0]['unitWeight']
				else:
					print "Failed to get unitWeight!!!  " + row['steelyardId'] + " " + row['skuCode']
					continue
			else:
				continue
			dic['currWeight'] = row['currWeight']
			result['result'].append(dic)
	else:
		result = {'result':'Failure', 'ErrMsg':'no_match_steelyard'}
		print "The DB does not have this shopId data!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

##custom ShoppingCart
#g_dicShoppingCart = {}

def ShoppingCartEnd(req):
	result = {'result':'Success'}
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	customId = str(req['customId'])
	#global g_dicShoppingCart
	#if customId in g_dicShoppingCart:
	#	del g_dicShoppingCart[customId]
	#use Memcached in Django
	cache_key = vendorId + "_" + shopId + "_" + customId
	cache.delete(cache_key)
	logFile = open('logFile.txt','a')
	#logFile.write("Succeed to delete " + customId + " g_dicShoppingCart")
	#print "Succeed to delete " + customId + " g_dicShoppingCart"
	logFile.write("Succeed to delete " + cache_key + " ShoppingCart")
	print "Succeed to delete " + cache_key + " ShoppingCart"
	logFile.write('\n')
	logFile.close()
	return result

def ShoppingCartGet(req):
	result = {'result':[]}
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	customId = str(req['customId'])
	#global g_dicShoppingCart
	#if customId in g_dicShoppingCart:
	#	result['result'] = g_dicShoppingCart[customId]['saleList']
	#use Memcached in Django
	cache_key = vendorId + "_" + shopId + "_" + customId
	cache_None = "cache_None"
	cache_value = cache.get(cache_key,cache_None)
	if cache_value != cache_None:
		result['result'] = eval(cache_value)['saleList']
	logFile = open('logFile.txt','a')
	strSkuMsg = json.dumps(result['result']).replace('\r','').replace('\n','').replace(' ','')
	#logFile.write("Ready to send " + customId + " g_dicShoppingCart " + strSkuMsg)
	#print "Ready to send " + customId + " g_dicShoppingCart " + strSkuMsg
	logFile.write("Ready to send " + cache_key + " ShoppingCart " + strSkuMsg)
	print "Ready to send " + cache_key + " ShoppingCart " + strSkuMsg
	logFile.write('\n')
	logFile.close()
	return result

def ShoppingCartAdd(req):
	result = {'result':'Success'}
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	customId = str(req['customId'])
	skuCode = str(req['skuCode'])
	skuCount = str(req['skuCount'])
	confidence = float(req['confidence'])
	#timeStamp = str(req['timeStamp'])
	if confidence >= 1:
		#use Memcached in Django
		cache_key = vendorId + "_" + shopId + "_" + customId
		cache_None = "cache_None"
		cache_value = cache.get(cache_key,cache_None)
		if cache_value != cache_None:
			nIsSkuCodeIn = 0
			dicValue = eval(cache_value)
			for i in dicValue['saleList']:
				if skuCode == i['skuCode']:
					i['skuCount'] += float(skuCount)
					cache.set(cache_key,str(dicValue))
					nIsSkuCodeIn = 1
					print "skuCode in"
					break
			if nIsSkuCodeIn == 0:
				saleList = {}
				saleList['skuCode'] = skuCode
				saleList['skuCount'] = float(skuCount)
				dicValue['saleList'].append(saleList)
				cache.set(cache_key,str(dicValue))
				print "skuCode not in"
		else:
			saleList = {}
			saleList['skuCode'] = skuCode
			saleList['skuCount'] = float(skuCount)
			dic = {'saleList':[]}
			dic['saleList'].append(saleList)
			cache.set(cache_key,str(dic))
			print "customId not in"
		#global g_dicShoppingCart
		#if customId in g_dicShoppingCart:
		#	nIsSkuCodeIn = 0
		#	for i in g_dicShoppingCart[customId]['saleList']:
		#		if skuCode == i['skuCode']:
		#			i['skuCount'] += float(skuCount)
		#			nIsSkuCodeIn = 1
		#			print g_dicShoppingCart
		#			print "skuCode in"
		#			break
		#	if nIsSkuCodeIn == 0:
		#		saleList = {}
		#		saleList['skuCode'] = skuCode
		#		saleList['skuCount'] = float(skuCount)
		#		g_dicShoppingCart[customId]['saleList'].append(saleList)
		#		print g_dicShoppingCart
		#		print "skuCode not in"
		#else:
		#	saleList = {}
		#	saleList['skuCode'] = skuCode
		#	saleList['skuCount'] = float(skuCount)
		#	dic = {'saleList':[]}
		#	dic['vendorId'] = vendorId
		#	dic['shopId'] = shopId
		#	dic['saleList'].append(saleList)
		#	g_dicShoppingCart[customId] = dic
		#	print g_dicShoppingCart
		#	print "customId not in"
		logFile = open('logFile.txt','a')
		#strSkuMsg = json.dumps(g_dicShoppingCart[customId]['saleList']).replace('\r','').replace('\n','').replace(' ','')
		#logFile.write("Succeed to insert " + customId + " g_dicShoppingCart " + strSkuMsg)
		#print "Succeed to insert " + customId + " g_dicShoppingCart " + strSkuMsg
		logFile.write("Succeed to insert " + cache_key + " ShoppingCart " + cache.get(cache_key,cache_None))
		print "Succeed to insert " + cache_key + " ShoppingCart " + cache.get(cache_key,cache_None)
		logFile.write('\n')
		logFile.close()
	return result

def CheckWeight(req):
	vendorId = str(req['vendorId'])
	shopId = str(req['shopId'])
	steelyardId = str(req['steelyardId'])
	skuCode = str(req['skuCode'])
	skuCount = str(req['skuCount'])
	operation = str(req['operation'])
	timestamp = str(req['timeStamp'])
	print "vendorId: " + vendorId + " steelyardId: " + steelyardId + " sku: " + skuCode + " operation: " + operation
	result = {'result':'Success'}
	if (operation == '0' or operation == '1') and skuCode != '' and skuCount != '0':
		conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
		cur = conn.cursor(MySQLdb.cursors.DictCursor)
		sql = "select * from steelyard where steelyardId = '" + steelyardId + "' and vendorId = '" + vendorId + "' and shopId = '" + shopId + "';"
		print sql
		n = cur.execute(sql)
		if n > 0:
			row = cur.fetchall()
			x = row[0]['posX']
			y = row[0]['posY']
			z = row[0]['posZ']
			#notify algorithm
			cmd = "SCALE$" + skuCode + "$" + skuCount + "$" + operation + "$" + timestamp + "$" + x + "," + y + "," + z + "$" + vendorId + "$" + shopId
			print cmd
			socket.send(cmd.encode('ascii'))
			logFile = open('logFile.txt','a')
			logFile.write(cmd)
			logFile.write('\n')
			logFile.close()
			skuNum = int(row[0]['skuNum'])
			if operation == '0':
				skuNum += int(skuCount)
			elif operation == '1':
				skuNum -= int(skuCount)
			sql = "update steelyard set skuNum = '" + str(skuNum) + "' where steelyardId = '" + steelyardId + "' and vendorId = '" + vendorId + "' and shopId = '" + shopId + "';"
			print sql
			cur.execute(sql)
		else:
			result = {'result':'Failure', 'ErrMsg':'Unknown_steelyardId/vendorId'}
			print "The DB does not have this steelyardId/vendorId!!!"
		cur.close()
		conn.commit()
		conn.close()
	return result

def steelyard_update(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	offsetWeight = req['offsetWeight']
	if offsetWeight == 'N':
		sql = "update steelyard set currWeight = '" + req['currWeight'] + "' where steelyardId = '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
		#print sql
		n = cur.execute(sql)
		if n > 0:
			result = {'result':'Success'}
		else:
			result = {'result':'Failure', 'ErrMsg':'Failed_update_currWeight'}
			print "Failed to update steelyard currWeight!!!"
	else:
		sql = "update steelyard set currWeight = '" + req['currWeight'] + "', offsetWeight = '" + req['offsetWeight'] + "' where steelyardId = '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
		#print sql
		n = cur.execute(sql)
		if n > 0:
			result = {'result':'Success'}
		else:
			result = {'result':'Failure', 'ErrMsg':'Failed_update_offsetWeight'}
			print "Failed to update steelyard offsetWeight!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def steelyard_update_status(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "select * from steelyard where steelyardId like '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
	print sql
	n = cur.execute(sql)
	if n > 0:
		sql = "update steelyard set status = '" + req['status'] + "' where status != '" + req['status'] + "' and steelyardId like '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
		print sql
		cur.execute(sql)
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Unknown_steelyardId'}
		print "The DB does not have this steelyardId!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def steelyard_update_isError(req):
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "select * from steelyard where steelyardId like '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
	print sql
	n = cur.execute(sql)
	if n > 0:
		sql = "update steelyard set isError = '" + req['isError'] + "' where isError != '" + req['isError'] + "' and steelyardId like '" + req['steelyardId'] + "' and vendorId = '" + req['vendorId'] + "';"
		print sql
		cur.execute(sql)
		result = {'result':'Success'}
	else:
		result = {'result':'Failure', 'ErrMsg':'Unknown_steelyardId'}
		print "The DB does not have this steelyardId!!!"
	cur.close()
	conn.commit()
	conn.close()
	return result

def InsertTable(req):
	result = {'result':[], 'ErrMsg':''}
	primary_key = ""
	conn = MySQLdb.connect(host="127.0.0.1",user="tangff",passwd="migrsoft*2017",db="1015shop",charset="utf8")
	cur = conn.cursor(MySQLdb.cursors.DictCursor)
	sql = "show columns from " + req['TableName'] + ";"
	print sql
	n = cur.execute(sql)
	rows = cur.fetchall()
	for row in rows:
		if row['Key'] == "PRI":
			primary_key = row['Field']
	if primary_key == "":
		result['ErrMsg'] = "no_primary_key"
		print "no_primary_key"
	else:
		mFieldList = req['FieldName']
		n = mFieldList.index(primary_key)
		if n < 0:
			result['ErrMsg'] = "no_match_primary_key"
			print "no_match_primary_key"
		else:
			mDataList = req['Data']
			for i in mDataList:
				sql = "select * from " + req['TableName'] + " where " + primary_key + " = '" + i[primary_key] + "';"
				print sql
				n = cur.execute(sql)
				if n > 0:
					dic = {}
					for x in mFieldList:
						dic[x] = i[x]
					result['result'].append(dic)
					result['ErrMsg'] = "Already_exists"
					print "Already_exists"
				else:
					fields = ""
					values = ""
					for j in mFieldList:
						fields += j + ","
						values += "\"" + i[j] + "\"" + ","
					fields = fields[:-1]
					values = values[:-1]
			 		sql = "insert into "+ req['TableName'] + "(" + fields + ") values(" + values + ");"
					print sql
					n = cur.execute(sql)
					if n < 0:
						dic = {}
						for x in mFieldList:
							dic[x] = i[x]
						result['result'].append(dic)
						result['ErrMsg'] = "Failed_to_insert"
						print "Failed_to_insert"
	cur.close()
	conn.commit()
	conn.close()
	return result

@csrf_exempt
def index(request):
	if request.method == 'POST':
		result = {'result':'Failure', 'ErrMsg':'Unknown_reason'}
		if request.body.find('steelyard_update') < 0:
			print "\n[" + datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S') + "]"
			strTemp = request.body.replace('\r','').replace('\n','').replace('  ','')
			print '\033[1;31;40m' + strTemp + '\033[0m'
		#request.body.encode('utf-8').strip()
		req = json.loads(request.body,encoding="utf-8")
		if request.body.find('CheckWeight') > 0:
			if int(req['skuCount']) > 0:
				logFile = open('logFile.txt','a')
				logFile.write(request.body)
				logFile.close()
		if request.body.find('ShoppingCartAdd') > 0:
			logFile = open('logFile.txt','a')
			logFile.write('\n')
			logFile.write(request.body)
			logFile.write('\n')
			logFile.close()
		if 'cpuId' in req:
			#cpuId >>> vendorId shopId
			reqJson = {}
			reqJson['cpuId'] = req['cpuId']
			response = http_post("https://base.1015bar.com/api/exec?m=getCpuMessage&token=H8DH9Snx9877SDER5667&reqJson=",reqJson)
			#print '\033[1;31;40m' + "HTTP response: " + response + '\033[0m'
			response = json.loads(response)
			if response['returnCode'] == 10 and response['returnObject'] != {}:
                        	req['vendorId'] = response['returnObject']['vendorId']
                        	req['shopId'] = response['returnObject']['storeCode']
				print req['cpuId'], " >>> ", req['vendorId'], " ", req['shopId']
				cmd = response['returnObject']['cmd']
				version = response['returnObject']['version']
				if cmd != "":
					print "cmd: ", cmd
			else:
				result = {'result':'Failure', 'ErrMsg':'Unknown_cpuId'}
				print "Failed to translate cpuId! ", req['cpuId']
				#return HttpResponse(json.dumps(result,ensure_ascii=False))
				return HttpResponse(json.dumps(result,ensure_ascii=False,separators=(',',':')))
		if (req['action'] == 'steelyard_get'):
			result = steelyard_get(req)
		
		elif (req['action'] == 'Alarm'):
			result = Alarm(req)

		elif (req['action'] == 'ShopHeartBeat'):
			result = ShopHeartBeat(req)

		elif (req['action'] == 'heartBeat'):
			result = heartBeat(req,cmd,version)

		elif (req['action'] == 'heart_beat'):
			result = heart_beat(req)

		elif (req['action'] == 'shopEntry_in'):
			result = shopEntry_in(req)

		elif (req['action'] == 'shopEntry_empty'):
			result = shopEntry_empty(req)

                elif (req['action'] == 'shopEntryHistory_insert'):
			result = shopEntryHistory_insert(req)

                elif (req['action'] == 'customManager_get'):
			result = customManager_get(req)

		elif (req['action'] == 'addskuStart'):
			result = addskuStart(req)

		elif (req['action'] == 'AddskuStart'):
			result = AddskuStart(req)

		elif (req['action'] == 'addskuEnd'):
			result = addskuEnd(req)

		elif (req['action'] == 'AddskuEnd'):
			result = AddskuEnd(req)

		elif (req['action'] == 'ShoppingChart'):
			result = ShoppingChart(req)

		elif (req['action'] == 'shoppingChart'):
			result = shoppingChart(req)

		elif (req['action'] == 'shopping_chart'):
			result = shopping_chart(req)

		elif (req['action'] == 'skuGet'):
			result = skuGet(req)

		elif (req['action'] == 'sku_get'):
			result = sku_get(req)

		elif (req['action'] == 'ShoppingCartEnd'):
			result = ShoppingCartEnd(req)

		elif (req['action'] == 'ShoppingCartGet'):
			result = ShoppingCartGet(req)

		elif (req['action'] == 'ShoppingCartAdd'):
			result = ShoppingCartAdd(req)

		elif (req['action'] == 'CheckWeight'):
			result = CheckWeight(req)

		elif (req['action'] == 'steelyard_update'):
			result = steelyard_update(req)

		elif (req['action'] == 'steelyard_update_status'):
			result = steelyard_update_status(req)

		elif (req['action'] == 'steelyard_update_isError'):
			result = steelyard_update_isError(req)

		elif (req['action'] == 'InsertTable'):
			result = InsertTable(req)
		else:
			result = {'result':'Failure', 'ErrMsg':'Unknown_action'}
			print '\033[1;31;40m' + "Error: Unknown action" + '\033[0m'
		#print result
		#return HttpResponse(json.dumps(result,ensure_ascii=False))
		return HttpResponse(json.dumps(result,ensure_ascii=False,separators=(',',':')))

	elif request.method == 'GET':
		return HttpResponse("[" + datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S') + "] " + "Hello World")
		#return render(request,'weixin/home.html')
	else:
		return HttpResponse("[" + datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S') + "]")

