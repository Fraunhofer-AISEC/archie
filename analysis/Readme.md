# Analysis

This is an example analysis of an AES attack. It is the same as described in "ARCHIE: A QEMU-Based Framework for Architecture-Independent Evaluation of Faults", which will be published with IEEE. The data temporarily at [https://syncandshare.lrz.de/getlink/fiH6PtwwY2yXpzGCexzntfaX/](https://syncandshare.lrz.de/getlink/fiH6PtwwY2yXpzGCexzntfaX/). We are currently looking for a more permanent solution of publishing the data.

## Attacks

Both attacks are described in full details here:

K. Garb and J. Obermaier, "Temporary Laser Fault Injection into Flash Memory: Calibration, Enhanced Attacks, and Countermeasures," 2020 IEEE 26th International Symposium on On-Line Testing and Robust System Design (IOLTS), 2020, pp. 1-7, doi: 10.1109/IOLTS50870.2020.9159712.

### Saha diagonal fault attack.

The Saha diagonal fault attack tries to introduce a fault at round 8 (assuming AES-128) inside the AES encrypted data (AES state). By using multiple faulted cyphertexts and the golden cyphertext (non faulted), Possible round key candidates can be calculated. The attack was originally published at

D. Saha, D. Mukhopadhyay, and D. Roy Chowdhury, “A Diagonal Fault
Attack on the Advanced Encryption Standard,” IACR Cryptology ePrint
Archive, vol. 2009, p. 581, 2009.

### Tenth round skip attack

In this attack we try to skip the last round of AES. When successfull the attacker optains the 9th round state. With the help of the original cyphertext, he then can proceed to calculate the tenth round key, which is trivial. With this roundkey he then can calculate the original key used. Advantage over a Saha diagonal fault attack is less needed faulted cyphertext. Disadvantage for this in practise is a precise fault is needed.

## Files

### analysis.ipynb

This file is the main analysis script. It tries to use the Tenth round attack skip and the saha diagonal fault attack to retrieve the tenth round key. The original key is not calculated, as it is only reversing the key scheduler, which is trivial with a round key at hand.
Furthermore it shows how to filter for specific experiments matching ones criteria. It shows how the filter functions provided can be used and how to read data from the HDF5 file.

### analysisfunctions.py

Contains functions needed to access and filter the hdf5 file for fault data. Currently supported:

* Get complete fault configurations
* Get tbinfo, tbexec, and meminfo compressed or deflated
* Query fault configuration inside the file without holding it in RAM

All functions either take a function handle or the fault group handle for their operation.
For example usage see analysis.ipynb

### tenthRound.py

Contains the logic to retrieve the tenth round key by using the original cyphertext and the 9th round state. Copyright K. Garb

### sahadiagonalfault.py

Contains the logic of a Saha diagonal fault analysis using the M0 model. Copyright K. Garb
