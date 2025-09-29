#######################################
#######################################
#    MOM_Processing.py 
#       Loadcell (Mass-o-Matic) trace parsing, viewing, and processing
#       R.A.M and L.U.T.
#       2024-08-27 cleanup of RAM_v10
#######################################
#######################################

#######################################
#######################################
# Imports and libraries
#######################################
#######################################

import os
import warnings
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time as tm

# import tkinter as tk
# from tkinter import filedialog, messagebox
# from tkinter import ttk
# import os
# import pandas as pd
import threading

import MOM_Calculations

#######################################
#######################################
# I/O Parameters
#######################################
#######################################
input_directory = os.getcwd()
output_directory = os.getcwd()

PLOT_VIEWER_WIDTH = 10
PLOT_VIEWER_HEIGHT = 5

#######################################
#######################################
# Internal Flag for printing
#######################################
#######################################
do_print = False

#######################################
#######################################
# File utilities
#######################################
#######################################

#######
# Function get_user_file
#   Asks user for select input measurement trace file
# Parameters: None
# Returns:
#   User-selected file path (str)
#######
def get_user_file():
    # Can update the global input_directory to call back later
    global input_directory


    # Default filetype fire
    files_types = [('TXT',"*.txt *.TXT"), 
                   ('CSV',"*.csv *.CSV")]    
    
    # Ask user to select file
    f_path = filedialog.askopenfilename(initialdir=input_directory,  title="Choose trace file", filetypes=files_types)

    # Catch no file selected
    if len(f_path) == 0:
        messagebox.showinfo("Error", "No file chosen. Try again.")
        return None, None

    # Update global input directory to call back later
    input_directory = os.path.dirname(f_path)

    return f_path

#######
# Function parse_trace_file
#   Wrangle and clean measurement strain data file 
#   Including some mangled data error catching
# Parameters:
#   path - file path to target load cell data (str)
# Returns:
#   Formatted dataframe (pandas Dataframe of form Measurement | Datetime)
#######
def parse_trace_file(path):
    # Try to parse file
    try:
        # Read original CSV file
        dat = pd.read_csv(path, header=None, names=["Measure", "Datetime"], 
                          encoding="utf-8", encoding_errors="replace", on_bad_lines="skip", 
                          engine="python")
        
        # Convert measurement column to numeric strain values
        dat["Measure"] = pd.to_numeric(dat["Measure"], errors="coerce")            

        # Convert Unix timestamp to datetime
        dat["Datetime"] = pd.to_datetime(dat["Datetime"], unit='s', utc=False, errors="coerce")
        dat["Datetime"] = dat["Datetime"].dt.strftime('%Y-%m-%d %H:%M:%S')

        # We've possibly forced parsing of some malformed data
        #   ("replace" utf-8 encoding errors in read_csv(), "coerce" datetime errors in to_numeric() and to_datetime(), 
        # Now we need to clean that up.
        # Simply drop all points from the file where Measure has been coerced to NaN
        #   and where Datetime has been coerced to NaT
        dat = dat[~dat.Measure.isnull() & ~dat.Datetime.isnull()]
        
        return dat
    
    # Common errors
    except FileNotFoundError:
        warnings.warn("\nInput file not found. FileNotFoundError")
    except pd.errors.EmptyDataError:
        warnings.warn("\nError parsing empty file. EmptyDataError")
    except pd.errors.ParserError:
        warnings.warn("\nError parsing input file. ParserError")
    except Exception as e:
        warnings.warn("\nError parsing input file. {}".format(e))

#######################################
#######################################
# Output formatting and writing
#######################################
#######################################

#######
# Function output_header
#   Write process function header file to GUI text frame
# Parameters:
#   dat               - full dataframe (pandas Dataframe of form Measurement | Datetime)
#   f_name            - path to measurement file (str)
#   header_label      - label to print bold, should be the processing type, e.g., "VIEW", "MANUAL PROCESSING" (str)
#   output_frame_text - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
#######
def output_header(dat, f_name, header_label, output_frame_text):
    # Configure the bold / regular fonts to stay consistent across machines
    output_frame_text.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
    output_frame_text.tag_configure("regular", font=("TkDefaultFont", 10))
    # Set frame in writable state
    output_frame_text.configure(state="normal")
    # Write bold header label (no linebreak after)
    output_frame_text.insert("end", "\n" + header_label + " ", "bold")
    # Write formatted data/file summary
    output_string = "file {fname}\n\t{length} samples, from {start_time} to {end_time}\n".format(fname=f_name, 
                                                                                                 length=len(dat), 
                                                                                                 start_time=dat.loc[0, "Datetime"], 
                                                                                                 end_time=dat.loc[len(dat)-1, "Datetime"])
    output_frame_text.insert("end", output_string, "regular")
    # Set frame back to read-only state
    output_frame_text.configure(state="disabled")

#######
# Function output_error
#   Write an error message to GUI text frame
# Parameters:
#   e                 - error text (str)
#   output_frame_text - tkinter output text widget frame for writing (tkinter.Text)   
# Returns: None
def output_error(e, output_frame_text):
    # Configure the regular font to stay consistent across machines
    output_frame_text.tag_configure("regular", font=("TkDefaultFont", 10))
    # Set frame to writable state
    output_frame_text.configure(state="normal")
    # Write the error message (tab-indented)
    output_frame_text.insert("end", "\t" + e + "\n", "regular")
    # Set frame back to read-only state
    output_frame_text.configure(state="disabled")

#######
# Function output_to_screen
#   Write error information to GUI text frame
# Parameters:
#   output_frame_text - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
def output_to_screen(output_string, output_frame_text):
    # Configure the regular font to stay consistent across machines
    output_frame_text.tag_configure("regular", font=("TkDefaultFont", 10))
    # Set frame to writable state
    output_frame_text.configure(state="normal")
    # Write formatted calibration regression information
    output_frame_text.insert("end", "\t" + output_string + "\n", "regular")
    # Set frame back to read-only state
    output_frame_text.configure(state="disabled")

#######
# Function output_calibration
#   Write initialized calibration information to GUI text frame
#   NOTE does not check if calibration is initialized, this should happen before calling
# Parameters:
#   calibration       - initialized calibration object (MOM_Calculations.Calibration)
#   output_frame_text - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
def output_calibration(calibration, output_frame_text):
    # Configure the regular font to stay consistent across machines
    output_frame_text.tag_configure("regular", font=("TkDefaultFont", 10))
    # Set frame to writable state
    output_frame_text.configure(state="normal")
    # Write formatted calibration regression information
    output_string = "\tCalibration.\tBaseline = {b}\tR^2 = {r}\tIntercept = {i}\tSlope = {s}\n".format(b=int(calibration.baseline),
                                                                                                       r=round(calibration.regression_rsquared,5),
                                                                                                       i=round(calibration.regression_intercept,5),
                                                                                                       s=round(calibration.regression_gradient,5))
    output_frame_text.insert("end", output_string, "regular")
    # Set frame back to read-only state
    output_frame_text.configure(state="disabled")


#######
# Function return_header
#   Single Function to encapsulate all header value, 
#   11/15/24:
#       include weights adjusted for gravity from run_wts
# NOTE rounding only happens here!
# Parameters:
#   header_type  - standard without diagnostics, diagnostic adds fields               
# Returns: 
#   Formatted CSV line (str) for that header type
#######
def return_header(header_type):

    match header_type:
        case "standard":
            return "\tFile,Trace#,dtTime,Pts_All,Pts_Min,Wt_Mean,Wt_Mn_Grav,Wt_Med,Wt_Min_Slope,Wt_Min_Grav,Slope,Min_Slope,Start_All,End_All,Start_Win,End_Win,Baseline, r2, Cal_Slope, Cal_Intcpt\n"
        case "diagnostic":
            return "\tFile,Trace#,dtTime,Pts_All,Pts_Min,Wt_Mean,Wt_Mn_Grav,Wt_Med,Wt_Min_Slope,Wt_Min_Grav,Slope,Min_Slope,d_nXSTD,d_STD,d_PctAbove,d_PctBelow,d_PctAboveX,d_PctBelowX,d_PctBelowBase,d_LongAbove,d_LongBelow\n"
        case "none":
            return ""
        case _:
            return "\tFile,Trace#,dtTime,Pts_All,Pts_Min,Wt_Mean,Wt_Mn_Grav,Wt_Med,Wt_Min_Slope,Wt_Min_Grav,Slope,Min_Slope,Start_All,End_All,Start_Win,Start_End,Baseline\n"

    
#######
# Function output_weights
#   Format CSV line for multiple weight measurement values
#   with OPTION to write to GUI
#   CHANGES 8/31/24:
#       include weights adjusted for gravity from run_wts
# NOTE rounding only happens here!
# Parameters:
#   f_name                 - measurement data file name (str)
#   counter                - number/id marking the relative location of the trace segment within the overall file (MOM_Calculations.Calibration)
#   datetime               - datetime of measurement (str)
#   start_index            - left index of the trace segment (int)
#   end_index              - right index of the trace segment (int)
#   window_start_index     - left index of the best (min) slope window within the trace segment, probably from MOM_Calculations.w_windowed_min_slope (int)
#   window_end_index       - right index of the best (min) slope window within the trace segment, probably from MOM_Calculations.w_windowed_min_slope (int)
#   slope                  - slope of points within the trace segment (float)
#   min_slope              - best (min) slope as found as a window within the trace segment, probably from MOM_Calculations.w_windowed_min_slope (float)
#   output_frame_text      - tkinter output text widget frame for writing (tkinter.Text)
#   include_header         - do you want a CSV header line printed before the data line? (bool, default False)
#   write_output_to_screen - do you want to write the output string to the GUI text widget? (bool, default False)
# Returns: 
#   Formatted CSV line (str)
#######
def output_weights(f_name, counter, datetime, 
                   start_index, end_index, 
                   window_start_index, window_end_index,
                   weight_mean, weight_mean_gravity, weight_median, weight_min_slope, weight_min_slope_gravity,
                   baseline_mean, d_nXSTD, d_STD, d_PctAbove, d_PctBelow, d_PctAboveX, d_Pct_BelowX, d_PctBelowBase, d_LongAbove, d_LongBelow,
                   slope, min_slope,
                   output_frame_text, 
                   include_header=False, write_output_to_screen=True, output_diagnostic=False):
    output_string = ""

    # Add CSV header line before data line, if requested  
    if include_header:
        output_string = return_header("standard")

    # Format data for CSV output
    # NOTE header line appended just before string here, if it's been added to output_string already
    output_string = output_string + "\t{fname},{counter},{dtime},{samples},{samplesMinSlope},{wMean},{wMeanG},{wMedian},{wMinSlope},{wMinSlopeG},{slope},{minSlope},{startIndex},{endIndex},{windowStartIndex},{windowEndIndex},{baselineMean}, {d_nXSTD},{d_STD},{d_PctAbove}\n".format(fname=f_name, 
                                                                                                                                                                                                                                                         counter=counter,
                                                                                                                                                                                                                                                         dtime=datetime,
                                                                                                                                                                                                                                                         samples=(end_index-start_index+1),
                                                                                                                                                                                                                                                         samplesMinSlope=(window_end_index-window_start_index+1),
                                                                                                                                                                                                                                                         wMean=round(weight_mean, 2),
                                                                                                                                                                                                                                                         wMeanG=round(weight_mean_gravity, 2),
                                                                                                                                                                                                                                                         wMedian=round(weight_median,2),
                                                                                                                                                                                                                                                         wMinSlope=round(weight_min_slope,2),
                                                                                                                                                                                                                                                         wMinSlopeG=round(weight_min_slope_gravity,2),
                                                                                                                                                                                                                                                         slope=round(slope,6),
                                                                                                                                                                                                                                                         minSlope=round(min_slope,6),
                                                                                                                                                                                                                                                         startIndex=start_index,
                                                                                                                                                                                                                                                         endIndex=end_index,
                                                                                                                                                                                                                                                         windowStartIndex=window_start_index,
                                                                                                                                                                                                                                                         windowEndIndex=window_end_index,
                                                                                                                                                                                                                                                         baselineMean=baseline_mean,
                                                                                                                                                                                                                                                         d_nXSTD=d_nXSTD,
                                                                                                                                                                                                                                                         d_STD = d_STD,
                                                                                                                                                                                                                                                         d_PctAbove = d_PctAbove)
    
    # If requested, write to GUI screen
    if write_output_to_screen:
        ### create simipler output for screen which already has all the information not related to weight

        screen_string = "\tTrace: {counter},\tTime: {dtime},\tWeight: {wMinSlopeG}\n".format(counter=counter,
                                                                                             dtime=datetime,
                                                                                             wMinSlopeG=round(weight_min_slope_gravity,2))
        # screen_string = screen_string +  "\tTrace: {counter},\Weight: {wMinSlopeG}\n".format(counter=counter, wMinSlopeG=round(weight_min_slope_gravity,1))
        screen_string = screen_string + output_string

        # Configure the regular font to stay consistent across machines    
        output_frame_text.tag_configure("regular", font=("TkDefaultFont", 10))
        # Set frame to writable state
        output_frame_text.configure(state="normal")
        # Write formatted CSV data (and/or header line, if it was added to the string)
        output_frame_text.insert("end", screen_string, "regular") # replaced output_string with screen_string
        # Set frame back to read-only state
        output_frame_text.configure(state="disabled")
        
    if output_diagnostic == True:
        #output withe diagnostics
        output_string = ""
        
        # Add CSV header line before data line, if requested  
        if include_header:
            output_string = return_header("diagnostic")
            # diag_string = "\tFile,Trace_Segment_Num,Datetime,Samples,Sample_Min_Slope,Weight_Mean,Weight_Median,Weight_Min_Slope,Slope,Min_Slope,d_nXSTD,d_STD,d_PctAbove,d_PctBelow,d_PctAboveX,d_PctBelowX,d_PctBelowBase,d_LongAbove,d_LongBelow\n"

        output_string = output_string + "\t{fname},{counter},{dtime},{samples},{samplesMinSlope},{wMean},{wMeanG},{wMedian},{wMinSlope},{wMinSlopeG},{slope},{minSlope},{d_nXSTD},{d_STD},{d_PctAbove},{d_PctBelow},{d_PctAboveX},{d_Pct_BelowX},{d_PctBelowBase},{d_LongAbove},{d_LongBelow}\n".format(fname=f_name, 
                                                                                                                                                                                                                                                                                                    counter=counter,
                                                                                                                                                                                                                                                                                                    dtime=datetime,
                                                                                                                                                                                                                                                                                                    samples=(end_index-start_index+1),
                                                                                                                                                                                                                                                                                                    samplesMinSlope=(window_end_index-window_start_index+1),
                                                                                                                                                                                                                                                                                                    wMean=round(weight_mean, 2),
                                                                                                                                                                                                                                                                                                    wMeanG=round(weight_mean_gravity, 2),
                                                                                                                                                                                                                                                                                                    wMedian=round(weight_median,2),
                                                                                                                                                                                                                                                                                                    wMinSlope=round(weight_min_slope,2),
                                                                                                                                                                                                                                                                                                    wMinSlopeG=round(weight_min_slope_gravity,2),
                                                                                                                                                                                                                                                                                                    slope=round(slope,6),
                                                                                                                                                                                                                                                                                                    minSlope=round(min_slope,6),
                                                                                                                                                                                                                                                                                                    d_nXSTD = d_nXSTD, 
                                                                                                                                                                                                                                                                                                    d_STD = d_STD, 
                                                                                                                                                                                                                                                                                                    d_PctAbove = d_PctAbove, 
                                                                                                                                                                                                                                                                                                    d_PctBelow = d_PctBelow, 
                                                                                                                                                                                                                                                                                                    d_PctAboveX = d_PctAboveX, 
                                                                                                                                                                                                                                                                                                    d_Pct_BelowX = d_Pct_BelowX, 
                                                                                                                                                                                                                                                                                                    d_PctBelowBase = d_PctBelowBase, 
                                                                                                                                                                                                                                                                                                    d_LongAbove = d_LongAbove, 
                                                                                                                                                                                                                                                                                                    d_LongBelow = d_LongBelow
                                                                                                                                                                                                                                                                                                    )

    # Return the formatted string, even if we did not write to GUI
    return output_string

#######################################
#######################################
# Interaction utilities 
#######################################
#######################################

#######
# Class DraggableMarkerPair
#   Draggable markers for selecting a pair of points from plots
#   User confirms selections with enter key
#   Can use is_good to confirm if both points were selected properly
# Adapted from https://stackoverflow.com/questions/43982250/draggable-markers-in-matplotlib
#######
class DraggableMarkerPair():
    def __init__(self, category, start_y, start_x=0):
        self.category = category
        self.start = 0
        self.end = 0
        self.is_good = False

        self.button_class_index = 0
        self.button_classes = ["{category} start".format(category=category), "{category} end".format(category=category)]

        self.ax = plt.gca() 
        self.lines=self.ax.lines[:]
        self.tx = [self.ax.text(0,0,"") for l in self.lines]
        self.marker = [self.ax.plot([start_x],[start_y], marker="o", color="red")[0]]

        self.draggable = False
        self.zooming = False
        self.panning = False

        self.curr_x = 0.0
        self.curr_y = 0.0

        self.c0 = self.ax.figure.canvas.mpl_connect("key_press_event", self.key)
        self.c1 = self.ax.figure.canvas.mpl_connect("button_press_event", self.click)
        self.c2 = self.ax.figure.canvas.mpl_connect("button_release_event", self.release)
        self.c3 = self.ax.figure.canvas.mpl_connect("motion_notify_event", self.drag)

    def click(self, event):
        if event.button == 1 and not self.panning and not self.zooming:
            self.draggable = True
            self.update(event)
            [tx.set_visible(self.draggable) for tx in self.tx]
            [m.set_visible(self.draggable) for m in self.marker]
            self.ax.figure.canvas.draw_idle()        
                
    def drag(self, event):
        if self.draggable:
            self.update(event)
            self.ax.figure.canvas.draw_idle()

    def release(self, event):
        self.draggable = False
        
    def update(self, event):
        try:        
            line = self.lines[0]
            x, y = self.get_closest(line, event.xdata) 
            self.tx[0].set_position((x,y))
            self.tx[0].set_text(self.button_classes[self.button_class_index])
            self.marker[0].set_data([x],[y])
            self.curr_x = x
            self.curr_y = y
        except TypeError:
            pass

    def get_closest(self, line, mx):
        x, y = line.get_data()
        try: 
            mini = np.argmin(np.abs(x-mx))
            return x[mini], y[mini]
        except TypeError:
            pass

    def key(self,event):
        if event.key == 'enter':  
            if self.button_class_index == 0:
                self.ax.plot([self.curr_x],[self.curr_y], marker="o", color="yellow")
                self.button_class_index = 1
                self.start = self.curr_x
                plt.title("Add {category} end point, then press enter.".format(category=self.category))

            elif self.button_class_index == 1:
                self.end = self.curr_x
                self.is_good = True
                plt.close()

            self.update(event)

#######
# Class AxesLimits
#   Stores x- and y- axes limits for re-opening pyplot displays in the same position
#######
class AxesLimits():
    def __init__(self, x_start, x_end, y_start, y_end):
        self.x_start = x_start
        self.x_end = x_end
        self.y_start = y_start
        self.y_end = y_end

#######
# Function annotate_current_markers
#   Adds a set of user marker points to existing (or new) axes
# Parameters:
#   markers         - a list of DraggableMarkerPair markers
# Returns: None
#######
def annote_current_markers(markers):
    # Get axes (or create new ones)
    ax = plt.gca()

    # Plot the pairs of marker points
    for _, d in markers.groupby("Category"):
        ax.plot(d.loc[:,"Measure"], marker="o", color="black", ms=8)
        for index, _ in d.iterrows():
            label = "{category} {point}".format(category=d.loc[index,"Category"], point=d.loc[index, "Point"])
            ax.annotate(label, (index, d.loc[index, "Measure"]), rotation=60)
            
#######
# Function get_trace_point_pair
#   Ask the user to select two points on an interactive pyplot window
# Parameters:
#   dat                    - full dataframe (pandas Dataframe of form Measurement | Datetime)
#   category               - a category label for the marker, probably like "Calibration" or "Bird" (str)
#   markers     (optional) - prexisting markers to add to the plot (optional, list of DraggableMarkerPairs)
#   axes_limits (optional) - prexisting axes limits to re-open plot in previous position
# Returns:
#   Confirmation if user selected two points, helps catch errors like user exiting plot window (bool)
#   Mean measurement value between the marked points (float)
#   Markers added by user (list of DraggableMarkerPair)
#   Axes limits from when the plot closed (MOM_Processing.AxesLimits) 
#######
def get_trace_point_pair(dat, category, markers=None, axes_limits=None):

    # Boot up interactive plot
    plt.ion()
    fig, ax = plt.subplots()
    fig.set_size_inches((PLOT_VIEWER_WIDTH, PLOT_VIEWER_HEIGHT))
    ax.plot(dat.loc[:,"Measure"])

    # Restore previous axes limits, if available
    if (axes_limits is not None):
        ax.set_xlim(left=axes_limits.x_start, right=axes_limits.x_end)
        ax.set_ylim(bottom=axes_limits.y_start, top=axes_limits.y_end)

    # Add previous markers, if available
    if (markers is not None):
        annote_current_markers(markers)

    # Initialize the draggable markers
    dm = DraggableMarkerPair(category=category, start_y=min(dat["Measure"]))
    ax.set_title("Add {category} start point, then press enter.".format(category=category))
    plt.show(block=True)

    plt.ioff()

    # Catch common draggable marker errors
    # First, if the pair was not initialzied correctly (e.g., user exited window)
    # Second, if the pair marks the same index (e.g., user double clicked enter)
    if not dm.is_good or dm.start == dm.end:
        return False, None, None, None

    # Extract the selected indices
    start_index = min(dm.start, dm.end)
    end_index = max(dm.start, dm.end)

    # Extract the axes limits from interactive viewer to restore limits later
    end_view_x_start, end_view_x_end = ax.get_xlim()
    end_view_y_start, end_view_y_end = ax.get_ylim()
    new_axes_limits = AxesLimits(end_view_x_start, end_view_x_end, end_view_y_start, end_view_y_end)

    # Calculate mean measure
    measures = dat.loc[start_index:end_index, "Measure"]
    mean_measure = measures.mean()

    # Calculate datetime range
    start_time = dat.loc[start_index, "Datetime"]
    end_time = dat.loc[end_index, "Datetime"]

    # Package up marked point information
    markers = pd.DataFrame({"Category":category,
                            "Point":["Start", "End"],
                            "Index":[start_index , end_index],
                            "Datetime":[start_time, end_time],
                            "Measure":[dat.loc[start_index ,"Measure"], dat.loc[end_index,"Measure"]]})
    markers = markers.set_index("Index")

    return True, mean_measure, markers, new_axes_limits

#######################################
#######################################
# Core processing functions
#######################################
#######################################

#######
# Function run_user_calibration
#   Perform user calibration with interactive plot of load cell trace 
# NOTE this will return an UNINITIALIZED calibration object if the user input failed!
#      you have to check for this outside the function
# Parameters:
#   dat                             - full dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration                     - weight calibration object (MOM_Calculations.Calibration)
#   calibration_user_entered_values - tkinter text input frames to update initial calibration values (list of tkinter.Entry)
#   output_frame_text               - tkinter output text widget frame for writing (tkinter.Text)
# Returns:
#   calibration object, uninitialized or initialized (MOM_Calculations.Calibration) or None, if user calibration failed 
#######
def run_user_calibration(dat, calibration, calibration_user_entered_values, output_frame_text):
    # If the calibration has not been initialized OR the user declines the opportunity to use the previous one, take it
    # NOTE python short-circuits the OR operator, so if the calibration has not been initialized, we will automatically take the calibration
    if not calibration.initialized or not messagebox.askyesno("Confirmation", "Use previous calibration?"):
        # Set manual calibration values from entry frames
        # checking to see that the values are well-formed floats (not e.g., text)
        if not calibration.set_true(*[entry.get() for entry in calibration_user_entered_values]):
            output_error("ERROR invalid calibration input value", output_frame_text)
            # We return without an initialized calibration object if this failed
            return

        # Conduct calibrations
        calibration_true_values = calibration.get_true()

        # Get baseline measurement from user
        # After each measurement, we check that BOTH points are selected, and kick out of the function if not
        good, baseline_cal_mean, baseline_cal_markers, axes_limits = get_trace_point_pair(dat, "Cal[Baseline]")
        if not good:
            output_error("ERROR user marker error during calibration", output_frame_text)
            return
        markers = baseline_cal_markers
        
        # Get three calibration measurements from user
        good, cal1_mean, cal1_markers, axes_limits = get_trace_point_pair(dat, "Cal1[{}]".format(calibration_true_values[0]), markers, axes_limits)
        if not good:
            output_error("ERROR user marker error during calibration", output_frame_text)
            return
        markers = pd.concat([markers, cal1_markers])

        good, cal2_mean, cal2_markers, axes_limits = get_trace_point_pair(dat, "Cal2[{}]".format(calibration_true_values[1]), markers, axes_limits)
        if not good:
            output_error("ERROR user marker error during calibration", output_frame_text)
            return
        markers = pd.concat([markers, cal2_markers])
        
        good, cal3_mean, cal3_markers, axes_limits = get_trace_point_pair(dat, "Cal3[{}]".format(calibration_true_values[2]), markers, axes_limits)
        if not good:
            output_error("ERROR user marker error during calibration", output_frame_text)
            return
        markers = pd.concat([markers, cal3_markers])

        # Conduct calibration regression (results stored in object)
        # Now calibration.initialized is True
        calibration.regression(baseline_cal_mean, cal1_mean, cal2_mean, cal3_mean)
        
        # Show the user the regression
        # First, extracting the calibration values from the stored object
        calibration_difference_values = calibration.get_difference()
        calibration_regressed_values = [x * calibration.regression_gradient + calibration.regression_intercept for x in calibration_difference_values]

        # Second, plotting the calibrations for user confirmation 
        _, ax = plt.subplots()
        ax.plot(calibration_difference_values, calibration_true_values, marker="o", color="black", linestyle="None")
        ax.plot(calibration_difference_values, calibration_regressed_values, color="gray", linestyle="dashed")
        plt.xlabel("Measured value (strain difference from baseline)")
        plt.ylabel("True value (g)")
        plt.title("Calibration regression\n(R^2={r}, Inter={i}, Slope={s})".format(r=round(calibration.regression_rsquared,5), 
                                                                                   s=round(calibration.regression_gradient,5),
                                                                                   i=round(calibration.regression_intercept,5)))
        plt.show()

    return calibration

#######
# Function run_weights
#   Calculate multiple weights, using whatever set of functions you'd like, given a start and end index
#   Passes results to output_weights() to format return value string 
#   CHANGES 8/31/2024
#       add weight_mean_gravity which adjusts weigh_mean for gravitational effect after Afanasyev et al. 2015
#       add weight_min_slope_gravity which adjusts that value for gravitational effect after Afanasyev et al. 2015
# Parameters:
#   dat                    - full dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration            - initialized weight calibration object (MOM_Calculations.Calibration)
#   start_index            - left index of the trace segment (int) - CHANGE 8/30/24 - start/stop index expanded in w_windowed_min_slope (RAM)
#   end_index              - right index of the trace segment (int)
#   baseline_mean          - baseline strain value near measurement (float)
#   f_name                 - measurement data file name (str)
#   counter                - number/id marking the relative location of the trace segment within the overall file (MOM_Calculations.Calibration)
#   output_frame_text      - tkinter output text widget frame for writing (tkinter.Text)
#   include_header         - do you want a CSV header line printed before the data line? (bool, default False)
#   write_output_to_screen - do you want to write the output string to the GUI text widget? (bool, default False)
# Returns: 
#   Formatted CSV line, from output_weights (str)
#######
def run_weights(dat, calibration, 
                start_index, end_index, 
                baseline_mean, 
                f_name, counter, 
                output_frame_text, 
                include_header=False, write_output_to_screen=True, do_diagnostic = False):
    
    # Call weight calculation functions
    weight_mean, slope = MOM_Calculations.w_mean(dat, calibration, start_index, end_index, baseline_mean)
    weight_mean_gravity = MOM_Calculations.w_adjust_for_gravity(weight_mean, slope)
    weight_median, _ = MOM_Calculations.w_median(dat, calibration, start_index, end_index, baseline_mean)
    weight_min_slope, min_slope, window_start_index, window_end_index = MOM_Calculations.w_windowed_min_slope(dat, calibration, start_index-10, end_index+10, baseline_mean, 25, 0.7)
    weight_min_slope_gravity = MOM_Calculations.w_adjust_for_gravity(weight_min_slope, min_slope)

    if do_diagnostic:  # run diagnostics only as needed
        d_nXSTD, d_STD, d_PctAbove, d_PctBelow, d_PctAboveX, d_Pct_BelowX, d_PctBelowBase, d_LongAbove, d_LongBelow = MOM_Calculations.w_Rtn_Diagnostics(dat, start_index, end_index, baseline_mean, 3)
    else:
        d_nXSTD = round(calibration.regression_rsquared,5)
        d_STD = round(calibration.regression_gradient,5)
        d_PctAbove = round(calibration.regression_intercept,5)
        d_PctBelow = d_PctAboveX = d_Pct_BelowX = d_PctBelowBase = d_LongAbove = d_LongBelow = 0

    # Datetime of the center of the trace segment
    datetime = dat.loc[int((start_index+end_index)/2), "Datetime"]

    # Return the formatted output string as defined in output_weights
    formatted_output_string = output_weights(f_name=f_name,
                                             counter=counter, 
                                             datetime=datetime, 
                                             start_index=start_index, 
                                             end_index=end_index, 
                                             window_start_index=window_start_index, 
                                             window_end_index=window_end_index, 
                                             weight_mean=weight_mean, 
                                             weight_mean_gravity=weight_mean_gravity,
                                             weight_median=weight_median,
                                             weight_min_slope=weight_min_slope,
                                             weight_min_slope_gravity=weight_min_slope_gravity,
                                             baseline_mean=baseline_mean,
                                             d_nXSTD = d_nXSTD, 
                                             d_STD = d_STD, 
                                             d_PctAbove = d_PctAbove, 
                                             d_PctBelow = d_PctBelow, 
                                             d_PctAboveX = d_PctAboveX, 
                                             d_Pct_BelowX = d_Pct_BelowX, 
                                             d_PctBelowBase = d_PctBelowBase, 
                                             d_LongAbove = d_LongAbove, 
                                             d_LongBelow = d_LongBelow,
                                             slope=slope,
                                             min_slope=min_slope,
                                             output_frame_text=output_frame_text,
                                             include_header=include_header,
                                             write_output_to_screen=write_output_to_screen)
    
    
    # if you wanted to save ethis string, you could save the return value from this function
    if False:
        return full_formatted_string
    else:
        return formatted_output_string

#######
# Function view [CORE OPERATION]
#   View a strain trace file as an interactive pyplot figure
# Parameters:
#   output_frame_text - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
#######
def view(output_frame_text):

    # User selects file
    f_path = get_user_file()

    # Parse data from the file
    dat = parse_trace_file(f_path)

    # File parse failures will return None data; exit if that occurred
    if dat is None:
        return
    
    # Extract useful file name for display / report
    f_name = os.path.basename(f_path)

    # Write the initial processing output to GUI text widget
    output_header(dat, f_name, "VIEWING", output_frame_text)

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches((PLOT_VIEWER_WIDTH, PLOT_VIEWER_HEIGHT))
    ax.plot(dat.loc[:,"Measure"])
    ax.set_title(os.path.splitext(f_name)[0])
    plt.show()

#######
# Function process_manual [CORE OPERATION]
#   User opens a strain measurement file from a loadcell, marks calibration segments, and then measures bird segments
#   Write output to GUI text widget
#   CHANGE NEEDED: lost ability to output results to a text file. Could copy/paste from screen, but better to allow export
# Parameters:
#   calibration                     - weight calibration object (MOM_Calculations.Calibration)
#   calibration_user_entered_values - tkinter text input frames to update initial calibration values (list of tkinter.Entry)
#   output_frame_text               - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
#######
def process_manual(calibration, calibration_user_entered_values, output_frame_text):
    
    # User selects file
    f_path = get_user_file()

    # Parse data from the file
    dat = parse_trace_file(f_path)

    # File parse failures will return None data; exit if that occurred
    if dat is None:
        return

    # Extract useful file name for display / report
    f_name = os.path.basename(f_path)

    # Write the initial processing output to GUI text widget
    output_header(dat, f_name, "MANUAL PROCESSING", output_frame_text)

    # Allow the user to calibrate
    #   (will check if calibration object is initialized and, if so, ask user if they want to retain)
    calibration = run_user_calibration(dat, calibration, calibration_user_entered_values, output_frame_text)
    if calibration is None or not calibration.initialized:
        return

    # Output calibration info to GUI
    output_calibration(calibration, output_frame_text)

    # Process multiple birds
    # Looping as long as the user confirms
    bird_counter = 1
    while (True):
        if messagebox.askyesno("Confirmation", "Enter bird data?"):
            # Process a bird

            # Get the baseline measurement from near the bird activity from the user
            # After each measurement, we check that BOTH points are selected, and allow the user to try again if not
            good, bird_baseline_mean, bird_baseline_markers, axes_limits = get_trace_point_pair(dat, "Bird[Baseline]")
            if not good:
                output_error("ERROR user marker error during bird baseline", output_frame_text)
                continue 
            markers = bird_baseline_markers

            # Measurement
            good, _, bird_value_markers, _ = get_trace_point_pair(dat, "Bird[Measure]", markers, axes_limits)
            if not good:
                output_error("ERROR user marker error during bird measurement", output_frame_text)
                continue
            markers = pd.concat([markers, bird_value_markers])

            # Get marked start and end points of bird measurements 
            bird_start_index = bird_value_markers.index[0]
            bird_end_index = bird_value_markers.index[1]

            # Calculate the weight information
            # This also write to GUI output
            # (you can store the return here if needed, which is CSV-formatted string)
            run_weights(dat=dat,
                        calibration=calibration,
                        start_index=bird_start_index,
                        end_index=bird_end_index,
                        baseline_mean=bird_baseline_mean,
                        f_name=f_name,
                        counter=bird_counter,
                        include_header=bird_counter==1,
                        output_frame_text=output_frame_text,
                        write_output_to_screen=True)
            
            # If we've successfully run the weights, we're on to the next bird
            bird_counter = bird_counter + 1
        else:
            break

#######
# ************************IN PROGRESS************************************
# Function process_auto[CORE OPERATION]
#   Currently, the function starts exactly the same as process_manual.
#   User selects a single file and conducts a manual calibration.
#   Changes from earlier: 
#   The program then automatically searches for windows >30g in the trace data.
#   Finds PR peaks (second, second-to-last)
#   Uses w_windowed_min_slope function to calculate weights between those peaks
#   Produces a plot with those weights annotated above each window
#   CHANGES 8/31/2024
#       Automatically finds calibration sections with no user input - assumes standard procedure in the field
#       Adds flag for showing plots
#       uses run_weights to get all calculated estimates
#       formats weight calculations and stores in a dataframe (results_df)
# Parameters:
#   calibration                     - weight calibration object (MOM_Calculations.Calibration)
#   calibration_user_entered_values - tkinter text input frames to update initial calibration values (list of tkinter.Entry)
#   output_frame_text               - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
#######
def process_auto(calibration, calibration_user_entered_values, output_frame_text, show_graph = True):
    
    # ------------------
    # Automatic calibration
    # ------------------

    # User selects file
    f_path = get_user_file()

    if(True):
        my_header = "Header above auto output"
        my_header = return_header("standard")
        output_to_screen(my_header, output_frame_text)
        my_output = auto_one_file(f_path, calibration, calibration_user_entered_values, output_frame_text, show_graph = True)




#######
# ************************************************************
# Function process_auto_batch [CORE OPERATION]
#   - Runs automated processing of multiple files
#   - User chooses a folder containing all the files to batch process
#   - Processes each file and saves the returned text info for all the relevant traces on the file
#   - Only processes files starting with "DL" and ending with "TXT" or "CSV" (and lowercase)
#
# Parameters:
#   calibration                     - weight calibration object (MOM_Calculations.Calibration)
#   calibration_user_entered_values - tkinter text input frames to update initial calibration values (list of tkinter.Entry)
#   output_frame_text               - tkinter output text widget frame for writing (tkinter.Text)
# Returns: None
#######
def process_auto_batch(calibration, calibration_user_entered_values, output_frame_text, show_graph = True):
 
    do_print = False

    # User selects folder to deal with 
    folder_path = filedialog.askdirectory()

    if do_print: 
        print(folder_path)
        all_files = os.listdir(folder_path)
    
        # Filter out only files (not directories)
        files = [f for f in all_files if os.path.isfile(os.path.join(folder_path, f))]

        # Print each file name
        for file_name in files: print(file_name)

    if(folder_path):

        ## start timer
        start_time = tm.time()

        # Define the header and initialize the list with the header
        column_names = ["Filename", "Sequence", "DateTime", "Start_pt", "End_pt", "W1", "W2", "W3", "W4", "W5", "Intcpt", "Slope"]

        # Setup a list to hold all the results from all the files
        batch_output = []

        # Define valid file extensions
        valid_extensions = ('.txt', '.csv', '.TXT', '.CSV')

        for filename in os.listdir(folder_path):
            if filename.startswith('.DS'):
                # skip this file that MacOS makes in the background
                continue

            if filename.startswith('DL') and filename.lower().endswith(valid_extensions):

                if do_print: print(f"Handling: {filename}")

                f_path = os.path.join(folder_path, filename)
                
                try:
                    # Process the file and get the output
                    my_output = auto_one_file(f_path, calibration, calibration_user_entered_values, output_frame_text, show_graph=False)
                    
                    # Assuming auto_one_file returns a list of lists or tuples with the expected data format
                    if do_print: print(my_output)
                except Exception as e:
                    print("error occurred")
                    my_output = filename

                # the built-in auto formatting doesn't work for exporting the data, so change a couple of things
                # 1- we don't need an extra hard return
                stripped_data = [line.strip('\n') for line in my_output]
                # 2- also remove the leading \t
                stripped_data = [line.strip('\t') for line in stripped_data]
                batch_output.extend(stripped_data)

                if do_print: print("Combined, next file...")

        # end timer and Calculate elapsed time
        end_time = tm.time()
        elapsed_time = end_time - start_time  
        print("-------- ")
        print(f"Time taken using time module: {end_time - start_time:.4f} seconds")
        print("--------")
        
        # Ask the user to choose the file path and name for saving the output
        output_file_path = filedialog.asksaveasfilename(title="Save Combined File As", defaultextension=".txt",
                                                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        
        batch_output_df = pd.DataFrame(batch_output, columns=['Formatted_Output'])

        # pseudo header added
        new_row = {"Formatted_Output": "fname,seq,dtime,start,stop,wMean,wMeanG,wMedian,wMinSlope,wMinSlopeG,slope,minSlope"}
        # Convert the new row to a DataFrame so we can put it at the top of the list
        new_row_df = pd.DataFrame([new_row])
        # put the new row before the rest of the data - now a header
        batch_output_df = pd.concat([new_row_df, batch_output_df], ignore_index=True)

        batch_output_df.to_csv(output_file_path, index=False, header=False, sep='\t')

        tk.messagebox.showinfo(message = "Files processed and saved.")
        return None
    else:
        tk.messagebox.showinfo(message = "No folder chosen. Try again.")
        return None
    


#######
# Function run_auto_calibration
#   Perform auto calibration with no user input
# NOTE this will return an UNINITIALIZED calibration object if the user input failed!
#      you have to check for this outside the function
# Parameters:
#   dat                             - full dataframe (pandas Dataframe of form Measurement | Datetime)
#   calibration                     - weight calibration object (MOM_Calculations.Calibration)
#   calibration_user_entered_values - tkinter text input frames to update initial calibration values (list of tkinter.Entry)
#   output_frame_text               - tkinter output text widget frame for writing (tkinter.Text)
# Returns:
#   calibration object, uninitialized or initialized (NONE), if user calibration failed, and T/F is initialized, T/F if R2 good
#######
def run_auto_calibration(dat, calibration, calibration_user_entered_values, output_frame_text):

    if not calibration.set_true(*[entry.get() for entry in calibration_user_entered_values]):
        output_error("ERROR invalid calibration input value", output_frame_text)
        # We return without an initialized calibration object if this failed
        return None, False  # Return indicating failure, the second value isn't really needed

    # Conduct calibrations
    calibration_true_values = calibration.get_true()

    baseline_cal_mean, cal1_mean, cal2_mean, cal3_mean = get_auto_calibration_values(dat, baseline_fraction=0.0003, num_sections=10, window_size=75, std_threshold=200, tolerance=5000, lines = 5000)

    # Conduct calibration regression (results stored in object)
    # Now calibration.initialized is True
    calibration.regression(baseline_cal_mean, cal1_mean, cal2_mean, cal3_mean)
    
    # First, extracting the calibration values from the stored object
    calibration_difference_values = calibration.get_difference()
    calibration_regressed_values = [x * calibration.regression_gradient + calibration.regression_intercept for x in calibration_difference_values]

    # check for a good calibration - Check the R² value of the regression
    is_good_r_squared = calibration.regression_rsquared > 0.99999

    if(False):  # do not plot the fit
        # Second, plotting the calibrations for user confirmation 
        _, ax = plt.subplots()
        ax.plot(calibration_difference_values, calibration_true_values, marker="o", color="black", linestyle="None")
        ax.plot(calibration_difference_values, calibration_regressed_values, color="gray", linestyle="dashed")
        plt.xlabel("Measured value (strain difference from baseline)")
        plt.ylabel("True value (g)")
        plt.title("Calibration regression\n(R^2={r}, Inter={i}, Slope={s})".format(r=round(calibration.regression_rsquared,5), 
                                                                                s=round(calibration.regression_gradient,5),
                                                                                i=round(calibration.regression_intercept,5)))
        plt.show()

    return calibration, is_good_r_squared


############################
#
#   get_auto_calibration_values
#       RAM, Aug 21, 2024
#
#    Detect sections in the first 5000 lines where values rise above and fall back to the baseline value.
#    can Plot the data with vertical lines at start and stop points of detected sections.
#
#    Parameters:
#    - dataframe: pd.DataFrame with a 'Measure' column
#    - baseline_fraction: Fraction of the baseline to determine thresholds wihtout user help (default is 0.0002)
#    - num_sections: Number of sections to detect (default is 10) - get more than you need to be sure we get first 3
#    - window_size: Minimum number of points/lines for detected section (default is 75) - default may cause some not to work
#    - std_threshold: Standard deviation threshold for baseline calculation (default is 200) - should be 150 for baseline
#    - tolerance: Tolerance for deviation from baseline mean (default is 5000) - not sure this is right
#    - lines - how much of the file to consider. Defaults to 5000 for detecting the calibration weights
#    
#    Returns:
#    - A tuple with the baseline value and a DataFrame with columns 'Section', 'Start', and 'Stop' indicating the detected sections
#   
##############
def get_auto_calibration_values(dataframe, baseline_fraction=0.0003, num_sections=10, window_size=75, std_threshold=200, tolerance=5000, lines = 5000):
 
    if do_print: print("in get_auto_calibration_values")

    # Slice the first 5000 lines - make this a parameter - 5000 ONLY FOR Calibration does this work!
    if(lines > 0):
        subset_data = dataframe.head(5000)
    else:
        subset_data = dataframe
    
    # Calculate rolling mean and standard deviation
    rolling_mean = subset_data['Measure'].rolling(window=window_size).mean()
    rolling_std = subset_data['Measure'].rolling(window=window_size).std()
    
    # Drop NaN values created by the rolling window
    rolling_mean = rolling_mean.dropna()
    rolling_std = rolling_std.dropna()
    
    # Combine the results into a DataFrame for easier analysis
    results = pd.DataFrame({
        'Mean': rolling_mean,
        'Std': rolling_std
    })

    if do_print:
        print(f"Length of results dataframe: {len(results)}")

    # Find the index of the row with the lowest mean and lowest variation
    min_mean_index = results['Mean'].idxmin()
    min_std_index = results['Std'].idxmin()

    m_value = results.iloc[min_mean_index]['Mean']
    s_value = results.iloc[min_std_index]['Mean']

    if do_print:
        print(f"Mean at min_mean_index {min_mean_index}: {results.iloc[min_mean_index]['Mean']}")
        print(f"Mean at min_std_index {min_std_index}: {results.iloc[min_std_index]['Mean']}")

    # Check which index satisfies both conditions - use lower value of the two, if needed
    # baseline_index = min_mean_index if min_std_index == min_mean_index else results['Mean'].idxmin()
    if (m_value < s_value):
        baseline_index = min_mean_index
    else:
        baseline_index = min_std_index

    # Extract the baseline window
    baseline_cal_mean= results.iloc[baseline_index]['Mean']

    # Define thresholds based on baseline fraction so dont' need user to tell us what is off baseline
    high_threshold = baseline_cal_mean + baseline_fraction * baseline_cal_mean
    low_threshold = baseline_cal_mean + (baseline_fraction*.8) * baseline_cal_mean  ### for dropping below it
    if do_print:
        print(f"Using baseline mean {baseline_cal_mean} from df at index: {baseline_index}")
        print(f"Hi/Low thresholds: {high_threshold} / {low_threshold}")

    # Initialize detection variables
    in_section = False
    start_idx = None
    detected_sections = []
    
    # Step through the data to detect rises and falls
    for i in range(len(subset_data)):
        value = subset_data['Measure'].iloc[i]
        
        if value > high_threshold and not in_section:
            # Start of a new section
            start_idx = i
            in_section = True
        elif value < high_threshold and in_section:  ## CHANGE from low threshold
            # End of the current section
            stop_idx = i
            if (stop_idx - start_idx) > window_size:  # Check window size condition
                detected_sections.append((start_idx, stop_idx))
            in_section = False
            
            # Stop if we've detected the required number of sections
            if len(detected_sections) >= num_sections:
                break
    
    if do_print: print(f"size of detected sections : {len(detected_sections)}")

    # Create a DataFrame to store the section start and stop indices
    sections_df = pd.DataFrame(detected_sections, columns=['Start', 'Stop'])
    sections_df.index.name = 'Section'
    sections_df.index += 1  # Start numbering from 1

    # Todo: check to see if we have detected enough sections (3) - or don't go forward
    if(len(sections_df)<3):
        # we have a problem
        cal1_mean = sections_df['Mean'].iloc[0] if len(sections_df) > 0 else 0
        cal2_mean = sections_df['Mean'].iloc[1] if len(sections_df) > 1 else 0
        cal3_mean = sections_df['Mean'].iloc[2] if len(sections_df) > 2 else 0 
    else:
        # Put another column into section_df with the mean values there with find_calibration_flats(measure_series, start_pt, stop_pt, min_len, min_threshold, max_pct=0.5):
        for i, row in sections_df.iterrows():      
            start_pt = row['Start']
            stop_pt = row['Stop']
            sections_df.at[i, 'Mean'], _, _, _,  = section_mean, section_slope, section_start, section_len = find_calibration_flats(subset_data, start_pt, stop_pt, 60, high_threshold, 0.7)

        cal1_mean = sections_df['Mean'].iloc[0] if len(sections_df) > 0 else None
        cal2_mean = sections_df['Mean'].iloc[1] if len(sections_df) > 1 else None
        cal3_mean = sections_df['Mean'].iloc[2] if len(sections_df) > 2 else None  

        if do_print:
            print("Detected Sections:")
            print(sections_df)  

        if do_print:
            # Plot the raw data with vertical lines for start and stop points
            plt.figure(figsize=(12, 6))
            plt.plot(subset_data['Measure'], label='Raw Data')
            
            for _, row in sections_df.iterrows():
                plt.axvline(x=row['Start'], color='r', linestyle='--', label=f'Start {row.name}')
                plt.axvline(x=row['Stop'], color='g', linestyle='--', label=f'Stop {row.name}')
            
            plt.xlabel('Index')
            plt.ylabel('Measure')
            plt.title('Raw Data with Detected Sections')
            plt.legend()
            plt.show()

    return baseline_cal_mean, cal1_mean, cal2_mean, cal3_mean

#############################
# Function get_bird_baseline: does automatic (no user input) ID of baseline value for a bird trace
#   RAM 8/21/24
#
#   looks before and after the passed point in a dataframe to find the lowest stable value to used as local baseline
#
#   parameters
#       dataframe with the traces
#       start and stop locations of the trace
#       buffer size is how far before and after trace we look for a good baseline - 60 SPS guides you
#       window size - how many points need to be level for us to use this as a baseline   
#   returns: Mean baseline value, all_good a flag to say that min mean and min std weren't the same
#######
def get_bird_baseline(my_bird_df, start_index, stop_index, buffer_size=300, window_size=40):

    # Define new indices before and after the focal trace by adding/subtracting the buffer
    new_start_index = start_index - buffer_size
    new_stop_index = stop_index + buffer_size

    if new_start_index < 0:
        new_start_index = 0
    if new_stop_index > len(my_bird_df):
        new_stop_index = len(my_bird_df)

    # Create subsets before and after the specified indices
    subset_before = my_bird_df.iloc[new_start_index:start_index]
    subset_after = my_bird_df.iloc[stop_index:new_stop_index]

    # Calculate rolling mean and standard deviation for the 'before' subset
    rolling_mean_before = subset_before['Measure'].rolling(window=window_size).mean().dropna()
    rolling_std_before = subset_before['Measure'].rolling(window=window_size).std().dropna()

    # Calculate rolling mean and standard deviation for the 'after' subset
    rolling_mean_after = subset_after['Measure'].rolling(window=window_size).mean().dropna()
    rolling_std_after = subset_after['Measure'].rolling(window=window_size).std().dropna()

    # Create DataFrames for before and after results
    results_bird_cal_before = pd.DataFrame({
        'Mean_Before': rolling_mean_before,
        'Std_Before': rolling_std_before
    })

    results_bird_cal_after = pd.DataFrame({
        'Mean_After': rolling_mean_after,
        'Std_After': rolling_std_after
    })

    # combine them since all we care is for the lowest value between the 2
    rolling_mean_combined = pd.concat([rolling_mean_before, rolling_mean_after], ignore_index=True)
    rolling_std_combined = pd.concat([rolling_std_before, rolling_std_after], ignore_index=True)

    # Create a DataFrame with combined rolling mean and std values
    results_bird_cal_combined = pd.DataFrame({
        'Mean': rolling_mean_combined,
        'Std': rolling_std_combined
    })

    # what are our values
    min_mean_index = results_bird_cal_combined['Mean'].idxmin()
    min_std_index = results_bird_cal_combined['Std'].idxmin()

    mean_value_at_minSTD = results_bird_cal_combined['Mean'].iloc[min_std_index]
    std_value_at_minSTD = results_bird_cal_combined['Std'].iloc[min_std_index]

    mean_value_at_minMean = results_bird_cal_combined['Mean'].iloc[min_mean_index]
    std_value_at_minMean = results_bird_cal_combined['Std'].iloc[min_mean_index]

    local_baseline = mean_value_at_minSTD

    #  we  pass a flag saying they weren't the same, or change it somehow, but not now just pass the flag
    if(min_mean_index != min_std_index):
        all_good = False
    else:
        all_good = True

    if do_print:
        print(f"Mean at mean_min index: {min_mean_index} is: {mean_value_at_minMean}, STD: {round(std_value_at_minMean,1)}")
        print(f"Mean at mean_std index: {min_std_index} is: {mean_value_at_minSTD}, STD: {round(std_value_at_minSTD,1)}")
        print(f"------- Return value: {mean_value_at_minSTD}")

    return(local_baseline, all_good)

##############
#    find_calibration_flats - RAM 7/23/2024
#    Function to ID calibration weights - was do_Slope_0
#       now only used when finding baseline and calibration weights without user input
#       CLUNKY - need to clean it up 8/4/2024
#    Parameters:
#    - measure_series: DataFrame  containing the measure data. Get the the whole dataframe, so you can go oustide bounds
#       - of the window of interst of your f\jull slope measures
#    - start_pt: Starting point (long integer). where to start and end the window counting
#    - stop_pt: Ending point (long integer).  could just be the lenght of the slice we are sending it when using real data
#    - min_len: Minimum length of windows (long integer). We have data that could determine the right number for this
#    - min_threshold: Minimum threshold for the intercept value (real number).
#    - max_pct: Max proportion of the passed series to be used to determine the max length of windows (real number, default is 0.5). NOT USED NOW
# 
#   Returns:
#    - Mean Value for calculation of mass AND starting point and width of window used
#########
def find_calibration_flats(measure_series, start_pt, stop_pt, min_len, min_threshold, max_pct=0.5):

    max_len = int((stop_pt - start_pt) * max_pct)
    max_len = min_len + 1  # only looking for a flat spot, so don't mess around, could get rid of these, too
    if(max_len <= min_len):
        max_len = min_len + 2 # (stop_pt - start_pt)
    total_windows = max_len - min_len
    trace_len = stop_pt - start_pt - 1

    if(do_print):
        print(f"max_len: {max_len}")
        print(f"total_windows: {total_windows}")
        print(f"trace_len: {trace_len}")

    if total_windows <= 0:
        raise ValueError("total_windows must be greater than 0")

    rows = []

    for i in range(start_pt, stop_pt):
        for w in range(min_len, max_len):
            v_start = int(i - (w/2)) - 1
            v_stop = int(i + (w/2))

            if (w % 2 != 0):
                v_start = v_start - 1

            new_series = measure_series.iloc[v_start:v_stop]
            if(do_print):
                print(f"\nnew_series (i={i}, w={w}):\n{new_series}")

            if len(new_series) < 2:
                continue

            x_values = np.arange(len(new_series))
            slope, intercept = np.polyfit(x_values, new_series['Measure'], 1)
            mean_val = new_series['Measure'].mean()

            if(do_print):
                # print(f"x_values: {x_values}")
                print(f"slope: {slope}")
                print(f"intercept: {intercept}")
                print(f"mean_val: {mean_val}")

            wt_calc = np.random.uniform(0, 100)

            row_data = {
                'slope': slope,
                'intercept': intercept,
                'wt_calc': wt_calc,
                'center_pt': i,
                'total_len': w,
                'v_start': v_start,
                'v_stop': v_stop,
                'mean_val': mean_val
            }

            rows.append(row_data)

    results_df = pd.DataFrame(rows, columns=['slope', 'intercept', 'wt_calc', 'center_pt', 'total_len', 'v_start', 'v_stop', 'mean_val'])
    results_df['slope_abs'] = abs(results_df['slope'])

    mymin = results_df['slope_abs'].min()

    if(do_print):
        print("Results DataFrame:")
        print(results_df.head())
        print(f"Min slope_abs value: {mymin}")

        # Get the row with the smallest values of 'slope_abs'
    filtered_df = results_df.nsmallest(1, 'slope_abs')
        # make sure it is above the background values
    filtered_df = filtered_df[filtered_df['mean_val'] >= min_threshold]

    if(do_print):
        print("Filtered DataFrame with 5 smallest slope_abs values:")
        print(filtered_df)
        print("Filtered DataFrame after mean_val threshold filter:")
        print(filtered_df.head())

    if not filtered_df.empty:
        min_abs_slope_mean = filtered_df['mean_val'].mean() 
        # Find the index of the row with the minimum 'slope_abs'
        min_slope_abs_index = results_df['slope_abs'].idxmin()

        # Retrieve the values of 'v_start' and 'total_len' for that row
        min_row = filtered_df.loc[min_slope_abs_index]
        v_start = min_row['v_start']
        total_len = min_row['total_len']
        min_slope = results_df['slope'].iloc[min_slope_abs_index]
        if(do_print):
            print(f"\nMean Value of the minimum absolute slope value row ({min_abs_slope_mean}):")
        return round(min_abs_slope_mean,1), min_slope, v_start, total_len
    
    else: # CLEAN this- flag a bad calibration
        # mb.showinfo("Cannot auto-calibrate. R2 = ", str(cal_r_squared) + ". NOT GOOD.")
        print("\nFiltered DataFrame is empty.")
        return 0, 999, 0, 0

##############
#    auto_one_file - RAM 9/1/2024
#       Function to do all the automatic calculations on a single file
#       Can be used as stand-alone (Automatic Button) or on each of a series of files (Auto Batch)
#       used when finding baseline and calibration weights without user input
#           - automatically does the calibration calculations from the beginning of the file
#           - locates and evaluates all relevant traces, including finding that trace's baseline
#    Parameters:
#       f_path - the location of the file to be processed 
#       calibration object
#       user values for the calibratoin from the screen
#       pointer to the onscreen text output
#       show_graph - if true, gives user look at the calibration regression and traces - should be False for batch operations
#   
#   Returns:
#       text list with (for each file): file name, trace number, date/time of trace, 5 weight values, slope of measured trace, min slope found
#########
def auto_one_file(f_path, calibration, calibration_user_entered_values, output_frame_text, show_graph = True):

      # Parse data from the file
    dat = parse_trace_file(f_path)

    # File parse failures will return None data; exit if that occurred
    if dat is None:
        return

    # Extract useful file name for display / report
    f_name = os.path.basename(f_path)

    # Write the initial processing output to GUI text widget
    output_header(dat, f_name, "AUTO PROCESSING", output_frame_text)

    calibration, good_R2 = run_auto_calibration(dat, calibration, calibration_user_entered_values, output_frame_text)
    if calibration is None or not calibration.initialized:
        print("Calibration failed. Invalid calibration object.")
        # messagebox.showerror("Calibration Error", "Calibration failed. Invalid calibration object.")
        return None
    elif not good_R2:
        print("Calibration unsuccessful with a bad R² value.")
        # messagebox.showerror("Calibration Error", "Calibration failed with a low R2.")
        return None
    else:
        print("Calibration succeeded.")

    # Output calibration info to GUI
    output_calibration(calibration, output_frame_text)

    # ------------------
    # Automatic measurements from single file
    # ------------------

    # Get the 30g threshold 
    threshold_30 = (30 - calibration.regression_intercept) / calibration.regression_gradient + calibration.baseline

    # Threshold the data
    # Values >30g become 1
    # Values <=30g become 0 
    threshed = (dat.loc[:, "Measure"] > threshold_30).astype(int)

    # Open small blips of 0s (<10 samples long)
    # This merges windows that are close to one another
    # For example: --_-------- becomes --------------

    # A string of 0s starts when the value is 0, and the previous (shifted 1) value is 1 
    zero_starts = (threshed == 0) & (threshed.shift(1) == 1)
    # A string of 0s ends when the value is 0, and the next (shifted -1) value is 1
    zero_ends = (threshed == 0) & (threshed.shift(-1) == 1)

    # Get the integer indices associated with those starts and ends
    zero_start_indices = zero_starts[zero_starts].index
    zero_end_indices = zero_ends[zero_ends].index

    # Cut any "ends" that are actually 0s->1s at the beginning of the file
    # As a result, the starts and ends are now aligned to mark a single window of 0s
    # Next line changed to ">=" from ">" to correct problem found 8/5/24
    zero_end_indices = zero_end_indices[zero_end_indices >= zero_start_indices.min()]
    
    # Go through every pair of start-end values (this marks the edges of a window of 0s) 
    for start, end in zip(zero_start_indices, zero_end_indices):
        # if the size of that window of 0s is <10 samples long
        # mark those values as 1s, instead of 0s
        if end - start + 1 < 10 :
            threshed.iloc[start:(end+1)] = 1

    # Now find the windows of 1s
    # These are values registered at >30g

    # A string of 1s starts when the value is 1, and the previous (shifted 1) value is 0
    window_starts = (threshed == 1) & (threshed.shift(1) == 0)
    # A string of 1s ends when the value is 1, and the next (shifted -1) value is 0
    window_ends = (threshed == 1) & (threshed.shift(-1) == 0)

    # Extend the window by one in each direction to get the left and the rightmost peaks included in the window
    # Needed when searching for 2nd peaks for penguin rule
    window_starts_indices = window_starts[window_starts].index - 1
    window_end_indices = window_ends[window_ends].index + 1

    # Cut any "ends" that are actually 1s->0s at the beginning of the file
    # As a result, the starts and ends are now aligned to mark a single window of 1s
    # Next line changed to ">=" from ">" to correct problem found 8/5/24
    window_end_indices = window_end_indices[window_end_indices >= window_starts_indices.min()]

    # Close small blips of 1s (<25 samples long)
    # This erases measurement windows that are very short
    # For example: __-______ becomes _________

    # Make a new list of the open windows to retain
    # (this allows us to retain the original windows if needed, unlike when closed down the blips of 0s)
    retained_window_starts_indices = []
    retained_window_ends_indices = []

    # Go through every pair of start-end values (this marks the edges of a window of 1s) 
    for start, end in zip(window_starts_indices, window_end_indices):
        # if the size of that window of 1s is <25 samples long
        if end - start + 1 > 25:
            # mark those values as 0s, instead of 1s
            retained_window_starts_indices.append(start)
            retained_window_ends_indices.append(end)
        else:
            # else added 8/5/24
            threshed.iloc[start:(end+1)] = 0

    # Lists to keep track of selected peak locations 
    # and corresponding measurements between those peaks
    peak_markers_x = []
    peak_markers_y = []
    measure_centers_x = []
    measure_centers_y = []
    measures = []

    # List to keep track of full output for every trace in the file
    formatted_output = []

    # as in manual multiple birds, this does all the traces in the file, so count them
    trace_counter = 1

    # For each measurement window of 1s, find the peaks and measure within those peaks
    for start, end in zip(retained_window_starts_indices, retained_window_ends_indices):
        # Get the measurement data in the window
        window = dat.loc[start:end, "Measure"]
        
        # Get the sign switches at every location in the trace
        # Start by calculating the rolling difference, like the first derivative: window.diff()
        #   series [a, b, c] becomes series[NA, b-a, c-b]
        # Simplify to the sign of the first derivative: np.sign(window.diff())
        #   increasing = 1, decreasing = -1
        # Now get the derivative of those signs: np.sign(window.diff()).diff()
        #   inc->inc =  1 -  1 =  0
        #   dec->dec = -1 - -1 =  0 
        #   inc->dec = -1 -  1 = -2
        #   dec->inc =  1 - -1 =  2
        # Fill the NA values with 0 
        # (will be the first values in the Series, because there are no previous values to take differences from with .diff)
        sign_switches = np.sign(window.diff()).diff().fillna(0)

        # The PEAKS are areas where the trace is going from increasing to decreasing
        # so find indices in the original trace where the sign_switch is -2
        # Shift one index to the left to adjust for .diff()
        peaks = sign_switches[sign_switches == -2].index - 1

        # Now we are finding the actual measurement window via penguin rule
        # By default, start with the actual starta nd end value of the window
        start_peak_index = start
        end_peak_index = end

        # If there are 3 or more peaks, take the penguin rule peaks
        if len(peaks) > 2:
            # Second peak
            start_peak_index = peaks[1]
            # Second-to-last peak
            end_peak_index = peaks[-2]

        # Find central value of the window
        measure_center = int((start_peak_index + end_peak_index) / 2)

        # CHANGE 8/30/24 - GET the LOCAL BASELINE VALUE HERE
        local_baseline, good_flag = get_bird_baseline(dat, start_peak_index, end_peak_index, buffer_size=300, window_size=40)

        # Find the weight within the window
        # NOTE you could call run_weights() here, like in process_manual
        #      For doing a batch of files, you could call run_weights() and store the csv-formatted output strings
        # measure, _, _, _ = MOM_Calculations.w_windowed_min_slope_mid(dat, calibration, start_peak_index, end_peak_index, local_baseline)
        # measure, _, _, _ = MOM_Calculations.w_windowed_min_slope(dat, calibration, start_peak_index, end_peak_index, local_baseline)
        wt_info = run_weights(dat, calibration, start_peak_index, end_peak_index, local_baseline, f_name, trace_counter, output_frame_text, include_header=False, write_output_to_screen=True)
        
        # add the weight info to the output to be saved
        formatted_output.append(wt_info)

        # Organize the tex
        # t annotations for the final trace graph
        if (show_graph):
            peak_markers_x.append(start_peak_index)
            peak_markers_x.append(end_peak_index)
            peak_markers_y.append(dat.loc[start_peak_index, "Measure"])
            peak_markers_y.append(dat.loc[end_peak_index, "Measure"])
            measure_centers_x.append(measure_center)
            measure_centers_y.append(dat.loc[measure_center, "Measure"])

            # get the 10th value (weight_min_slope_gravity) to put toward the graphing
            values = wt_info.split(',')
            if len(values) >= 10:
                weight_min_slope_gravity = values[9].strip()
                measure = round(float(weight_min_slope_gravity), 2) # Convert to float and round
        
            else:
                measure = 0

            # Append the value labeled by the trace counter
            measures.append(str(trace_counter) + ": " + str(measure))

        # increment the trace
        trace_counter = trace_counter + 1

    if (show_graph):
        # ------------------
        # This is all just plotting
        # ------------------
        peak_markers = pd.DataFrame({"x":peak_markers_x,
                                    "y":peak_markers_y})
        measure_labels = pd.DataFrame({"x":measure_centers_x,
                                      "y":measure_centers_y,
                                      "label":measures})
        
        plt.ion()
        fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)
        fig.set_size_inches((15,4))  # (default_figure_width, default_figure_height)) 
        ax1.plot(dat.loc[:, "Measure"])
        ax1.scatter(peak_markers["x"].astype(float), peak_markers["y"].astype(float), color="red")
        for i in range(len(measure_labels)):
            ax1.text(measure_labels["x"].astype(float).iloc[i], 
                     measure_labels["y"].astype(float).iloc[i], 
                     measure_labels["label"].iloc[i], 
                     color="red", horizontalalignment="center")

        # Currently just show plot the user and exit
        ax2.plot(threshed, "r")

    return formatted_output

##############################################################
##############################################################
# Code to add user feedback during Auto Batch process
# May need to move all/some of it to GUI.py or another file
##############################################################
##############################################################

'''  IN case we move this to another file, here are the libararies needed
import tkinter as tk
from tkinter import filedialog, messagebox

import os
import pandas as pd
import threading
'''
# need this just for the progress window, "tk" alone isn't enough
from tkinter import ttk

# Global variables needed for the progress window management
stop_processing = False
progress_window = None

##############
#    create_progress_window
#       
#    Parameters:
#       number of files to go thru, flag for whether to close it or not
# 
#   Returns:
#    - progress bar oject, text for the label, text for current file, filename_label
#########
def create_progress_window(total_files, on_close):
    global progress_window
    progress_window = tk.Toplevel()
    progress_window.title("Processing Files")

    window_width = 400
    window_height = 200
    screen_width = progress_window.winfo_screenwidth()
    screen_height = progress_window.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    progress_window.protocol("WM_DELETE_WINDOW", on_close)

    progress_label = tk.Label(progress_window, text=f"Processing item 1 of {total_files}", font=("Helvetica", 16))
    progress_label.pack(pady=(10, 5))

    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=10)

    labels_frame = tk.Frame(progress_window)
    labels_frame.pack(pady=10)

    current_item_label = tk.Label(labels_frame, text="Current item:", font=("Helvetica", 14))
    current_item_label.pack(anchor='center')

    filename_label = tk.Label(labels_frame, text="", font=("Helvetica", 14))
    filename_label.pack(anchor='center')

    return progress_bar, progress_label, current_item_label, filename_label

##############
#    update_progress
#      called each time user feedback is neew
#    Parameters:
#     infor for updating the progress bar
# 
#   Returns:
#    - None
#########
def update_progress(progress_bar, progress_label, current_item_label, filename_label, current_item_index, total_files, current_item):
    progress_bar["value"] = current_item_index
    progress_bar["maximum"] = total_files
    progress_label.config(text=f"Processing item {current_item_index} of {total_files}")
    current_item_label.config(text="Current item:")
    filename_label.config(text=f"Filename: {current_item}")
    progress_bar.update_idletasks()

##############
#    on_close
#       called when done processing, shuts it down
#    Parameters:
#       None
# 
#   Returns:
#       None
#########
def on_close():
    global stop_processing
    stop_processing = True
    if progress_window is not None:
        progress_window.destroy()

##############
#    process_auto_batch_2
#       a subset of original fuction: process_auto(calibration, calibration_user_entered_values, output_frame_text, show_graph = True):
#    Parameters:
#    - f_path - the location of the file to be processed 
#    - of the window of interst of your f\jull slope measures
#    - start_pt: Starting point (long integer). where to start and end the window counting
# 
#   Returns:
#    - None; this outputs all the data to the screen and to a text file
#########
def process_auto_batch_2(calibration, calibration_user_entered_values, output_frame_text, show_graph=True):

    no_diagnostics = True

    global stop_processing, progress_window

    stop_processing = False

    folder_path = filedialog.askdirectory()
    if not folder_path:
        tk.messagebox.showinfo(message="No folder chosen. Try again.")
        return

    all_files = os.listdir(folder_path)
    # files = [f for f in all_files if os.path.isfile(os.path.join(folder_path, f))]

    files = [f for f in all_files if os.path.isfile(os.path.join(folder_path, f)) and f.startswith("DL_")]


    if not files:
        tk.messagebox.showinfo(message=f"No files starting with 'DL_' found in the selected folder.")
        return

    if show_graph:
        progress_bar, progress_label, current_item_label, filename_label = create_progress_window(len(files), on_close)

    # use the appropriate header
    if no_diagnostics:
        column_names = ["File", "Trace_Num_Sequence", "DateTime", "Start_pt", "End_pt", "W1", "W2", "W3", "W4", "W5", "Intcpt", "Slope"]
    else:
        column_names = ["File", "Trace_Num_Sequence", "DateTime", "Stop_pt", "Start_pt", "W1", "W2", "W3", "W4", "W5", "Intcpt", "Slope","Nstd","Std","PctAbove","PctBelow","PctBelowXstd","PctAboveXstd","PctBelowBaseine","LongRunAbove","LongRunBelow"]
    batch_output = []

    valid_extensions = ('.txt', '.csv', '.TXT', '.CSV')

    for index, filename in enumerate(files, start=1):
        if stop_processing:
            break

        if filename.startswith('.DS'):
            continue

        if filename.startswith('DL') and filename.lower().endswith(valid_extensions):
            if show_graph:
                update_progress(progress_bar, progress_label, current_item_label, filename_label, index, len(files), filename)

            f_path = os.path.join(folder_path, filename)

            try:
                # Assuming auto_one_file is a function that processes the file
                my_output = auto_one_file(f_path, calibration, calibration_user_entered_values, output_frame_text, False)
                if my_output:
                        # Strip newlines and tabs from the output if calibration was successful
                    stripped_data = [line.strip('\n').strip('\t') for line in my_output]
                else:
                    # If calibration was bad, log the file name with "Bad Calibration"
                    stripped_data = [f_path + " Bad Calibration"]
                    output_error(stripped_data, output_frame_text)
                
                # Extend batch_output with the processed or error data
                batch_output.extend(stripped_data)
            except Exception as e:
                print("Error occurred:", e)
                my_output = filename + " - redo manually"
                print(my_output)
                output_to_screen(my_output, output_frame_text)
                batch_output.extend([my_output])

            if show_graph:
                progress_bar["value"] = index
                progress_window.update_idletasks()

    if show_graph:
        progress_window.destroy()

    output_file_path = filedialog.asksaveasfilename(title="Save Combined File As", defaultextension=".txt",
                                                   filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    if output_file_path:
        batch_output_df = pd.DataFrame(batch_output, columns=['Formatted_Output'])
        if no_diagnostics: # true when no diagnostics are printed
            new_row = return_header("standard")
            # new_row = {"Formatted_Output": "fname,seq,dtime,start,stop,wMean,wMeanG,wMedian,wMinSlope,wMinSlopeG,slope,minSlope"}
        else:
            new_row = return_header("diagnostic")
            # new_row =  {"Formatted_Output": "File,Trace_Segment_Num,DateTime,Win_All,Win_Slope,Wt_Mean,Wt_MeanG,Wt_Median,Wt_Min_Slope,Wt_Min_Grav,Slope,Min_Slope,All_Start,All_End,Min_Start,Min_End,Baseline,Type,Method,Notes"}
        new_row_df = pd.DataFrame([new_row])
        batch_output_df = pd.concat([new_row_df, batch_output_df], ignore_index=True)
        batch_output_df.to_csv(output_file_path, index=False, header=False, sep='\t')

    tk.messagebox.showinfo(message=f"Files processed: {len(files)}")

##############
#    process_auto_start
#       to be called when button pressed
#       starts threading so the GUI can be updated with progress message and the output window is updated as files are processed
#    Parameters:
#    - everything needed for process_auto_batch_2 to work
#    - show_graph must be True to show the progress bar
# 
#   Returns:
#    - None
#########
def process_auto_start(calibration, calibration_user_entered_values, output_frame_text, show_graph=True):
    processing_thread = threading.Thread(target=process_auto_batch_2, args=(calibration, calibration_user_entered_values, output_frame_text, show_graph))
    processing_thread.start()