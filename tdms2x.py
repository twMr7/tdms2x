"""
    *tdms2x* - utility to convert NI TDMS file to various other scientific data formats.

Usage examples:

    - Checking the content of a TDMS file by displaying its meta information.

        $ python tdms2x.py -d test_data/dev2_1.tdms

    - Exporting channel data to a .npy file

        $ python tdms2x.py -o npy test_data/dev2_1.tdms

    - Exporting channel data to a .mat file, and also saving the meta info of recording

        $ python tdms2x.py -mo mat test_data/dev2_1.tdms

    - Batch converting all TDMS file in "test_data" folder to .npz file (compressed npy format)

        $ python tdms2x.py -zo npy test_data

    - Exporting only the 1st, 3rd, and 4th channels, split these channels and save to
      individual files. Note that default format is npy if "-o" option is ommited. Be sure to
      check for available channel numbers and provide only valid indexes. Otherwise, you may
      be prompted with the error message "IndexError: list index out of range".

        $ python tdms2x.py -c 0 2 3 -s test_data/dev2_1.tdms

    - Exporting all channel data and splitting to multiple .mat files with variable name
      stored with specified channel names "x, y, z, w, u".

        $ python tdms2x.py -n x y z w u -so mat test_data/dev2_1.tdms

Note:
    1. Names for the target file are auto generated with the combination of source file name,
       recording datetime, and/or channel names. Converted files are written into the same folder
       of source TDMS files.
    2. For options accept variable length of arguments, e.g. "-c" and "-n", these options
       should be followed by another option, or placed at the last of command-line. Avoid to place
       the required file PATH right after arguments of "-c" and "-n", it will be treated
       as if PATH is part of the sequence of these variable length arguments, and you should be
       prompt with error like "error: the following arguments are required: PATH".
    3. The code does not test against TDMS file contains multiple groups, scaled data, and
       non-waveform data.

Author: James Chang <twmr7@outlook.com>
Date: 2020-07-08
"""
import sys
import numpy as np
from nptdms import TdmsFile
from pathlib import Path
from datetime import datetime

def print_metainfo(input_file, output_file=sys.stdout):
    """output TDMS meta info

    [Parameters]:
        input_file - str or path object, the path to a TDMS file
        output_file - file, the target file object to output info
    """
    # concatenate all the information in a string
    strinfo = '>>> TDMS file "{}" info：\n'.format(input_file)
    with TdmsFile.open(input_file) as tdms_file:
        strinfo += '  - root name: {}\n'.format(tdms_file.properties['name'])
        all_group = tdms_file.groups()
        for m, group in enumerate(all_group):
            strinfo += '\tGroup #{}: {}\n'.format(m+1, group.path)
            all_channels = group.channels()
            for n, channel in enumerate(all_channels):
                strinfo += '\t  - Channel #{}: {}\n'.format(n+1, channel.path)
                strinfo += '\t\tdate_type: {}\n'.format(channel.data_type.__name__)
                #strinfo += '\t\tlength: {}\n'.format(channel.number_values)
                strinfo += '\t\tlength: {}\n'.format(len(channel))
                for name, value in channel.properties.items():
                    strinfo += '\t\t{}: {}\n'.format(name, value)
                strinfo += '\n'

    # ouput info to a file
    result_code = 0
    try:
        print(strinfo, file=output_file)
    except:
        print("[Error]: Unexpected error to output meta info.\n{}".format(sys.exc_info()[0]), file=sys.stderr)
        result_code = -2
    
    return result_code

def write_meta2file(input_file):
    """save TDMS meta info to a file, the info file is saved under the same folder
    of the input_file with suffix extension name changed to '.info'.

    [Parameters]:
        input_file - str or path object, the path to a TDMS file
    """
    output_filename = Path(input_file).with_suffix('.info')
    result_code = 0
    with open(output_filename, 'w', encoding='utf-8') as fout:
        result_code = print_metainfo(input_file, fout)
    return result_code

def read_tdms2array(input_file, channel_selection=[], time_track=False):
    """read data from TDMS file to numpy ndarray.

    [Parameters]:
        input_file - str or path object, the path to a TDMS file
        channel_selection - list, index of channel to select as output, empty equals select all
        time_track - bool, prepend time track column if this info is available
    
    [Returns]:
        data_array - np.ndarray, the channel data
        meta_list - list of dict, meta information about the recording of each channel
    """
    meta_list = list()
    data_array = np.array([])
    with TdmsFile.open(input_file) as tdms_file:
        group0 = tdms_file.groups()[0]
        all_channels = group0.channels()
        # prepare the list of indexes of selected channels
        if channel_selection == None or len(channel_selection) == 0:
            channel_selection = list(range(len(all_channels)))
        # decide the shape of output array from the first channel
        n_row = len(all_channels[0])
        with_timetrack = time_track and 'wf_increment' in all_channels[0].properties.keys()
        n_col = len(channel_selection)+1 if with_timetrack else len(channel_selection)
        data_array = np.empty((n_row, n_col), dtype=all_channels[0].dtype)
        # assign actual channel values
        offset = 0
        if with_timetrack:
            data_array[:, 0] = all_channels[0].time_track()
            meta_list.append({'name': 'time'})
            offset = 1
        for n, index in enumerate(channel_selection):
            channel = all_channels[index]
            data_array[:, n+offset] = channel[:]
            meta_info = dict()
            meta_info['name'] = channel.name
            meta_info['unit'] = channel.properties['unit_string']
            # extract waveform information 
            if 'wf_samples' in channel.properties.keys():
                str_rec_time = np.datetime_as_string(channel.properties['wf_start_time'], timezone='local')
                meta_info['wf_start_time'] = datetime.strptime(str_rec_time, '%Y-%m-%dT%H:%M:%S.%f%z')
                meta_info['wf_start_offset'] = channel.properties['wf_start_offset']
                meta_info['wf_increment'] = channel.properties['wf_increment']
            meta_list.append(meta_info)
    return data_array, meta_list

def prepare_names(input_file, meta_info, channel_names=[], split_file=False, extension='npy'):
    """gather info and generate proper names for channels and output file.

    [Parameters]:
        input_file - str or path object, the path to a TDMS file
        meta_info - list of dict, meta info from TDMS file
        channel_names - list of str, customized names from user input
        split_file - bool, one file for each channel
        extension - str, the file extension name is also the format code
    
    [Returns]:
        new_filename - str or list, depends on split file or not
        new_chnames - list, new channel names
    """
    assert(type(channel_names) is list)
    new_chnames = channel_names.copy()
    # user may not provide custom names
    if len(new_chnames) == 0:
        new_chnames = [str()] * len(meta_info)
    # user may provide insufficient names
    elif len(new_chnames) < len(meta_info):
        new_chnames += [str()] * (len(meta_info) - len(new_chnames))
    # user may provide too many names
    elif len(new_chnames) > len(meta_info):
        del new_chnames[len(meta_info):]
    # fill names from meta info if it is empty
    for n, meta in enumerate(meta_info):
        if new_chnames[n] == str():
            new_chnames[n] = meta['name'].split('/')[-1]

    # index to the first channel
    idxch1 = 1 if meta_info[0]['name'] == 'time' else 0
    # assumed the 1st channel has recording start time info
    rectime_base = meta_info[idxch1]['wf_start_time'].strftime('%Y%m%d-%H%M%S')
    # base name for output file, with parent path, without suffix extension
    file_base = str(Path(input_file).parent.joinpath(Path(input_file).stem))
    if split_file:
        new_filename = [str()] * len(meta_info)
        for n, meta in enumerate(meta_info):
            rectime = meta['wf_start_time'].strftime('%Y%m%d-%H%M%S') if 'wf_start_time' in meta.keys() else rectime_base
            new_filename[n] = '{}-{}-{}.{}'.format(file_base, rectime, new_chnames[n], extension)
    else:
        # append datetime and suffix extension
        new_filename = '{}-{}.{}'.format(file_base, rectime_base, extension)

    return new_filename, new_chnames

def save_array2npy(array, output_name, channel_names=[], dozip=False):
    """save array to npy, or npz if zip is true. 

    [Parameters]:
        array - ndarray, channel data
        output_name - str or list, the output file name
        channel_names - list of str, channel/title/column names
        dozip - bool, apply compression if supported
    """
    # basic key validation
    channel_name_valid = type(channel_names) is list and len(channel_names) == array.shape[1]
    if type(output_name) is list:
        # split channels to multiple files
        for n, fname in enumerate(output_name):
            if dozip:
                fname = Path(fname).with_suffix('.npz')
                if channel_name_valid:
                    np.savez(fname, **{channel_names[n]: array[:,n]})
                else:
                    np.savez(fname, array[:,n])
            else:
                np.save(fname, array[:,n])
    else:
        if dozip:
            output_name = Path(output_name).with_suffix('.npz')
            if channel_name_valid:
                datadict = {channel_names[n]: array[:,n] for n in range(array.shape[1])}
                np.savez(output_name, **datadict)
            else:
                np.savez(output_name, array)
        else:
            np.save(output_name, array)

def save_array2mat(array, output_name, channel_names=[], dozip=False):
    """save array to Matlab MAT file format

    [Parameters]:
        array - ndarray, channel data
        output_name - str or list, the output file name
        channel_names - list of str, channel/title/column names
        dozip - bool, apply compression if supported
    """
    import scipy.io as sio
    # basic key validation
    assert(type(channel_names) is list and len(channel_names) == array.shape[1])
    if type(output_name) is list:
        # split channels to multiple files
        assert(len(output_name) == array.shape[1])
        for n, (fname, chname) in enumerate(zip(output_name, channel_names)):
            sio.savemat(fname, mdict={chname:array[:,n]}, do_compression=dozip)
    else:
        datadict = {channel_names[n]: array[:,n] for n in range(array.shape[1])}
        sio.savemat(output_name, mdict=datadict, do_compression=dozip)

def save_array2csv(array, output_name, channel_names=[], delimiter=' '):
    """save array to CSV file format

    [Parameters]:
        array - ndarray, channel data
        output_name - str or list, the output file name
        channel_names - list of str, channel/title/column names
    """
    # basic key validation
    channel_name_valid = type(channel_names) is list and len(channel_names) == array.shape[1]
    if type(output_name) is list:
        # split channels to multiple files
        for n, fname in enumerate(output_name):
            if channel_name_valid:
                np.savetxt(fname, array[:,n], delimiter=delimiter,
                           header=channel_names[n], comments='', encoding='utf-8')
            else:
                np.savetxt(fname, array[:,n], delimiter=delimiter, encoding='utf-8')
    else:
        np.savetxt(output_name, array, delimiter=delimiter,
                   header=delimiter.join(channel_names), comments='', encoding='utf-8')

def write_array2file(array, output_name, channel_names=[], dozip=False):
    """export and write numpy array to specific file format.

    [Parameters]:
        array - ndarray, channel data
        output_name - str or list, the output file name
        channel_names - list of str, channel/title/column names
        dozip - bool, apply compression if supported
    """
    # save in a single file or split into multiple files
    if type(output_name) is list:
        output_format = Path(output_name[0]).suffix
    else:
        output_format = Path(output_name).suffix

    if output_format == '.npy':
        save_array2npy(array, output_name, channel_names, dozip) 
    elif output_format == '.mat':
        save_array2mat(array, output_name, channel_names, dozip) 
    elif output_format == '.csv':
        save_array2csv(array, output_name, channel_names) 
    else:
        print('Target format {} not supported.'.format(output_format), file=sys.stderr)

# -----------------------------------------------------------------------------
# __name__ == "__main__"
#   the execution entry point only when this script is executed with:
#   (1) "python tdms2x.py" or "python -m tdms2x.py" from a console, or
#   (2) "%run tdms2x.py" from an interactive jupyter console/notebook,
#   but not when it is imported.
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import time

    # setup options
    parser = argparse.ArgumentParser(prog='tdms2x', description='''
        *tdms2x* convert NI TDMS file to various other scientific data formats.
        ''')
    parser.add_argument('-v','--version', action='version', version='%(prog)s 2020-07-08',
                        help='display version number and exit.')
    parser.add_argument('-d','--display_only', action='store_true',
                        help='display file meta info to console and exit, no any file is saved.')
    parser.add_argument('input_path', metavar='PATH', type=str,
                        help='path to a TDMS file or a folder contains plenty of it.')
    parser.add_argument('-m','--meta_save2file', action='store_true',
                        help='also save meta file to a .info file.')
    parser.add_argument('-c','--channel_selection', nargs='+', type=int, metavar=('0','1'),
                        help='''Option to output only those channels with index specified in the list.
                        Zero is the index to the first channel, and default is all selected.''')
    parser.add_argument('-t','--time_track', action='store_true',
                        help='the output shall contain an additional time track column if available.')
    parser.add_argument('-z','--zip_compression', action='store_true',
                        help='compress the output file if the output format supports this option.')
    parser.add_argument('-s','--split_file', action='store_true',
                        help='Split channels to save as separate files.')
    parser.add_argument('-n','--name_channel', nargs='+', type=str, metavar=('x','y'),
                        help='''Option to specify header names in the order of selected channels.
                        Default is to use the name from TDMS meta info. If option -t is specified,
                        the first name in the list is the name for time track. For those file formats
                        without annotation property, e.g. npy, channel names are silently ignored.''')
    parser.add_argument('-o','--output_format', type=str, choices=['npy','mat','csv'], default='npy',
                        help='''Select an output type from currently implemented formats. Default is
                        to use "npy" format if this option is not specified.''')

    # parse command line arguments
    args = parser.parse_args()

    # collecting and validating options
    if not Path(args.input_path).exists():
        sys.exit('[Error]: path {} does not exist.'.format(args.input_path))

    if Path(args.input_path).is_dir():
        tdms_files = [str(file) for file in Path(args.input_path).glob('**/*.tdms')]
        if len(tdms_files) == 0:
            sys.exit('[Error]: no .tdms file is found in {}.'.format(args.input_path))
    elif Path(args.input_path).is_file():
        if Path(args.input_path).suffix == '.tdms':
            tdms_files = [args.input_path]
        else:
            sys.exit('[Error]: file {} is not a TDMS file.'.format(args.input_path))
    else:
        sys.exit('[Error]: path {} is not a file or folder.'.format(args.input_path))

    result_code = 0
    # iterating over all files
    for n, input_file in enumerate(tdms_files):
        if args.display_only:
            # display TDMS meta file info
            result_code += print_metainfo(input_file)
        else:
            print(' -- #{} file {}, start processing.'.format(n+1, input_file), flush=True)
            t_start = time.time()
            # save the meta info if asked to do so
            if args.meta_save2file:
                result_code += write_meta2file(input_file)
                if result_code != 0:
                    print('Something is wrong while saving meta info, abort further processing.', file=sys.stderr)
                    break
            # read data out of TDMS file as numpy array
            data, meta = read_tdms2array(input_file, args.channel_selection, args.time_track)
            # get proper output filename and header names
            channel_names = list() if args.name_channel is None else args.name_channel
            file_name, channel_names = prepare_names(input_file, meta, channel_names, args.split_file, args.output_format)
            write_array2file(data, file_name, channel_names, args.zip_compression)
            print(' -- #{} file processing time {}sec.\n'.format(n+1, time.time() - t_start))

    # end of the main application
    sys.exit(result_code)