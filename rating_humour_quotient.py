# -*- coding: utf-8 -*-
"""Rating Humour Quotient

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15_8SDHSIK2avDIBZF9lDHyVGXLv2Cf4L
"""

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/MansiBellani/Laughter-Detection-Model.git

# %cd Laughter-Detection-Model/
!pip install tgt #tgt is Text Grid Tools - Read, write, and manipulate Praat TextGrid files
!pip install pyloudnorm #Algorithms to measure loudness of audio (true peak)
!pip install praatio==3.8.0 #Time allign with audio transcript.
!pip install tensorboardX==1.9 #Let's you watch tensors flow without tensorflow

from google.colab import files #Used to create option that lets user upload the files

import os, sys, pickle, time, librosa, argparse, torch, numpy as np, pandas as pd, scipy
from tqdm import tqdm #Progress bar
import tgt #Text Grid Tools (Praat)
sys.path.append('./utils/') #To access the 'utils' directory
import laugh_segmenter
import models, configs
import dataset_utils, audio_utils, data_loaders, torch_utils
from tqdm import tqdm
from torch import optim, nn #nn is used to apply a 2D max pooling and optim is used to implement various optimization algorithms
from functools import partial
from distutils.util import strtobool #Yes/No prompt 
sample_rate = 8000 #Adequate for human speech but without sibilance.

model_path = 'checkpoints/in_use/resnet_with_augmentation'
config = configs.CONFIG_MAP['resnet_with_augmentation']

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device {device}")
# CUDA provides support for debugging and optimization, compiling, documentation, runtimes, signal processing, and parallel algorithms. 
# torch.device is used here to specify the device type responsible to load a tensor into memory

model = config['model'](dropout_rate=0.0, linear_layer_size=config['linear_layer_size'], filter_sizes=config['filter_sizes'])
feature_fn = config['feature_fn']
model.set_device(device)

if os.path.exists(model_path):
    torch_utils.load_checkpoint(model_path+'/best.pth.tar', model)
    model.eval()
else:
    raise Exception(f"Model checkpoint not found at {model_path}")

uploaded = files.upload()
audio_path = list(uploaded.keys())[0]

import scipy
import wave # write audio data in raw format and read the attributes of a WAV file
import scipy.io.wavfile
threshold = 0.5
min_length = 2
save_to_audio_files = True 
save_to_textgrid = False 
output_dir = 'laughter_detection_output' 
ele = 0
res=0
sum = 0

inference_dataset = data_loaders.SwitchBoardLaughterInferenceDataset(
    audio_path=audio_path, feature_fn=feature_fn, sr=sample_rate)

collate_fn=partial(audio_utils.pad_sequences_with_labels,
                        expand_channel_dim=config['expand_channel_dim'])
# padding sequential data to a max length of a batch

inference_generator = torch.utils.data.DataLoader(
    inference_dataset, num_workers=4, batch_size=8, shuffle=False, collate_fn=collate_fn)
#Inference is generated,batch size is set.

probs = []
for model_inputs, _ in tqdm(inference_generator):
    x = torch.from_numpy(model_inputs).float().to(device)
    preds = model(x).cpu().detach().numpy().squeeze() # converting a torch.tensor to np.ndarray (Numpy Ndarray)
    if len(preds.shape)==0:
        preds = [float(preds)]
    else:
        preds = list(preds)
    probs += preds
probs = np.array(probs)

file_length = audio_utils.get_audio_length(audio_path)

fps = len(probs)/float(file_length)

probs = laugh_segmenter.lowpass(probs)
instances = laugh_segmenter.get_laughter_instances(probs, threshold=threshold, min_length = float(min_length), fps=fps)
print("when threshold = ", threshold)
print("when min_length = " , min_length)
for i in range(len(instances)):
  diff = instances[i][1] - instances[i][0]
  print(diff)
  sum = sum + diff
  diff += i
  if diff >= min_length:
    # a = sum([diff])
    res =(sum/file_length)



print(); print("Found %d Laughs" % (len (instances)))
print("Total Laughter Duration: ", sum)
print("Humour Rating (Out of 10): ")
print(res*10)


# if len(instances) > float(min_length):
# for ele in range(0, len(instances)):
#     # sum_instances = sum(['instances'])
#     a= sum([ele])
#     res=(a/file_length)
# else:
#   print('error')

#     total_dur = a+1
# print("Total Laughter Duration: ", total_dur)
# x = np.array([instances])
# b=np.sum(x)
# print(b)

if len(instances) > 0:
    full_res_y, full_res_sr = librosa.load(audio_path,sr=44100)
    wav_paths = []
    maxv = np.iinfo(np.int16).max
    
    if save_to_audio_files:
        if output_dir is None:
            raise Exception("Need to specify an output directory to save audio files")
        else:
            os.system(f"mkdir -p {output_dir}")
            for index, instance in enumerate(instances):
                laughs = laugh_segmenter.cut_laughter_segments([instance],full_res_y,full_res_sr)
                wav_path = output_dir + "/laugh_" + str(index) + ".wav"
                scipy.io.wavfile.write(wav_path, full_res_sr, (laughs * maxv).astype(np.int16))
                wav_paths.append(wav_path)
            print(laugh_segmenter.format_outputs(instances, wav_paths))

        # s = 0
        # s += laughs
        # print("Total Laughter Duration: ", s)
    
    if save_to_textgrid:
        laughs = [{'start': i[0], 'end': i[1]} for i in instances]

        tg = tgt.TextGrid()

        # laughs_tier = tgt.IntervalTier(name='laughter', objects=[
        # tgt.Interval(l['start'], l['end'], 'laugh') for l in laughs])
        # tg.add_tier(laughs_tier)
        fname = os.path.splitext(os.path.basename(audio_path))[0]
        tgt.write_to_file(tg, os.path.join(output_dir, fname + '_laughter.TextGrid'))

        print('Saved laughter segments in {}'.format(
            os.path.join(output_dir, fname + '_laughter.TextGrid')))

from sklearn.linear_model import LinearRegression

x = threshold
y = min_length

model = LinearRegression()
model.fit(instances, y)

model_pkl = pickle.load(open('model.pkl', 'rb'))