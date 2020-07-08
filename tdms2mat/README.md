# tdms2mat

*tdms2mat.py* 是用來將儲存成 National Instruments (NI) [Technical Data Management Streaming (TDMS)](https://www.ni.com/en-us/support/documentation/supplemental/06/the-ni-tdms-file-format.html) 檔案格式的數據資料轉換成 Matlab MAT 檔案格式的 Python script 程式。

## 執行條件及必要模組
- python 3 (在 3.7 版開發測試)
- [nptdms](https://github.com/adamreeve/npTDMS) （在 0.26.0 版開發測試）
- numpy (在 1.18 版開發測試)
- scipy (在 1.4 版開發測試)

## 使用說明

在 console 下切換到此 script 檔的所在目錄下，執行 `python tdms2mat.py` 的指令，後面接命令列參數。若是使用 *ipython* 或 *jupyter console*，則可以輸入 `%run tdms2mat.py` 的 magic 指令，後面接命令列參數。。

例如：
```
$ python tdms2mat.py -h
```

會輸出如下的說明訊息。
```
usage: tdms2mat [-h] [-v] [-l] [-i] [-t] [-z] [-o DIR] [-f NAME] [-c X Y Z W]
                PATH

*tdms2mat* 將 NI TDMS 檔案的數據轉換為 Matlab MAT 格式檔案。

positional arguments:
  PATH                  輸入TDMS檔案或目錄的路徑。

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         顯示程式版本並離開。
  -l, --list_fileinfo   不轉檔，僅列出TDMS檔案的描述資訊。
  -i, --info_save2file  一併將TDMS檔案的描述資訊儲存到另外的檔案（.info）。
  -t, --time_track      一併儲存取樣的相對遞增時間欄位。
  -z, --zip_compression
                        使用壓縮格式儲存。
  -o DIR, --output_dir DIR
                        指定輸出MAT檔案的儲存目錄，預設輸出至"./export"目錄。
  -f NAME, --file_name NAME
                        指定輸出的MAT檔案前置名稱，後置名稱會自動加上記錄起始的日期和時間。
  -c X Y Z W, --channel_name X Y Z W
                        依序指定四個通道的欄位名稱，預設為 ["x","y","z","w"]，
                        避免使用保留給時間的欄位名稱"t"。
```

## 操作範例

假設與 tdms2mat.py 同目錄下有一個 "dev2" 的目錄，裡面儲存了 "dev2_1.tdms" 的 TDMS 檔案。

- 檢視指定TDMS檔案的描述資訊：
```
  $ python tdms2mat.py -l dev2/dev2_1.tdms
```
- 將指定的TDMS檔案轉成MAT，其他參數全部使用預設值：
```
  $ python tdms2mat.py dev2/dev2_1.tdms
```
- 使用預設參數將指定的TDMS檔案轉成MAT，同時一併儲存TDMS檔案的描述資訊：
```
  $ python tdms2mat.py -i dev2/dev2_1.tdms
```
- 將指定的TDMS檔案轉成MAT，使用壓縮格式，一併儲存描述資訊及取樣時間欄位：
```
  $ python tdms2mat.py -itz dev2/dev2_1.tdms
```
- 將 "dev2" 目錄下所有的TDMS檔案轉成MAT，其他參數全部使用預設值：
```
  $ python tdms2mat.py dev2
```
- 將 "dev2" 目錄下所有的TDMS檔案轉成MAT，檔案存到 "mat" 目錄，全部使用壓縮格式儲存：
```
  $ python tdms2mat.py -zo mat dev2
```
- 將 "dev2" 目錄下所有的TDMS波形訊號檔案轉成MAT，前置檔名"mt5acc"：
```
  $ python tdms2mat.py -f mt5acc dev2
```
- 將 "dev2" 目錄下所有的TDMS波形訊號檔案轉成MAT，自行指定通道欄位名稱 [fx, fy, gx, gy]：
```
  $ python tdms2mat.py -c fx fy gx gy dev2
```

## 注意事項

* 目前版本只處理一個 group 的 channel 資料，並假定都是 unscaled。
* 所有通道的訊號都儲存在同一個 MAT 檔，目前假定最多不會超過四個通道。
* 不使用預設名稱，要自行指定通道名稱時，即使實際上沒有四個通道，請還是指定四個通道的名稱清單，
  輸出檔案時只會按照順序套用到有資料的通道欄位名稱。
* 假如記錄的是波形訊號，可以選擇一併儲存每個 sample 對應記錄開始的相對遞增時間欄位，欄位名稱
  固定為 "t"。
* 假如記錄的是波形訊號，輸出的檔名的尾碼會自動加上對應的TDMS開始記錄的日期時間。
* 若儲存有壓縮的MAT檔，檔案大小可以縮小近一半，檔案寫入時間較長，讀取速度則影響較小。
* 一次轉檔目錄下的多個檔案時，使用輸出檔名的前置碼加上日期時間尾碼的命名方式，只有很小的機率、
  但還是有可能會碰到剛好相同的檔名，請自行檢查應有的輸出檔案數量，確認沒有發生覆蓋相同檔名發生。

---

James Chang < twmr7@outlook.com >