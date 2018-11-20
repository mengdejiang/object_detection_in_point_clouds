import torch
import torch.nn as nn
import os
from threading import Thread
from queue import Queue
import config as cnf

# custom weights initialization called on network
def weights_init(m):
	classname = m.__class__.__name__
	if classname.find('Conv') != -1:
		m.weight.data.normal_(0.0, 0.001)
	elif classname.find('BatchNorm') != -1:
		m.weight.data.normal_(1.0, 0.02)
		m.bias.data.fill_(0)

# identity weights initialization
def weights_init_identity(m):
	if isinstance(m, nn.Conv2d):
		m.weight.data.copy_(torch.eye(m.weight.data.size()))
	elif isinstance(m, nn.BatchNorm2d):
		nn.init.constant_(m.weight, 1)
		nn.init.constant_(m.bias, 0)

# weights initialization for resnet
def weights_init_resnet(m):
	if isinstance(m, nn.Conv2d):
		nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
	elif isinstance(m, nn.BatchNorm2d):
		nn.init.constant_(m.weight, 1)
		nn.init.constant_(m.bias, 0)

def savebatchOutput(cla, loc, filenames, outputDir, epoch):
	for i in range(len(filenames)):
		filename = filenames[i]

		# make directory if it doesnt exists
		if not os.path.exists(outputDir+'/'+str(epoch)+'/output'):
			os.makedirs(outputDir+'/'+str(epoch)+'/output')

		torch.save(cla[i],
			outputDir+'/'+str(epoch)+'/output/'+filename+'_cla.pt')
		torch.save(loc[i],
			outputDir+'/'+str(epoch)+'/output/'+filename+'_loc.pt')

def savebatchTarget(target, filenames, outputDir, epoch):
	for i in range(len(filenames)):
		filename = filenames[i]

		# make directory if it doesnt exists
		if not os.path.exists(outputDir+'/'+str(epoch)+'/target'):
			os.makedirs(outputDir+'/'+str(epoch)+'/target')

		torch.save(target[i],
			outputDir+'/'+str(epoch)+'/target/'+filename+'.pt')

def writeToFile(filename, line):
	with open(filename, 'a') as file:
		file.write(line)

class Logger():

	def __init__(self, filename):
		queue = Queue()
		worker = FileWriterThread(queue, cnf.trainlog)
		worker.daemon = True
		worker.start()

	def join(self):
		self.queue.join()

	def put(self, s):
		self.queue.put(s)

class FileWriterThread(Thread):

	def __init__(self, queue, filename):
		Thread.__init__(self)
		self.queue = queue
		self.filename = filename

	def run(self):
		while True:
			try:
				epoch, batchId, cl, nsl, psl, ll, tl, ps, ns, iou, mc, oamc, lt, bt = self.queue.get()
				if cl is None:
					ls = cnf.logString3.format(batchId, epoch, ps, ns, lt, bt)
				elif ll is not None:
					ls = cnf.logString1.format(batchId, epoch, cl, ll, tl, ps, ns, iou, mc, oamc, lt, bt)
				else:
					ls = cnf.logString2.format(batchId, epoch, cl, tl, ps, ns, oamc, lt, bt)
				writeToFile(self.filename, ls)
			finally:
				self.queue.task_done()

def parameterNorm(parameters, p):
	vec = []
	for param in parameters:
		if p == 'grad':
			vec.append(param.grad.view(-1))
		elif p == 'weight':
			vec.append(param.view(-1))
	param_norm = torch.cat(vec).norm(2)
	return param_norm