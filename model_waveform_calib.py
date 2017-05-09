#!/usr/local/bin/python

import ROOT
import math
from array import array
import random
import sys

ROOT.gROOT.SetStyle("Plain")
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit()
ROOT.gStyle.SetCanvasColor(0)
ROOT.gStyle.SetTitleFillColor(0)
ROOT.gStyle.SetTitleBorderSize(0)
ROOT.gStyle.SetFrameBorderMode(0)
ROOT.gStyle.SetMarkerSize(0.2)
ROOT.gStyle.SetMarkerStyle(7)
ROOT.gStyle.SetTitleX(0.5)
ROOT.gStyle.SetTitleAlign(23)
ROOT.gStyle.SetLineWidth(3)
ROOT.gStyle.SetLineColor(1)
ROOT.gStyle.SetTitleSize(0.03,"t")

def filldiff(up,down):
      n = up.GetN()
      diffgraph = ROOT.TGraph(2*n);
      i = 0
      xup = ROOT.Double(-9.9)
      yup = ROOT.Double(-9.9)
      xlo = ROOT.Double(-9.9)
      ylo = ROOT.Double(-9.9)
      while i<n:
          up.GetPoint(i,xup,yup);
          down.GetPoint(n-i-1,xlo,ylo);
          diffgraph.SetPoint(i,xup,yup);
          diffgraph.SetPoint(n+i,xlo,ylo);
          i += 1
      return diffgraph;


def readcalib(gain_dict,offset_dict,corr_dict):
    calibfile = open("adccalib.txt","r")
    lines = calibfile.readlines()
    for line in lines:
        if ("***" in line or "Row" in line): continue
        cols = line.split()
        chip = cols[3]
        chan = cols[5]
        gain = float(cols[7])
        offset = float(cols[9])
        mykey = chip+"_"+chan
        gain_dict[mykey] = gain
        offset_dict[mykey] = offset
    corrfile = open("adccorr.txt","r")
    lines = corrfile.readlines()
    ii = 0
    kk = 0
    kksum = 0
    kkdiv = 0
    for line in lines:
          if ("***" in line or "Row" in line): continue
          cols = line.split()
          chip = cols[5]
          chan = cols[7]
          gain = float(cols[9])
          offset = float(cols[11])
          code = int(cols[13])
          mean = float(cols[15])
          corr = mean - (code*gain + offset)
          mykey = chip+"_"+chan+"_"+str(code)
          corr_dict[mykey] = corr
          if (abs(corr)<20):
                kksum += corr
                kkdiv += 1
          else:
                kksum += 0
          kk += 1
          if (kk == 64):
                mykey2 = chip+"_"+chan+"_calib64_bin"+str(ii)
                if (kkdiv==0):
                      corr_dict[mykey2] = 0
                else:
                      corr_dict[mykey2] = kksum/kkdiv
                kk = 0
                kksum = 0
                kkdiv = 0
                if (ii==63):
                      ii = 0
                else:
                      ii += 1
    calibfile.close()
    corrfile.close()
    return
        
#Get number of throws and percent to plot from input
nrand = int(sys.argv[1])
myrange = float(sys.argv[2])
myrangepc = str(int(100.*myrange))
calibtype = sys.argv[3] # 'linear', 'full', '64bin'
baseline = int(sys.argv[4])

if (calibtype == 'linear'):
      calibtext = "mV (Linear Calibration)"
elif (calibtype == 'full'):
      calibtext = "mV (Full Calibration)"
elif (calibtype == '64bin'):
      calibtext = "mV (64-bin Nonlinear Calibration)"
else:
      raise Exception("Calibration type must be linear or full")

bltext = str(baseline)+"mv"


#Set threshold, etc
threshold = 4 #mV

#Read in original waveform and put into TGraph

collfile = "waveforms/angle0coll/event1/chan10430.txt"
#collfile = "waveforms/angle0coll/event1/chan10530.txt"

mypulsefile = open(collfile,"r")
lines = mypulsefile.readlines()
mypulsefile.close()

ticks = []
waveform_orig = []
i = 0
for line in lines:
    if (i < 1230 or i > 1370):
          i += 1
          continue
    waveform_orig.append(float(line.strip())+baseline)
    ticks.append(float(i))
    i += 1
n = len(waveform_orig)

waveform_copy = waveform_orig[:]

#Get nominal info for orignal waveform
baselinelow_nom = sum(waveform_copy[i] for i in range(0,20) if waveform_copy[i]>0)/20
baselinehi_nom = sum(waveform_copy[i] for i in range(n-20,n) if waveform_copy[i]>0)/20
baseline_nom = 0.5*(baselinelow_nom+baselinehi_nom)
peak_nom = max(waveform_copy)
peak_to_baseline_nom = peak_nom-baseline_nom
i_crossing = next((i for i,v in enumerate(waveform_copy) if v>baseline_nom+threshold), 0)
j_crossing = next((i for i,v in enumerate(waveform_copy) if (v<baseline_nom+threshold and i > i_crossing)),0)
int_under_pulse_nom = sum(waveform_copy[i]-baseline_nom for i in range(i_crossing,j_crossing))

ticks = array('d',ticks)
waveform_orig = array('d',waveform_orig)
g_pulse_orig = ROOT.TGraph(n,ticks,waveform_orig)

# Read in test stand data and sample from histogram to create nrand new waveforms

# For testing insist on single chip
badchips = [61, 67, 68] #Keep good and fair
#badchips = [61, 67, 68, 64, 66, 63, 69] #Keep only good
goodchip = [60, 62, 65]

datafile = ROOT.TFile("responseplots.root","READ")
hlist = datafile.GetListOfKeys()
nhist = len(hlist)
badcodefile = ROOT.TFile("badcodes.root")
gain_dict = {}
offset_dict = {}
corr_dict = {}
readcalib(gain_dict,offset_dict,corr_dict)

#Set up histograms
h_peak_to_baseline = ROOT.TH1F("h_peak_to_baseline","Peak - Baseline", 100, 20., 30.)
h_peak_to_baseline_diff = ROOT.TH1F("h_peak_to_baseline_diff","Peak - Baseline (True - Distorted)", 100, -5., 5.)
h_int_under_pulse = ROOT.TH1F("h_int_under_pulse","Integral Under Pulse", 200, 100, 200)
h_int_under_pulse_diff = ROOT.TH1F("h_int_under_pulse_diff","Integral Under Pulse (True - Distorted)", 200, -20, 20) 

waveform_nom = []
list_waveform_distort = []
list_waveform_distort_removeall = []
list_waveform_distort_removebad = []
list_waveform_distort_interp = []
it = 0
nointerp = 0
while it < nrand:
    waveform_distort = []
    waveform_distort_removeall = []
    waveform_distort_removebad = []
    hname = hlist[random.randint(1, nhist)-1].GetName()
    fields = hname.split("_")
    chip = fields[1][1:]
    if (int(chip) not in goodchip):
          continue
    chan = fields[2]
    if (int(chan) > 5):
          continue
    resp_hist = datafile.Get(hname)
    if (it%100==0): print "Pulse #",it

    #Get bad codes for this chip/chan
    badcode_name = "badchan_chip"+chip+"_chan"+chan
    badcode_hist = badcodefile.Get(badcode_name)
    nbins = badcode_hist.GetNbinsX()
    ibin = 0
    badcodelist = []
    while (ibin < nbins):
          if (badcode_hist.GetBinContent(ibin) > 0):
                badcodelist.append(int(badcode_hist.GetBinCenter(ibin)))
          ibin += 1
    #print "Bad code list for chip ", chip, " ,chan ",chan, "= ", badcodelist

    #Get calibration info
    mykey = chip+"_"+chan
    gain = gain_dict[mykey]
    offset = offset_dict[mykey]

    #Do stuff to waveform
    for mv in waveform_copy:
        ybin = resp_hist.GetYaxis().FindBin(mv)
        projx = resp_hist.ProjectionX("projx",ybin,ybin)
        myadc = int(projx.GetRandom())
        mymv_linear = myadc*gain + offset
        if (calibtype == 'linear'):
              mymv_corr = mymv_linear
        elif (calibtype == 'full'):
              codekey = mykey+"_"+str(myadc)
              calibcorr = corr_dict[codekey]
              mymv_corr = mymv_linear + calibcorr
        elif (calibtype == '64bin'):
              codebin = int(myadc/64)
              codekey = mykey+"_calib64_bin"+str(codebin)
              calibcorr = corr_dict[codekey]              
              mymv_corr = mymv_linear + calibcorr
        waveform_distort.append(mymv_corr)
        if (myadc%64 == 0 or myadc%64 == 63):
              waveform_distort_removeall.append(-99)
        else:
              waveform_distort_removeall.append(mymv_corr)
        if (myadc in badcodelist):
              waveform_distort_removebad.append(-99)
        else:
              waveform_distort_removebad.append(mymv_corr)
    list_waveform_distort.append(waveform_distort)
    list_waveform_distort_removeall.append(waveform_distort_removeall)
    list_waveform_distort_removebad.append(waveform_distort_removebad)
    
    #Do interpolation:
    count = 0
    waveform_distort_interp = []
    for mv in waveform_distort_removebad:
          if (mv == -99):
                ntry = 10
                itry = 0
                noval = 1
                while (itry < ntry and noval):
                      ii = count-(itry+1)
                      if (ii >= 0):
                            if (waveform_distort_removebad[ii] != -99):
                                  noval = 0
                                  break
                      itry += 1
                jtry = 0
                noval = 1
                while (jtry < ntry and noval):
                      jj = count+(jtry+1)
                      if (jj < len(waveform_distort_removebad)-1):
                            if (waveform_distort_removebad[jj] != -99):
                                  noval = 0
                                  break
                      jtry += 1

                if (not noval):
                      newmv = 0.5*(waveform_distort_removebad[ii]+waveform_distort_removebad[jj])
                      waveform_distort_interp.append(newmv)
                else:
                      waveform_distort_interp.append(mv)
                      nointerp += 1
                      #print "Warning, can not interpolate: ", count, waveform_distort_removebad[count-10:count+11]
          else:
                waveform_distort_interp.append(mv)
          count += 1
    list_waveform_distort_interp.append(waveform_distort_interp)

    #Now analyze the interpolated pulse
    baselinelow = sum(waveform_distort_interp[i] for i in range(0,20) if waveform_distort_interp[i]>0)/20
    baselinehi = sum(waveform_distort_interp[i] for i in range(n-20,n) if waveform_distort_interp[i]>0)/20
    baseline_meas = 0.5*(baselinelow+baselinehi)
    peak = max(waveform_distort_interp)
    peak_to_baseline = peak-baseline_meas
    h_peak_to_baseline.Fill(peak_to_baseline)
    h_peak_to_baseline_diff.Fill(peak_to_baseline_nom-peak_to_baseline)
    i_crossing = next((i for i,v in enumerate(waveform_distort_interp) if v>baseline_meas+threshold), 0)
    j_crossing = next((i for i,v in enumerate(waveform_distort_interp) if (v<baseline_meas+threshold and i > i_crossing)), 0)
    int_under_pulse = sum(waveform_distort_interp[i]-baseline_meas for i in range(i_crossing,j_crossing))
    h_int_under_pulse.Fill(int_under_pulse)
    h_int_under_pulse_diff.Fill(int_under_pulse_nom-int_under_pulse)
    
    it += 1
    

print "Total number of values for which interpolation was not possible: ", nointerp
waveform_distort_1sighi = []
waveform_distort_1siglo = []
waveform_distort_hiall = []
waveform_distort_loall = []

waveform_distort_removeall_1sighi = []
waveform_distort_removeall_1siglo = []
waveform_distort_removeall_hiall = []
waveform_distort_removeall_loall = []

waveform_distort_removebad_1sighi = []
waveform_distort_removebad_1siglo = []
waveform_distort_removebad_hiall = []
waveform_distort_removebad_loall = []

waveform_distort_interp_1sighi = []
waveform_distort_interp_1siglo = []
waveform_distort_interp_hiall = []
waveform_distort_interp_loall = []

i = 0
jlo = int(nrand/2) - 1 - int(myrange*(nrand)/2)
jhi = int(nrand/2) - 1 + int(myrange*(nrand)/2)
while i < n:
    list_thistick = [l[i] for l in list_waveform_distort]
    list_thistick_sorted = sorted(list_thistick)
    waveform_distort_1siglo.append(list_thistick_sorted[jlo])
    waveform_distort_1sighi.append(list_thistick_sorted[jhi])
    waveform_distort_hiall.append(max(list_thistick))
    waveform_distort_loall.append(min(list_thistick))

    list_thistick_removeall = [l[i] for l in list_waveform_distort_removeall]
    list_thistick_removeall_sorted = sorted(list_thistick_removeall)
    waveform_distort_removeall_1siglo.append(list_thistick_removeall_sorted[jlo])
    waveform_distort_removeall_1sighi.append(list_thistick_removeall_sorted[jhi])
    waveform_distort_removeall_hiall.append(max(list_thistick_removeall))
    waveform_distort_removeall_loall.append(min(list_thistick_removeall))

    list_thistick_removebad = [l[i] for l in list_waveform_distort_removebad]
    list_thistick_removebad_sorted = sorted(list_thistick_removebad)
    waveform_distort_removebad_1siglo.append(list_thistick_removebad_sorted[jlo])
    waveform_distort_removebad_1sighi.append(list_thistick_removebad_sorted[jhi])
    waveform_distort_removebad_hiall.append(max(list_thistick_removebad))
    waveform_distort_removebad_loall.append(min(list_thistick_removebad))

    list_thistick_interp = [l[i] for l in list_waveform_distort_interp]
    list_thistick_interp_sorted = sorted(list_thistick_interp)
    waveform_distort_interp_1siglo.append(list_thistick_interp_sorted[jlo])
    waveform_distort_interp_1sighi.append(list_thistick_interp_sorted[jhi])
    waveform_distort_interp_hiall.append(max(list_thistick_interp))
    waveform_distort_interp_loall.append(min(list_thistick_interp))
    
    i += 1

waveform_distort_1siglo = array('d',waveform_distort_1siglo)
waveform_distort_1sighi = array('d',waveform_distort_1sighi)
waveform_distort_loall = array('d',waveform_distort_loall)
waveform_distort_hiall = array('d',waveform_distort_hiall)
g_pulse_distort_1siglo = ROOT.TGraph(n,ticks,waveform_distort_1siglo)
g_pulse_distort_1sighi = ROOT.TGraph(n,ticks,waveform_distort_1sighi)
g_pulse_distort_loall = ROOT.TGraph(n,ticks,waveform_distort_loall)
g_pulse_distort_hiall = ROOT.TGraph(n,ticks,waveform_distort_hiall)

waveform_distort_removeall_1siglo = array('d',waveform_distort_removeall_1siglo)
waveform_distort_removeall_1sighi = array('d',waveform_distort_removeall_1sighi)
waveform_distort_removeall_loall = array('d',waveform_distort_removeall_loall)
waveform_distort_removeall_hiall = array('d',waveform_distort_removeall_hiall)
g_pulse_distort_removeall_1siglo = ROOT.TGraph(n,ticks,waveform_distort_removeall_1siglo)
g_pulse_distort_removeall_1sighi = ROOT.TGraph(n,ticks,waveform_distort_removeall_1sighi)
g_pulse_distort_removeall_loall = ROOT.TGraph(n,ticks,waveform_distort_removeall_loall)
g_pulse_distort_removeall_hiall = ROOT.TGraph(n,ticks,waveform_distort_removeall_hiall)

waveform_distort_removebad_1siglo = array('d',waveform_distort_removebad_1siglo)
waveform_distort_removebad_1sighi = array('d',waveform_distort_removebad_1sighi)
waveform_distort_removebad_loall = array('d',waveform_distort_removebad_loall)
waveform_distort_removebad_hiall = array('d',waveform_distort_removebad_hiall)
g_pulse_distort_removebad_1siglo = ROOT.TGraph(n,ticks,waveform_distort_removebad_1siglo)
g_pulse_distort_removebad_1sighi = ROOT.TGraph(n,ticks,waveform_distort_removebad_1sighi)
g_pulse_distort_removebad_loall = ROOT.TGraph(n,ticks,waveform_distort_removebad_loall)
g_pulse_distort_removebad_hiall = ROOT.TGraph(n,ticks,waveform_distort_removebad_hiall)

waveform_distort_interp_1siglo = array('d',waveform_distort_interp_1siglo)
waveform_distort_interp_1sighi = array('d',waveform_distort_interp_1sighi)
waveform_distort_interp_loall = array('d',waveform_distort_interp_loall)
waveform_distort_interp_hiall = array('d',waveform_distort_interp_hiall)
g_pulse_distort_interp_1siglo = ROOT.TGraph(n,ticks,waveform_distort_interp_1siglo)
g_pulse_distort_interp_1sighi = ROOT.TGraph(n,ticks,waveform_distort_interp_1sighi)
g_pulse_distort_interp_loall = ROOT.TGraph(n,ticks,waveform_distort_interp_loall)
g_pulse_distort_interp_hiall = ROOT.TGraph(n,ticks,waveform_distort_interp_hiall)

g_pulse_distort_band = filldiff(g_pulse_distort_1sighi,g_pulse_distort_1siglo)
g_pulse_distort_maxband = filldiff(g_pulse_distort_hiall,g_pulse_distort_loall)
g_pulse_distort_band.SetFillColor(ROOT.kCyan)
g_pulse_distort_maxband.SetFillColor(ROOT.kMagenta)
g_pulse_distort_band.SetLineWidth(0)
g_pulse_distort_maxband.SetLineWidth(0)
c1 = ROOT.TCanvas("c1","c1",800,800)
ylo = min(waveform_distort_loall)-3
yhi = max(waveform_distort_hiall)+3
h1 = c1.DrawFrame(1250,ylo,1350,yhi)
h1.GetXaxis().SetNdivisions(505)
h1.GetXaxis().SetTitle("Ticks")
h1.GetYaxis().SetTitleOffset(1.2)
h1.GetYaxis().SetTitle(calibtext)
h1.GetXaxis().SetLabelSize(0.03)
h1.GetYaxis().SetLabelSize(0.03)
h1.SetTitle("Selected Chips")
g_pulse_distort_maxband.Draw("Fsame")
g_pulse_distort_band.Draw("Fsame")
g_pulse_orig.Draw("LPsame")
l1 = ROOT.TLegend(0.55,0.78,0.89,0.89)
l1.AddEntry(g_pulse_orig,"Original pulse","L")
l1.AddEntry(g_pulse_distort_band,"Distorted pulse "+myrangepc+"% band","F")
l1.AddEntry(g_pulse_distort_maxband,"Distorted pulse all","F")
l1.SetBorderSize(0)
l1.SetFillStyle(0)
l1.Draw("same")
c1.RedrawAxis()
c1.SaveAs("plots/waveform_overlay1_"+calibtype+"_"+bltext+".png")

g_pulse_distort_removeall_band = filldiff(g_pulse_distort_removeall_1sighi,g_pulse_distort_removeall_1siglo)
g_pulse_distort_removeall_maxband = filldiff(g_pulse_distort_removeall_hiall,g_pulse_distort_removeall_loall)
g_pulse_distort_removeall_band.SetFillColor(ROOT.kCyan)
g_pulse_distort_removeall_maxband.SetFillColor(ROOT.kMagenta)
g_pulse_distort_removeall_band.SetLineWidth(0)
g_pulse_distort_removeall_maxband.SetLineWidth(0)
c2 = ROOT.TCanvas("c2","c2",800,800)
ylo = min(waveform_distort_loall)-3
yhi = max(waveform_distort_removeall_hiall)+3
h2 = c2.DrawFrame(1250,ylo,1350,yhi)
h2.GetXaxis().SetNdivisions(505)
h2.GetXaxis().SetTitle("Ticks")
h2.GetYaxis().SetTitleOffset(1.2)
h2.GetYaxis().SetTitle(calibtext)
h2.GetXaxis().SetLabelSize(0.03)
h2.GetYaxis().SetLabelSize(0.03)
h2.SetTitle("Remove All 0/63 Codes")
g_pulse_distort_removeall_maxband.Draw("Fsame")
g_pulse_distort_removeall_band.Draw("Fsame")
g_pulse_orig.Draw("LPsame")
l1.Draw("same")
c2.RedrawAxis()
c2.SaveAs("plots/waveform_overlay2_"+calibtype+"_"+bltext+".png")

g_pulse_distort_removebad_band = filldiff(g_pulse_distort_removebad_1sighi,g_pulse_distort_removebad_1siglo)
g_pulse_distort_removebad_maxband = filldiff(g_pulse_distort_removebad_hiall,g_pulse_distort_removebad_loall)
g_pulse_distort_removebad_band.SetFillColor(ROOT.kCyan)
g_pulse_distort_removebad_maxband.SetFillColor(ROOT.kMagenta)
g_pulse_distort_removebad_band.SetLineWidth(0)
g_pulse_distort_removebad_maxband.SetLineWidth(0)
c3 = ROOT.TCanvas("c3","c3",800,800)
ylo = min(waveform_distort_loall)-3
yhi = max(waveform_distort_removebad_hiall)+3
h3 = c3.DrawFrame(1250,ylo,1350,yhi)
h3.GetXaxis().SetNdivisions(505)
h3.GetXaxis().SetTitle("Ticks")
h3.GetYaxis().SetTitleOffset(1.2)
h3.GetYaxis().SetTitle(calibtext)
h3.GetXaxis().SetLabelSize(0.03)
h3.GetYaxis().SetLabelSize(0.03)
h3.SetTitle("Remove Bad Codes")
g_pulse_distort_removebad_maxband.Draw("Fsame")
g_pulse_distort_removebad_band.Draw("Fsame")
g_pulse_orig.Draw("LPsame")
l1.Draw("same")
c3.RedrawAxis()
c3.SaveAs("plots/waveform_overlay3_"+calibtype+"_"+bltext+".png")

g_pulse_distort_interp_band = filldiff(g_pulse_distort_interp_1sighi,g_pulse_distort_interp_1siglo)
g_pulse_distort_interp_maxband = filldiff(g_pulse_distort_interp_hiall,g_pulse_distort_interp_loall)
g_pulse_distort_interp_band.SetFillColor(ROOT.kCyan)
g_pulse_distort_interp_maxband.SetFillColor(ROOT.kMagenta)
g_pulse_distort_interp_band.SetLineWidth(0)
g_pulse_distort_interp_maxband.SetLineWidth(0)
c4 = ROOT.TCanvas("c4","c4",800,800)
ylo = min(waveform_distort_loall)-3
yhi = max(waveform_distort_interp_hiall)+3
h4 = c4.DrawFrame(1250,ylo,1350,yhi)
h4.GetXaxis().SetNdivisions(505)
h4.GetXaxis().SetTitle("Ticks")
h4.GetYaxis().SetTitleOffset(1.2)
h4.GetYaxis().SetTitle(calibtext)
h4.GetXaxis().SetLabelSize(0.03)
h4.GetYaxis().SetLabelSize(0.03)
h4.SetTitle("Remove Bad Codes and Interpolate")
g_pulse_distort_interp_maxband.Draw("Fsame")
g_pulse_distort_interp_band.Draw("Fsame")
g_pulse_orig.Draw("LPsame")
l1.Draw("same")
c4.RedrawAxis()
c4.SaveAs("plots/waveform_overlay4_"+calibtype+"_"+bltext+".png")

c5 = ROOT.TCanvas("c5","c5",800,800)
h_peak_to_baseline.SetLineWidth(3)
h_peak_to_baseline.GetXaxis().SetTitle("Peak-Baseline (mV)")
h_peak_to_baseline.Draw()
ROOT.gStyle.SetOptStat(1111)
c5.SaveAs("plots/peak_to_baseline_"+calibtype+".png")

c6 = ROOT.TCanvas("c6","c6",800,800)
h_peak_to_baseline_diff.SetLineWidth(3)
h_peak_to_baseline_diff.GetXaxis().SetTitle("Peak-Baseline Difference (mV) (True-Distorted)")
h_peak_to_baseline_diff.Draw()
c6.SaveAs("plots/peak_to_baseline_diff_"+calibtype+"_"+bltext+".png")

c7 = ROOT.TCanvas("c7","c7",800,800)
h_int_under_pulse.SetLineWidth(3)
h_int_under_pulse.GetXaxis().SetTitle("Integral Under Pulse (mV)")
h_int_under_pulse.Draw()
c7.SaveAs("plots/int_under_pulse_"+calibtype+"_"+bltext+".png")

c8 = ROOT.TCanvas("c8","c8",800,800)
h_int_under_pulse_diff.SetLineWidth(3)
h_int_under_pulse_diff.GetXaxis().SetTitle("Integral Under Pulse Difference (mV) (True-Distorted)")
h_int_under_pulse_diff.Draw()
c8.SaveAs("plots/int_under_pulse_diff_"+calibtype+"_"+bltext+".png")


