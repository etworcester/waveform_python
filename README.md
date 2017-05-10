# waveform_python
Simple python scripts to simulate waveforms using test bench ADC data

Usage

python model_waveform_calib.py #throws #rangeforband #calibtype #baseline #gaintype

#throws: How many samples?
#range for band: 0.95 plots a 95% band
#calibtype: 'linear', 'full', '64bin'
#baseline: 200 is nominal for collection, 750 or 900 for induction (can scan through artificially)
#gaintype: 'single' or 'dual' (Dual gain is x4 relative to nominal)