Pytorch Implementation of Glow and conditonal Glow and PixelCNN. Based on the paper:

  > [Density estimation using Real NVP](https://arxiv.org/abs/1807.03039)\
  > Diederik P. Kingma, Prafulla Dhariwal\
  >  arXiv:1807.03039

  > [Conditional Image Generation with PixelCNN Decoders](https://arxiv.org/abs/1606.05328)\
  > Aaron van den Oord, Nal Kalchbrenner, Oriol Vinyals, Lasse Espeholt, Alex Graves, Koray Kavukcuoglu\
  > arXiv:1606.05328




The results for conditional Glow samples can be found in the `gen_imgs` folder.

## MNIST
### Epoch 1

![Samples at Epoch 1000](./gen_imgs/0.png "Samples at Epoch 1000")

### Epoch 10

![Samples at Epoch 10000](./gen_imgs/10.png "Samples at Epoch 10000")

### Epoch 20

![Samples at Epoch 20000](./gen_imgs/18.png "Samples at Epoch 20000")

### Epoch 50

![Samples at Epoch 50000](./gen_imgs/50.png "Samples at Epoch 50000")


## Usage
The entire code is self contained in the Jupyter notebook,just run the cells sequentially. It is made this way for ease of training on Google Colab.