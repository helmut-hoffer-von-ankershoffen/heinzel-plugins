# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py    |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py    |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/\_presentation.py  |       87 |       11 |       36 |        6 |     83% |35-36, 44, 50, 61, 71, 79-82, 194 |
| src/heinzel\_plugin\_tools/audit.py           |       53 |        2 |       20 |        2 |     95% |   12, 144 |
| src/heinzel\_plugin\_tools/capture.py         |      896 |       64 |      404 |       59 |     90% |35, 85, 87-\>83, 146-\>145, 169, 174, 191, 198, 202, 209, 212, 219, 227, 235, 242, 245, 248, 264, 266, 270, 283, 285-287, 295, 308, 312-313, 371, 373, 443, 456, 546, 576-\>588, 579-582, 600-602, 603-\>exit, 682-683, 691, 788-789, 790-\>792, 835, 839, 847, 872, 918, 988, 1181, 1285, 1286-\>1246, 1354-1355, 1379-\>1378, 1455-\>1459, 1560, 1563, 1571, 1574, 1576, 1580, 1621, 1623, 1627, 1629, 1632-\>1637, 1658-\>1665, 1663, 1670 |
| src/heinzel\_plugin\_tools/capture\_host.py   |       85 |        6 |       38 |        7 |     89% |32-\>exit, 41, 53, 68, 72, 88, 109 |
| src/heinzel\_plugin\_tools/capture\_linux.py  |      295 |       19 |      112 |       15 |     91% |145-156, 206, 274, 318, 322, 334-\>315, 358, 409, 473, 489, 493-495, 500, 508, 522-\>524, 529, 532 |
| src/heinzel\_plugin\_tools/capture\_scene.py  |       31 |       18 |        8 |        1 |     36% | 28-45, 49 |
| src/heinzel\_plugin\_tools/capture\_worker.py |      104 |       15 |       52 |       15 |     81% |13, 33, 43, 50, 58, 61, 78, 91, 94, 105, 118, 123, 127, 149, 156 |
| src/heinzel\_plugin\_tools/cli.py             |      828 |       20 |      376 |       25 |     96% |38, 150-\>147, 390, 489-\>483, 591-\>593, 616-\>exit, 673, 679-\>681, 688, 691, 704, 733, 788, 1039, 1056, 1064, 1067-\>1071, 1216, 1218, 1304, 1306, 1465-\>1472, 1486-1487, 1507, 1509, 1551 |
| src/heinzel\_plugin\_tools/focused\_policy.py |      133 |       10 |       54 |        8 |     89% |291, 294, 309-310, 318, 320, 341, 366, 388-389 |
| src/heinzel\_plugin\_tools/installation.py    |      111 |        1 |       18 |        3 |     97% |56-\>58, 59, 125-\>119 |
| src/heinzel\_plugin\_tools/planning.py        |       23 |        0 |        4 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/privacy.py         |      137 |        6 |       48 |        4 |     95% |94, 109, 134, 137, 188-189 |
| src/heinzel\_plugin\_tools/publishing.py      |      305 |       14 |      160 |        7 |     94% |72-74, 130, 226, 279-\>283, 304, 425-\>429, 433-436, 451-454 |
| src/heinzel\_plugin\_tools/vendor.py          |      539 |       19 |      304 |       21 |     95% |178, 190, 197, 201, 204, 247, 251, 286, 299, 320, 360, 365, 515, 518, 539, 558, 585-\>587, 667-\>670, 682, 727, 858 |
| **TOTAL**                                     | **3629** |  **207** | **1634** |  **173** | **92%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fhelmut-hoffer-von-ankershoffen%2Fheinzel-plugins%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.