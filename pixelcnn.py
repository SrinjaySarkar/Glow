# -*- coding: utf-8 -*-
"""PixelCNN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1cfjLCM58zecPB8_jBEGjIovxZ_xe9Gxg
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torchvision import transforms,datasets
import torch.utils as utils
from torch.autograd import Variable
import tqdm
import torch.optim
device=torch.device("cuda" if torch.cuda.is_available() else "cpu")

!mkdir sample_images

epochs=5
path=os.path.join("./sampled_images",str(epochs))
print(path)

"""Refer http://bjlkeng.github.io/posts/pixelcnn/ for a detailed explaination"""
"""The output of the "G" sub-pixel in Mask B, depends on the "G" sub-pixel output from Mask A, which in turn depends only 
on the "R". That means "G" from the second layer only depends on "R" from the original input, which is what we wanted. 
If we didn't do this, the "G" output from Mask B would never be able to "read" from the "R" sub-pixel in the original input."""
class masked_conv(torch.nn.Conv2d):
  def __init__(self,mask_type,cin,cout,filter_size,stride,padding):
    super(masked_conv,self).__init__(cin,cout,filter_size,stride,padding,bias=False)
    self.mask_type=mask_type
    assert (self.mask_type == "A" or self.mask_type=="B")
    _,_,height,width=self.weight.shape
    mask=torch.zeros(self.weight.shape)
    if self.mask_type == "A":
      mask[:,:,height//2,0:width//2]=1
      mask[:,:,0:height//2,:]=1
    else:#B
      mask[:,:,height//2,0:width//2]=1
      mask[:,:,0:height//2+1,0:width//2+1]=1
    self.register_buffer("conv_mask",mask)
  
  def forward(self,x):
    self.weight.data=self.weight.data * self.conv_mask
    op=super(masked_conv,self).forward(x)
    return (op)

class MaskedConv2d(nn.Conv2d):
    def __init__(self, mask_type, c_in, c_out, k_size, stride, pad):
        """2D Convolution with masked weight for Autoregressive connection"""
        super(MaskedConv2d, self).__init__(
            c_in, c_out, k_size, stride, pad, bias=False)
        assert mask_type in ['A', 'B']
        self.mask_type = mask_type
        ch_out, ch_in, height, width = self.weight.size()
        mask = torch.ones(ch_out, ch_in, height, width)
        if mask_type == 'A':
            # First Convolution Only
            # => Restricting connections to
            #    already predicted neighborhing channels in current pixel
            mask[:, :, height // 2, width // 2:] = 0
            mask[:, :, height // 2 + 1:] = 0
        else:
            mask[:, :, height // 2, width // 2 + 1:] = 0
            mask[:, :, height // 2:,:] = 0
        self.register_buffer('mask', mask)

    def forward(self, x):
        self.weight.data *= self.mask
        return super(MaskedConv2d, self).forward(x)

class Bconv_block(torch.nn.Module):
  def __init__(self,cin=128,cout=256,filter_size=3,stride=1,padding=1):
    super(Bconv_block,self).__init__()
    self.layer1=torch.nn.Conv2d(in_channels=256,out_channels=128,kernel_size=1)
    self.layer2=torch.nn.BatchNorm2d(num_features=128)
    self.layer3=masked_conv(mask_type="B",cin=128,cout=128,filter_size=3,stride=1,padding=1)
    self.layer4=torch.nn.BatchNorm2d(num_features=128)
    self.layer5=torch.nn.Conv2d(in_channels=128,out_channels=256,kernel_size=1)
    self.layer6=torch.nn.BatchNorm2d(num_features=256)
  
  def forward(self,x):
    ip=x
    x=F.relu(x)
    x=self.layer1(x)
    x=self.layer2(x)
    x=F.relu(x)
    x=self.layer3(x)
    x=self.layer4(x)
    x=F.relu(x)
    x=self.layer5(x)
    x=self.layer6(x)
    op=ip+x
    return (op)

class pixel_cnn(torch.nn.Module):
  def __init__(self,n_channels=1,mid_channels=128,op_dist_dim=256):
    super(pixel_cnn,self).__init__()
    self.op_dist_dim=op_dist_dim
    self.layer1=masked_conv(mask_type="A",cin=1,cout=256,filter_size=7,stride=1,padding=3)
    self.layer2=torch.nn.BatchNorm2d(num_features=256)
    self.layer3=torch.nn.ModuleList([Bconv_block() for _ in range(15)])
    #relu
    self.layer4=torch.nn.Conv2d(256,1024,kernel_size=1,stride=1,padding=0,bias=True)
    self.layer5=torch.nn.BatchNorm2d(num_features=1024)
    #relu
    self.layer6=torch.nn.Conv2d(1024,1*op_dist_dim,kernel_size=1,stride=1,padding=0,bias=True)
  
  def forward(self,x):
    ip=x
    x=self.layer1(x)
    x=self.layer2(x)
    for i in range(len(self.layer3)):
      x=self.layer3[i](x)
    x=F.relu(x)
    x=self.layer4(x)
    x=self.layer5(x)
    x=F.relu(x)
    x=self.layer6(x)
    x=x.reshape(ip.shape[0],ip.shape[1],self.op_dist_dim,ip.shape[2],ip.shape[3])#(bs,3,256,32,32)
    x=x.permute(0,1,3,4,2)#(bs,3,32,32,256);256*3 dim op dist for every pixel
    return (x)

"""## DATALOADERS"""

transform=torchvision.transforms.Compose([torchvision.transforms.ToTensor()])
bs=32
training_data=torchvision.datasets.MNIST(root='torch/data/MNIST',train=True, download=True, transform=transform)
train_loader=torch.utils.data.DataLoader(training_data,batch_size=bs, shuffle=True, num_workers=2)

validation_data=torchvision.datasets.MNIST(root='torch/data/MNIST',train=False,download=True,transform=transform)
val_loader=torch.utils.data.DataLoader(validation_data,batch_size=bs,shuffle=True,num_workers=2)

"""## TRAINING LOOP

"""

model=pixel_cnn().to(device)
optimizer=torch.optim.Adam(model.parameters(),lr=1e-4)
loss_function=torch.nn.CrossEntropyLoss()

n_epochs=200
batch_loss_number=50
for epochs in range(n_epochs):
  model.train()
  batch_loss=[]
  for batch_idx,(x,y) in enumerate(train_loader):
    image=x.to(device)
    #print(image.shape)=>bs,3,32,32
    prob=model(image)
    prob=prob.reshape(-1,256)
    image=image.view(-1)*255 
    image=image.long()
    loss=loss_function(prob,image)#Entropy loss between value of each pixel(from distribution) and target value of pixel
    #print(loss)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    batch_loss.append(loss)
    if batch_idx > 1 and batch_idx % batch_loss_number == 0:
      print("Batch %s:" % batch_idx, 'batch_loss= %.3f'% loss)
  final_loss=torch.mean(torch.stack(batch_loss))
  print("Epoch %s:" % epochs, 'Epoch_loss= %.3f'% final_loss)
  ## test
  model.eval()
  for val_batch_idx,(x,y) in enumerate(val_loader):
    test_error=[]
    image=x.to(device)
    probs=model(image)
    probs=probs.reshape(-1,256)
    image=image.view(-1)*255 
    image=image.long()
    val_loss=F.cross_entropy(probs,image)
    test_error.append(val_loss)
  epoch_val_loss=torch.mean(torch.stack(test_error))
  print("Epoch %s:" % epochs, 'Epoch_val_loss= %.3f'% epoch_val_loss)
  ## sample
  model.eval()
  path=os.path.join("./sampled_images",str(epochs))
  #torchvision.utils.save_image(torchvision.utils.make_grid(gen_samples),'./new_samples/'+'iter%d.png' % total_iter)
  gen_samples=torch.rand(*x.shape).to(device)
  for height in range(x.shape[2]):
    for width in range(x.shape[3]):
      op=model(gen_samples)
      probs=F.softmax(op[:,:,height,width],dim=2).data
      for channel in range(x.shape[1]):
        px=torch.multinomial(probs[:,channel],1).float()/255.
        gen_samples[:,channel,height,width]=px[:,0]
  
  gen_img=gen_samples.cpu()
  torchvision.utils.save_image(torchvision.utils.make_grid(gen_img),"./sample_images/"+"epochs%d.png" % epochs)
  print("Images saved for epoch%d" %epochs)