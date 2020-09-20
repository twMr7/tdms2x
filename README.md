# tdms2x

*tdms2x.py* is a Python utility scipt for exporting data stored in National Instruments (NI) [Technical Data Management Streaming (TDMS)](https://www.ni.com/en-us/support/documentation/supplemental/06/the-ni-tdms-file-format.html) format to various other scientific data formats.

This project was started as a TDMS to MAT converter for the students working on smart manufacturing projects in our lab. Since the choice of data format varies from project to project, it makes more sense to design the tool to output various different formats. The underlying TDMS format parsing relys on [nptdms](https://github.com/adamreeve/npTDMS) package, *tdms2x* implememts only frontend logics to *nptdms*.

The original *tdms2mat* script and description can be found in ["tdms2mat"](tdms2mat) folder. Note that all console messages are written in Chinese in this original script.

原始的 *tdms2mat* 程式可以在 ["tdms2mat"](tdms2mat) 目錄中找到，這個版本的說明及程式輸出訊息都是中文的。

## Prerequisites
- python 3 (tested on 3.7)
- nptdms (tested on 0.27.0)
- numpy (for data readout and exporting to .npy and .npz file format)
- scipy (for Matlab MAT file)

## Import as a Library

Besides working as a conversion utility script, *tdms2x.py* has simple I/O functions that intend to be able to work instantly with other preprocessing or analysis tasks. Following two lines of code should read you a numpy.ndarray from TDMS file right away.

```
import tdms2x as t2x
wfdata, _ = t2x.read_tdms2array('test_data/dev2_1.tdms')
```

Most of the functions should be easy to tell what it does from its name: `print_metainfo`, `write_meta2file`, `read_tdms2array`, `save_array2npy`, `save_array2mat`, `save_array2csv`, ..., and so on. Codes under `__name__ == "__main__"` block are good example to show how these functions are designed to work.

## Run as a Script

Under a normal console, enter `python tdms2x.py` followed by command-line options. For *ipython* or *jupyter* family, magic command `%run tdms2x.py` should work the same. For example, following line shows the command-line usages.
```
 $ python tdms2x.py -h
```

The usage message should look like this.
```
usage: tdms2x [-h] [-v] [-d] [-m] [-c 0 [1 ...]] [-t] [-z] [-s] [-n x [y ...]]
              [-o {npy,mat,wav,csv}] [-r Hz]
              PATH

*tdms2x* convert NI TDMS file to various other scientific data formats.

positional arguments:
  PATH                  Path to a TDMS file or a folder contains plenty of it.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Display version number and exit.
  -d, --display_info    Display meta info of the TDMS file to console, also
                        save to file if -m option is also specified.
  -m, --meta_save2file  Also save meta file to a .info file.
  -c 0 [1 ...], --channel_selection 0 [1 ...]
                        Option to output only those channels with index
                        specified in the list. Zero is the index to the first
                        channel, and default is all selected.
  -t, --time_track      The output shall contain an additional time track
                        column if available.
  -z, --zip_compression
                        Compress the output file if the output format supports
                        this option.
  -s, --split_file      Split channels to save as separate files.
  -n x [y ...], --name_channel x [y ...]
                        Option to specify header names in the order of
                        selected channels. Default is to use the name from
                        TDMS meta info. If option -t is specified, the first
                        name in the list is the name for time track. For those
                        file formats without annotation property, e.g. npy,
                        channel names are silently ignored.
  -o {npy,mat,wav,csv}, --output_format {npy,mat,wav,csv}
                        Select an output type from currently implemented
                        formats. Default is to use "npy" format if this option
                        is missing. For "wav" file format, the -r option shall
                        explicit specify and -s option is auto implied.
  -r Hz, --rate_sampling Hz
                        The sampling rate in Hz for .wav file format.
```

### Examples

All the following examples are tested with TDMS files in the ["test_data"](test_data) folder. Names for the target file are auto generated with the combination of source file name, recording datetime, and/or channel names. Converted files are written into the same folder of source TDMS files.

- Checking the content of a TDMS file by displaying its meta information.
```
 $ python tdms2x.py -d test_data/dev2_1.tdms
```

- Exporting channel data to a *.npy* file
```
 $ python tdms2x.py -o npy test_data/dev2_1.tdms
```

- Exporting channel data to a *.mat* file, and also saving the meta info of recording
```
 $ python tdms2x.py -mo mat test_data/dev2_1.tdms
```

- Batch converting all TDMS file in "test_data" folder to *.npz* file (compressed npy format)
```
 $ python tdms2x.py -zo npy test_data
```

- Exporting only the *1st*, *3rd*, and *4th* channels, split these channels and save to individual files. Note that default format is npy if "-o" option is ommited. Be sure to check for available channel numbers and provide only valid indexes. Otherwise, you may be prompted with the error message *"IndexError: list index out of range"*.
```
 $ python tdms2x.py -c 0 2 3 -s test_data/dev2_1.tdms
```

- Exporting all channel data and splitting to multiple *.mat* files with variable name stored with specified channel names "x, y, z, w, u".
```
 $ python tdms2x.py -n x y z w u -so mat test_data/dev2_1.tdms
```

### Notes
1. For options accept variable length of arguments, e.g. "**-c**" and "**-n**", these options should be followed by another option, or placed at the last of command-line. Avoid to place the required file **PATH** right after arguments of "**-c**" and "**-n**", it will be treated as if **PATH** is part of the sequence of these variable length arguments, and you should be prompt with error like *"error: the following arguments are required: PATH"*.
2. The code does not test against TDMS file contains multiple groups, scaled data, and non-waveform data.

---

James Chang < twmr7@outlook.com >