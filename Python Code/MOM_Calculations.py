#######################################
#######################################
#    MOM_Calculations.py
#       Calibrating and calculating real weights from load cell (Mass-o-Matic) trace data
#       R.A.M and L.U.T.
#       2024-08-27 cleanup of RAM_v10
#       Updated 8/31/2
#######################################
#######################################

#######################################
#######################################
# Imports and libraries
#######################################
#######################################

import numpy as np
from scipy import stats 
from tkinter import messagebox

#######################################
#######################################
# Calibration object
#######################################
#######################################

#######
# Class Calibration
#   Stores regression coefficients to map between true (g) vs. measured (strain) values.
#   After obtaining strain values that correspond to three known-true (g) values,
#   use the regression() function to fully initialize the object.
#######
class Calibration:
    def __init__(self):
        # Default calibration values
        self.cal1_true = 15.97
        self.cal2_true = 32.59
        self.cal3_true = 50.22

        # Pre-initialized measurement values
        self.cal1_measured = -1.0
        self.cal2_measured = -1.0
        self.cal3_measured = -1.0

        self.baseline = -1.0
        self.regression_gradient = -1.0
        self.regression_intercept = -1.0
        self.regression_rsquared = -1.0

        # You can use initialized to check if the user has
        #   performed an appropriate calibration value yet
        self.initialized = False

    # Get the list of real values in grams
    def get_true(self):
        return [self.cal1_true, self.cal2_true, self.cal3_true]
    
    # Get the list of measured values in strain units
    def get_measured(self):
        return [self.cal1_measured, self.cal2_measured, self.cal3_measured]

    # Get the list of difference between measurement and baseline
    def get_difference(self):
        return [x - self.baseline for x in self.get_measured()]
    
    # Set the true values, with error catching if the GUI-entered values are invalid
    def set_true(self, cal1_true, cal2_true, cal3_true):
        try:
            self.cal1_true = float(cal1_true)
            self.cal2_true = float(cal2_true)
            self.cal3_true = float(cal3_true)
            return True
        except ValueError:
            messagebox.showerror("Error.", "User entered invalid calibration value(s).")
            return False

    # Conduct a calibration regression between stored true values and the input measurements
    def regression(self, cal_baseline, cal1_measured, cal2_measured, cal3_measured):
        # Set the measured values
        self.baseline = cal_baseline
        self.cal1_measured = cal1_measured
        self.cal2_measured = cal2_measured
        self.cal3_measured = cal3_measured

        # Get the true values
        true_values = self.get_true()

        # The regression is performed on the difference between the measured and the true
        # NOTE this needs to be consistent between calibration and bird measurements
        #      to keep the intercept meaningful
        difference_values = self.get_difference()

        # Store linear regression information across the three calibration points
        self.regression_gradient, self.regression_intercept, cal_r_value, cal_p_value, cal_std_err = stats.linregress(difference_values, true_values)
        self.regression_rsquared = cal_r_value**2

        # The regression is now complete, and this calibration object is fully initialized
        self.initialized = True

#######################################
#######################################
# Measurement functions
#######################################
#######################################

#######
# Function fit_slope
#   Fits a linear regression slope across all trace values between two points
#   NOTE these slopes are uncalibrated; 
#        need to multiply by calibration regression for slope in y-axis grams  
# Parameters:
#   dat         - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   start_index - start point for trace segment (int)
#   end_index   - end point for trace segment (int)
# Returns: 
#   Uncalibrated slope points in the trace segment (float)
#######
def fit_slope(dat, start_index, end_index):
    # Isolate the trace segment
    trace_segment = dat.loc[start_index:end_index, "Measure"]
    # Get discrete range of x values across the segment
    x_values = np.arange(0, len(trace_segment))
    # Fit regression for slope
    slope, _ = np.polyfit(x_values, trace_segment, 1)
    return slope
    
#######
# Function w_mean
#   Calculates calibrated bird weight as the mean trace value between two points 
# Parameters:
#   dat         - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration - initialized weight calibration object (MOM_Calculations.Calibration)
#   start_index - start point for bird activity in the trace (int)
#   end_index   - end point for bird activity in the trace (int)
#   baseline    - baseline value near bird activity for calibration (float)
# Returns: 
#   Calibrated weight in grams, unrounded (float)
#   Calibrated slope associated with the trace segment (float)
#######
def w_mean(dat, calibration, start_index, end_index, baseline):
    # Get the mean measurement from the trace segment
    measure_mean = dat.loc[start_index:end_index, "Measure"].mean()
    # Calibrate raw values to grams
    calibrated_weight = (measure_mean - baseline) * calibration.regression_gradient + calibration.regression_intercept
    # Get the slope of the segment and calibrate to y-axis grams
    calibrated_slope = fit_slope(dat, start_index, end_index) * calibration.regression_gradient

    return calibrated_weight, calibrated_slope

#######
# Function w_windowed_min_slope
#   Calculates calibrated bird weight as the mean trace value
#   for the sub-window that has the minimum slope, 
#   checking all sub-windows of appropriate sizes between two points
# NOTE formerly do_slope_0, but now despends on calibration object to exist so can't to auto-find calibration values
# Parameters:
#   dat               - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration       - initialized weight calibration object (MOM_Calculations.Calibration)
#   start_index       - start point for bird activity in the trace (int)
#   end_index         - end point for bird activity in the trace (int)
#   baseline          - baseline value near bird activity for calibration (float)
#   min_window_length - the minimum window length to check slope (int)
# Returns: 
#   Calibrated weight in grams, unrounded (float)
#   Calibrated slope of the chosen window with the minimum slope (float)
#   Window start index (int)
#   Window end index (int)
#######
def w_windowed_min_slope(dat, calibration, start_index, end_index, baseline,
                         min_window_length = 25, max_window_proportion = 0.5):
    
    do_print = False
    
    # Baseline comparison values
    # Starting "best" (min) slope is the slope across the whole trace segment
    # Starting "best" window range is the full trace segment
    min_slope = fit_slope(dat, start_index, end_index)
    best_start_index = start_index
    best_end_index = end_index

    # Define the maximum window length,
    # as user-defined proportion of full trace segment size (default 0.5)
    # or minimum window length + 2, whichever longer
    max_window_length = int((end_index - start_index + 1) * max_window_proportion)    
    if max_window_length < min_window_length:
        max_window_length = min_window_length + 2 

    # Begin searching through windows, where the start index marks the LEFT edge of the window
    # For every start point
    for window_start in range(start_index, end_index - min_window_length):
        # For every allowed window size beginning at that start point
        for window_size in range(min_window_length, max_window_length):
            window_end = window_start + window_size
            
            # Fit the slope to that window of the data
            curr_slope = fit_slope(dat, window_start, window_end)

            # If the current slope is smaller in magnitude than the best slope, 
            # then this is your new preferred window
            if abs(curr_slope) <= abs(min_slope):
                min_slope = curr_slope
                best_start_index = window_start
                best_end_index = window_end

    # Calculate mean value of the preferred window (min slope)
    measure_mean = dat.loc[best_start_index:best_end_index, "Measure"].mean()

    # Calibrated raw values to grams
    calibrated_weight = (measure_mean - baseline) * calibration.regression_gradient + calibration.regression_intercept
    calibrated_slope = min_slope * calibration.regression_gradient

    if(do_print):
        print(f"---- In w_windowed... measured mean: {measure_mean} and Calibrated Weight: {calibrated_weight}")

    # Because this function finds an optimal window, 
    # we return not only the weight calculated from that window,
    # but also the start and end indices of the window itself 
    return calibrated_weight, calibrated_slope, best_start_index, best_end_index


#######
# Function w_windowed_min_slope_mid
#   Same as w_windowed_min_slope but uses current point in loop as mid-point rather than start point for window
#   Added for testing purposes 8/30/24 because results don't agree with previous auto results using w_windowed_min_slope
# Parameters:
#   dat               - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration       - initialized weight calibration object (MOM_Calculations.Calibration)
#   start_index       - start point for bird activity in the trace (int)
#   end_index         - end point for bird activity in the trace (int)
#   baseline          - baseline value near bird activity for calibration (float)
#   min_window_length - the minimum window length to check slope (int)
# Returns: 
#   Calibrated weight in grams, unrounded (float)
#   Calibrated slope of the chosen window with the minimum slope (float)
#   Window start index (int)
#   Window end index (int)
#######
def w_windowed_min_slope_mid(dat, calibration, start_index, end_index, baseline,
                         min_window_length = 25, max_window_proportion = 0.5):
    
    # Baseline comparison values
    # Starting "best" (min) slope is the slope across the whole trace segment
    # Starting "best" window range is the full trace segment
    min_slope = fit_slope(dat, start_index, end_index)
    best_start_index = start_index
    best_end_index = end_index

    # Define the maximum window length,
    # as user-defined proportion of full trace segment size (default 0.5)
    # or minimum window length + 2, whichever longer
    max_window_length = int((end_index - start_index + 1) * max_window_proportion)    
    if max_window_length < min_window_length:
        max_window_length = min_window_length + 2 

    # CHANGE Is HERE - CENTERED WINDOWS ENTIRE LENGTH
    # Begin searching through windows, where the start index marks the LEFT edge of the window
    # For every start point
    for window_start in range(start_index, end_index):
        # For every allowed window size beginning at that start point
        for window_size in range(min_window_length, max_window_length):
            window_end = window_start + window_size

            v_start = int(window_start - (window_size/2)) - 1
            v_stop = int(window_start + (window_size/2))
            
            # Fit the slope to that window of the data
            curr_slope = fit_slope(dat, v_start, v_stop)

            # If the current slope is smaller in magnitude than the best slope, 
            # then this is your new preferred window
            if abs(curr_slope) <= abs(min_slope):
                min_slope = curr_slope
                best_start_index = v_start
                best_end_index = v_stop

    # Calculate mean value of the preferred window (min slope)
    measure_mean = dat.loc[best_start_index:best_end_index, "Measure"].mean()

    # Calibrated raw values to grams
    calibrated_weight = (measure_mean - baseline) * calibration.regression_gradient + calibration.regression_intercept
    calibrated_slope = min_slope * calibration.regression_gradient

    # Because this function finds an optimal window, 
    # we return not only the weight calculated from that window,
    # but also the start and end indices of the window itself 
    return calibrated_weight, calibrated_slope, best_start_index, best_end_index


#######
# Function w_median
#   Calculates calibrated bird weight as the median trace value between two points 
#   CHANGE 8/31 RAM: move end point forward to adjust for MFH directive (= ups and downs)
# Parameters:
#   dat         - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration - initialized weight calibration object (MOM_Calculations.Calibration)
#   start_index - start point for bird activity in the trace (int)
#   end_index   - end point for bird activity in the trace (int)
#   baseline    - baseline value near bird activity for calibration (float)
# Returns: 
#   Calibrated weight in grams, unrounded (float)
#   Calibrated slope associated with the trace segment (float)
#######
def w_median(dat, calibration, start_index, end_index, baseline):
    # Get the median measurement from the trace segment
    measure_median = dat.loc[start_index:(end_index+1), "Measure"].median()
    # Calibrate raw values to grams    
    calibrated_weight = (measure_median - baseline) * calibration.regression_gradient + calibration.regression_intercept
    # Get the slope of the segment and calibrate to y-axis grams
    calibrated_slope = fit_slope(dat, start_index, end_index) * calibration.regression_gradient
    return calibrated_weight, calibrated_slope


################
#  w_adjust_for_gravity: 
#   Function: Adjust weight for effect of gravity after Algorithm from Afanasyev et al. 2015 - RAM 6/25/2024 with help from ChatGPT
#   Parameters
#       receives unadjusted weight in grams (W1)
#       receives slope of data used to calculate W1 (adj_slope)
#       Penguin Calculation
#          a = slope
#          g = 9.8
#          W1 = Mean Value between the two points - all normal to this point
#          W2 = W1 ( 1 + a/g)
#    Returns
#       value for W2 increases accuracy
#######
def w_adjust_for_gravity(W1, adj_slope):
    # Define gravitational constant
    g = 9.81
    
    # Calculate W2 using the adjusted slope
    W2 = W1 * (1 + adj_slope / g)
    
    return W2

################
#  w_linear_model: 
#   Function: Adjust weight for effect of gravity after Algorithm from Afanasyev et al. 2015 - RAM 6/25/2024 with help from ChatGPT
#       Could change the actual model if we find somethng better. See PPT discussion 
#   Parameters
#       receives the weight according to w_median (W4) and w_slope (W3)
#       runs linear model based on 100 known weights from R analysis
#       linear model Calculation
#          wt = w_slope*0.37074 + w_median*0.32060 + 15.88565
#    Returns
#       value for wt
#######
def w_linear_model(W3, W4):
    
    # Calculate Wt
    wt = W3*0.37074 + W4*0.32060 + 15.88565
    
    return wt


#######
# Function w_Rtn_Diagnostics
#   Calculates the following from a section of data defined by start_index, end_index 
#       STD
#       Mean
#       # pts above/below mean
#       # pts > XSD above/below mean 
#       # pts below the baseline value
#       # longest stretch above/below mean
# Parameters:
#   dat         - full loadcell dataframe (pandas Dataframe of form Measurement | Datetime)
#   start_index - start point for bird activity in the trace (int)
#   end_index   - end point for bird activity in the trace (int)
#   baseline    - baseline value near bird activity for calibration (float)
#   XSTED       - number of STD above/below baseline for calculation of instability
# Returns: 
#   STD, PctAbove/Below Mean, PctAbove/Below XSD, Pts_Below_Baseline, Longest Stretch above/below mean
#       Change Pts_Below_Baseline to reflect Points below the equivalent of 10g - get the regression for this so can calculate that
#######
def w_Rtn_Diagnostics(dat, start_index, end_index, baseline, XSTD):

    # Isolate the trace segment
    trace_segment = dat.loc[start_index:end_index, "Measure"]
    
    # Convert to numpy array for efficient calculations
    my_numpy_array = trace_segment.to_numpy()
    
    # Adjust the array by subtracting the baseline
    my_adjusted_array = my_numpy_array - baseline

    # Get the mean and standard deviation of the adjusted array
    adjusted_mean = my_adjusted_array.mean()
    adjusted_STD = my_adjusted_array.std()

    # Calculate points below the baseline (from original array, before adjustment)
    below_baseline = my_numpy_array < 0 # these are below baseline since baseline was subtracted from numpy_array
    measure_below_baseline = below_baseline.sum()

    # Calculate points above and below the mean using the adjusted array
    points_above_mean = (my_adjusted_array > adjusted_mean).sum()
    points_below_mean = (my_adjusted_array < adjusted_mean).sum()

    # Calculate points above and below XSTD deviations from the mean in the adjusted array
    points_above_XSTD = (my_adjusted_array > (adjusted_mean + XSTD * adjusted_STD)).sum()
    points_below_XSTD = (my_adjusted_array < (adjusted_mean - XSTD * adjusted_STD)).sum()

    # Define a function to calculate the longest stretch of points above or below the mean
    def longest_stretch(arr, condition):
        max_stretch = 0
        current_stretch = 0
        for val in arr:
            if condition(val):
                current_stretch += 1
                max_stretch = max(max_stretch, current_stretch)
            else:
                current_stretch = 0
        return max_stretch

    # Calculate the longest stretch above and below the mean using the adjusted array
    longest_above_mean = longest_stretch(my_adjusted_array, lambda x: x > adjusted_mean)
    longest_below_mean = longest_stretch(my_adjusted_array, lambda x: x < adjusted_mean)

    # prep a string for export
    d_nX = XSTD
    d_STD = round(adjusted_STD, 2)
    d_PctAboveMean = round(points_above_mean / len(my_adjusted_array) * 100, 2)
    d_PctBelowMean = round(points_below_mean / len(my_adjusted_array) * 100, 2)
    d_PctAboveXSTD = round(points_above_XSTD / len(my_adjusted_array) * 100, 2)
    d_PctBelowXSTD = round(points_below_XSTD / len(my_adjusted_array) * 100, 2)
    d_PtsBelowBaseline = measure_below_baseline
    d_LongestAboveMean = longest_above_mean
    d_LongestBelowMean = longest_below_mean

    if False:
        print("******* XSTD")
        print(XSTD)
        print("******* d_nX")
        print("d_nX")
        print("***** ***")

    if True:
        # return 9 values for diagnostics d_STD, d_PctAbove, d_PctBelow, d_PctAboveX, d_Pct_BelowX, d_PctBelowBase, d_PctAboveBase, d_LongAbove, d_LongBelow 
        return d_nX, d_STD, d_PctAboveMean, d_PctBelowMean, d_PctAboveXSTD, d_PctBelowXSTD, d_PtsBelowBaseline, d_LongestAboveMean, d_LongestBelowMean
    else:
                
        return {  # Return the required diagnostics based on the adjusted array just to print
            "STD": round(adjusted_STD, 2),
            "PctAboveMean": round(points_above_mean / len(my_adjusted_array) * 100, 2),
            "PctBelowMean": round(points_below_mean / len(my_adjusted_array) * 100, 2),
            "PctAboveXSTD": round(points_above_XSTD / len(my_adjusted_array) * 100, 2),
            "PctBelowXSTD": round(points_below_XSTD / len(my_adjusted_array) * 100, 2),
            "PtsBelowBaseline": measure_below_baseline,
            "LongestAboveMean": longest_above_mean,
            "LongestBelowMean": longest_below_mean
        }