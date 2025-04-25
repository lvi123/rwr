import random
import csv
import sys
from datetime import datetime, timedelta
import numpy as np

def generate_data_period(writer, 
                        start_time, 
                        num_intervals, 
                        change_rate_kbps,
                        name,
                        initial_total_uncompressed=0.0, 
                        initial_total_compressed=0.0,
                        compression_ratios=None,
                        data_randomness_percent=0.10,
                        interval_seconds=300):
    """
    Generate data for a specific time period.
    
    Args:
        writer: CSV writer to output the data
        start_time: Starting timestamp for this period
        num_intervals: Number of intervals to generate in this period
        change_rate_kbps: Data change rate in KB/s for this period
        name: Name identifier for the VM/instance
        initial_total_uncompressed: Starting accumulated uncompressed value in KB
        initial_total_compressed: Starting accumulated compressed value in KB
        compression_ratios: List of compression ratios to use (must have length >= num_intervals)
        data_randomness_percent: Randomness percentage for data generation
        interval_seconds: Duration of each interval in seconds
        
    Returns:
        tuple: (end_time, final_total_uncompressed, final_total_compressed)
    """
    total_uncompressed = initial_total_uncompressed
    total_compressed = initial_total_compressed
    
    for i in range(num_intervals):
        timestamp = start_time + timedelta(seconds=i * interval_seconds)
        compression_ratio = compression_ratios[i] if compression_ratios else 2.0
        
        # Generate randomized uncompressed size for this interval
        base_uncompressed = change_rate_kbps * interval_seconds  # in KB
        uncompressed_noise = random.uniform(-data_randomness_percent, data_randomness_percent)
        uncompressed_this_interval = base_uncompressed * (1 + uncompressed_noise)
        
        # Compressed size for this interval using variable compression ratio
        compressed_this_interval = uncompressed_this_interval / compression_ratio
        
        # Update totals
        total_uncompressed += uncompressed_this_interval
        total_compressed += compressed_this_interval
        
        # Write row
        writer.writerow([
            name,
            timestamp.strftime("%b %d, %Y, %I:%M:%S %p"),
            "{:,.2f}".format(total_compressed),
            "{:,.2f}".format(total_uncompressed)
        ])
    
    # Return the end state to use as the starting point for the next period
    end_time = start_time + timedelta(seconds=num_intervals * interval_seconds)
    return end_time, total_uncompressed, total_compressed

def generate_compression_ratios(num_intervals, base_compression_ratio, randomness_percent, smoothing_factor=0.7):
    """
    Generate time-correlated compression ratios.
    
    Args:
        num_intervals: Number of intervals to generate ratios for
        base_compression_ratio: Base compression ratio value
        randomness_percent: How much random variation to add
        smoothing_factor: Controls smoothness of transitions (0-1)
        
    Returns:
        list: Generated compression ratios
    """
    compression_ratios = []
    prev_ratio = base_compression_ratio
    
    for i in range(num_intervals):
        # Generate a random factor for this interval
        random_factor = random.uniform(1 - randomness_percent, 1 + randomness_percent)
        
        # Smooth the variation by considering previous ratio
        if i == 0:
            # First interval just uses the random factor
            ratio = base_compression_ratio * random_factor
        else:
            # Subsequent intervals blend previous ratio with new random factor
            ratio = (smoothing_factor * prev_ratio) + ((1 - smoothing_factor) * base_compression_ratio * random_factor)
        
        compression_ratios.append(ratio)
        prev_ratio = ratio
    
    return compression_ratios

# Main script execution
if __name__ == "__main__":
    # Configurations
    VM_NAME = "vm-1"  # Name identifier for the VM/instance
    base_change_rate_kbps = 200  # 200 KB per second for first 4 hours and 8-12 hours
    high_change_rate_kbps = 2048  # 2 MB per second for hours 12-16
    rate_increase_hour = 4  # When to start the increased rate (in hours)
    rate_return_hour = 8   # When to return to the base rate (in hours)
    high_rate_hour = 12    # When to start the high rate period (in hours)
    high_rate_end_hour = 16  # When to end the high rate period (in hours)
    no_compression_end_hour = 14  # When to end the no-compression period (in hours)
    interval_seconds = 300  # 5 minutes
    total_duration_minutes = 960  # 16 hours
    
    # Calculate period durations
    period1_duration_minutes = rate_increase_hour * 60  # First 4 hours (base rate)
    period2_duration_minutes = (rate_return_hour - rate_increase_hour) * 60  # Hours 4-8 (increased rate)
    period3_duration_minutes = (high_rate_hour - rate_return_hour) * 60  # Hours 8-12 (base rate again)
    period4a_duration_minutes = (no_compression_end_hour - high_rate_hour) * 60  # Hours 12-14 (high rate, no compression)
    period4b_duration_minutes = (high_rate_end_hour - no_compression_end_hour) * 60  # Hours 14-16 (high rate, normal compression)
    
    # Calculate intervals per period
    period1_intervals = period1_duration_minutes * 60 // interval_seconds
    period2_intervals = period2_duration_minutes * 60 // interval_seconds
    period3_intervals = period3_duration_minutes * 60 // interval_seconds
    period4a_intervals = period4a_duration_minutes * 60 // interval_seconds
    period4b_intervals = period4b_duration_minutes * 60 // interval_seconds
    total_intervals = period1_intervals + period2_intervals + period3_intervals + period4a_intervals + period4b_intervals
    
    base_compression_ratio = 2.0  # Base compression ratio
    data_randomness_percent = 0.10  # ±10% for data size
    compression_randomness_percent = 0.15  # ±15% for compression ratio
    
    # Set seed for reproducibility
    random.seed(42)
    np.random.seed(42)
    
    # Generate compression ratios for periods 1-3 and 4b (normal compression periods)
    normal_compression_intervals = total_intervals - period4a_intervals
    normal_compression_ratios = generate_compression_ratios(
        normal_compression_intervals, 
        base_compression_ratio, 
        compression_randomness_percent
    )
    
    # Create compression ratios for all periods
    all_compression_ratios = []
    current_index = 0
    
    # Add ratios for periods 1-3
    ratios_before_period4 = period1_intervals + period2_intervals + period3_intervals
    all_compression_ratios.extend(normal_compression_ratios[:ratios_before_period4])
    current_index += ratios_before_period4
    
    # Add fixed ratio of 1.0 for period 4a (no compression)
    all_compression_ratios.extend([1.0] * period4a_intervals)
    
    # Add normal ratios for period 4b
    all_compression_ratios.extend(normal_compression_ratios[current_index:])
    
    # Start time for the entire simulation
    start_time = datetime.now()
    
    # Initialize CSV writer
    writer = csv.writer(sys.stdout)
    writer.writerow(['Name', 'timestamp', 'compressed', 'uncompressed'])
    
    # Generate period 1 (normal rate, hours 0-4)
    period1_compression_ratios = all_compression_ratios[:period1_intervals]
    period1_end_time, period1_uncompressed, period1_compressed = generate_data_period(
        writer,
        start_time,
        period1_intervals,
        base_change_rate_kbps,
        VM_NAME,
        compression_ratios=period1_compression_ratios,
        data_randomness_percent=data_randomness_percent,
        interval_seconds=interval_seconds
    )
    
    # Generate period 2 (increased rate, hours 4-8)
    start_idx = period1_intervals
    end_idx = start_idx + period2_intervals
    period2_compression_ratios = all_compression_ratios[start_idx:end_idx]
    period2_end_time, period2_uncompressed, period2_compressed = generate_data_period(
        writer,
        period1_end_time,
        period2_intervals,
        high_change_rate_kbps,
        VM_NAME,
        initial_total_uncompressed=period1_uncompressed,
        initial_total_compressed=period1_compressed,
        compression_ratios=period2_compression_ratios,
        data_randomness_percent=data_randomness_percent,
        interval_seconds=interval_seconds
    )
    
    # Generate period 3 (back to base rate, hours 8-12)
    start_idx = end_idx
    end_idx = start_idx + period3_intervals
    period3_compression_ratios = all_compression_ratios[start_idx:end_idx]
    period3_end_time, period3_uncompressed, period3_compressed = generate_data_period(
        writer,
        period2_end_time,
        period3_intervals,
        base_change_rate_kbps,
        VM_NAME,
        initial_total_uncompressed=period2_uncompressed,
        initial_total_compressed=period2_compressed,
        compression_ratios=period3_compression_ratios,
        data_randomness_percent=data_randomness_percent,
        interval_seconds=interval_seconds
    )
    
    # Generate period 4a (high rate with no compression, hours 12-14)
    start_idx = end_idx
    end_idx = start_idx + period4a_intervals
    period4a_compression_ratios = all_compression_ratios[start_idx:end_idx]
    period4a_end_time, period4a_uncompressed, period4a_compressed = generate_data_period(
        writer,
        period3_end_time,
        period4a_intervals,
        high_change_rate_kbps,
        VM_NAME,
        initial_total_uncompressed=period3_uncompressed,
        initial_total_compressed=period3_compressed,
        compression_ratios=period4a_compression_ratios,
        data_randomness_percent=data_randomness_percent,
        interval_seconds=interval_seconds
    )
    
    # Generate period 4b (high rate with normal compression, hours 14-16)
    start_idx = end_idx
    end_idx = start_idx + period4b_intervals
    period4b_compression_ratios = all_compression_ratios[start_idx:end_idx]
    generate_data_period(
        writer,
        period4a_end_time,
        period4b_intervals,
        base_change_rate_kbps,
        VM_NAME,
        initial_total_uncompressed=period4a_uncompressed,
        initial_total_compressed=period4a_compressed,
        compression_ratios=period4b_compression_ratios,
        data_randomness_percent=data_randomness_percent,
        interval_seconds=interval_seconds
    )
    
    # Print statistics about the compression ratios
    print(f"Compression Ratio Statistics (across {total_intervals} intervals):", file=sys.stderr)
    print(f"Min: {min(all_compression_ratios):.4f}", file=sys.stderr)
    print(f"Max: {max(all_compression_ratios):.4f}", file=sys.stderr)
    print(f"Mean: {sum(all_compression_ratios)/len(all_compression_ratios):.4f}", file=sys.stderr)
    print(f"Base: {base_compression_ratio}", file=sys.stderr)
    
    # Print information about the change rate pattern
    print(f"\nChange Rate Pattern:", file=sys.stderr)
    print(f"Hours 0-{rate_increase_hour}: {base_change_rate_kbps} KB/s (base rate)", file=sys.stderr)
    print(f"Hours {rate_increase_hour}-{rate_return_hour}: {high_change_rate_kbps} KB/s (2x increase)", file=sys.stderr)
    print(f"Hours {rate_return_hour}-{high_rate_hour}: {base_change_rate_kbps} KB/s (back to base rate)", file=sys.stderr)
    print(f"Hours {high_rate_hour}-{no_compression_end_hour}: {high_change_rate_kbps} KB/s (high rate, no compression)", file=sys.stderr)
    print(f"Hours {no_compression_end_hour}-{high_rate_end_hour}: {base_change_rate_kbps} KB/s (high rate, normal compression)", file=sys.stderr)
