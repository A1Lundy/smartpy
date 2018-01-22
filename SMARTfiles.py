from csv import DictReader, writer
from datetime import datetime, timedelta
from fractions import gcd
from numpy import float64
from collections import OrderedDict


def get_dict_rain_series_simu(file_location, start_simu, end_simu, time_delta_simu):
    dict_rain, start_data, end_data, time_delta_data = read_rain_file(file_location)

    if (start_data - time_delta_data + time_delta_simu <= start_simu) and (end_simu <= end_data):
        time_delta_res = get_required_resolution(start_data, start_simu, time_delta_data, time_delta_simu)
        return rescale_data_time_resolution(dict_rain,
                                            start_data, end_data, time_delta_data,
                                            time_delta_res,
                                            start_simu, end_simu, time_delta_simu)
    else:
        raise Exception('Rain data not sufficient for simulation.')


def get_dict_peva_series_simu(file_location, start_simu, end_simu, time_delta_simu):
    dict_peva, start_data, end_data, time_delta_data = read_peva_file(file_location)

    if (start_data - time_delta_data + time_delta_simu <= start_simu) and (end_simu <= end_data):
        time_delta_res = get_required_resolution(start_data, start_simu, time_delta_data, time_delta_simu)
        return rescale_data_time_resolution(dict_peva,
                                            start_data, end_data, time_delta_data,
                                            time_delta_simu,
                                            start_simu, end_simu, time_delta_res)
    else:
        raise Exception('PEva data not sufficient for simulation.')


def get_dict_discharge_series(file_location, start_report, end_report):
    dict_flow = read_flow_file(file_location)

    for dt in dict_flow.iterkeys():
        if not ((start_report <= dt) and (dt <= end_report)):
            del dict_flow[dt]

    return dict_flow


def read_rain_file(file_location):
    return read_csv_time_series_with_delta_check(file_location, key_header='DATETIME', val_header='RAIN')


def read_peva_file(file_location):
    return read_csv_time_series_with_delta_check(file_location, key_header='DATETIME', val_header='PEVA')


def read_flow_file(file_location):
    return read_csv_time_series_with_missing_check(file_location, key_header='DATETIME', val_header='FLOW')


def read_csv_time_series_with_delta_check(csv_file, key_header, val_header):
    try:
        with open(csv_file, 'rb') as my_file:
            my_dict_data = dict()
            my_list_dt = list()
            my_reader = DictReader(my_file)
            try:
                for row in my_reader:
                    my_dict_data[datetime.strptime(row[key_header], "%Y-%m-%d %H:%M:%S")] = float64(row[val_header])
                    my_list_dt.append(datetime.strptime(row[key_header], "%Y-%m-%d %H:%M:%S"))
            except KeyError:
                raise Exception('Field {} or {} does not exist in {}.'.format(key_header, val_header, csv_file))

        start_data, end_data, time_delta = check_interval_in_list(my_list_dt, csv_file)

        return my_dict_data, start_data, end_data, time_delta
    except IOError:
        raise Exception('File {} could not be found.'.format(csv_file))


def read_csv_time_series_with_missing_check(csv_file, key_header, val_header):
    try:
        with open(csv_file, 'rb') as my_file:
            my_dict_data = OrderedDict()
            my_reader = DictReader(my_file)
            try:
                for row in my_reader:
                    if row[val_header] != -99.0:
                        my_dict_data[datetime.strptime(row[key_header], "%Y-%m-%d %H:%M:%S")] = float64(row[val_header])
            except KeyError:
                raise Exception('Field {} or {} does not exist in {}.'.format(key_header, val_header, csv_file))
        return my_dict_data
    except IOError:
        raise Exception('File {} could not be found.'.format(csv_file))


def check_interval_in_list(list_of_dt, csv_file):
    list_intervals = list()
    for i in range(len(list_of_dt) - 1):
        list_intervals.append(list_of_dt[i+1] - list_of_dt[i])
    interval = list(set(list_intervals))
    if len(interval) == 1:
        if list_of_dt[0] + interval[0] * (len(list_of_dt) - 1) == list_of_dt[-1]:
            return list_of_dt[0], list_of_dt[-1], interval[0]
        else:
            raise Exception('Missing Data: {} is missing at least one datetime in period.'.format(csv_file))
    else:
        raise Exception('Inconsistent Interval: {} does not feature a single time interval.'.format(csv_file))


def get_required_resolution(start_data, start_simu, delta_data, delta_simu):
    # GCD(delta_data, delta_simu) gives the maximum time resolution possible to match data and simu
    # shift = start_data - start_simu gives the data shift (e.g. data starting at 8am, simu starting at 9am)
    # GCD(shift, GCD(delta_data, delta_simu)) gives the maximum time resolution to match both the difference in
    # start dates and the difference in data/simu time deltas.
    return timedelta(seconds=gcd((start_data - start_simu).total_seconds(),
                                 gcd(delta_data.total_seconds(), delta_simu.total_seconds())))


def increase_data_time_resolution(dict_info, start_lo, end_lo,
                                  time_delta_lo, time_delta_hi):
    """ Use the low resolution to create the high resolution """
    my_dt_lo = start_lo
    (divisor, remainder) = divmod(int(time_delta_lo.total_seconds()), int(time_delta_hi.total_seconds()))
    if remainder != 0:
        raise Exception("Increase Resolution: Time Deltas are not multiples of each other.")
    elif divisor < 1:
        raise Exception("Increase Resolution: Low resolution lower than higher resolution.")

    new_dict_info = dict()
    while (start_lo <= my_dt_lo) and (my_dt_lo <= end_lo):
        my_value = dict_info[my_dt_lo]
        my_portion = my_value / divisor
        for my_sub_step in xrange(0, -divisor, -1):
            new_dict_info[my_dt_lo + my_sub_step * time_delta_hi] = my_portion
        my_dt_lo += time_delta_lo

    return new_dict_info


def decrease_data_time_resolution(dict_info, start_lo, end_lo,
                                  time_delta_lo, time_delta_hi):
    """ Use the high resolution to create the low resolution """
    my_dt_lo = start_lo
    (divisor, remainder) = divmod(int(time_delta_lo.total_seconds()), int(time_delta_hi.total_seconds()))
    if remainder != 0:
        raise Exception("Decrease Resolution: Time Deltas are not multiples of each other.")
    elif divisor < 1:
        raise Exception("Decrease Resolution: Low resolution lower than higher resolution.")

    new_dict_info = dict()
    while (start_lo <= my_dt_lo) and (my_dt_lo <= end_lo):
        my_portion = 0.0
        for my_sub_step in xrange(0, -divisor, -1):
            my_portion += dict_info[my_dt_lo + my_sub_step * time_delta_hi]
        new_dict_info[my_dt_lo] = my_portion
        my_dt_lo += time_delta_lo

    return new_dict_info


def rescale_data_time_resolution(dict_data,
                                 start_data, end_data, time_delta_data,
                                 time_delta_res,
                                 start_simu, end_simu, time_delta_simu):

    if time_delta_data > time_delta_res:  # i.e. information resolution too low to generate simu timeseries
        my_tmp_dict = increase_data_time_resolution(dict_data, start_data, end_data,
                                                    time_delta_data, time_delta_res)
    else:  # i.e. information resolution suitable to generate simu timeseries
        # i.e. time_delta_data == time_delta_res (time_delta_data < time_delta_res cannot be true because use of GCD)
        my_tmp_dict = dict_data, start_data, end_data

    if time_delta_simu > time_delta_res:  # i.e. information resolution too high to generate simu timeseries
        my_new_dict = decrease_data_time_resolution(my_tmp_dict, start_simu, end_simu,
                                                    time_delta_simu, time_delta_res)
    else:  # i.e. information resolution suitable to generate simu timeseries
        # i.e. time_delta_simu == time_delta_res (time_delta_simu < time_delta_res cannot be true because use of GCD)
        my_new_dict = decrease_data_time_resolution(my_tmp_dict, start_simu, end_simu,
                                                    time_delta_simu, time_delta_res)
        # use decrease_data_time_resolution anyway for the only purpose to reduce the size of the dict
        # to the only required DateTimes in the simulation period

    return my_new_dict


def write_flow_file_from_list(timeframe, discharge, csv_file, report='gap_report', method='summary'):
    # Select the relevant list of DateTime given the argument used during function call
    if report == 'gap_report':  # standard situation
        my_list_datetime = timeframe.get_series_report()  # list of DateTime to be written in file
        simu_steps_per_reporting_step = \
            int(timeframe.get_gap_report().total_seconds() / timeframe.get_gap_simu().total_seconds())
    elif report == 'gap_simu':  # useful for debugging
        my_list_datetime = timeframe.get_series_simu()  # list of DateTime to be written in file
        simu_steps_per_reporting_step = 1
    else:
        raise Exception('Unknown reporting time gap for updating simulations files.')

    if method == 'summary':
        with open(csv_file, 'wb') as my_file:
            my_writer = writer(my_file, delimiter=',')
            my_writer.writerow(['DATETIME', 'FLOW'])
            my_index_simu = simu_steps_per_reporting_step   # ignoring first value that is for initial conditions
            my_index_report = 1  # ignoring first value that is for initial conditions
            while my_index_report <= len(my_list_datetime) - 1:
                my_values = list()
                for my_sub_index in xrange(0, -simu_steps_per_reporting_step, -1):
                    my_values.append(discharge[my_index_simu + my_sub_index])
                my_value = sum(my_values) / len(my_values)
                my_writer.writerow([my_list_datetime[my_index_report], '%e' % my_value])
                my_index_simu += simu_steps_per_reporting_step
                my_index_report += 1
    elif method == 'raw':
        with open(csv_file, 'wb') as my_file:
            my_writer = writer(my_file, delimiter=',')
            my_writer.writerow(['DATETIME', 'FLOW'])
            my_index_simu = simu_steps_per_reporting_step  # ignoring first value that is for initial conditions
            my_index_report = 1  # ignoring first value that is for initial conditions
            while my_index_report <= len(my_list_datetime):
                my_value = discharge[my_index_simu]
                my_writer.writerow([my_list_datetime[my_index_report], '%e' % my_value])
                my_index_simu += simu_steps_per_reporting_step
                my_index_report += 1
    else:
        raise Exception("Unknown method for updating simulations files.")


def write_flow_file_from_dict(timeframe, discharge, csv_file, report='gap_report', method='summary'):
    # Select the relevant list of DateTime given the argument used during function call
    if report == 'gap_report':  # standard situation
        my_list_datetime = timeframe.get_series_report()  # list of DateTime to be written in file
        simu_steps_per_reporting_step = \
            int(timeframe.get_gap_report().total_seconds() / timeframe.get_gap_simu().total_seconds())
    elif report == 'gap_simu':  # useful for debugging
        my_list_datetime = timeframe.get_series_simu()  # list of DateTime to be written in file
        simu_steps_per_reporting_step = 1
    else:
        raise Exception('Unknown reporting time gap for updating simulations files.')

    if method == 'summary':
        with open(csv_file, 'wb') as my_file:
            my_writer = writer(my_file, delimiter=',')
            my_writer.writerow(['DATETIME', 'FLOW'])
            for step in my_list_datetime[1:]:
                my_values = list()
                for my_sub_step in xrange(0, -simu_steps_per_reporting_step, -1):
                    my_values.append(
                        discharge[step + my_sub_step * timeframe.gap_simu])
                my_value = sum(my_values) / len(my_values)
                my_writer.writerow([step, '%e' % my_value])
    elif method == 'raw':
        with open(csv_file, 'wb') as my_file:
            my_writer = writer(my_file, delimiter=',')
            my_writer.writerow(['DATETIME', 'FLOW'])
            for step in my_list_datetime[1:]:
                my_writer.writerow([step, '%e' % discharge[step]])
    else:
        raise Exception("Unknown method for updating simulations files.")
