# Data to be excluded

## Unwanted SubNo
1, 15, 17

## How to exclude these data
use `raw = raw[raw['SubNo'] != 15]` to exclude data. This is helpful for subsequent debugging, just use the pass comment to control whether to include this data or not