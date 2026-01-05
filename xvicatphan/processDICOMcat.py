# %reset -f

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)



import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pydicom as dicom
import numpy as np
from scipy.interpolate import interp1d
from scipy.interpolate import interpn
import datetime
# from scipy.interpolate import interpn,interp1d
# from scipy.fft import fft
from scipy.signal import find_peaks
from scipy.signal import peak_widths

# from IS_CTP528 import image_selector_CTP528
# from IS_CTP528_3slice import image_selector_CTP528

# from analysis_CTP404 import analysis_CTP404
# from analysis_CTP486 import analysis_CTP486
# from analysis_CTP528 import analysis_CTP528
# from FindCatPhanCentre import FindCatPhanCentre
# from FindSliceCTP528 import FindSliceCTP528
# from FindCTP404Rotation import FindCTP404Rotation
# from analysis_CTP404_scaling import ScalingXY_CTP404



def image_selector_CTP528(ds, z):
    import numpy as np
    from scipy.interpolate import interpn
    
    # Takes given slice +/- 2 images, will find maximum image and then three slice average around it
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n--- Performing 3-slice averaging of CTP528 module\n')
    
    img_zm2 = ds[z-2].pixel_array
    img_zm1 = ds[z-1].pixel_array
    img_z = ds[z].pixel_array
    img_zp1 = ds[z+1].pixel_array
    img_zp2 = ds[z+2].pixel_array

    
    sz    = (ds[z].Rows,ds[z].Columns)
    space = ds[z].PixelSpacing
    c     = (int(sz[0]/2),int(sz[1]/2))
    
    # Trace through line pairs
    lp_r = 47  # radius in mm so scalable to other image matrix sizes
    
    
    tfine = np.linspace(0,np.pi,500)
    lp_b = lp_r/space[0]*np.cos(tfine) + c[0] # x coordinates of line pair trace for visual purposes
    lp_a = lp_r/space[1]*np.sin(tfine) + c[1] # y coordinates of line pair trace for visual purposes
    
    print('lp_b:{}'.format(lp_b[:10]))
    print('lp_a:{}'.format(lp_a[:10]))
    # Get indexing for image matrix
    x = np.linspace(0,(sz[0]-1)/2,sz[0])
    y = np.linspace(0,(sz[1]-1)/2,sz[1])
    
    # Make a copy of images
    im1 = img_zm2
    im2 = img_zm1
    im3 = img_z
    im4 = img_zp1
    im5 = img_zp2
    
    # Initialize variables to store line pair profiles
    f1 = np.zeros(len(lp_a))
    f2 = np.zeros(len(lp_a))
    f3 = np.zeros(len(lp_a))
    f4 = np.zeros(len(lp_a))
    f5 = np.zeros(len(lp_a))
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Interpolating line pair profiles...\n')
    
    # Interpolate profiles through line pairs for each image
    print([lp_a[0]*space[0],lp_b[0]*space[1]])
    print(im1[0]+2048)
    for i in range(len(lp_a)):
        f1[i] = interpn((x,y),im1+2048,[lp_a[i]*space[0],lp_b[i]*space[1]])
        
    for i in range(len(lp_a)):
        f2[i] = interpn((x,y),im2+2048,[lp_a[i]*space[0],lp_b[i]*space[1]])
        
    for i in range(len(lp_a)):
        f3[i] = interpn((x,y),im3+2048,[lp_a[i]*space[0],lp_b[i]*space[1]])
        
    for i in range(len(lp_a)):
        f4[i] = interpn((x,y),im4+2048,[lp_a[i]*space[0],lp_b[i]*space[1]])
        
    for i in range(len(lp_a)):
        f5[i] = interpn((x,y),im5,[lp_a[i]*space[0],lp_b[i]*space[1]])
        
    # Find slice with highest average intensity  
    means = [np.mean(f1),np.mean(f2),np.mean(f3),np.mean(f4),np.mean(f5)]
    tmp = np.argmax(means)
    
    
    try:
        idx = np.zeros(5)
        idx[tmp-1] = 1
        idx[tmp] = 1
        idx[tmp+1] = 1
    except:
        if tmp == 0:
            idx = [1, 1, 0, 0, 0]
        elif tmp == 4:
            idx = [0, 0, 0, 1, 1]
        else:
            with open('ScriptLog.txt', 'a') as file:
                file.write('Error: Three slice averaging failed. Returning single image\n')
            return im3, means, 0
                
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Calculating 3-slice average for CTP528\n')
    
    # Initialize blank image and add images together with highest intensity
    im = np.zeros(sz)
    z_mean = []
    if idx[0]:
        im = np.array(im) + np.array(img_zm2)
        z_mean.append(-2)
        # print('Slice 1')
        
    if idx[1]:
        im = np.array(im) + np.array(img_zm1)
        z_mean.append(-1)
        # print('Slice 2')
    
    if idx[2]:
        im = np.array(im) + np.array(img_z)
        z_mean.append(0)
        # print('Slice 3')
    
    if idx[3]:
        im = np.array(im) + np.array(img_zp1)
        z_mean.append(1)
        # print('Slice 4')
    
    if idx[4]:
        im = np.array(im) + np.array(img_zp2)
        z_mean.append(2)
        # print('Slice 5')
        
    # Calculate pixel-averaged image 
    im = np.array(im)/sum(idx)
    z_mean = np.mean(z_mean)  # middle slice, = 0 if original z is centre slice
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('3-slice average for CTP528 complete.\n')
    
    return im, means, z_mean





def FindCatPhanCentre(im):

    sz = np.zeros((2,1))
    sz[0] = len(im)    
    sz[1] = len(im[0])
    matrix_c = (np.round(sz[0]/2),np.round(sz[1]/2)) # Start with centre pixel
    
    # x = np.linspace(0,int(sz[0]-1),int(sz[0]))
    px = im[int(matrix_c[0]),:]
    py = im[:,int(matrix_c[1])]
    # dpx = np.diff(px)     Can use derivative to find Catphan edges too...
    # dpy = np.diff(py)
    
    
    # Find edges of Catphan by finding first/last pixels above a threshold HU 
    thres = 400
    offset= 1       # shift by 1 since indexing starts at 0

    try:
        x1 = next(x for x, val in enumerate(px) if val > thres) + offset
        y1 = next(x for x, val in enumerate(py) if val > thres) - offset
        x2 = next(x for x, val in reversed(list(enumerate(px))) if val > thres) + offset
        y2 = next(x for x, val in reversed(list(enumerate(py))) if val > thres) - offset
        
    except:
        thres = 300
        x1 = next(x for x, val in enumerate(px) if val > thres) + offset
        y1 = next(x for x, val in enumerate(py) if val > thres) - offset
        x2 = next(x for x, val in reversed(list(enumerate(px))) if val > thres) + offset
        y2 = next(x for x, val in reversed(list(enumerate(py))) if val > thres) - offset
        
    szx = x2 - x1
    szy = y2 - y1
    
    c = [(x1+x2)/2,(y1+y2)/2]   # Centre of Catphan
    
    outer_r = (szx+szy)/4      # Take radius as avg x and y diameters, crude but for visual purposes only
    t = np.linspace(0,2*np.pi,100)
    outer_a_new = outer_r*np.cos(t) + c[0]
    outer_b_new = outer_r*np.sin(t) + c[1]
    
    return c, [outer_a_new,outer_b_new]



def FindSliceCTP528(ds): 
    def get_lp_profile(x, y, npeaks, lpx, lpy, img):
        
        
        # Interpolate profile across line pair
        x1 = np.linspace(lpx[0],lpx[1],50)
        y1 = np.linspace(lpy[0],lpy[1],50)
        f1 = np.zeros(len(x1))
        
        for i in range(len(x1)):
            f1[i] = interpn((x,y),img,[y1[i],x1[i]])
        
        # Derivative of profile
        df1 = np.diff(f1)    

        return f1, df1
    

    z_tmp      = 86 #50#262

    outer_c, _ = FindCatPhanCentre(ds[z_tmp].pixel_array)

    
    idx_tmp    = 10    # arbitrary slice just to grab image size and spacing
    sz         = (ds[idx_tmp].Rows,ds[idx_tmp].Columns)
    space      = ds[idx_tmp].PixelSpacing
    
    # x,y coordinates of image (in pixels)
    x = np.linspace(0,(sz[0]-1),sz[0])
    y = np.linspace(0,(sz[1]-1),sz[1])
    
    # Extract profiles through individual line pairs
    lp_r = 48
    
    # Angles between each line pair (i.e. LP1 between 10 and 38 degrees, etc)
    theta = [np.radians(10),
              np.radians(38),
              np.radians(62),
              np.radians(85),
              np.radians(103),
              np.radians(121),
              np.radians(140),
              np.radians(157),
              np.radians(173),
              np.radians(186)]
    
    lpx = lp_r/space[0]*np.cos(theta) + outer_c[0] # x coord of points between line pairs
    lpy = lp_r/space[0]*np.sin(theta) + outer_c[1] # y coord of points between line pairs
    
    
    # [line pair number in increasing order, number of lines in this position]
    npeaks = [[1,2],[2,3],[3,4],[4,4],[5,4],[6,5],[7,5],[8,5],[9,5],[10,5]]
    
    
    # Arbitrary threshold, for each LP profile we sum the # of derivative points that exceed this threshold
    # CTP528 module has lots of inflection points along LP profile, should have many points exceeding this threshold
    thres1 = 35#100
    # Arbitrary threshold, count # of points that exceeds the above thres1 per slice
    # CTP528 module should have substantially more points exceeding thres1 than any other slice
    thres2 = 18#50 
    
    # Try a few expected slices first to save time. If not these slices, then go through them all
    n = (z_tmp,z_tmp+1,z_tmp-1,z_tmp+2,z_tmp-2)
    
    print('Searching for CTP528 module starting at expected slices')
    for i in n:
    # for i in [0]:
        print('\nSlice %i\n' % int(i+1))
        with open('ScriptLog.txt', 'a') as file:
            file.write('\nSlice %i\n' % int(i+1))
        
        
        
        # tmpf2 = np.zeros(0)
        # tmpdf2 = np.zeros(0)
        for j in (range(len(theta)-1)):
            # print('Line pair: %i' % j)
            j = int(j)
            tmpf, tmpdf = get_lp_profile(x,y,npeaks[j],(lpx[j],lpx[j+1]),(lpy[j],lpy[j+1]),ds[i].pixel_array)
            
            if j==0:
                tmpf2  = tmpf
                tmpdf2 = tmpdf
            else:
                tmpf2  = np.hstack((tmpf2,tmpf))
                tmpdf2 = np.hstack((tmpdf2,tmpdf))
        
            
        
        if np.sum(abs(tmpdf2)>thres1) > thres2:
            print('CTP528 module located: Slice %i\n' % (i+1))
            with open('ScriptLog.txt', 'a') as file:
                file.write('CTP528 module located: Slice %i\n' % (i+1))
            return i
            break
        
        # if i==0:
        if ('df' in locals()) == 0:
            f = tmpf2
            df = tmpdf2
        else:
            f = np.vstack((f,tmpf2))
            df = np.vstack((df,tmpdf2))
            
    
    print('--- Parsing through each slice to find module CTP528 ---\n')
    with open('ScriptLog.txt', 'a') as file:
        file.write('--- Parsing through each slice to find module CTP528 ---\n')
    # return 0
    
    
    
    
    for i in (range(len(ds)-1)):
    # for i in [0]:
        print('\nSlice %i\n' % int(i+1))
        with open('ScriptLog.txt', 'a') as file:
            file.write('\nSlice %i\n' % int(i+1))
        
        # tmpf2 = np.zeros(0)
        # tmpdf2 = np.zeros(0)
        for j in (range(len(theta)-1)):
            # print('Line pair: %i' % j)
            j = int(j)
            tmpf, tmpdf = get_lp_profile(x,y,npeaks[j],(lpx[j],lpx[j+1]),(lpy[j],lpy[j+1]),ds[i].pixel_array)
            
            if j==0:
                tmpf2 = tmpf
                tmpdf2 = tmpdf
            else:
                tmpf2 = np.hstack((tmpf2,tmpf))
                tmpdf2 = np.hstack((tmpdf2,tmpdf))
                
        
        if np.sum(abs(tmpdf2)>thres1) > thres2:
            print('CTP528 module located: Slice %i\n' % (i+1))
            return i
            break
        
        if i==0:
            f = tmpf2
            df = tmpdf2
        else:
            f = np.vstack((f,tmpf2))
            df = np.vstack((df,tmpdf2))
            
    
    print('Error: Cannot locate CTP528 module\n')
    with open('ScriptLog.txt', 'a') as file:
        file.write('Error: Cannot locate CTP528 module\n')
    return 0


def get_Zscale_intensities(im,c,t_offset):

    rsample = 5 # Size of circle to sample/mask the z posts
    rz = 70.7   # sqrt(2) * distance between z posts (50 mm)
    tz = 45 + t_offset      # z posts at 45 deg plus previously found rotation error
    
    # Centre of z-rods, starting bottom right and going clockwise
    x = []
    y = []
    x.append(c[0] + rz*np.cos(np.radians(tz)))
    y.append(c[1] + rz*np.sin(np.radians(tz)))
    x.append(c[0] + rz*np.cos(np.radians(tz+90)))
    y.append(c[1] + rz*np.sin(np.radians(tz+90)))
    x.append(c[0] + rz*np.cos(np.radians(tz+180)))
    y.append(c[1] + rz*np.sin(np.radians(tz+180)))
    x.append(c[0] + rz*np.cos(np.radians(tz+270)))
    y.append(c[1] + rz*np.sin(np.radians(tz+270)))
    
    
    # Grab image size for mask function
    h, w = im.shape[:2]

    # Get binary masks of each z post
    m1 = create_circular_mask(h, w, center=[x[0],y[0]], radius=rsample)
    m2 = create_circular_mask(h, w, center=[x[1],y[1]], radius=rsample)
    m3 = create_circular_mask(h, w, center=[x[2],y[2]], radius=rsample)
    m4 = create_circular_mask(h, w, center=[x[3],y[3]], radius=rsample)
    
    # Get average intensity values of each z post
    i1 = np.sum(im[m1])/np.sum(m1)
    i2 = np.sum(im[m2])/np.sum(m2)
    i3 = np.sum(im[m3])/np.sum(m3)
    i4 = np.sum(im[m4])/np.sum(m4)
    
    
    # tplot = np.linspace(0,2*np.pi,20)
    # xplot = x[3] + rsample*np.cos(tplot)
    # yplot = y[3] + rsample*np.sin(tplot)
    
    return [i1,i2,i3,i4]


########################################
# Not using currently, and not well tested....
########################################
def CalculateZScale(dicom_set,idx_CTP404,c_CTP404,t_offset):

    l = np.round(27/dicom_set[1].SliceThickness)  # approximate length of the z posts in # slices (approx 27 mm)
    b = 5   # number of slices as buffer on either side to sample profile
    isample = np.linspace(idx_CTP404-np.round(l/2)-b, idx_CTP404+np.round(l/2)+b,np.int32(l+(2*b)+1))
    
    iprofiles = []
    for i in isample:
        iprofiles.append(get_Zscale_intensities(dicom_set[np.int32(i)].pixel_array,c_CTP404,t_offset))
        
        # test = get_Zscale_intensities(im_CTP404,c_CTP404,t_offset)
    
    zprofs = np.array(iprofiles)
    # diff1 = np.diff(zprofs[:,0])
    # diff2 = np.diff(zprofs[:,1])
    # diff3 = np.diff(zprofs[:,2])
    # diff4 = np.diff(zprofs[:,3])
    diff1 = np.abs(np.diff(zprofs[:,0]))
    diff2 = np.abs(np.diff(zprofs[:,1]))
    diff3 = np.abs(np.diff(zprofs[:,2]))
    diff4 = np.abs(np.diff(zprofs[:,3]))
    
    h = 60      # Arbitrary peak height... Code may fail here
    d = 5       # Arbitrary distance between peaks
    peaks_max1, _ = find_peaks(diff1,height=h,distance=d)
    peaks_max2, _ = find_peaks(diff2,height=h,distance=d)
    peaks_max3, _ = find_peaks(diff3,height=h,distance=d)
    peaks_max4, _ = find_peaks(diff4,height=h,distance=d)
    
    z_scale_calc = np.mean([np.diff(peaks_max1),np.diff(peaks_max2),np.diff(peaks_max3),np.diff(peaks_max4)])*dicom_set[1].SliceThickness

    return z_scale_calc



def FindSliceThickness(im,sz,c_tmp):
    
    c = np.int32(c_tmp)
    
    roit = 80
    roib = 70
    roil = -30 
    roir = 30
   
    profs = im[c[1]+roil:c[1]+roir,c[0]+roib:c[0]+roit]
    idx_prof = np.argmax(np.sum(profs,axis=0))
    
    h = (np.max(profs)+np.min(profs))/2
    peaks, _ = find_peaks(profs[:,idx_prof],height=h)
    peaks_results = peak_widths(profs[:,idx_prof], peaks, rel_height=0.5)
    FWHM = peaks_results[0]*np.sin(np.deg2rad(23))*sz[0]
    
    return FWHM




def FindCTP404Rotation(data, c):

    # Grab image data
    im = data.pixel_array
    sz = (data.Rows,data.Columns)
    space = data.PixelSpacing
    
    ring_r = 58.5/space[0] # converts known radius of CatPhan to pixels (scalable)
    # ring_r = 58.5
    
    cb = ring_r*np.cos(np.radians(90))+c[0],ring_r*np.sin(np.radians(90))+c[1]
    ct = ring_r*np.cos(np.radians(-90))+c[0],ring_r*np.sin(np.radians(-90))+c[1]
    
    # x,y coordinates of image (in pixels)
    x = np.linspace(0,(sz[0]-1),sz[0])
    y = np.linspace(0,(sz[1]-1),sz[1])
    
    
    
    l = 25              # Number of pixels in profile to find centre of air ROIs
    granularity = 3     # Multiplier, higher = more finely sampled profiles
    
    def FindC(ct,cb,l,granularity):
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('Interpolating profiles across top and bottom air ROIs...\n') 
        
        # Coordinates for top air ROI
        x_horiz_top = np.linspace(ct[0]-l,ct[0]+l,l*granularity) 
        x_vert_top = np.linspace(ct[1]-l,ct[1]+l,l*granularity) 
        
        # Coordinates for bottom air ROI
        x_horiz_bot = np.linspace(cb[0]-l,cb[0]+l,l*granularity) 
        x_vert_bot = np.linspace(cb[1]-l,cb[1]+l,l*granularity) 

        # Initialize profiles
        pht = np.zeros(len(x_horiz_top))
        pvt = np.zeros(len(x_horiz_top))
        phb = np.zeros(len(x_horiz_top))
        pvb = np.zeros(len(x_horiz_top))
        
        # Interpolate profiles
        for i in range(len(x_horiz_top)-1):
            # print('%i' % i)
            pht[i] = interpn((x,y), im, [ct[1], x_horiz_top[i]])
            pvt[i] = interpn((x,y), im, [x_vert_top[i], ct[0]])
            phb[i] = interpn((x,y), im, [cb[1], x_horiz_bot[i]])
            pvb[i] = interpn((x,y), im, [x_vert_bot[i], cb[0]])
        
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('Taking derivative of profiles...\n') 
        
        # Derivative of profile
        dht = np.diff(pht)
        dvt = np.diff(pvt)
        dhb = np.diff(phb)
        dvb = np.diff(pvb)
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('Finding peaks of derivatives which correspond to CatPhan edges...\n') 
            file.write('If failing here, may need to change threshold for peak finding algorithm...\n') 
            
        # Find inflection points in profile (minima/maxima of derivative)
        h = 100     # Pixel intensity derivative threshold, currently not scalable to other CBCT matrix sizes...
        peaks_ht, _ = find_peaks(abs(dht),height=h)
        peaks_vt, _ = find_peaks(abs(dvt),height=h)
        peaks_hb, _ = find_peaks(abs(dhb),height=h)
        peaks_vb, _ = find_peaks(abs(dvb),height=h)
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('Now finding centre of top and bottom air ROIs...\n') 
        # Find centre of each ROI in pixel coordinates of original image
        offset = np.array(len(x_horiz_top)/2)
        mid_top = [sum(np.array(peaks_ht))/2-offset,sum(np.array(peaks_vt))/2-offset]
        mid_bot = [sum(np.array(peaks_hb))/2-offset,sum(np.array(peaks_vb))/2-offset]
        
        # mid_top = [sum(x_horiz_top[peaks_ht])/2,sum(x_vert_top[peaks_vt])/2]
        # mid_bot = [sum(x_horiz_bot[peaks_hb])/2,sum(x_vert_bot[peaks_vb])/2]
        
        ct_new = np.add(ct,mid_top)
        cb_new = np.add(cb,mid_bot)
    
        return ct_new, cb_new
    
    
    # Seems to work better if this algorithm ran several times...
    iterations = 5
    ct_originalt = ct
    cb_originalb = cb
    ct_old = ct
    cb_old = cb
    c_thres = 30
    for i in (range(iterations)):
        with open('ScriptLog.txt', 'a') as file:
            file.write('Iteration ' + str(i+1) + '\n') 
        try:
            ct, cb = FindC(ct,cb,l,granularity)
        except:
            print('Failed to find centre of CatPhan module CTP404...\n')
            with open('ScriptLog.txt', 'a') as file:
                file.write('Failed to find centre of CatPhan module CTP404...\n')
        
        if np.abs(ct[0]-ct_old[0])>c_thres or np.abs(ct[1]-ct_old[1])>c_thres or np.abs(cb[0]-cb_old[0])>c_thres or np.abs(cb[1]-cb_old[1])>c_thres:
            print('Finding CTP404 module centre, exceeds threshold, skipping...\n')
            ct = ct_originalt
            cb = cb_originalb
            break
        else:
            ct_old = ct
            cb_old = cb
    
    ct_new = ct
    cb_new = cb
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\nCalculating rotation between top and bottom air ROIs...\n') 
    
    # Calculate rotation between top and bottom air ROIs
    tx = ct_new[0] - cb_new[0]
    ty = ct_new[1] - cb_new[1]
    t = -np.arctan(tx/ty)*180/np.pi
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Rotation = ' + str(t) + ' deg \n') 

    return t, ct, cb





def ScalingXY_CTP404(data,idx,t_offset,ct,cb,c):
    
    # 3 slice averaging
    im1 = data[idx].pixel_array
    im2 = data[idx+1].pixel_array
    im3 = data[idx-1].pixel_array
    
    imtmp = np.add(im1,im2)
    im = np.add(imtmp,im3)/3

    # Get image size and pixel spacing
    sz = (data[idx].Rows,data[idx].Columns)
    space = data[idx].PixelSpacing
    
    # Index for x and y pixel positions in image
    x = np.linspace(0,(sz[0]-1),sz[0])
    y = np.linspace(0,(sz[1]-1),sz[1])
    
    # Get centre of CatPhan from averaging centres of top and bottom air ROIs
    cmid = [np.add(ct[0],cb[0])/2,np.add(ct[1],cb[1])/2]
    
    # Get (x,y) coordinates and length of line passing through centre of top and bottom ROIs
    r = 70 # Radius of circle passing through centre of ROIs
    xscale_xcoord = [cmid[0] - r/space[0]*np.cos(t_offset*2*np.pi/360), cmid[0] + r/space[0]*np.cos(t_offset*2*np.pi/360)]
    xscale_ycoord = [cmid[1] - r/space[0]*np.sin(t_offset*2*np.pi/360), cmid[1] + r/space[0]*np.sin(t_offset*2*np.pi/360)] 
    l = np.sqrt((xscale_xcoord[1]-xscale_xcoord[0])**2 + (xscale_ycoord[1]-xscale_ycoord[0])**2)
    
    # Creates profiles to sample pixel values through each air ROI
    n = 150 # number of sample points in profile through ROI (to find edges of ROIs to calculate scaling)
    xtmp = np.linspace(xscale_xcoord[0],xscale_xcoord[1],n)
    ytmp = np.linspace(xscale_ycoord[0],xscale_ycoord[1],n)
    ltmp = np.linspace(0,l,n)   # just an indexing variable, used later to identify points along the profile
    ftmp = np.zeros(len(xtmp))

    # Populate profile (sampled via linear interpolation)
    for i in range(len(xtmp)):
        ftmp[i] = interpn((x,y),im,[ytmp[i],xtmp[i]])
        
    # Save top and bottom air ROI profile to variable
    f1 = ftmp
    pts = []
    pts.append(xtmp)
    pts.append(ytmp)
    
    # Repeat same method for left/right ROIs (Delrin and LDPE) for horizontal scaling
    t_offset = t_offset + 90
    xscale_xcoord = [cmid[0] - r/space[0]*np.cos(t_offset*2*np.pi/360), cmid[0] + r/space[0]*np.cos(t_offset*2*np.pi/360)]
    xscale_ycoord = [cmid[1] - r/space[0]*np.sin(t_offset*2*np.pi/360), cmid[1] + r/space[0]*np.sin(t_offset*2*np.pi/360)] 
    
    xtmp = np.linspace(xscale_xcoord[0],xscale_xcoord[1],n)
    ytmp = np.linspace(xscale_ycoord[0],xscale_ycoord[1],n)
    ltmp = np.linspace(0,l,n)
    ftmp = np.zeros(len(xtmp))

    for i in range(len(xtmp)):
        ftmp[i] = interpn((x,y),im,[ytmp[i],xtmp[i]])
        
    f2 = ftmp
    pts.append(xtmp)
    pts.append(ytmp)
    
    
    # Take derivative of horizontal and vertical profiles
    df1 = np.diff(f1)
    df2 = np.diff(f2)
    
    # plt.plot(df1)
    
    # Find inflection points in profile (minima/maxima of derivative)
    try:
        h = 40
        peaks_max1, _ = find_peaks(df1,height=h)
        peaks_min1, _ = find_peaks(-df1,height=h)
        peaks_max2, _ = find_peaks(df2,height=h)
        peaks_min2, _ = find_peaks(-df2,height=h)
        
        # Sort peak positions in ascending order
        peaks1 = np.hstack((peaks_max1,peaks_min1))
        peaks1 = np.array(sorted(peaks1))
        peaks2 = np.hstack((peaks_max2,peaks_min2))
        peaks2 = np.array(sorted(peaks2))
        
        # First, second, second last, and last peaks represent edges of each ROI
        # Pull these coordinates and find the difference for (x,y) scaling
        # This scaling calculation mimics the current procedure for manual calculation of CBCT scaling for monthly QC
        # Scale1 is top-to-top/left-to-left distances, scale2 is bottom-to-bottom/right-to-right distances
        xscale1 = np.abs((ltmp[peaks1[0]] - ltmp[peaks1[len(peaks1)-2]]))*space[0]
        xscale2 = np.abs((ltmp[peaks1[1]] - ltmp[peaks1[len(peaks1)-1]]))*space[0]
        yscale1 = np.abs((ltmp[peaks2[0]] - ltmp[peaks2[len(peaks2)-2]]))*space[0]
        yscale2 = np.abs((ltmp[peaks2[1]] - ltmp[peaks2[len(peaks2)-1]]))*space[0]
    
    except:
        h = 30
        peaks_max1, _ = find_peaks(df1,height=h)
        peaks_min1, _ = find_peaks(-df1,height=h)
        peaks_max2, _ = find_peaks(df2,height=h)
        peaks_min2, _ = find_peaks(-df2,height=h)
        
        # Sort peak positions in ascending order
        peaks1 = np.hstack((peaks_max1,peaks_min1))
        peaks1 = np.array(sorted(peaks1))
        peaks2 = np.hstack((peaks_max2,peaks_min2))
        peaks2 = np.array(sorted(peaks2))
        
        # First, second, second last, and last peaks represent edges of each ROI
        # Pull these coordinates and find the difference for (x,y) scaling
        # This scaling calculation mimics the current procedure for manual calculation of CBCT scaling for monthly QC
        # Scale1 is top-to-top/left-to-left distances, scale2 is bottom-to-bottom/right-to-right distances
        xscale1 = np.abs((ltmp[peaks1[0]] - ltmp[peaks1[len(peaks1)-2]]))*space[0]
        xscale2 = np.abs((ltmp[peaks1[1]] - ltmp[peaks1[len(peaks1)-1]]))*space[0]
        yscale1 = np.abs((ltmp[peaks2[0]] - ltmp[peaks2[len(peaks2)-2]]))*space[0]
        yscale2 = np.abs((ltmp[peaks2[1]] - ltmp[peaks2[len(peaks2)-1]]))*space[0]
    
    # Take average value of scaling, convert from mm to cm
    results = [(xscale1+xscale2)/2/10,(yscale1+yscale2)/2/10]
    
    return results, pts




# Function that creates circular boolean masks
def create_circular_mask(h, w, center=None, radius=None):

    if center is None: # use the middle of the image
        center = (int(w/2), int(h/2))
    if radius is None: # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w-center[0], h-center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y-center[1])**2)

    mask = dist_from_center <= radius
    return mask


def analysis_CTP404(data, idx, c, t_offset):

    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Deriving 3-slice averaged image\n')
    # 3 slice averaging
    im1 = data[idx].pixel_array
    im2 = data[idx+1].pixel_array
    im3 = data[idx-1].pixel_array
    
    imtmp = np.add(im1,im2)
    im = np.add(imtmp,im3)/3

    # Grab image data
    # im = data[idx].pixel_array
    sz = (data[idx].Rows,data[idx].Columns)
    space = data[idx].PixelSpacing
    
    # mt = np.zeros((sz))
    
    # Mask outer boundary - visual aid to show phantom and ROI alignment
    # outer_c = (np.round(sz[0]/2),np.round(sz[1]/2)) # Centre of image
    outer_c = c
    outer_r = 98
    
    t = np.linspace(0,2*np.pi,100)
    outer_a = outer_r/space[0]*np.cos(t) + outer_c[0] # x coordinates of outer mask
    outer_b = outer_r/space[1]*np.sin(t) + outer_c[1] # y coordinates of outer mask
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Generating masks for each contrast ROI\n')
    
    # Mask ROIs
    h, w = im.shape[:2]
    r = 3.5/space[0]
    ring_r = 58.5/space[0]
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 1...\n')
    c1 = ring_r*np.cos(np.radians(0+t_offset))+outer_c[0],ring_r*np.sin(np.radians(0+t_offset))+outer_c[1]
    m1 = create_circular_mask(h, w, center=c1, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 2...\n')
    c2 = ring_r*np.cos(np.radians(30+t_offset))+outer_c[0],ring_r*np.sin(np.radians(30+t_offset))+outer_c[1]
    m2 = create_circular_mask(h, w, center=c2, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 3...\n')
    c3 = ring_r*np.cos(np.radians(60+t_offset))+outer_c[0],ring_r*np.sin(np.radians(60+t_offset))+outer_c[1]
    m3 = create_circular_mask(h, w, center=c3, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 4...\n')
    c4 = ring_r*np.cos(np.radians(90+t_offset))+outer_c[0],ring_r*np.sin(np.radians(90+t_offset))+outer_c[1]
    m4 = create_circular_mask(h, w, center=c4, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 5...\n')
    c5 = ring_r*np.cos(np.radians(120+t_offset))+outer_c[0],ring_r*np.sin(np.radians(120+t_offset))+outer_c[1]
    m5 = create_circular_mask(h, w, center=c5, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 6...\n')
    c6 = ring_r*np.cos(np.radians(180+t_offset))+outer_c[0],ring_r*np.sin(np.radians(180+t_offset))+outer_c[1]
    m6 = create_circular_mask(h, w, center=c6, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 7...\n')
    c7 = ring_r*np.cos(np.radians(-120+t_offset))+outer_c[0],ring_r*np.sin(np.radians(-120+t_offset))+outer_c[1]
    m7 = create_circular_mask(h, w, center=c7, radius=r)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 8...\n')
    c8 = ring_r*np.cos(np.radians(-60+t_offset))+outer_c[0],ring_r*np.sin(np.radians(-60+t_offset))+outer_c[1]
    m8 = create_circular_mask(h, w, center=c8, radius=r)
    
    # Used later for scaling
    with open('ScriptLog.txt', 'a') as file:
        file.write('Mask 9...\n')
    c9 = ring_r*np.cos(np.radians(-90+t_offset))+outer_c[0],ring_r*np.sin(np.radians(-90+t_offset))+outer_c[1]
    mScale = create_circular_mask(h, w, center=c9, radius=r)
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Calculating mean and std of each ROI\n')
    results = []
    results.append([1,'Delrin',np.mean(im[m1]),np.std(im[m1])])
    results.append([2,'none',np.mean(im[m2]),np.std(im[m2])])
    results.append([3,'Acrylic',np.mean(im[m3]),np.std(im[m3])])
    results.append([4,'Air',np.mean(im[m4]),np.std(im[m4])])
    results.append([5,'Polystyrene',np.mean(im[m5]),np.std(im[m5])])
    results.append([6,'LDPE',np.mean(im[m6]),np.std(im[m6])])
    results.append([7,'PMP',np.mean(im[m7]),np.std(im[m7])])
    results.append([8,'Air',np.mean(im[m8]),np.std(im[m8])])
    results.append([9,'Teflon',np.mean(im[mScale]),np.std(im[mScale])])
    
    LCV = 3.25*(results[4][3]+results[5][3])/(results[4][2]-results[5][2])
    
    
    # Composite of masks for visual purposes, not used for calculation
    m_total = m1+m2+m3+m4+m5+m6+m7+m8
    im_total = im.copy()
    im_total[m_total==0] = 0
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Generating traces of each ROI for visual purposes\n')
    
    # Map out ROIs for visual purposes, not used in calculation
    roi1_off = (ring_r*np.cos(np.radians(0+t_offset)),ring_r*np.sin(np.radians(0+t_offset)))
    roi1_a = r*np.cos(t) + roi1_off[0] + outer_c[0]
    roi1_b = r*np.sin(t) + roi1_off[1] + outer_c[1]
    
    roi2_off = (ring_r*np.cos(np.radians(30+t_offset)),ring_r*np.sin(np.radians(30+t_offset)))
    roi2_a = r*np.cos(t) + roi2_off[0] + outer_c[0]
    roi2_b = r*np.sin(t) + roi2_off[1] + outer_c[1]
    
    roi3_off = (ring_r*np.cos(np.radians(60+t_offset)),ring_r*np.sin(np.radians(60+t_offset)))
    roi3_a = r*np.cos(t) + roi3_off[0] + outer_c[0]
    roi3_b = r*np.sin(t) + roi3_off[1] + outer_c[1]
    
    roi4_off = (ring_r*np.cos(np.radians(90+t_offset)),ring_r*np.sin(np.radians(90+t_offset)))
    roi4_a = r*np.cos(t) + roi4_off[0] + outer_c[0]
    roi4_b = r*np.sin(t) + roi4_off[1] + outer_c[1]
    
    roi5_off = (ring_r*np.cos(np.radians(120+t_offset)),ring_r*np.sin(np.radians(120+t_offset)))
    roi5_a = r*np.cos(t) + roi5_off[0] + outer_c[0]
    roi5_b = r*np.sin(t) + roi5_off[1] + outer_c[1]
    
    roi6_off = (ring_r*np.cos(np.radians(180+t_offset)),ring_r*np.sin(np.radians(180+t_offset)))
    roi6_a = r*np.cos(t) + roi6_off[0] + outer_c[0]
    roi6_b = r*np.sin(t) + roi6_off[1] + outer_c[1]
    
    roi7_off = (ring_r*np.cos(np.radians(-120+t_offset)),ring_r*np.sin(np.radians(-120+t_offset)))
    roi7_a = r*np.cos(t) + roi7_off[0] + outer_c[0]
    roi7_b = r*np.sin(t) + roi7_off[1] + outer_c[1]
    
    roi8_off = (ring_r*np.cos(np.radians(-60+t_offset)),ring_r*np.sin(np.radians(-60+t_offset)))
    roi8_a = r*np.cos(t) + roi8_off[0] + outer_c[0]
    roi8_b = r*np.sin(t) + roi8_off[1] + outer_c[1]
    
    roi9_off = (ring_r*np.cos(np.radians(-90+t_offset)),ring_r*np.sin(np.radians(-90+t_offset)))
    roi9_a = r*np.cos(t) + roi9_off[0] + outer_c[0]
    roi9_b = r*np.sin(t) + roi9_off[1] + outer_c[1]
    
    # Write out traces to variable to plot later
    tmp = np.zeros((2,len(roi1_a),10))
    tmp[:,:,0] = [roi1_a,roi1_b]
    tmp[:,:,1] = [roi2_a,roi2_b]
    tmp[:,:,2] = [roi3_a,roi3_b]
    tmp[:,:,3] = [roi4_a,roi4_b]
    tmp[:,:,4] = [roi5_a,roi5_b]
    tmp[:,:,5] = [roi6_a,roi6_b]
    tmp[:,:,6] = [roi7_a,roi7_b]
    tmp[:,:,7] = [roi8_a,roi8_b]
    tmp[:,:,8] = [roi9_a,roi9_b]
    tmp[:,:,9] = [outer_a,outer_b]
    

    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Calculating scaling factor based on top/bottom and left/right ROIs...\n')
    
    
    # For scaling calculation, use central x/y profiles
    px = im[int(np.round(sz[0]/2)),:]
    py = im[:,int(np.round(sz[1]/2))]
    
    px = px.astype(float)
    py = py.astype(float)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Grabbing profiles and derivatives for T/B and L/R ROIs\n')
    
    profile_length = 26 # Arbitrary, large enough to capture profile across each ROI
    px1 = px[int(c1[0])-profile_length:int(c1[0])+profile_length]
    px2 = px[int(c6[0])-profile_length:int(c6[0])+profile_length]
    py1 = py[int(c4[1])-profile_length:int(c4[1])+profile_length]
    py2 = py[int(c9[1])-profile_length:int(c9[1])+profile_length]
    
    # Centre index of profile, should be just profile_length-1 
    # cProf = (len(px1)-1)/2
    
    # Take derivative of ROI profiles
    dpx1 = np.diff(px1)
    dpx2 = np.diff(px2)
    dpy1 = np.diff(py1)
    dpy2 = np.diff(py2)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Finding ROI edge points for scaling calculation\n')
    
    # Find index of inflection points in ROI profiles as min/max of derivatives
    minx1 = np.argmin(dpx1)
    maxx1 = np.argmax(dpx1)
    minx2 = np.argmin(dpx2)
    maxx2 = np.argmax(dpx2)
    miny1 = np.argmin(dpy1)
    maxy1 = np.argmax(dpy1)
    miny2 = np.argmin(dpy2)
    maxy2 = np.argmax(dpy2)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Calculating x and y scaling factors\n')
    
    # Distances are then the difference between ROI centres plus the differences in min/max inflection point positions
    scaleX1 = (np.abs(c6[0]-c1[0])*space[0] - np.abs(np.min([minx1,maxx1])-np.min([minx2,maxx2]))*space[0])/10 # [cm]
    scaleX2 = (np.abs(c6[0]-c1[0])*space[0] - np.abs(np.max([minx1,maxx1])-np.max([minx2,maxx2]))*space[0])/10 # [cm]
    scaleY1 = (np.abs(c4[1]-c9[1])*space[1] - np.abs(np.min([miny1,maxy1])-np.min([miny2,maxy2]))*space[1])/10 # [cm]
    scaleY2 = (np.abs(c4[1]-c9[1])*space[1] - np.abs(np.max([miny1,maxy1])-np.max([miny2,maxy2]))*space[1])/10 # [cm]
    
    # Take the average
    scaleX = np.mean([scaleX1,scaleX2])
    scaleY = np.mean([scaleY1,scaleY2])
    scale = [scaleX,scaleY]
    
    
    
    
    print('\n')
    print("ROI: \t \t \tmean, \t std")
    print("1 Delrin: \t \t", end="")
    print('%0.1f,\t %0.1f' % (np.mean(im[m1]),np.std(im[m1])))
    print("2 none: \t \t", end="")
    print('%0.1f,\t %0.1f' % (np.mean(im[m2]),np.std(im[m2])))
    print("3 Acrylic: \t \t", end="")
    print('%0.1f,\t %0.1f' % (np.mean(im[m3]),np.std(im[m3])))
    print("4 Air: \t \t \t", end="")
    print('%0.1f, \t %0.1f' % (np.mean(im[m4]),np.std(im[m4])))
    print("5 Polystyrene: \t", end="")
    print('%0.1f, \t %0.1f' % (np.mean(im[m5]),np.std(im[m5])))
    print("6 LDPE: \t \t", end="")
    print('%0.1f, \t %0.1f' % (np.mean(im[m6]),np.std(im[m6])))
    print("7 PMP: \t \t \t", end="")
    print('%0.1f, \t %0.1f' % (np.mean(im[m7]),np.std(im[m7])))
    print("8 Teflon: \t \t", end="")
    print('%0.1f,\t %0.1f' % (np.mean(im[m8]),np.std(im[m8])))
    print("9 Air2: \t \t", end="")
    print('%0.1f,\t %0.1f' % (np.mean(im[mScale]),np.std(im[mScale])))
    
    print("Low contrast visibility: ", end="")
    print('%0.3f %%\n\n' % LCV)
    
    
    print('Scaling calculation using old method:')
    print("X scaling distance: ", end="")
    print('%0.2f cm' % scaleX)
    print("Y scaling distance: ", end="")
    print('%0.2f cm' % scaleY)
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('CTP404 complete with no errors.\n')
    
    return results, scale, tmp



def analysis_CTP486(data,idx,c,b,off):    

    with open('ScriptLog.txt', 'a') as file:
        file.write('Deriving 3-slice averaged image\n')
    # 3 slice averaging
    im1 = data[idx].pixel_array
    im2 = data[idx+1].pixel_array
    im3 = data[idx-1].pixel_array
    
    imtmp = np.add(im1,im2)
    im = np.add(imtmp,im3)/3
    
    # Grab image data
    # im = data[idx].pixel_array
    sz = (data[idx].Rows,data[idx].Columns)
    space = data[idx].PixelSpacing

    
    # Mask outer boundary - visual aid to show phantom and ROI alignment
    outer_c = c
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Defining centre and top/bottom/left/right box ROIs\n')
        file.write('Generating mask for each box\n')
    
    # Uniformity ROIs: centre, north, south, east, west
    # Generating mask for each ROI
    roi_sz = b/space[0]
    roi_off = off/space[0]
    mc = np.zeros(sz)
    mc[int(outer_c[0])-int(roi_sz/2):int(outer_c[0])+int(roi_sz/2),int(outer_c[1])-int(roi_sz/2):int(outer_c[1])+int(roi_sz/2)]=1
    roic = im[mc==1]
    
    mn = np.zeros(sz)
    mn[int(outer_c[0])-int(roi_sz/2):int(outer_c[0])+int(roi_sz/2),int(outer_c[1]+roi_off)-int(roi_sz/2):int(outer_c[1]+roi_off)+int(roi_sz/2)]=1
    roin = im[mn==1]
    
    ms = np.zeros(sz)
    ms[int(outer_c[0])-int(roi_sz/2):int(outer_c[0])+int(roi_sz/2),int(outer_c[1]-roi_off)-int(roi_sz/2):int(outer_c[1]-roi_off)+int(roi_sz/2)]=1
    rois = im[mn==1]
    
    me = np.zeros(sz)
    me[int(outer_c[1]+roi_off)-int(roi_sz/2):int(outer_c[1]+roi_off)+int(roi_sz/2),int(outer_c[0])-int(roi_sz/2):int(outer_c[0])+int(roi_sz/2)]=1
    roie = im[me==1]
    
    mw = np.zeros(sz)
    mw[int(outer_c[1]-roi_off)-int(roi_sz/2):int(outer_c[1]-roi_off)+int(roi_sz/2),int(outer_c[0])-int(roi_sz/2):int(outer_c[0])+int(roi_sz/2)]=1
    roiw = im[mw==1]
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Pulling pixel values from each ROI using masks\n')
    
    # Saving ROIs to variable to return to main script in case debugging desired
    boxc = [int(outer_c[0])-int(roi_sz/2),int(outer_c[0])+int(roi_sz/2),int(outer_c[1])-int(roi_sz/2),int(outer_c[1])+int(roi_sz/2)]
    boxn = [int(outer_c[0])-int(roi_sz/2),int(outer_c[0])+int(roi_sz/2),int(outer_c[1]+roi_off)-int(roi_sz/2),int(outer_c[1]+roi_off)+int(roi_sz/2)]
    boxs = [int(outer_c[0])-int(roi_sz/2),int(outer_c[0])+int(roi_sz/2),int(outer_c[1]-roi_off)-int(roi_sz/2),int(outer_c[1]-roi_off)+int(roi_sz/2)]
    boxe = [int(outer_c[0]+roi_off)-int(roi_sz/2),int(outer_c[0]+roi_off)+int(roi_sz/2),int(outer_c[1])-int(roi_sz/2),int(outer_c[1])+int(roi_sz/2)]
    boxw = [int(outer_c[0]-roi_off)-int(roi_sz/2),int(outer_c[0]-roi_off)+int(roi_sz/2),int(outer_c[1])-int(roi_sz/2),int(outer_c[1])+int(roi_sz/2)]
    
    roi = [boxc,boxn,boxs,boxe,boxw]
    
    
    # Composite mask of the five ROIs for visualization purposes
    m_total = mc + mn + ms + me + mw
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Calculating uniformity\n')
    
    # Calculate mean pixel value of each ROI, calculate uniformity metric
    means = [np.mean(roic),np.mean(roin),np.mean(rois),np.mean(roie),np.mean(roiw)]
    uniformity = (np.max(means)-np.min(means))/np.max(means)*100
    
    
    results = []
    results.append(['centre',np.mean(roic),np.std(roic)])
    results.append(['north',np.mean(roin),np.std(roin)])
    results.append(['south',np.mean(rois),np.std(rois)])
    results.append(['east',np.mean(roie),np.std(roie)])
    results.append(['west',np.mean(roiw),np.std(roiw)])
    results.append(['Uniformity: ',uniformity])
    
    print("ROI: \tmean, \t\tstd")
    print("Centre: ", end="")
    print('%0.1f, \t\t%0.1f' % (np.mean(roic),np.std(roic)))
    print("North: ", end="")
    print('\t%0.1f, \t%0.1f' % (np.mean(roin),np.std(roin)))
    print("South: ", end="")
    print('\t%0.1f, \t%0.1f' % (np.mean(rois),np.std(rois)))
    print("East: ", end="")
    print('\t%0.1f, \t%0.1f' % (np.mean(roie),np.std(roie)))
    print("West: ", end="")
    print('\t%0.1f, \t%0.1f' % (np.mean(roiw),np.std(roiw)))
    print('\n')
    print("Uniformity: ", end="")
    print('%0.2f %%' % uniformity)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('CTP486 complete with no errors.\n')


    return results, m_total, roi





def analysis_CTP528(data, im, c, t_offset):    

    # Grab image data
    sz = (data.Rows,data.Columns)
    space = data.PixelSpacing
    
    # x,y coordinates of image (in pixels)
    x = np.linspace(0,(sz[0]-1),sz[0])
    y = np.linspace(0,(sz[1]-1),sz[1])

    # Trace outer boundary - visual aid to show phantom and ROI alignment
    outer_c = c     # ? Redundant, but afraid to change in case something breaks...
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Drawing profiles through each line pair, up to 10th pair\n')
    
    # Extract profiles through individual line pairs
    lp_r = 48
    
    theta = [np.radians(10+t_offset),
             np.radians(40+t_offset),
             np.radians(62+t_offset),
             np.radians(85+t_offset),
             np.radians(103+t_offset),
             np.radians(121+t_offset),
             np.radians(140+t_offset),
             np.radians(157+t_offset),
             np.radians(173+t_offset),
             np.radians(186+t_offset)]
    lpx = lp_r/space[0]*np.cos(theta) + outer_c[0] # x coord of centre of line pair
    lpy = lp_r/space[0]*np.sin(theta) + outer_c[1] # y coord of centre of line pair
    
    
    # Number of lines in each line pair = number of peaks expected in profile
    npeaks = [[1,2],[2,3],[3,4],[4,4],[5,4],[6,5],[7,5],[8,5],[9,5],[10,5]]
    
    
    def get_MTF(x, y, npeaks, lpx, lpy, img):
        
        # Interpolate profile across line pair
        x1 = np.linspace(lpx[0],lpx[1],50)
        y1 = np.linspace(lpy[0],lpy[1],50)
        f1 = np.zeros(len(x1))
        
        # print('x: %i %i' % (lpx[0],lpx[1]))
        # print('y: %i %i' % (lpy[0],lpy[1]))
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('...Interpolating across line pair\n')
        
        for i in range(len(x1)):
            f1[i] = interpn((x,y),img,[y1[i],x1[i]])
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('...Taking derivative and finding peaks\n')
            
        # Derivative of profile
        df1 = np.diff(f1)
        
        # Find inflection points in profile (minima/maxima of derivative)
        h = 50
        peaks_max1, _ = find_peaks(df1,height=h)
        peaks_min1, _ = find_peaks(-df1,height=h)
        
        
        # if (len(peaks_max1) != npeaks[1]) or (len(peaks_min1) != npeaks[1]):
            
        #     print("Line pair: ", end="")
        #     print('%i' % npeaks[0])
        #     print("Peaks max: ", end="")
        #     print('%i' % len(peaks_max1))
        #     print("Peaks min: ", end="")
        #     print('%i' % len(peaks_min1))
        #     print('\n')
        
        while (len(peaks_max1) < npeaks[1]) or (len(peaks_min1) < npeaks[1]):
            
            if (h <= 10):
                print("CTP528: Cannot resolve line pair ", end="")
                print("%i \n" % npeaks[0])
                
                with open('ScriptLog.txt', 'a') as file:
                    file.write('...Cannot resolve line pair ' + str(npeaks[0]) + '\n')
                    file.write('...Assigning MTF = 0 for this line pair\n')
                return 0, f1, 0, 0, 0, lpx, lpy
            
            h -= 1

            peaks_max1, _ = find_peaks(df1,height=h)
            peaks_min1, _ = find_peaks(-df1,height=h)
        
        
        peaks1 = np.hstack((peaks_max1,peaks_min1))
        peaks1 = np.array(sorted(peaks1))



        with open('ScriptLog.txt', 'a') as file:
            file.write('...Taking minima/maxima of profiles located at derivative peak locations\n')
                    
        idxmax = []
        idxmin = []      
        Imax = []
        Imin = []    
        # I = []
        offset = 1
        for i in range(len(peaks1)-1):
            # print('%i' % i)
            if i%2 == 0:
                tmp = np.array(f1[peaks1[i]-offset:peaks1[i+1]+offset]).argmax()
                idxmax.append(tmp-offset+peaks1[i])
                Imax.append(f1[tmp-offset+peaks1[i]])
            else:
                tmp = np.array(f1[peaks1[i]-offset:peaks1[i+1]+offset]).argmin()
                idxmin.append(tmp-offset+peaks1[i])
                Imin.append(f1[tmp-offset+peaks1[i]])
        
        with open('ScriptLog.txt', 'a') as file:
            file.write('...Calculating MTF for this line pair\n')
        MTF = (np.mean(Imax)-np.mean(Imin))/(np.mean(Imax)+np.mean(Imin))
                    
        return MTF, f1, peaks_max1, peaks_min1, peaks1, lpx, lpy
            
    MTF = []
    lp_x = []
    lp_y = []
    f = []
    for i in (range(len(theta)-1)):
    # for i in np.linspace(0,8,9):
        i = int(i)
        print('\nAnalyzing line pair %i' % int(i+1))
        with open('ScriptLog.txt', 'a') as file:
            file.write('\nAnalyzing line pair ' + str(int(i+1)) + '\n')
        # print('Peaks: %i %i' % (int(npeaks[i][0]),int(npeaks[i][1])))
        # print('LPX: %0.2f %0.2f' % (lpx[i],lpx[i+1]))
        # print('LPY: %0.2f %0.2f ' % (lpy[i],lpy[i+1]))
        mtf, tmpf, a, b, c, tmpx, tmpy = get_MTF(x,y,npeaks[i],(lpx[i],lpx[i+1]),(lpy[i],lpy[i+1]),im)
        lp_x.append(tmpx)
        lp_y.append(tmpy)
        MTF.append(mtf)
        f.append(tmpf)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\nNormalizing MTF function\n')
    
    # Normalize MTF and find 10% and 50% MTF
    nMTF = MTF/max(np.array(MTF))
    
    # lp = np.linspace(1,len(MTF),len(MTF))/10
    # fMTF = interp1d(nMTF,lp)
    # nMTF80 = fMTF(0.8)
    # nMTF50 = fMTF(0.5)
    # nMTF30 = fMTF(0.3)
    # nMTF10 = fMTF(0.1)
    
    lp = np.linspace(1,len(MTF),len(MTF))/10
    MTF_sample = (0.8,0.5,0.3,0.1)
    fMTF = np.interp(MTF_sample,nMTF[::-1],lp[::-1])
    nMTF80 = fMTF[0]
    nMTF50 = fMTF[1]
    nMTF30 = fMTF[2]
    nMTF10 = fMTF[3]
    
    print("50% MTF: ", end="")
    print('%0.3f' % nMTF50)
    print("10% MTF: ", end="")
    print('%0.3f' % nMTF10)
    print('\n')
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('CTP528 complete with no errors.\n')
    
    return MTF, f, a, b, c, lp_x, lp_y
    

    



def main(mainpath):
    print('mainpath-------------------------------------------------')
    print(mainpath)
    
    # open files for results and for error log
    f    = open(mainpath + '\\CatPhan_results.txt','w')
    flog = open(mainpath + '\\ScriptLog.txt','w')
    
    # write to log
    dateandtime = datetime.datetime.now()
    print('CatPhan analysis script\n', file=flog)
    print('Date/Time: \t', dateandtime, file=flog)
    print('Path: \t', mainpath, file=flog)
    
    
    
    # script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    # dir_path = script_directory + '\\drop_CatPhan_images_here\\'
    dir_path = mainpath
    
    
    s                  = []
    dicom_set_original = []
    for root, _, filenames in os.walk(dir_path):
        for filename in filenames:
            
            if 'dir' in filename or 'txt' in filename:
                continue
            
            
            dcm_path = Path(root, filename)
    
            try:
                ds = dicom.dcmread(dcm_path, force=True)
                ds.file_meta.TransferSyntaxUID = dicom.uid.ImplicitVRLittleEndian  # or whatever is the correct transfer syntax for the file
                # n.append(ds.SOPInstanceUID[ds.SOPInstanceUID.rfind('.')+1:])
                s.append(ds.SliceLocation)
            except IOError:
                print(f"Can't import {dcm_path.stem}")
            else:
                dicom_set_original.append(ds)
    
    dicom_set = []
    s         = np.array(s)
    tmp       = (-s).argsort()
    
    
    for i in (range(len(dicom_set_original))):  
        # print('%s' % dicom_set[n.index(str(i+1))].SOPInstanceUID)
        # dicom_set.append(dicom_set_original[n.index(str(i+1))])
        
        dicom_set.append(dicom_set_original[tmp[i]])
        # print(dicom_set_original[tmp[i]].SliceLocation)
        
    
    
    # Write to log file
    print('Unit: \t\t', dicom_set[1].StationName, file=flog)
    print('Images found: \t%i' % len(dicom_set), file=flog)
    print('\n', file=flog)
    print('--- Searching for slice that contains CTP528 Line Pair module', file=flog)
    print('Starting at expected slice locations', file=flog)
    try:
        idx_CTP528 = FindSliceCTP528(dicom_set)
        print('CTP528 slice found: \t%i' % idx_CTP528, file=flog)
    except:
        print('Module FindSliceCTP528 failed...', file=flog)
    flog.close()
    
    # Get general image information (matrix size, pixel spacing, slice thickness)
    im_tmp = dicom_set[idx_CTP528].pixel_array
    sz     = (dicom_set[idx_CTP528].Rows,dicom_set[idx_CTP528].Columns)
    space  = dicom_set[idx_CTP528].PixelSpacing
    z      = dicom_set[idx_CTP528].SliceThickness


    # Find CTP528 slice, average 2-3 slices, accounts for Long setup error
    im_CTP528, _, z_mean = image_selector_CTP528(dicom_set, idx_CTP528)
    

    #######################################################################################
    #######################################################################################
    #######################################################################################
    #######################################################################################
    # Below is from Devin's original script, for use with the CatPhan-504. The offsets
    # are not the same in the 504 as in the 500, so we've changed the offsets to match the 
    # CatPhan-500 specs:
    '''
    # Find other two module slices based on CTP528
    d_CTP404 = 30       # distance between CTP528 and CTP404 [mm]
    d_CTP486 = -80      # distance between CTP528 and CTP486 [mm]
    '''
    # Find other two module slices based on CTP528
    d_CTP404 = -30       # distance between CTP528 and CTP404 [mm]
    d_CTP486 = -110      # distance between CTP528 and CTP486 [mm]

    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n--- Finding CTP404 and CTP486 modules...\n')
    
    # Check whether slices are increasing or decreasing in z
    z1 = dicom_set[idx_CTP528].SliceLocation
    z2 = dicom_set[idx_CTP528+1].SliceLocation
    
    
    
    if (z2-z1) > 0:
        print('Z is increasing')
        with open('ScriptLog.txt', 'a') as file:
            file.write('Note: Z slice number is increasing.\n')
        idx_CTP404 = int(idx_CTP528 + z_mean + float(d_CTP404)/z)
        idx_CTP486 = int(idx_CTP528 + z_mean + float(d_CTP486)/z)
        
    else:
        print('Z is decreasing')
        with open('ScriptLog.txt', 'a') as file:
            file.write('Note: Z slice number is decreasing.\n')
        idx_CTP404 = int(idx_CTP528 + z_mean - float(d_CTP404)/z)
        idx_CTP486 = int(idx_CTP528 + z_mean - float(d_CTP486)/z)
        
    
    
    # Obtain CTP404 and CTP486 module images
    im_CTP404_SliceThickness = dicom_set[idx_CTP404].pixel_array    # NO 3 SLICE AVG FOR SLICE THICKNESS TEST
    # im_CTP486 = dicom_set[idx_CTP486].pixel_array
    
    # Three slice averaging:
    im_CTP404 = (dicom_set[idx_CTP404].pixel_array + dicom_set[idx_CTP404+1].pixel_array + dicom_set[idx_CTP404-1].pixel_array)/3
    im_CTP486 = (dicom_set[idx_CTP486].pixel_array + dicom_set[idx_CTP486+1].pixel_array + dicom_set[idx_CTP486-1].pixel_array)/3 
    
        
    
    
    # Find centre of CatPhan in each module to correct for Vrt/Lat setup error
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n--- Finding centre of each module based on outer surface of CatPhan...\n')
        file.write('Finding centre of CTP528 module\n')  
    c_CTP528, out_CTP528 = FindCatPhanCentre(im_CTP528)
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Finding centre of CTP404 module\n')
    c_CTP404, out_CTP404 = FindCatPhanCentre(im_CTP404)
    
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('Finding centre of CTP486 module\n')  
    c_CTP486, out_CTP486 = FindCatPhanCentre(im_CTP486)
    
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n--- Finding CatPhan rotation in CTP404 module\n')
        file.write('Will assume same rotation for other two modules.\n\n')
    # Find CatPhan rotation in CTP404 (based on air ROIs), assume same rotation for all three modules
    t_offset, ct, cb = FindCTP404Rotation(dicom_set[idx_CTP404], c_CTP404)


    # Analyze each module
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n\n--- Analyzing CTP404 module\n')
        file.write('First calculating X/Y/Z scaling...\n')
        
    scaleFine, pts = ScalingXY_CTP404(dicom_set,idx_CTP404,t_offset,ct,cb,c_CTP404) 
    c_CTP404 = [np.mean([pts[0],pts[2]]),np.mean([pts[1],pts[3]])] # better calculation of centre of this module
    
    # z_scale_calc = CalculateZScale(dicom_set,idx_CTP404,c_CTP404,t_offset)
    # print('Z scale: %0.2f' % z_scale_calc)
    SliceThickness = FindSliceThickness(im_CTP404_SliceThickness,space,c_CTP404)
    print('Slice thickness: %0.2f\n' % SliceThickness)
        
    with open('ScriptLog.txt', 'a') as file:
        file.write('Analyzing rest of CTP404 module...\n')
    # results_CTP404, scale, ROI_CTP404 = analysis_CTP404(dicom_set[idx_CTP404],c_CTP404,t_offset)
    results_CTP404, scale, ROI_CTP404 = analysis_CTP404(dicom_set,idx_CTP404,c_CTP404,t_offset)
    LCV = 3.25*(results_CTP404[4][3]+results_CTP404[5][3])/(results_CTP404[4][2]-results_CTP404[5][2])
    
    print('\nScaling calculation using new method:')
    print("X scaling distance: ", end="")
    print('%0.2f cm' % scaleFine[0])
    print("Y scaling distance: ", end="")
    print('%0.2f cm\n' % scaleFine[1])
        
    
    # Sets ROI sizes for CTP486 uniformity module
    ROI_box_size = 15   # CTP486 uniformity roi box size
    ROI_offset = 50     # CTP486 uniformity roi box offset from centre
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n\n--- Analyzing CTP486 module\n')
    # results_CTP486, mask_CTP486, ROI_CTP486 = 
    # (dicom_set[idx_CTP486],c_CTP486,ROI_box_size,ROI_offset)
    results_CTP486, mask_CTP486, ROI_CTP486 = analysis_CTP486(dicom_set,idx_CTP486,c_CTP486,ROI_box_size,ROI_offset)
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n\n--- Analyzing CTP528 module\n')
    MTF, lpf, _, _, _, lpx, lpy = analysis_CTP528(dicom_set[idx_CTP528],im_CTP528,c_CTP528,t_offset)
    
    # Normalize MTF and find 10% and 50% MTF
    nMTF = MTF/max(np.array(MTF))
    
    # lp = np.linspace(1,len(MTF),len(MTF))/10
    # fMTF = interp1d(nMTF,lp)
    # nMTF80 = fMTF(0.8)
    # nMTF50 = fMTF(0.5)
    # nMTF30 = fMTF(0.3)
    # nMTF10 = fMTF(0.1)
    
    lp = np.linspace(1,len(MTF),len(MTF))/10
    MTF_sample = (0.8,0.5,0.3,0.1)
    fMTF = np.interp(MTF_sample,nMTF[::-1],lp[::-1])
    nMTF80 = fMTF[0]
    nMTF50 = fMTF[1]
    nMTF30 = fMTF[2]
    nMTF10 = fMTF[3]
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('\n\n--- Generating plots\n')
    
    fsize = 15
    window = 1000
    level = 1000
    Vmin  = int(level - window/2)
    Vmax  = int(level + window/2)
    # plt.rcParams['figure.figsize'] = [fsize, fsize]
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('...Plot 1 - CTP528 image\n')
    
    plt.subplots(2,2,figsize=(fsize,fsize))
    pltTxt = 'Unit: '+dicom_set[1].StationName+', Window/level: '+str(window)+'/'+str(level)
    plt.suptitle(pltTxt, fontsize=16)
    
    
    plt.subplot(2,2,1)
    plt.cla()
    plt.imshow(im_CTP528, cmap='gray', vmin=Vmin, vmax=Vmax)
    plt.plot(lpx,lpy,'-r')
    plt.plot(np.array(out_CTP528[0]),np.array(out_CTP528[1]),'r')
    plt.title('CTP528')
    plt.axis('off')
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('...Plot 2 - CTP528 MTF\n')
    
    plt.subplot(2,2,2)
    plt.cla()
    plt.plot(lp,nMTF)
    plt.plot([nMTF50,nMTF10],[0.5,0.1],'or', mfc='none')
    plt.title('10%% MTF = %0.3f lp/mm' % nMTF10)
    plt.ylabel('Normalized MTF')
    plt.xlabel('lp/mm')
    plt.grid()
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('...Plot 3 - CTP404 image\n')
    
    plt.subplot(2,2,3)
    plt.cla()
    plt.imshow(im_CTP404, cmap='gray', vmin=Vmin, vmax=Vmax)
    plt.plot(ROI_CTP404[0,:,0],ROI_CTP404[1,:,0],'r')
    plt.plot(ROI_CTP404[0,:,1],ROI_CTP404[1,:,1],'r')
    plt.plot(ROI_CTP404[0,:,2],ROI_CTP404[1,:,2],'r')
    plt.plot(ROI_CTP404[0,:,3],ROI_CTP404[1,:,3],'r')
    plt.plot(ROI_CTP404[0,:,4],ROI_CTP404[1,:,4],'r')
    plt.plot(ROI_CTP404[0,:,5],ROI_CTP404[1,:,5],'r')
    plt.plot(ROI_CTP404[0,:,6],ROI_CTP404[1,:,6],'r')
    plt.plot(ROI_CTP404[0,:,7],ROI_CTP404[1,:,7],'r')
    plt.plot(ROI_CTP404[0,:,8],ROI_CTP404[1,:,8],'r')
    plt.plot(ROI_CTP404[0,:,9],ROI_CTP404[1,:,9],'r')
    plt.title('CTP404')
    plt.axis('off')
    plt.plot(pts[0],pts[1],'g')
    plt.plot(pts[2],pts[3],'g')
    
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('...Plot 4 - CTP486 image\n')
    
    plt.subplot(2,2,4)
    plt.cla()
    plt.imshow(im_CTP486, cmap='gray', vmin=Vmin, vmax=Vmax)
    plt.plot(np.array(out_CTP486[0]),np.array(out_CTP486[1]),'r')
    
    b = np.array(ROI_CTP486) # for convenience to index the following plot:
    
    plt.plot([b[0,0],b[0,0]],[b[0,2],b[0,3]],'r')
    plt.plot([b[0,1],b[0,1]],[b[0,2],b[0,3]],'r')
    plt.plot([b[0,0],b[0,1]],[b[0,2],b[0,2]],'r')
    plt.plot([b[0,0],b[0,1]],[b[0,3],b[0,3]],'r')
    
    plt.plot([b[1,0],b[1,0]],[b[1,2],b[1,3]],'r')
    plt.plot([b[1,1],b[1,1]],[b[1,2],b[1,3]],'r')
    plt.plot([b[1,0],b[1,1]],[b[1,2],b[1,2]],'r')
    plt.plot([b[1,0],b[1,1]],[b[1,3],b[1,3]],'r')
    
    plt.plot([b[2,0],b[2,0]],[b[2,2],b[2,3]],'r')
    plt.plot([b[2,1],b[2,1]],[b[2,2],b[2,3]],'r')
    plt.plot([b[2,0],b[2,1]],[b[2,2],b[2,2]],'r')
    plt.plot([b[2,0],b[2,1]],[b[2,3],b[2,3]],'r')
    
    plt.plot([b[3,0],b[3,0]],[b[3,2],b[3,3]],'r')
    plt.plot([b[3,1],b[3,1]],[b[3,2],b[3,3]],'r')
    plt.plot([b[3,0],b[3,1]],[b[3,2],b[3,2]],'r')
    plt.plot([b[3,0],b[3,1]],[b[3,3],b[3,3]],'r')
    
    plt.plot([b[4,0],b[4,0]],[b[4,2],b[4,3]],'r')
    plt.plot([b[4,1],b[4,1]],[b[4,2],b[4,3]],'r')
    plt.plot([b[4,0],b[4,1]],[b[4,2],b[4,2]],'r')
    plt.plot([b[4,0],b[4,1]],[b[4,3],b[4,3]],'r')
    
    plt.title('CTP486')
    plt.axis('off')
    
    
    plt.savefig(mainpath + '\\CatPhan_results.png')
    
    
    
    
    # Time to write the output
        
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\n------------------------------------------------------\n')
        file.write('Writing results to CatPhan_Results.txt file\n')
    
    print('Catphan Analysis Script Results:/n', file=f)
    print('Date,', dicom_set[0].StudyDate[0:4] + '-' + dicom_set[0].StudyDate[4:6] + '-' + dicom_set[0].StudyDate[6:8], file=f)
    print('Time,', dicom_set[0].StudyTime[0:2] + ':' + dicom_set[0].StudyTime[2:4] + ':' + dicom_set[0].StudyTime[4:6], file=f)
    print('Unit,', dicom_set[0].StationName, file=f)
    
    print('----- Module 404 (Contrast Circles) -----,', file=f)
    print('ROI,mean,STD', file=f)
    print("1 Delrin,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[0][2],results_CTP404[0][3]), file=f)
    print("2 none,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[1][2],results_CTP404[1][3]), file=f)
    print("3 Acrylic,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[2][2],results_CTP404[2][3]), file=f)
    print("4 Air,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[3][2],results_CTP404[3][3]), file=f)
    print("5 Polystyrene,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[4][2],results_CTP404[4][3]), file=f)
    print("6 LDPE,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[5][2],results_CTP404[5][3]), file=f)
    print("7 PMP,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[6][2],results_CTP404[6][3]), file=f)
    print("8 Teflon,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[7][2],results_CTP404[7][3]), file=f)
    print("9 Air2,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP404[8][2],results_CTP404[8][3]), file=f)
    
    print("Low contrast visibility,", end="", file=f)
    print('%0.3f, %%' % LCV, file=f)
    
    print("Transverse Distances: Vertical (cm),", end="", file=f)
    print('%0.2f' % scaleFine[0], file=f)
    print("Transverse Distances: Horizontal (cm),", end="", file=f)
    print('%0.2f' % scaleFine[1], file=f)
    # print("Axial Distance: (cm),", end="", file=f)
    # print('%0.2f' % (z_scale_calc/10), file=f)
    print("Slice thickness (mm),", end="", file=f)
    print('%0.2f' % SliceThickness, file=f)
    
    
    
    print('----- Module 486 (Uniformity) -----,', file=f)
    print("ROI,Mean,STD", file=f)
    print("Centre,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP486[0][1],results_CTP486[0][2]), file=f)
    print("North,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP486[1][1],results_CTP486[1][2]), file=f)
    print("South,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP486[2][1],results_CTP486[2][2]), file=f)
    print("East,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP486[3][1],results_CTP486[3][2]), file=f)
    print("West,", end="", file=f)
    print('%0.1f,%0.1f' % (results_CTP486[4][1],results_CTP486[4][2]), file=f)
    print("Uniformity,", end="", file=f)
    print('%0.2f, %%' % (results_CTP486[5][1]), file=f)
    
    
    
    print('----- Module 528 (Line Pairs) -----', file=f)
    print("10% MTF (lp/mm),", end="", file=f)
    print('%0.3f' % nMTF10, file=f)
    print("30% MTF (lp/mm),", end="", file=f)
    print('%0.3f' % nMTF30, file=f)
    print("50% MTF (lp/mm),", end="", file=f)
    print('%0.3f' % nMTF50, file=f)
    print("80% MTF (lp/mm),", end="", file=f)
    print('%0.3f' % nMTF80, file=f)
    
    
    print('----- Misc -----', file=f)
    print("Catphan rotation (deg),", end="", file=f)
    print('%0.1f' % t_offset, file=f)
        
    
    fnametag = dicom_set[0].StationName + '_' + dicom_set[0].StudyDate[0:4] + '-' + dicom_set[0].StudyDate[4:6] + '-' + dicom_set[0].StudyDate[6:8]
    fname = mainpath + '\\CatPhan_' + fnametag
    fnamelog = mainpath + '\\ScriptLog_' + fnametag
    
    with open('ScriptLog.txt', 'a') as file:
        file.write('\n\nCatPhan analysis complete.\n')
        file.write('Plots saved as CatPhan_results/CatPhan_' + fnametag + '.png\n')
        file.write('Results saved as CatPhan_results/CatPhan_' + fnametag + '.txt\n')
    
    
    f.close()
    flog.close()
    
    
    
    try:
        os.rename(mainpath + '\\CatPhan_results.txt',fname + '.txt')
    except FileExistsError:
        os.remove(fname + '.txt')
        os.rename(mainpath + '\\CatPhan_results.txt',fname + '.txt')
       
    try:
        os.rename(mainpath + '\\CatPhan_results.png',fname + '.png')
    except FileExistsError:
        os.remove(fname + '.png')
        os.rename(mainpath + '\\CatPhan_results.png',fname + '.png')
        
    try:
        os.rename(mainpath + '\\ScriptLog.txt',fnamelog + '.txt')
    except FileExistsError:
        os.remove(fnamelog + '.txt')
        os.rename(mainpath + '\\ScriptLog.txt',fnamelog + '.txt')



if __name__ == "__main__":
    #####################################################################################
    ############################################
    # Testing block - comment out when done testing
    # Hardcoding main_path for testing:
    main_path =  'C:\\TOH Data\\CATPHAN_PHAN\\newdata'#'C:\\TOH Data\\Catphan3 - Pruned\\newdata'#'C:\\TOH Data\\CATPHAN 17June2025\\newdata' #'C:\\TOH Data\\Catphan3_XVI_mix\\newdata'
    main(main_path)
    ############################################
    

    ############################################
    # Real block - uncomment when done testing:
    # main(sys.argv[1])

    ############################################
    #####################################################################################
