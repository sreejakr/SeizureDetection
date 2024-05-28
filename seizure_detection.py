# -*- coding: utf-8 -*-
"""Seizure-Detection.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Gln-snQhYT8ZaSMkjbCD4z-pZsHwywIH
"""

! rmdir

! mkdir ~/.kaggle

! cp /content/drive/MyDrive/Projects/kaggle.json ~/.kaggle/

! chmod 600 ~/.kaggle/kaggle.json

!kaggle competitions download -c seizure-detection

! unzip seizure-detection

!pip install mne

import pandas as pd
import scipy.io
import zipfile
import os
import re
import mne

import tarfile
import gzip
import shutil
import numpy as np
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, KFold
from scipy.stats import skew, kurtosis
from scipy.signal import welch
from sklearn.preprocessing import StandardScaler

tar_gz_file = 'clips.tar.gz'
mat_gz_file = 'clip.mat.gz'
extracted_dir_path = "/content/dataset"

if not os.path.exists(extracted_dir_path):
    os.makedirs(extracted_dir_path)

with tarfile.open(tar_gz_file, 'r:gz') as tar:
    tar.extractall(extracted_dir_path)

"""Pick out a random ictal and interictal from each patient. Then convert the files to a dataframe (channels specified in mat file) which used for making an mne object. Ictal and interictal graphs are then analysed for all the patients."""

import random

def find_ictal_and_interictal(folder_path):
    ictal_files = []
    interictal_files = []
    test_files = []

    for file_name in os.listdir(folder_path):
        if file_name.lower().find("_ictal")!=-1:
            ictal_files.append(os.path.join(folder_path, file_name))
        elif file_name.lower().find("_interictal")!=-1:
            interictal_files.append(os.path.join(folder_path, file_name))

    print(interictal_files)
    if  len(ictal_files) ==0 or len(interictal_files)==0:
        return None, None

    return ictal_files, interictal_files

def mat_to_df(path):
  mat = scipy.io.loadmat(path)
  channels = mat['channels']
  channels_list = []
  for channel_array in channels[0][0]:
    channels_list.append(channel_array[0])
  # Rows of the DataFrame correspond to different time points, and columns correspond to different channels.
  df = pd.DataFrame(mat['data'],
                    index=channels_list)
  # The DataFrame is transposed to have time points as rows and channels as columns
  df = df.T
  df = df.loc[:, (df != df.iloc[0]).any()]
  return df, mat['freq'][0]

"""Structure of the mat file -

data: A NumPy array containing the EEG data. Each row represents a different channel, and each column represents a sample at a specific time. The values in the array represent the amplitude of the EEG signal.

channels: A structured NumPy array with a single field. Each field is a tuple containing arrays of strings representing the channel names. The channels are categorized into different types such as 'ATD', 'ITS', 'LFS', 'LG', 'PTD', and 'STS'.
"""

mat = scipy.io.loadmat("/content/dataset/Volumes/Seagate/seizure_detection/competition_data/clips/Patient_3/Patient_3_interictal_segment_315.mat")
mat

def create_mne_object(data, freq):
    # Create an MNE info file with meta data about the EEG
    info = mne.create_info(ch_names=list(data.columns),
                           sfreq=freq,
                           ch_types=['eeg'] * data.shape[-1])

    # Convert data to volts (from microvolts)
    data = data.apply(lambda x: x * 1e-6)
    data_T = data.transpose()
    raw = mne.io.RawArray(data_T, info)

    return raw

# Plot parameters
args = {
    'scalings': dict(eeg=20e-5),
    'highpass': 0.5,
    'lowpass': 70.,
    'show_scrollbars': False,
    'show': True,
}

top_directory = extracted_dir_path+'/Volumes/Seagate/seizure_detection/competition_data/clips'
file_paths_dict = {}
for subfolder in os.listdir(top_directory):
    subfolder_path = os.path.join(top_directory, subfolder)
    print(subfolder_path)
    if os.path.isdir(subfolder_path):
      ictal_files, interictal_files = find_ictal_and_interictal(subfolder_path)
      random_ictal_file = random.choice(ictal_files)
      random_interictal_file = random.choice(interictal_files)

      # Store the file paths in the dictionary with the folder name as the key to use later
      file_paths_dict[subfolder] = {
          'ictal': ictal_files,
          'interictal': interictal_files
      }

    df_ictal, freq_ictal = mat_to_df(random_ictal_file)
    df_interictal, freq_interictal = mat_to_df(random_ictal_file)

    print("Random ICTAL file:", random_ictal_file)
    ictal = create_mne_object(df_ictal, freq_ictal)
    ictal.plot(**args)
    print("Random INTERICTAL file:", random_interictal_file)
    interictal = create_mne_object(df_interictal, freq_interictal)
    interictal.plot(**args)

# for file_name in file_paths_dict['Patient_4']['interictal']:
#   df_ictal, freq_ictal = mat_to_df(file_name)
#   df_interictal, freq_interictal = mat_to_df(random_ictal_file)
#   channels_list = []
#   ictal = create_mne_object(df_ictal, freq_ictal)
#   interictal = create_mne_object(df_interictal, freq_ictal)
#   channels_list.append(set(ictal.ch_names))
#   channels_list.append(set(interictal.ch_names))

# if len(set(map(tuple, channels_list))) == 1:
#   print("All files have the same channels: True")
# else:
#   print("All files have the same channels: False")

"""Apply FFT transformation: For each file, it loads the EEG data, transposes it to have time as rows and channels as columns, and then applies the Fast Fourier Transform (FFT) to each channel across all time points. This results in a matrix of complex numbers representing the frequency components of the signal.

Slice frequencies: It selects the frequencies in the range 1 to 47Hz from the FFT result. This range was chosen based on trial and error for dimensionality reduction.

Take log10 of magnitudes: The function takes the absolute value of the FFT result to get magnitudes and then applies the log10 transformation. This is helpful for scaling.

Create DataFrame: It converts the resulting feature matrix into a Pandas DataFrame. Each row corresponds to a 1-second EEG clip for a specific channel, and each column represents a frequency bin in the specified range. The last column 'label' is added to indicate whether the clip is ictal (1) or interictal (0).
"""

def extract_eeg_features(file_dict):
    data_list = []

    for label, files in file_dict.items():
        for file in files:
            df, _ = mat_to_df(file)

            # Apply FFT to each channel (row) across all time points
            fft_result = np.abs(np.fft.fft(df.iloc[:, :-1], axis=1))

            # Slice frequencies in the range 1 to 47Hz
            freq_slice = slice(1, 48)

            # Take log10 of the magnitudes
            fft_features = np.log10(fft_result[:, freq_slice])
            fft_features = pd.DataFrame(fft_features)

            mean_values = np.mean(df.iloc[:, :-1], axis=1)
            median_values = np.median(df.iloc[:, :-1], axis=1)
            std_dev_values = np.std(df.iloc[:, :-1], axis=1)
            skewness_values = skew(df.iloc[:, :-1], axis=1)
            kurtosis_values = kurtosis(df.iloc[:, :-1], axis=1)

            # Concatenate statistical features to the dataframe
            stat_features = pd.DataFrame({
                'mean': mean_values,
                'median': median_values,
                'std_dev': std_dev_values,
                'skewness': skewness_values,
                'kurtosis': kurtosis_values
            })

            # Concatenate all features
            features = pd.concat([fft_features, stat_features], axis=1)
            del fft_features, stat_features
            # Add label (1 for ictal, 0 for interictal) as a new column
            features['label'] = np.where(label == 'ictal', 1, 0)

            data_list.append(features)

    feature_df = pd.concat(data_list, ignore_index=True)
    del data_list, features
    return feature_df



"""# Training Models"""

def split_data(data, test_size=0.2, random_state=42):
    X = data.drop(columns=['label'])
    y = data['label']
    # Use stratified sampling to maintain the distribution of 'ictal' and 'interictal'
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)

    return X_train, X_test, y_train, y_test

def train_xgboost_model(X_train, y_train, params=None):
    if params is None:
        params = {'objective': 'binary:logistic', 'max_depth': 3, 'learning_rate': 0.1, 'eval_metric': 'logloss'}

    dtrain = xgb.DMatrix(X_train, label=y_train)
    model = xgb.train(params, dtrain)

    return model

def evaluate_model(model, X_test, y_test):
    y_pred_prob = model.predict(X_test)
    y_pred = np.round(y_pred_prob)

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_prob)
    del X_test, y_pred_prob, y_pred, y_test

    print(f"Accuracy: {accuracy}")
    print(f"AUC: {auc}\n")

    return accuracy

# Creating a dictionary patient_data_dict with extracted features data
patient_data_dict = {}

for patient, person_file_dict in file_paths_dict.items():
    print(f"\nExtracting features for {patient}:\n")
    data = extract_eeg_features(person_file_dict)
    patient_data_dict[patient] = data
    del data

del file_paths_dict

all_accuracies = []
for patient, data in patient_data_dict.items():
    print(f"\Training models for {patient}:\n")
    data = data.astype(float)
    X_train, X_test, y_train, y_test = split_data(data)
    del data
    xgboost_model = train_xgboost_model(X_train, y_train)
    del X_train
    del y_train
    # Evaluate accuracy for the current patient
    dtest = xgb.DMatrix(X_test)
    xgboost_accuracy = evaluate_model(xgboost_model, dtest, y_test)
    del X_test
    del y_test

    all_accuracies.append(xgboost_accuracy)


# Calculate the average accuracy across all patients
average_accuracy = np.mean(all_accuracies)
print(f"Average Accuracy Across All Patients: {average_accuracy}")

def train_random_forest_cv(X, y, n_estimators=100, cv=5, random_state=42):
    rf_model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    kf = KFold(n_splits=cv, shuffle=True, random_state=random_state)
    fold_accuracies = []

    for train_index, test_index in kf.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        rf_model.fit(X_train, y_train)

        fold_accuracy = rf_model.score(X_test, y_test)
        fold_accuracies.append(fold_accuracy)

        del X_train, X_test, y_train, y_test

    average_accuracy = np.mean(fold_accuracies)
    print(average_accuracy)
    del rf_model, fold_accuracies

    return average_accuracy

# all_accuracies_rf = []
# for patient, data in patient_data_dict.items():
#     print(f"Training Random Forest for {patient}:\n")
#     data = data.astype(float)
#     X_train, X_test, y_train, y_test = split_data(data)
#     del data
#     rf_accuracy = train_random_forest_cv(X_train, y_train)
#     del X_train, y_train
#     all_accuracies_rf.append(rf_accuracy)

# average_accuracy_rf = np.mean(all_accuracies_rf)
# print(f"Average Accuracy Across All Patients (Random Forest): {average_accuracy_rf}")
#AUC to see how good a model is at making the right predictions.

from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

all_accuracies = []

for patient, data in patient_data_dict.items():
    print(f"{patient}:\n")

    data = data.astype(float)
    data.columns = data.columns.astype(str)
    X_train, X_test, y_train, y_test = split_data(data)
    del data

    # Create and train the ExtraTreesClassifier model
    extra_trees_model = ExtraTreesClassifier(n_estimators=100, random_state=42)
    extra_trees_model.fit(X_train, y_train)
    del X_train
    del y_train

    y_pred_prob = extra_trees_model.predict_proba(X_test)[:, 1]
    y_pred = np.round(y_pred_prob)

    etc_accuracy = evaluate_model(extra_trees_model, X_test, y_test)
    del X_test
    del y_test
    all_accuracies.append(etc_accuracy)

# Calculate the average accuracy across all patients
average_accuracy = np.mean(all_accuracies)
print(f"Average Accuracy Across All Patients: {average_accuracy}")





"""Observations:

**XGBoost with only FFT transformation** -
Patient_1:

XGBoost - Accuracy: 0.7910344827586206
XGBoost - AUC: 0.7973069642857142

Dog_3:

XGBoost - Accuracy: 0.941956106870229
XGBoost - AUC: 0.9183539993927258

Patient_3:

XGBoost - Accuracy: 0.6858789625360231
XGBoost - AUC: 0.6870688027265952

Dog_1:

XGBoost - Accuracy: 0.8338926174496645
XGBoost - AUC: 0.8844335338993871

Patient_5:

XGBoost - Accuracy: 0.9508196721311475
XGBoost - AUC: 0.6715664502398186

Patient_7:

XGBoost - Accuracy: 0.9231831865947174
XGBoost - AUC: 0.7732055708891412

Dog_4:

XGBoost - Accuracy: 0.9301074827699376
XGBoost - AUC: 0.7421295248499016

Patient_4:

XGBoost - Accuracy: 0.905647619047619
XGBoost - AUC: 0.9139963084210527

Patient_6:

XGBoost - Accuracy: 0.9251528194861528
XGBoost - AUC: 0.8525205152725669

Patient_8:

XGBoost - Accuracy: 0.9306608465608466
XGBoost - AUC: 0.906929595802469

Dog_2:

XGBoost - Accuracy: 0.8696969696969697
XGBoost - AUC: 0.6351330161846183

Patient_2:

XGBoost - Accuracy: 0.9519261381725566
XGBoost - AUC: 0.852606705284724

Average Accuracy Across All Patients: 0.8866630753395403

With Statistical features average acuracy  = 0.8896201800414341


Extra Trees classifier

Patient_1:

Accuracy: 0.9187931034482759
AUC: 0.8990714285714285

Dog_3:

Accuracy: 0.9549570610687023
AUC: 0.7978692883403361

Patient_3:

Accuracy: 0.9999798270893372
AUC: 0.9999728625395112

Dog_1:

Accuracy: 0.8946728187919463
AUC: 0.8356005725498629

Patient_5:

Accuracy: 0.9999668488160292
AUC: 0.999662962962963

Patient_7:

Accuracy: 0.999964498721954
AUC: 0.9997816061563524

Dog_4:

Accuracy: 0.9444576632753529
AUC: 0.6746521327559517

Patient_4:

Accuracy: 1.0
AUC: 1.0

Patient_6:

Accuracy: 0.999995995995996
AUC: 0.9999733333333334

Patient_8:

Accuracy: 0.9938523809523809
AUC: 0.9683513157894736

Dog_2:

Accuracy: 0.8885227272727273
AUC: 0.579745360991816

Patient_2:

Accuracy: 0.994694364851958
AUC: 0.9451637245564687

Average Accuracy Across All Patients: 0.9658214408570549
"""

!curl --header 'Host: dl.boxcloud.com' --header 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' --header 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' --header 'Accept-Language: en-US,en;q=0.9' --header 'Referer: https://nihcc.app.box.com/' 'https://dl.boxcloud.com/zip_download/zip_download?ProgressReportingKey=4C3C8BC4231B4182830BDF5A2093C1B8&d=36938765345&ZipFileName=CXR8.zip&Timestamp=1716293195&SharedLink=https%3A%2F%2Fnihcc.box.com%2Fv%2FChestXray-NIHCC&HMAC2=e5ecc57e9a677dac0abd3882d91bc83e8d3c9d82079813bd49a374bbbeaa83c3' -L -o 'CXR8.zip'

!unzip CXR8

