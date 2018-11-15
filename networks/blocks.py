import torch
import torch.nn as nn
import torch.nn.functional as F

# resnet reference: https://github.com/pytorch/vision/blob/master/torchvision/models/resnet.py

class Bottleneck_3_0(nn.Module):
	expansion = 4

	# input dim : c x 800 x 700
	# output dim: c x 400 x 350
	def __init__(self, in_channels, out_channels):
		super(Bottleneck_3_0, self).__init__()

		# using pre-normalization and pre-activation
		# TODO: switch stride=2 between conv1 and conv2 and check results
		self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
		self.bn1 = nn.BatchNorm2d(out_channels)

		self.conv2 = nn.Conv2d(out_channels, out_channels*self.expansion, kernel_size=3, stride=2, padding=1, bias=False)
		self.bn2 = nn.BatchNorm2d(out_channels*self.expansion)

		self.conv1_skip = nn.Conv2d(in_channels, out_channels*self.expansion, kernel_size=3, stride=2, padding=1, bias=False)
		self.bn1_skip = nn.BatchNorm2d(out_channels*self.expansion)

		self.relu = nn.ReLU(inplace=True)

	def forward(self, x):
		res = self.conv1_skip(x)
		res = self.bn1_skip(res)

		x = self.conv1(x)
		x = self.bn1(x)
		x = self.conv2(self.relu(x))
		x = self.bn2(x)

		out = self.relu(x+res)

		return out


class Bottleneck_6_0(nn.Module):
	expansion = 4

	def __init__(self, in_channels, out_channels):
		super(Bottleneck_6_0, self).__init__()

		# using pre-normalization and pre-activation
		# TODO: switch stride=2 between conv1 and conv2 and check results
		self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
		self.bn1 = nn.BatchNorm2d(out_channels)

		self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=2, padding=1, bias=False)
		self.bn2 = nn.BatchNorm2d(out_channels)

		self.conv3 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
		self.bn3 = nn.BatchNorm2d(out_channels)

		self.conv4 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
		self.bn4 = nn.BatchNorm2d(out_channels)

		self.conv5 = nn.Conv2d(out_channels, out_channels*self.expansion, kernel_size=3, stride=1, padding=1, bias=False)
		self.bn5 = nn.BatchNorm2d(out_channels*self.expansion)

		self.conv1_skip = nn.Conv2d(in_channels, out_channels*self.expansion, kernel_size=3, stride=2, padding=1, bias=False)
		self.bn1_skip = nn.BatchNorm2d(out_channels*self.expansion)

		self.relu = nn.ReLU(inplace=True)

	def forward(self, x):
		res = self.conv1_skip(x)
		res = self.bn1_skip(res)

		x = self.conv1(x)
		x = self.bn1(x)
		x = self.conv2(self.relu(x))
		x = self.bn2(x)
		x = self.conv3(self.relu(x))
		x = self.bn3(x)
		x = self.conv4(self.relu(x))
		x = self.bn4(x)
		x = self.conv5(self.relu(x))
		x = self.bn5(x)

		out = self.relu(x+res)

		return out


class Upsample_1(nn.Module):
	'''
	Upsamples the input sample by a factor of 2.
	First the input is upsample by bilinear interpolation.
	Then, convolution is applied to the interpolated image.
	Reference: https://distill.pub/2016/deconv-checkerboard/
	'''
	def __init__(self, in_channels, out_channels, output_size=None):
		super(Upsample, self).__init__()
		if output_size:
			self.upsample = nn.Upsample(size=output_size, mode='bilinear')
		else:
			self.upsample = nn.Upsample(scale_factor=2,  mode='bilinear')

		self.conv_upsample = nn.Conv2d(in_channels[0], out_channels, kernel_size=3, padding=1, bias=False)
		self.conv1 = nn.Conv2d(in_channels[1], out_channels, kernel_size=1, bias=False)

	def forward(self, featureMapToUpsample, originalFeatureMap):
		u = self.upsample(featureMapToUpsample)
		u = self.conv_upsample(u)

		x = self.conv1(originalFeatureMap)
		return x + u


class Upsample_2(nn.Module):
	'''
	Upsampling block as described in the PIXOR paper.
	First apply deconvolution to input, apply convolution 
	to res connection, and perform element wise addition.

	Requires: in_channels
			: out_channels
			: output_size
			: args - (dilation, stride, padding, output_padding) for deconv layer
	'''
	def __init__(self, in_channels, out_channels, args):
		super(Upsample, self).__init__()

		dilation, stride, padding, output_padding = args
		self.deconv1 = nn.ConvTranspose2d(
			in_channels[0],
			out_channels,
			kernel_size=3,
			stride=stride,
			padding=padding,
			output_padding=output_padding,
			groups=1,
			bias=False,
			dilation=dilation
		)
		self.bn_deconv1 = nn.BatchNorm2d(out_channels)

		self.conv1 = nn.Conv2d(in_channels[1], out_channels, kernel_size=1, bias=False)
		self.bn1 = nn.BatchNorm2d(out_channels)

		self.relu = nn.ReLU(inplace=True)

	def forward(self, featureMapToUpsample, originalFeatureMap):
		d = self.deconv1(featureMapToUpsample)
		d = self.bn_deconv1(d)

		res = self.conv1(originalFeatureMap)
		res = self.bn1(res)

		out = self.relu(d+res)

		return out


class UnStandarizeLayer(nn.Module):
	'''
	Changes the view of the input tensor
	Then un standarizes the input tensor by given mean and std
	'''
	def __init__(self, mean, std):
		super(UnStandarizeLayer, self).__init__()

		self.register_buffer('mean', mean)
		self.register_buffer('std', std)

	def forward(self, X):
		m, c, h, w = X.size()
		h = X.permute(0, 2, 3, 1).contiguous().view(m, w*h, c)
		h = h*self.std + self.mean
		return h


# for new variants of bottleneck change names here
Bottleneck_3 = Bottleneck_3_0
Bottleneck_6 = Bottleneck_6_0
Upsample = Upsample_2
UnStandarizeLayer = UnStandarizeLayer