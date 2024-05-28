# SeizureDetection
Refer this link for the dataset and description - https://www.kaggle.com/c/seizure-detection

Description
For individuals with drug-resistant epilepsy, responsive neurostimulation systems hold promise for augmenting current therapies and transforming epilepsy care.

Of the more than two million Americans who suffer from recurrent, spontaneous epileptic seizures, 500,000 continue to experience seizures despite multiple attempts to control the seizures with medication. For these patients responsive neurostimulation represents a possible therapy capable of aborting seizures before they affect a patient's normal activities. 

Ambulatory EEG recording from dog with epilepsy. Seizure shown in red.

In order for a responsive neurostimulation device to successfully stop seizures, a seizure must be detected and electrical stimulation applied as early as possible. A seizure that builds and generalizes beyond its area of origin will be very difficult to abort via neurostimulation. Current seizure detection algorithms in commercial responsive neurostimulation devices are tuned to be hypersensitive, and their high false positive rate results in unnecessary stimulation.

In addition, physicians and researchers working in epilepsy must often review large quantities of continuous EEG data to identify seizures, which in some patients may be quite subtle. Automated algorithms to detect seizures in large EEG datasets with low false positive and false negative rates would greatly assist clinical care and basic research.

Intracranial EEG was recorded from dogs with naturally occurring epilepsy using an ambulatory monitoring system. EEG was sampled from 16 electrodes at 400 Hz, and recorded voltages were referenced to the group average. 

In addition, datasets from patients with epilepsy undergoing intracranial EEG monitoring to identify a region of brain that can be resected to prevent future seizures are included in the contest. These datasets have varying numbers of electrodes and are sampled at 500 Hz or 5000 Hz, with recorded voltages referenced to an electrode outside the brain.


# Dataset Description
Data are organized in folders containing training and testing data for each human or canine subject. The training data is organized into 1-second EEG clips labeled "Ictal" for seizure data segments, or "Interictal" for non-seizure data segments. Training data are arranged sequentially while testing data are in random order. Ictal training and testing data segments are provided covering the entire seizure, while interictal data segments are provided covering approximately the mean seizure duration for each subject. Starting points for the interictal data segments were chosen randomly from the full data record, with the restriction that no interictal segment be less than one hour before or after a seizure.

Within folders data segments are stored in matlab .mat files, arranged in a data structure with fields as follow:

data: a matrix of EEG sample values arranged row x column as electrode x time.
data_length_sec: the time duration of each data row (1 second for all data in this case)
latency: the time in seconds between the expert-marked seizure onset and the first data point in the data segment (in ictal training segments only) 
sampling_frequency: the number of data samples representing 1 second of EEG data. (Non-integer values represent an average across the full data record and may reflect missing EEG samples)
channels: a list of electrode names corresponding to the rows in the data field
The human data are from patients with temporal and extratemporal lobe epilepsy undergoing evaluation for epilepsy surgery. The iEEG recordings are from depth electrodes implanted along anterior-posterior axis of hippocampus, and from subdural electrode grids in various locations. Data sampling rates vary from 500 Hz to 5,000 Hz.

The canine data are from an implanted device acquiring data from 16 subdural electrodes. Two 4-contact strips are implanted over each hemisphere in an antero-posterior orientation. Data are recorded continuously at a sampling frequency of 400 Hz and referenced to the group average.

File descriptions
ictal_segment_N.mat - the Nth seizure training data segment
interictal_segment_N.mat - the Nth non-seizure training data segment
test_segment_N.mat -  the Nth testing data segment
Additional annotated intracranial EEG data is freely available at the International Epilepsy Electrophysiology Portal, jointly developed by the University of Pennsylvania and the Mayo Clinic.

# Code Description 
