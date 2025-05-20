import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from matplotlib.dates import HourLocator, DateFormatter
from matplotlib.ticker import FuncFormatter
import argparse
from datetime import datetime

# Set up argument parser
parser = argparse.ArgumentParser(description='Visualize compression report data')
parser.add_argument('input_file', nargs='?', default='report.csv',
                   help='Input CSV file (default: report.csv)')
parser.add_argument('--name', '-n', required=True,
                   help='Name to filter the data on')
parser.add_argument('--start', '-s',
                   help='Start timestamp (format: "MMM DD, YYYY, HH:MM:SS AM/PM")')
parser.add_argument('--end', '-e',
                   help='End timestamp (format: "MMM DD, YYYY, HH:MM:SS AM/PM")')
args = parser.parse_args()

# Set Seaborn style
sns.set(style="darkgrid")

# Read the CSV file
csv_path = os.path.join(os.path.dirname(__file__), args.input_file)
try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find file '{args.input_file}'")
    print(f"Full path attempted: {csv_path}")
    print("Please make sure the file exists and you have the correct permissions.")
    exit(1)

# Filter data by name
df = df[df['Name'] == args.name]

if len(df) == 0:
    print(f"No data found for name: {args.name}")
    exit(1)

# Convert timestamp to datetime and numeric columns
df['timestamp'] = pd.to_datetime(df['timestamp'], format="%b %d, %Y, %I:%M:%S %p")

# Apply timestamp filters if provided
if args.start:
    try:
        start_time = pd.to_datetime(args.start, format="%b %d, %Y, %I:%M:%S %p")
        df = df[df['timestamp'] >= start_time]
    except ValueError as e:
        print(f"Error parsing start timestamp: {args.start}")
        print("Expected format: 'MMM DD, YYYY, HH:MM:SS AM/PM' (e.g., 'Jan 01, 2024, 12:00:00 PM')")
        exit(1)

if args.end:
    try:
        end_time = pd.to_datetime(args.end, format="%b %d, %Y, %I:%M:%S %p")
        df = df[df['timestamp'] <= end_time]
    except ValueError as e:
        print(f"Error parsing end timestamp: {args.end}")
        print("Expected format: 'MMM DD, YYYY, HH:MM:SS AM/PM' (e.g., 'Jan 01, 2024, 12:00:00 PM')")
        exit(1)

if len(df) == 0:
    print("No data found within the specified time range")
    exit(1)

df['compressed'] = df['compressed'].str.replace(',', '').astype(float)  # Data in KB
df['uncompressed'] = df['uncompressed'].str.replace(',', '').astype(float)  # Data in KB

# Calculate metrics for all plots
df['uncompressed_rate'] = df['uncompressed'].diff() / df['timestamp'].diff().dt.total_seconds() * 60  # KB per minute
df['compressed_rate'] = df['compressed'].diff() / df['timestamp'].diff().dt.total_seconds() * 60  # KB per minute
# Calculate compression ratio based on rates instead of totals
df['compression_ratio'] = df['compressed_rate'] / df['uncompressed_rate']  # instantaneous compression ratio

# Print diagnostic information about compression ratio
print("Compression Ratio Statistics (based on rates):")
print(f"Min: {df['compression_ratio'].min()}")
print(f"Max: {df['compression_ratio'].max()}")
print(f"Mean: {df['compression_ratio'].mean()}")
print(f"Values near minimum: {df.loc[df['compression_ratio'] == df['compression_ratio'].min(), ['timestamp', 'compressed_rate', 'uncompressed_rate', 'compression_ratio']]}")
print("\nFirst 10 rows of data:")
print(df[['timestamp', 'compressed_rate', 'uncompressed_rate', 'compression_ratio']].head(10))

# Drop the first row which has NaN for rate calculations
df_rate = df.dropna()

# Skip initial noisy datapoints for compression ratio plots
skip_initial = 2  # Number of initial datapoints to skip
df_rate_stable = df_rate.iloc[skip_initial:]

# Create a figure with three subplots
fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)

# Plot 1: Line plot showing both compressed and uncompressed data
sns.lineplot(x='timestamp', y='uncompressed', 
             data=df, label='Uncompressed', linewidth=2, ax=axes[0])
sns.lineplot(x='timestamp', y='compressed', 
             data=df, label='Compressed', linewidth=2, ax=axes[0])
axes[0].set_title('Accumulated Data Over Time', fontsize=16)
axes[0].set_ylabel('Data (KB)', fontsize=12)
axes[0].legend(fontsize=12)

# Format y-axis for plot 1 to show KB values properly
def format_kb(x, p):
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    elif x >= 1e3:
        return f'{x/1e3:.1f}K'
    else:
        return f'{x:.0f}'

axes[0].yaxis.set_major_formatter(FuncFormatter(format_kb))

# Plot 2: Data rates
sns.lineplot(x='timestamp', y='uncompressed_rate', 
             data=df_rate, label='Uncompressed Rate', linewidth=2, ax=axes[1])
sns.lineplot(x='timestamp', y='compressed_rate', 
             data=df_rate, label='Compressed Rate', linewidth=2, ax=axes[1])
axes[1].set_title('Data Rates Over Time', fontsize=16)
axes[1].set_ylabel('Rate (KB/minute)', fontsize=12)
axes[1].legend(fontsize=12)

# Plot 3: Compression ratio
sns.lineplot(x='timestamp', y='compression_ratio', 
             data=df_rate_stable, label='Compression Ratio', linewidth=2, color='red', ax=axes[2])

# Calculate appropriate y-axis limits for compression ratio based on actual data
ratio_min = max(0, df_rate_stable['compression_ratio'].min())  # Ensure minimum is not negative
ratio_max = df_rate_stable['compression_ratio'].max()
ratio_range = max(0.001, ratio_max - ratio_min)  # Ensure minimum range to avoid too narrow display

# Use multiplicative padding for ratio (since it's always positive)
padding_factor = 0.2  # 20% padding on each side
y_min = max(0, ratio_min * (1 - padding_factor))  # Ensure we never go below 0
y_max = ratio_max * (1 + padding_factor)

axes[2].set_ylim(y_min, y_max)
print(f"Setting compression ratio y-axis limits to {y_min:.6f} - {y_max:.6f} (min: {ratio_min:.6f}, max: {ratio_max:.6f})")

axes[2].set_title('Compression Ratio Over Time', fontsize=16)
axes[2].set_ylabel('Compression Ratio (Rate-based)', fontsize=12)
axes[2].legend(fontsize=12)

# Format x-axis dates on all plots
for ax in axes:
    # Set major ticks every hour
    ax.xaxis.set_major_locator(HourLocator(interval=1))
    # Format the date to show only hour and minute
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    plt.setp(ax.get_xticklabels(), rotation=0, ha='center')

# Add an overall x-axis label at the bottom
axes[2].set_xlabel('Time (HH:MM)', fontsize=12)

# Adjust layout with more space at the bottom for timestamps
plt.tight_layout()

# Save the figure
plt.savefig(os.path.join(os.path.dirname(__file__), 'report_visualization.png'), dpi=300)

# Show the plot
plt.show() 