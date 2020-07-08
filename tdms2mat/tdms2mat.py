"""
    *tdms2mat* - utility to convert NI TDMS file to Matlab MAT file.

操作範例：
    * 用命令列參數 '-h' 或 '--help' 查看參數使用說明：
        $ python tdms2mat.py --help

    * 在 ipython 或 jupyter console 下查看說明：
        [1] %run tdms2mat.py -h

    * 檢視指定TDMS檔案的描述資訊：
        $ python tdms2mat.py -l dev2/dev2_1.tdms

    * 將指定的TDMS檔案轉成MAT，其他參數全部使用預設值：
        $ python tdms2mat.py dev2/dev2_1.tdms

    * 使用預設參數將指定的TDMS檔案轉成MAT，同時一併儲存TDMS檔案描述資訊：
        $ python tdms2mat.py -i dev2/dev2_1.tdms

    * 將指定的TDMS檔案轉成MAT，使用壓縮格式，一併儲存描述資訊及取樣時間欄位：
        $ python tdms2mat.py -itz dev2/dev2_1.tdms

    * 將 "dev2" 目錄下所有的TDMS檔案轉成MAT，其他參數全部使用預設值：
        $ python tdms2mat.py dev2

    * 將 "dev2" 目錄下所有的TDMS檔案轉成MAT，檔案存到 "mat" 目錄，全部使用壓縮格式儲存：
        $ python tdms2mat.py -zo mat dev2

    * 將 "dev2" 目錄下所有的TDMS波形訊號檔案轉成MAT，前置檔名"mt5acc"：
        $ python tdms2mat.py -f mt5acc dev2

    * 將 "dev2" 目錄下所有的TDMS波形訊號檔案轉成MAT，自行指定通道欄位名稱 [fx, fy, gx, gy]：
        $ python tdms2mat.py -c fx fy gx gy dev2

注意事項：
    * 目前版本只處理一個 group 的 channel 資料，並假定都是 unscaled。
    * 所有通道的訊號都儲存在同一個 MAT 檔，目前假定最多不會超過四個通道。
    * 不使用預設名稱，要自行指定通道名稱時，即使實際上沒有四個通道，請還是指定四個通道的名稱清單，
      輸出檔案時只會按照順序套用到有資料的通道欄位名稱。
    * 假如記錄的是波形訊號，可以選擇一併儲存每個 sample 對應記錄開始的相對遞增時間欄位，欄位名稱
      固定為 "t"。
    * 假如記錄的是波形訊號，輸出的檔名的尾碼會自動加上對應的TDMS開始記錄的日期時間。
    * 若儲存壓縮格式的MAT檔，檔案大小可以縮小近一半，檔案寫入時間較長，讀取速度則影響較小。
    * 一次轉檔目錄下的多個檔案時，使用輸出檔名的前置碼加上日期時間尾碼的命名方式，只有很小的機率、
      但還是有可能會碰到剛好相同的檔名，請自行檢查應有的輸出檔案數量，確認沒有發生覆蓋相同檔名發生。

Author: James Chang <twmr7@outlook.com>
Date: 2020-05-20

"""
from pathlib import Path
from nptdms import TdmsFile
from datetime import datetime
import numpy as np
import scipy.io as sio

def list_tdmsinfo(input_file, output_file=None, no_display=False):
    """印出TDMS檔案的描述資訊，選擇性僅儲存、僅顯示、或同時儲存及顯示。

    [參數]：
        input_file - str, TDMS檔案的路徑字串。
        output_file - str, 輸出.info檔案的路徑字串，空字串或None則僅顯示。
        no_display - bool, 有儲存檔案時是否仍顯示到標準輸出。
    
    [Note]:
        nptdms comes with a utility tool "tdmsinfo.exe" to list the
        TDMS file info. The following code shows how to call this
        tool to get the job done.
        ```
            import subprocess
            proc_done = subprocess.run(['tdmsinfo', '-p', file],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
            print(proc_done.stdout.decode('utf-8'))
            return proc_done.returncode
        ```
        To traverse over all groups and channels is quite simple, though.
        No need to depends on external tool to get this job done.
    """
    # 將要輸出的訊息字串串接起來
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
                strinfo += '\t\tlength: {}\n'.format(channel.number_values)
                for name, value in channel.properties.items():
                    strinfo += '\t\t{}: {}\n'.format(name, value)
                strinfo += '\n'
    # 決定輸出的目標檔案
    if output_file != None and output_file != '':
        output_file += '.info'
        with open(output_file, 'w', encoding='utf-8') as fout:
            fout.write(strinfo)
        if not no_display:
            print(strinfo)
    else:
        print(strinfo)
    return 0

def convert_to_mat(input_file,
                   output_dir,
                   output_file,
                   channel_name,
                   info_save2file=False,
                   include_timetrack=False,
                   zip_compression=False):
    """將TDMS檔第一個 group 的 channel 資料轉存成 MAT 檔案

    [參數]：
        input_file - str, TDMS 檔案的路徑字串。
        output_dir - str, 輸出轉檔的目錄。
        output_file - str, 指定輸出檔案的前置名稱。
        channel_name - str list, 四個通道的名稱。
        info_save2file - bool, 一併儲存TDMS檔案描述資訊。
        include_timetrack - bool, 一併儲存取樣相對遞增時間欄位。
        zip_compression - bool, 使用壓縮格式儲存。
    """
    print('>>> 輸入TDMS檔案：', input_file)
    returncode = -1
    # 檢查輸出目錄
    if Path(output_dir).exists():
        print('  - 輸出至現有資料夾', output_dir)
    else:
        Path(output_dir).mkdir(parents=True)
        print('  - 輸出至新資料夾', output_dir)
    # 組合輸出路徑及檔名前置名稱
    if output_file == None or output_file == '':
        # 使用指定的輸出目錄 + 輸入檔名（無副檔名）
        output_file = Path(output_dir).joinpath(Path(input_file).stem)
    else:
        # 使用指定的輸出目錄 + 指定的輸出檔名（無副檔名）
        output_file = Path(output_dir).joinpath(output_file)

    with TdmsFile.open(input_file) as tdms_file:
        group0 = tdms_file.groups()[0]
        all_channels = group0.channels()

        # 擷取波形訊號資訊
        if 'wf_samples' in all_channels[0].properties.keys():
            print('  - 通道資料包含波形訊號：')
            str_rec_time = np.datetime_as_string(all_channels[0].properties['wf_start_time'], timezone='local')
            rec_time = datetime.strptime(str_rec_time, '%Y-%m-%dT%H:%M:%S.%f%z')
            print('\t開始記錄時間：', str(rec_time))
            print('\t初始時間偏移：', all_channels[0].properties['wf_start_offset'])
            print('\t取樣時間間隔：', all_channels[0].properties['wf_increment'])

        # 將資料與對應的名稱組織成寫入 MAT 所需的 dict
        dict_channels = dict()
        print('  - 指定通道名稱與資料封裝：')
        if include_timetrack and 'wf_increment' in all_channels[0].properties.keys():
            print('\t取樣遞增時間欄位名稱 = "t"')
            dict_channels['t'] = all_channels[0].time_track()
        for n,channel in enumerate(all_channels):
            print('\t通道 #{} 名稱 = "{}", 長度 = {}，單位 = {}'.format(n,
            channel_name[n], channel.number_values, channel.properties['unit_string']))
            # 通道名稱為 key，通道資料為 value
            dict_channels[channel_name[n]] = channel[:]
            # 處理最多不超過通道名稱有定義的數量
            if n+1 >= len(channel_name):
                break

        # 準備輸出檔名的字串
        output_name = str(output_file)
        if 'wf_start_time' in all_channels[0].properties.keys():
            output_name = '{}-{}'.format(output_name, rec_time.strftime('%Y%m%d-%H%M%S'))
        print('  - 儲存至 MAT 檔： {}.mat, {}壓縮\n'.format(output_name, '有' if zip_compression else '無'))
        sio.savemat(file_name=output_name+'.mat',
                    mdict=dict_channels,
                    do_compression=zip_compression)
        returncode = 0

    if info_save2file:
        returncode = list_tdmsinfo(input_file, output_name, no_display=True)

    return returncode

# -----------------------------------------------------------------------------
# __name__ == "__main__" 是主程式進入點
#   只有在 console 執行 "python tdms2mat.py"，
#   或是在 ipython 執行 "%run tdms2mat.py"，
#   才會執行這個主程式區段，用 import 的不會執行這個區段。
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import argparse
    import time

    # 設置可接受的命令列參數
    parser = argparse.ArgumentParser(prog='tdms2mat', description='''
        *tdms2mat* 將 NI TDMS 檔案的數據轉換為 Matlab MAT 格式檔案。
        ''')
    parser.add_argument('-v','--version', action='version', version='%(prog)s 2020-05-20',
                        help='顯示程式版本並離開。')
    parser.add_argument('input_path', metavar='PATH', type=str,
                        help='輸入TDMS檔案或目錄的路徑。')
    parser.add_argument('-l','--list_fileinfo', action='store_true',
                        help='不轉檔，僅列出TDMS檔案的描述資訊。')
    parser.add_argument('-i','--info_save2file', action='store_true',
                        help='一併將TDMS檔案的描述資訊儲存到另外的檔案（.info）。')
    parser.add_argument('-t','--time_track', action='store_true',
                        help='一併儲存取樣的相對遞增時間欄位。')
    parser.add_argument('-z','--zip_compression', action='store_true',
                        help='使用壓縮格式儲存。')
    parser.add_argument('-o','--output_dir', metavar='DIR', type=str, default='./export',
                        help='指定輸出MAT檔案的儲存目錄，預設輸出至"./export"目錄。')
    parser.add_argument('-f','--file_name', metavar='NAME', type=str,
                        help='指定輸出的MAT檔案前置名稱，後置名稱會自動加上記錄起始的日期和時間。')
    parser.add_argument('-c','--channel_name', nargs=4, metavar=('X','Y','Z','W'),
                        type=str, default=['x','y','z','w'],
                        help='''依序指定四個通道的欄位名稱，預設為 ["x","y","z","w"]，
                        避免使用保留給時間的欄位名稱"t"。''')

    # 解譯命令列參數
    args = parser.parse_args()

    # 基本參數需求檢查
    if not Path(args.input_path).exists():
        sys.exit('[錯誤]：指定的輸入路徑 {} 不存在!'.format(args.input_path))
    if (not args.list_fileinfo) and \
       (Path(args.output_dir).exists() and \
       (not Path(args.output_dir).is_dir())):
        sys.exit('[錯誤]：指定的輸出路徑 {} 已存在而且不是目錄!'.format(args.output_dir))

    # 收集要處理的TDMS檔案清單，並進一步檢查
    if Path(args.input_path).is_dir():
        tdms_files = [str(file) for file in Path(args.input_path).glob('**/*.tdms')]
        if len(tdms_files) == 0:
            sys.exit('[錯誤]：指定的目錄 {} 不存在TDMS檔案!'.format(args.input_path))
    elif Path(args.input_path).is_file():
        if Path(args.input_path).suffix == '.tdms':
            tdms_files = [args.input_path]
        else:
            sys.exit('[錯誤]：指定的輸入 {} 不是TDMS檔案!'.format(args.input_path))
    else:
        # 不是目錄也不是檔案，不確定指定的路徑是否可以處理
        sys.exit('[錯誤]：指定路徑 {} 不是目錄或檔案，不進行處理!'.format(args.input_path))

    result_code = 0
    # 處理所有的檔案
    for n, input_file in enumerate(tdms_files):
        t_start = time.time()
        if args.list_fileinfo == True:
            # 顯示TDMS檔案的描述資訊
            result_code = list_tdmsinfo(input_file)
        else:
            # 轉檔並儲存至指定目錄
            result_code = convert_to_mat(input_file,
                                        args.output_dir,
                                        args.file_name,
                                        args.channel_name,
                                        args.info_save2file,
                                        args.time_track,
                                        args.zip_compression)
        print(' -- 檔案#{}輸出完成，耗時{}秒。\n'.format(n+1, time.time() - t_start))

    # end of the main application
    sys.exit(result_code)